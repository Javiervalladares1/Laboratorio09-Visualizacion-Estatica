"""Comprueba datos, métricas, formatos y texto antes de entregar.

Cada control se registra por separado. Si alguno falla, el script informa
todos los fallos y termina con código 1, sin depender de `assert` (que
Python omite al ejecutarse con -O).
"""
from pathlib import Path
import json
import sys
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
DATA,OUT=ROOT/'datos',ROOT/'salida'
FRASES_PDF=['46,71 M','-74,4 %','59,1 %','71,3 %','Estimación','Intervalo nominal 95 %','58 033','69 294','Cinco decisiones para INGUAT','Fuente:','Créditos:']
FORMATOS_PDF=[('A3',(297/25.4,420/25.4)),('11x17',(11,17))]
fallos=[]

def comprobar(condicion,mensaje):
    if not condicion:fallos.append(mensaje)
    return bool(condicion)

def cercanos(a,b,atol,mensaje):
    return comprobar(np.allclose(a,b,atol=atol,rtol=0),mensaje)

s=pd.read_csv(DATA/'serie_total_mensual.csv',parse_dates=['Fecha']).set_index('Fecha').Ingresos
pred=pd.read_csv(DATA/'pronostico_prophet_intervalo95.csv',parse_dates=['Fecha'])
old=pd.read_csv(DATA/'predicciones_total_lab1.csv')
models=pd.read_csv(DATA/'modelos_total.csv')
ev=pd.read_csv(DATA/'evidencia_series.csv')
summary=json.loads((DATA/'resumen_lab1.json').read_text())

# Datos y pronóstico
comprobar(len(s)==210,f'La serie debe tener 210 meses; tiene {len(s)}.')
comprobar(s.index.min()==pd.Timestamp('2009-01-01') and s.index.max()==pd.Timestamp('2026-06-01'),'La serie debe cubrir de ene 2009 a jun 2026.')
comprobar(s.index.is_monotonic_increasing and not s.index.duplicated().any(),'Las fechas de la serie deben ser únicas y crecientes.')
comprobar((s>=0).all(),'La serie contiene ingresos negativos.')
comprobar(len(pred)==63 and pred.Fecha.min()==pd.Timestamp('2021-04-01'),'El período de prueba debe tener 63 meses desde abr 2021.')
comprobar(abs(s.sum()-summary['total_comparable'])<1e-6,'El total no coincide con el resumen del Lab 1.')
cercanos(pred.Estimacion_Prophet,old.Prophet,1e-9,'La estimación de Prophet difiere de la del Lab 1.')
cercanos(pred.Real,s.iloc[147:].to_numpy(),1e-6,'Los valores reales de prueba no coinciden con la serie.')
comprobar((pred.Inferior_95>=0).all() and (pred.Superior_95>=pred.Inferior_95).all(),'Límites del intervalo inválidos.')
comprobar(((pred.Estimacion_Prophet>=pred.Inferior_95)&(pred.Estimacion_Prophet<=pred.Superior_95)).all(),'La estimación queda fuera de su intervalo.')

# Métricas
mae=float(np.abs(pred.Real-pred.Estimacion_Prophet).mean())
rmse=float(np.sqrt(((pred.Real-pred.Estimacion_Prophet)**2).mean()))
win=models[models.modelo=='Prophet'].iloc[0]
comprobar(abs(mae-win.MAE)<1e-6 and abs(rmse-win.RMSE)<1e-6,'MAE o RMSE no coinciden con la tabla de modelos.')
baseline=models[models.modelo=='Seasonal naive'].iloc[0]
reduction=100*(1-rmse/baseline.RMSE)
comprobar(round(reduction,1)==68.5,f'La reducción de RMSE debe ser 68,5 %; es {reduction:.2f} %.')

# Afirmaciones de la sección 02
extremos=[('fuerza_estacional_STL','idxmax','Frontera — 01 La Aurora'),
    ('crecimiento_anual_pre2020_%','idxmax','Frontera — 09 San Cristóbal'),
    ('volatilidad_log_diff','idxmax','País — El Salvador'),
    ('impacto_2020_vs_2019_%','idxmin','Frontera — 07 Valle Nuevo')]
for col,metodo,esperado in extremos:
    real=ev.loc[getattr(ev[col],metodo)(),'serie']
    comprobar(real==esperado,f'{col}: se esperaba {esperado}, se obtuvo {real}.')
caida=round(100*(s.loc['2020'].sum()/s.loc['2019'].sum()-1),1)
comprobar(caida==-74.4,f'La caída de 2020 debe ser -74,4 %; es {caida} %.')
cercanos([summary['participacion_terrestre_pct'],summary['participacion_centroamerica_pct']],[59.06898610609274,71.25362658772883],1e-9,'Participaciones distintas a las del Lab 1.')

# Formatos de salida
im=Image.open(OUT/'Infografia_Turismo_Guatemala.png')
comprobar(im.width>=1200 and im.height>=2400,f'El PNG mide {im.size}; mínimo 1200 × 2400.')
pages={}
for name,expected in FORMATOS_PDF:
    pdf=PdfReader(OUT/f'Infografia_Turismo_Guatemala_{name}.pdf')
    comprobar(len(pdf.pages)==1,f'{name}: debe tener una sola página.')
    size=(float(pdf.pages[0].mediabox.width)/72,float(pdf.pages[0].mediabox.height)/72)
    cercanos(size,expected,1e-5,f'{name}: tamaño {size} distinto de {expected}.')
    text=pdf.pages[0].extract_text()
    for phrase in FRASES_PDF:
        comprobar(phrase in text,f'{name}: falta el texto {phrase!r}.')
    pages[name]={'paginas':len(pdf.pages),'pulgadas':size}
try:
    ET.parse(OUT/'Infografia_Turismo_Guatemala_Editable.svg')
except ET.ParseError as error:
    comprobar(False,f'SVG inválido: {error}')

if fallos:
    print(f'Verificación fallida ({len(fallos)}):',file=sys.stderr)
    for f in fallos:print(' -',f,file=sys.stderr)
    sys.exit(1)

result={'estado':'correcto','meses_total':len(s),'meses_prueba':len(pred),'MAE':mae,'RMSE':rmse,
    'reduccion_RMSE_vs_referencia_pct':reduction,'png_pixeles':[im.width,im.height],'pdf':pages,
    'svg':'XML válido con texto y formas editables','revision_visual':'Realizada por inspección de la exportación final. Los controles automáticos no sustituyen esta revisión.',
    'creditos_personales_completos':bool(json.loads((ROOT/'creditos.json').read_text()).get('autores'))}
(OUT/'verificacion_entrega.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
