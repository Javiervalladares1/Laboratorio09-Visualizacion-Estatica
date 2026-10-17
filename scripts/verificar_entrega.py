"""Verifica datos y entregables; --solo-datos no requiere exportaciones."""
from pathlib import Path
from zipfile import BadZipFile, ZipFile
import argparse
import hashlib
import json
import sys
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader
from pypdf.errors import PdfReadError

ROOT = Path(__file__).resolve().parents[1]
MODELS = ['Prophet', 'Red neuronal MLP', 'SARIMA seleccionado',
          'Suavizamiento exponencial simple', 'Holt-Winters', 'Seasonal naive']


def require(condition, message):
    if not condition:
        raise ValueError(message)


def close(actual, expected, message, atol=1e-6):
    require(np.allclose(actual, expected, atol=atol, rtol=0, equal_nan=False), message)


def read_table(path, columns):
    frame = pd.read_csv(path)
    require(set(columns).issubset(frame.columns), f'{path.name}: faltan columnas {columns}.')
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors='raise')
        require(np.isfinite(frame[column]).all(), f'{path.name}: {column} contiene valores no finitos.')
    return frame


def monthly_table(path, columns, expected):
    frame = read_table(path, columns)
    require('Fecha' in frame.columns, f'{path.name}: falta Fecha.')
    frame['Fecha'] = pd.to_datetime(frame.Fecha, errors='raise')
    require(frame.Fecha.notna().all(), f'{path.name}: fechas vacías.')
    require(not frame.Fecha.duplicated().any(), f'{path.name}: fechas duplicadas.')
    frame = frame.set_index('Fecha').sort_index()
    require(frame.index.equals(expected), f'{path.name}: faltan o sobran meses en la cobertura esperada.')
    return frame


def validate_data(root=ROOT):
    root = Path(root)
    data = root / 'datos'
    expected = pd.date_range('2009-01-01', '2026-06-01', freq='MS', name='Fecha')
    series = monthly_table(data / 'serie_total_mensual.csv', ['Ingresos'], expected).Ingresos
    require((series >= 0).all(), 'La serie contiene ingresos negativos.')
    test_dates = expected[147:]
    pred = monthly_table(data / 'pronostico_prophet_intervalo95.csv',
                         ['Real', 'Estimacion_Prophet', 'Estimacion_reajuste', 'Inferior_95', 'Superior_95'], test_dates)
    old = monthly_table(data / 'predicciones_total_lab1.csv', ['Real'] + MODELS, test_dates)
    close(pred.Real, series.loc[test_dates], 'Observaciones desalineadas con la serie por Fecha.')
    close(old.Real, pred.Real, 'El observado del Lab 1 difiere del observado del intervalo.')
    close(pred.Estimacion_Prophet, old.Prophet, 'Cambió la predicción original de Prophet.', atol=1e-9)
    require((pred.Inferior_95 >= 0).all(), 'Límites inferiores negativos.')
    require(((pred.Inferior_95 <= pred.Estimacion_Prophet) &
             (pred.Estimacion_Prophet <= pred.Superior_95)).all(), 'Intervalos invertidos o sin su estimación.')
    delta = float(np.abs(pred.Estimacion_reajuste - old.Prophet).max())
    require(delta <= 1 and np.allclose(pred.Estimacion_reajuste, old.Prophet, rtol=1e-6, atol=.01),
            'El reajuste se aparta del pronóstico original por encima de la tolerancia.')

    models = read_table(data / 'modelos_total.csv', ['MAE', 'RMSE', 'n_prueba'])
    require('modelo' in models.columns and not models.modelo.duplicated().any(), 'Modelos duplicados o sin nombre.')
    require(set(models.modelo) == set(MODELS), 'La comparación no incluye exactamente los seis modelos del Lab 1.')
    require((models.n_prueba == len(test_dates)).all(), 'Los modelos usan diferentes períodos de prueba.')
    metrics = {}
    for row in models.itertuples():
        error = old.Real - old[row.modelo]
        mae, rmse = float(np.abs(error).mean()), float(np.sqrt((error ** 2).mean()))
        close([row.MAE, row.RMSE], [mae, rmse], f'Métricas inconsistentes: {row.modelo}.')
        metrics[row.modelo] = {'MAE': mae, 'RMSE': rmse}
    require(models.loc[models.RMSE.idxmin(), 'modelo'] == 'Prophet', 'El ganador ya no es Prophet; revisar la narrativa.')
    improvement = 100 * (1 - metrics['Prophet']['RMSE'] / metrics['Seasonal naive']['RMSE'])

    summary = json.loads((data / 'resumen_lab1.json').read_text(encoding='utf-8'))
    close(series.sum(), summary['total_comparable'], 'Acumulado diferente del resumen del Lab 1.')
    drop = 100 * (series.loc['2020'].sum() / series.loc['2019'].sum() - 1)
    close(drop, summary['caida_2020_vs_2019_pct'], 'Caída de 2020 diferente del resumen.')
    close([summary['meses'], summary['train_meses'], summary['test_meses']], [210, 147, 63], 'Cortes incorrectos en el resumen.')

    profile = read_table(data / 'perfil_mensual_2009_2019.csv', ['Mes', 'Promedio_ingresos'])
    require(not profile.Mes.duplicated().any() and set(profile.Mes) == set(range(1, 13)), 'Perfil mensual incompleto o duplicado.')
    pre = series.loc[:'2019-12-01']
    close(profile.set_index('Mes').sort_index().Promedio_ingresos,
          pre.groupby(pre.index.month).mean(), 'El perfil mensual no coincide con 2009-2019.')

    shares = read_table(data / 'participaciones.csv', ['Ingresos', 'Porcentaje'])
    require(not shares.duplicated(['Dimension', 'Categoria']).any(), 'Participaciones duplicadas.')
    require(set(shares.Dimension) == {'Vía', 'Región dos'}, 'Dimensiones inesperadas en las participaciones.')
    require((shares.Ingresos >= 0).all(), 'Participaciones negativas.')
    close(shares.Porcentaje, 100 * shares.Ingresos / series.sum(), 'Denominador incorrecto en participaciones.')
    for _, group in shares.groupby('Dimension'):
        close(group.Ingresos.sum(), series.sum(), 'Una dimensión no reconcilia con el total.')
    for category, field in [('Terrestre', 'participacion_terrestre_pct'),
                            ('América Del Centro', 'participacion_centroamerica_pct')]:
        close(shares.loc[shares.Categoria == category, 'Porcentaje'].item(), summary[field],
              f'Participación inconsistente: {category}.')

    evidence = read_table(data / 'evidencia_series.csv', ['fuerza_estacional_STL', 'fuerza_tendencia_STL',
                          'crecimiento_anual_pre2020_%', 'volatilidad_log_diff', 'impacto_2020_vs_2019_%'])
    require('serie' in evidence.columns, 'Falta la columna serie en la evidencia.')
    require(len(evidence) == 7 and not evidence.serie.duplicated().any(), 'La evidencia debe incluir siete series únicas.')
    for field in ['fuerza_estacional_STL', 'fuerza_tendencia_STL']:
        require(evidence[field].between(0, 1).all(), f'{field} fuera de la escala 0 a 1.')
    winners = pd.read_csv(data / 'ganadores_por_serie.csv')
    require(not winners.serie.duplicated().any() and set(winners.serie) == set(evidence.serie), 'Ganadores y evidencia no cubren las mismas series.')
    counts = {str(k): int(v) for k, v in winners.modelo.value_counts().items()}
    require(counts == {'Prophet': 5, 'SARIMA seleccionado': 2}, 'Cambió el reparto de ganadores; revisar la narrativa.')

    meta = json.loads((data / 'metadatos_intervalo.json').read_text(encoding='utf-8'))
    coverage = float(((pred.Real >= pred.Inferior_95) & (pred.Real <= pred.Superior_95)).mean())
    require(meta['intervalo_nominal'] == .95 and meta['modelo'] == 'Prophet', 'Nivel o modelo del intervalo incorrecto.')
    require(meta['entrenamiento_inicio'] == '2009-01' and meta['entrenamiento_fin'] == '2021-03'
            and meta['prueba_inicio'] == '2021-04' and meta['prueba_fin'] == '2026-06', 'Fechas incorrectas en los metadatos.')
    close([meta['n_train'], meta['n_test']], [147, 63], 'Tamaño incorrecto de los cortes del modelo.')
    close([meta['MAE'], meta['RMSE']], list(metrics['Prophet'].values()), 'Métricas de metadatos inconsistentes.')
    close(coverage, meta['cobertura_observada_intervalo_prueba'], 'Cobertura del intervalo inconsistente.')
    close(delta, meta['diferencia_maxima_puntual_lab1'], 'Diferencia del reajuste inconsistente.')
    return {'estado': 'correcto', 'meses_total': len(series), 'meses_prueba': len(pred),
            **metrics['Prophet'], 'modelos_verificados': metrics,
            'reduccion_RMSE_vs_referencia_pct': improvement,
            'cobertura_observada_intervalo_prueba': coverage,
            'insumos_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(data.iterdir()) if p.suffix in {'.csv', '.json'}}}


def validate_artifacts(root=ROOT):
    root = Path(root)
    out = root / 'salida'
    with Image.open(out / 'Infografia_Turismo_Guatemala.png') as im:
        im.verify()
    with Image.open(out / 'Infografia_Turismo_Guatemala.png') as im:
        pixels = [im.width, im.height]
        require(im.width >= 1200 and im.height >= 2400, 'PNG por debajo del mínimo de la guía.')
    pages = {}
    for name, expected in [('A3', (297 / 25.4, 420 / 25.4)), ('11x17', (11, 17))]:
        pdf = PdfReader(out / f'Infografia_Turismo_Guatemala_{name}.pdf')
        require(len(pdf.pages) == 1, f'{name}: se requiere exactamente una página.')
        size = [float(pdf.pages[0].mediabox.width) / 72, float(pdf.pages[0].mediabox.height) / 72]
        close(size, expected, f'{name}: tamaño de página incorrecto.', atol=1e-5)
        text = pdf.pages[0].extract_text()
        for phrase in ['Estimación', 'Intervalo nominal 95 %', 'Cinco decisiones para INGUAT', 'Fuente:', 'Créditos:']:
            require(phrase in text, f'{name}: falta texto requerido: {phrase}.')
        pages[name] = {'paginas': 1, 'pulgadas': size}
    svg = ET.parse(out / 'Infografia_Turismo_Guatemala_Editable.svg').getroot()
    require(bool(svg.findall('{http://www.w3.org/2000/svg}text')), 'El SVG no contiene texto editable.')
    with ZipFile(out / 'Infografia_Editable_Canva.zip') as archive:
        require(set(archive.namelist()) == {'index.html', 'graficos.png'}, 'Paquete editable incompleto.')
        require(archive.testzip() is None, 'Paquete editable corrupto.')
        for name in archive.namelist():
            require(archive.read(name) == (root / 'editable' / name).read_bytes(), f'ZIP desactualizado: {name}.')
    explanation = PdfReader(root / 'documento' / 'Explicacion_Diseno_Laboratorio09.pdf')
    require(len(explanation.pages) > 0, 'Falta el documento de explicación.')
    credits = json.loads((root / 'creditos.json').read_text(encoding='utf-8'))
    warnings = []
    if not credits.get('autores') or not str(credits.get('grupo', '')).strip():
        warnings.append('Completar autores y grupo confirmados en creditos.json antes de entregar.')
    warnings.append('La copia de Canva debe sincronizarse por separado tras regenerar los archivos locales.')
    return {'png_pixeles': pixels, 'pdf': pages, 'svg': 'XML válido con texto editable',
            'revision_visual': 'No evaluada por este script; requiere inspección de las exportaciones.',
            'advertencias': warnings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solo-datos', action='store_true', help='Validar insumos sin requerir PNG/PDF/SVG/ZIP.')
    args = parser.parse_args()
    try:
        result = validate_data()
        if not args.solo_datos:
            result.update(validate_artifacts())
    except (ValueError, OSError, KeyError, IndexError, ET.ParseError, BadZipFile, PdfReadError) as error:
        result = {'estado': 'error', 'detalle': str(error)}
    if not args.solo_datos:
        (ROOT / 'salida').mkdir(exist_ok=True)
        (ROOT / 'salida' / 'verificacion_entrega.json').write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result['estado'] == 'correcto' else 1


if __name__ == '__main__':
    sys.exit(main())
