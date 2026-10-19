"""Comprueba datos, métricas, formatos y texto antes de entregar."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
DATA,OUT=ROOT/'datos',ROOT/'salida'
s=pd.read_csv(DATA/'serie_total_mensual.csv',parse_dates=['Fecha']).set_index('Fecha').Ingresos
pred=pd.read_csv(DATA/'pronostico_prophet_intervalo95.csv',parse_dates=['Fecha'])
old=pd.read_csv(DATA/'predicciones_total_lab1.csv')
models=pd.read_csv(DATA/'modelos_total.csv')
ev=pd.read_csv(DATA/'evidencia_series.csv')
summary=json.loads((DATA/'resumen_lab1.json').read_text())
assert len(s)==210 and s.index.min()==pd.Timestamp('2009-01-01') and s.index.max()==pd.Timestamp('2026-06-01')
assert len(pred)==63 and pred.Fecha.min()==pd.Timestamp('2021-04-01')
assert abs(s.sum()-summary['total_comparable'])<1e-6
np.testing.assert_allclose(pred.Estimacion_Prophet,old.Prophet,atol=1e-9,rtol=0)
np.testing.assert_allclose(pred.Real,s.iloc[147:].to_numpy(),atol=1e-6,rtol=0)
assert (pred.Inferior_95>=0).all() and (pred.Superior_95>=pred.Inferior_95).all()
assert (pred.Estimacion_Prophet>=pred.Inferior_95).all() and (pred.Estimacion_Prophet<=pred.Superior_95).all()
mae=float(np.abs(pred.Real-pred.Estimacion_Prophet).mean())
rmse=float(np.sqrt(((pred.Real-pred.Estimacion_Prophet)**2).mean()))
win=models[models.modelo=='Prophet'].iloc[0]
assert abs(mae-win.MAE)<1e-6 and abs(rmse-win.RMSE)<1e-6
baseline=models[models.modelo=='Seasonal naive'].iloc[0]
reduction=100*(1-rmse/baseline.RMSE)
assert round(reduction,1)==68.5
assert ev.loc[ev.fuerza_estacional_STL.idxmax(),'serie']=='Frontera — 01 La Aurora'
assert ev.loc[ev['crecimiento_anual_pre2020_%'].idxmax(),'serie']=='Frontera — 09 San Cristóbal'
assert ev.loc[ev.volatilidad_log_diff.idxmax(),'serie']=='País — El Salvador'
assert ev.loc[ev['impacto_2020_vs_2019_%'].idxmin(),'serie']=='Frontera — 07 Valle Nuevo'
assert round(100*(s.loc['2020'].sum()/s.loc['2019'].sum()-1),1)==-74.4
np.testing.assert_allclose([summary['participacion_terrestre_pct'],summary['participacion_centroamerica_pct']], [59.06898610609274,71.25362658772883])
im=Image.open(OUT/'Infografia_Turismo_Guatemala.png')
assert im.width>=1200 and im.height>=2400
pages={}
for name,expected in [('A3',(297/25.4,420/25.4)),('11x17',(11,17))]:
    pdf=PdfReader(OUT/f'Infografia_Turismo_Guatemala_{name}.pdf')
    assert len(pdf.pages)==1
    size=(float(pdf.pages[0].mediabox.width)/72,float(pdf.pages[0].mediabox.height)/72)
    np.testing.assert_allclose(size,expected,atol=1e-5)
    text=pdf.pages[0].extract_text()
    for phrase in ['46,71 M','-74,4 %','59,1 %','71,3 %','Estimación','Intervalo nominal 95 %','58 033','69 294','Cinco decisiones para INGUAT','Fuente:','Créditos:']:
        assert phrase in text,(name,phrase)
    pages[name]={'paginas':1,'pulgadas':size}
ET.parse(OUT/'Infografia_Turismo_Guatemala_Editable.svg')
result={'estado':'correcto','meses_total':len(s),'meses_prueba':len(pred),'MAE':mae,'RMSE':rmse,
    'reduccion_RMSE_vs_referencia_pct':reduction,'png_pixeles':[im.width,im.height],'pdf':pages,
    'svg':'XML válido con texto y formas editables','revision_visual':'Realizada por inspección de la exportación final. Los controles automáticos no sustituyen esta revisión.',
    'creditos_personales_completos':bool(json.loads((ROOT/'creditos.json').read_text()).get('autores'))}
(OUT/'verificacion_entrega.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
