"""Recupera el intervalo nominal del 95 % del ganador del total del Lab 1.

Mantiene el mismo entrenamiento, configuración, frecuencia y estacionalidad.
Contrasta la predicción puntual con el archivo original antes de exportar.
"""
from pathlib import Path
import json
import logging
import numpy as np
import pandas as pd
from prophet import Prophet
import prophet

HERE = Path(__file__).resolve().parents[1]
DATA = HERE/'datos'
logging.getLogger('cmdstanpy').setLevel(logging.WARNING)
series = pd.read_csv(DATA/'serie_total_mensual.csv', parse_dates=['Fecha']).set_index('Fecha').Ingresos
train = series.iloc[:147]
test = series.iloc[147:]
assert str(train.index[-1].date()) == '2021-03-01'
assert str(test.index[0].date()) == '2021-04-01' and len(test) == 63
model = Prophet(growth='linear', yearly_seasonality=False, weekly_seasonality=False,
    daily_seasonality=False, seasonality_mode='additive', changepoint_prior_scale=0.01,
    seasonality_prior_scale=10.0, interval_width=0.95, uncertainty_samples=2000)
model.add_seasonality(name='estacionalidad_anual_mensual',period=365.25,fourier_order=6,mode='additive')
print('Ajustando Prophet con los 147 meses originales de entrenamiento', flush=True)
model.fit(pd.DataFrame({'ds': train.index, 'y': train.values}))
np.random.seed(2026)
forecast = model.predict(pd.DataFrame({'ds':test.index}))
old = pd.read_csv(DATA/'predicciones_total_lab1.csv',parse_dates=['Fecha']).set_index('Fecha')
point = forecast.yhat.clip(lower=0).to_numpy()
max_delta = float(np.max(np.abs(point-old.loc[test.index,'Prophet'].to_numpy())))
print('Diferencia máxima con el pronóstico del Lab 1:',max_delta, flush=True)
if max_delta > .01:
    raise ValueError('El ajuste no reproduce el Lab 1 con tolerancia de 0,01 ingresos. Revisar versiones.')
out = pd.DataFrame({'Fecha':test.index,'Real':test.values,'Estimacion_Prophet':point,
    'Inferior_95':forecast.yhat_lower.clip(lower=0).values,
    'Superior_95':forecast.yhat_upper.clip(lower=0).values})
assert (out.Inferior_95 <= out.Superior_95).all()
out.to_csv(DATA/'pronostico_prophet_intervalo95.csv', index=False)
meta = {'modelo':'Prophet','version_prophet':prophet.__version__,'intervalo_nominal':.95,'seed_numpy':2026,
    'uncertainty_samples':2000,'entrenamiento_inicio':'2009-01','entrenamiento_fin':'2021-03',
    'prueba_inicio':'2021-04','prueba_fin':'2026-06','n_train':147,'n_test':63,
    'configuracion':{'seasonality_mode':'additive','changepoint_prior_scale':.01,'seasonality_prior_scale':10.,'fourier_order':6,'period':365.25},
    'diferencia_maxima_puntual_lab1':max_delta,
    'cobertura_observada_intervalo_prueba':float(((out.Real>=out.Inferior_95)&(out.Real<=out.Superior_95)).mean()),
    'MAE':float(np.abs(out.Real-point).mean()),'RMSE':float(np.sqrt(((out.Real-point)**2).mean())),
    'limites_no_negativos':True,'nota':'Intervalo predictivo nominal del modelo. No garantiza cobertura del 95 % en este corte. Prueba retrospectiva; no es una proyección posterior a junio de 2026.'}
(DATA/'metadatos_intervalo.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(meta,ensure_ascii=False,indent=2), flush=True)
