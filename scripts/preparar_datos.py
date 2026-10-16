"""Extrae los insumos del Lab 1: python scripts/preparar_datos.py --lab1 RUTA."""
from pathlib import Path
from shutil import copyfile
import argparse
import hashlib
import json
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
FILES = ['base_migracion_limpia.csv', 'predicciones_modelos.csv',
         'comparacion_modelos.csv', 'comparativo_evidencia.csv',
         'ganadores_por_serie.csv', 'cobertura_series.csv']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lab1', type=Path, required=True,
                        help='Carpeta que contiene outputs/lab1_final del Laboratorio 1.')
    args = parser.parse_args()
    source = args.lab1.expanduser().resolve() / 'outputs/lab1_final'
    tables = source / 'tablas'
    missing = [str(tables / name) for name in FILES if not (tables / name).is_file()]
    if not (source / 'resumen_ejecutivo.json').is_file():
        missing.append(str(source / 'resumen_ejecutivo.json'))
    if missing:
        parser.error('No se modificaron los insumos. Faltan archivos:\n' + '\n'.join(missing))

    raw = pd.read_csv(tables / 'base_migracion_limpia.csv', parse_dates=['Fecha'])
    vis = raw[raw['Tipo de Viajero'].isin(['Turista', 'Excursionista'])].copy()
    monthly = vis.groupby('Fecha').Viajero.sum().rename('Ingresos')
    summary = json.loads((source / 'resumen_ejecutivo.json').read_text(encoding='utf-8'))
    if len(monthly) != 210 or abs(monthly.sum() - summary['total_comparable']) >= 1e-6:
        raise ValueError('La cobertura o el acumulado no coincide con el resumen del Lab 1.')
    drop = 100 * (monthly.loc['2020'].sum() / monthly.loc['2019'].sum() - 1)
    if abs(drop - summary['caida_2020_vs_2019_pct']) >= 1e-8:
        raise ValueError('La caída de 2020 no coincide con el resumen del Lab 1.')

    dest = HERE / 'datos'
    dest.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(dest / 'serie_total_mensual.csv', encoding='utf-8', index=True)
    pred = pd.read_csv(tables / 'predicciones_modelos.csv', parse_dates=['Fecha'])
    pred[pred.serie.str.startswith('Total')].to_csv(dest / 'predicciones_total_lab1.csv', index=False)
    models = pd.read_csv(tables / 'comparacion_modelos.csv')
    models[models.serie.str.startswith('Total')].sort_values('RMSE').to_csv(dest / 'modelos_total.csv', index=False)
    for source_name, target_name in [('comparativo_evidencia.csv', 'evidencia_series.csv'),
                                     ('ganadores_por_serie.csv', 'ganadores_por_serie.csv'),
                                     ('cobertura_series.csv', 'cobertura_series.csv')]:
        copyfile(tables / source_name, dest / target_name)
    (dest / 'resumen_lab1.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    pre = monthly.loc[:'2019-12-01']
    profile = pre.groupby(pre.index.month).mean().rename('Promedio_ingresos')
    profile.index.name = 'Mes'
    profile.to_csv(dest / 'perfil_mensual_2009_2019.csv')
    shares = []
    for col in ['Vía', 'Región dos']:
        for name, value in vis.groupby(col).Viajero.sum().items():
            shares.append({'Dimension': col, 'Categoria': name, 'Ingresos': value,
                           'Porcentaje': 100 * value / monthly.sum()})
    pd.DataFrame(shares).to_csv(dest / 'participaciones.csv', index=False)
    manifest = {name: hashlib.sha256((tables / name).read_bytes()).hexdigest() for name in FILES}
    provenance = {'fuentes': manifest, 'definicion': 'Turista + Excursionista',
                  'cobertura': '2009-01 a 2026-06', 'estatus': 'Uso académico. No son cifras oficiales.',
                  'derivacion_perfil': 'Promedio por mes calendario, 2009-2019'}
    (dest / 'procedencia.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Insumos verificados en {dest}', flush=True)


if __name__ == '__main__':
    main()
