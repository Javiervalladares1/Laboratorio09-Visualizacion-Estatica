"""Extrae los insumos de la infografía del Laboratorio 1 sin modificarlos."""
from pathlib import Path
from shutil import copyfile
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DEST = Path(__file__).resolve().parents[1] / 'datos'
DEST.mkdir(parents=True, exist_ok=True)
TABLES = ROOT / 'outputs/lab1_final/tablas'
raw = pd.read_csv(TABLES/'base_migracion_limpia.csv', parse_dates=['Fecha'])
vis = raw[raw['Tipo de Viajero'].isin(['Turista', 'Excursionista'])].copy()
monthly = vis.groupby('Fecha').Viajero.sum().rename('Ingresos')
monthly.to_csv(DEST/'serie_total_mensual.csv', encoding='utf-8', index=True)
summary = json.loads((ROOT/'outputs/lab1_final/resumen_ejecutivo.json').read_text())
assert len(monthly) == 210
assert abs(monthly.sum()-summary['total_comparable']) < 1e-6
assert abs(100*(monthly.loc['2020'].sum()/monthly.loc['2019'].sum()-1)-summary['caida_2020_vs_2019_pct']) < 1e-8
pred = pd.read_csv(TABLES/'predicciones_modelos.csv', parse_dates=['Fecha'])
pred = pred[pred.serie.str.startswith('Total')]
pred.to_csv(DEST/'predicciones_total_lab1.csv', encoding='utf-8', index=False)
models = pd.read_csv(TABLES/'comparacion_modelos.csv')
models[models.serie.str.startswith('Total')].sort_values('RMSE').to_csv(DEST/'modelos_total.csv', index=False)
copyfile(TABLES/'comparativo_evidencia.csv', DEST/'evidencia_series.csv')
copyfile(TABLES/'ganadores_por_serie.csv', DEST/'ganadores_por_serie.csv')
copyfile(TABLES/'cobertura_series.csv', DEST/'cobertura_series.csv')
(DEST/'resumen_lab1.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
pre = monthly.loc[:'2019-12-01']
profile = pre.groupby(pre.index.month).mean().rename('Promedio_ingresos')
profile.index.name = 'Mes'
profile.to_csv(DEST/'perfil_mensual_2009_2019.csv')
shares = []
for col in ['Vía', 'Región dos']:
    for name, value in vis.groupby(col).Viajero.sum().items():
        shares.append({'Dimension':col, 'Categoria':name, 'Ingresos':value, 'Porcentaje':100*value/monthly.sum()})
pd.DataFrame(shares).to_csv(DEST/'participaciones.csv', index=False)
files = ['base_migracion_limpia.csv','predicciones_modelos.csv','comparacion_modelos.csv','comparativo_evidencia.csv','ganadores_por_serie.csv','cobertura_series.csv']
manifest = {name: hashlib.sha256((TABLES/name).read_bytes()).hexdigest() for name in files}
(DEST/'procedencia.json').write_text(json.dumps({'fuentes':manifest,'definicion':'Turista + Excursionista','cobertura':'2009-01 a 2026-06','estatus':'Uso académico. No son cifras oficiales.','derivacion_perfil':'Promedio por mes calendario, 2009-2019'}, ensure_ascii=False, indent=2)+'\n')
print(f'Insumos verificados en {DEST}', flush=True)
