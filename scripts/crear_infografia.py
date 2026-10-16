"""Genera la infografía completa como PDF vectorial, SVG editable y PNG.

Uso: python scripts/crear_infografia.py
Los insumos agregados ya están en datos/. Para modificar créditos, editar
creditos.json. El SVG preserva texto y formas editables.
"""
from pathlib import Path
from html import escape
import json
import math
import numpy as np
import pandas as pd
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A3
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[1]
DATA, OUT = ROOT/'datos', ROOT/'salida'
OUT.mkdir(parents=True, exist_ok=True)
W, H, M = 840, 1188, 42
NAVY, TEAL, ORANGE = '#16324F', '#006D77', '#C05510'
MUTED, GRID, PALE, INK = '#525866', '#E0E5E9', '#F2F5F6', '#182A36'
ORANGE_PALE, WHITE = '#F8E9DE', '#FFFFFF'

def register_fonts():
    candidates = [ROOT/'fuentes', Path('/System/Library/Fonts/Supplemental'), Path('/usr/share/fonts/truetype/msttcorefonts')]
    for folder in candidates:
        regular = next((folder/n for n in ['Arial.ttf','arial.ttf'] if (folder/n).exists()),None)
        bold = next((folder/n for n in ['Arial Bold.ttf','arialbd.ttf'] if (folder/n).exists()),None)
        if regular and bold:
            pdfmetrics.registerFont(TTFont('Body',str(regular)))
            pdfmetrics.registerFont(TTFont('Bold',str(bold)))
            return 'Arial'
    # Alternativa libre cuando Arial no está instalada.
    for folder in [Path('/usr/share/fonts/truetype/liberation2'),Path('/usr/share/fonts/truetype/dejavu')]:
        pairs=[('LiberationSans-Regular.ttf','LiberationSans-Bold.ttf'),('DejaVuSans.ttf','DejaVuSans-Bold.ttf')]
        for a,b in pairs:
            if (folder/a).exists() and (folder/b).exists():
                pdfmetrics.registerFont(TTFont('Body',str(folder/a)))
                pdfmetrics.registerFont(TTFont('Bold',str(folder/b)))
                return 'Liberation Sans' if 'Liberation' in a else 'DejaVu Sans'
    raise FileNotFoundError('Instalar Arial, Liberation Sans o DejaVu Sans para regenerar la pieza.')

FONT_FAMILY = register_fonts()

def fmt(x, dec=0):
    return f'{x:,.{dec}f}'.replace(',',' ').replace('.',',')

def width(text,size=10,bold=False):
    return pdfmetrics.stringWidth(str(text),'Bold' if bold else 'Body',size)

class Artwork:
    def __init__(self,path,pagesize):
        self.c=canvas.Canvas(str(path),pagesize=pagesize,pageCompression=1)
        self.c.setTitle('El turismo en Guatemala se mueve por temporadas y depende de sus vecinos')
        self.c.setSubject('Laboratorio 09 Visualización estática - datos académicos INGUAT IGM 2009 a junio 2026')
        self.c.setAuthor('Equipo del Laboratorio 1 - CC3084 UVG')
        pw,ph=pagesize;scale=min(pw/W,ph/H)
        self.c.translate((pw-W*scale)/2,(ph-H*scale)/2)
        self.c.scale(scale,scale)
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="2520" height="3564" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
            '<title id="title">Infografía sobre turismo en Guatemala de 2009 a junio de 2026</title>',
            '<desc id="desc">Datos académicos de visitantes, historia mensual, estacionalidad, comparación entre series, evaluación de modelos e intervalo nominal de Prophet del 95 por ciento.</desc>']
        self.text_records=[]
    def rect(self,x,y,w,h,fill,stroke=None,r=0):
        self.c.setFillColor(HexColor(fill))
        if stroke:self.c.setStrokeColor(HexColor(stroke))
        self.c.roundRect(x,H-y-h,w,h,r,fill=1,stroke=int(bool(stroke)))
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke or "none"}"/>')
    def line(self,x1,y1,x2,y2,color=GRID,lw=.65,dash=None):
        self.c.saveState();self.c.setStrokeColor(HexColor(color));self.c.setLineWidth(lw)
        if dash:self.c.setDash(dash)
        self.c.line(x1,H-y1,x2,H-y2);self.c.restoreState()
        ds=f' stroke-dasharray="{dash} {dash}"' if dash else ''
        self.svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{lw}"{ds}/>')
    def text(self,x,y,text,size=10,color=INK,bold=False,align='left'):
        text=str(text)
        tw=width(text,size,bold)
        left=x if align=='left' else x-tw if align=='right' else x-tw/2
        if left < M-20 or left+tw>W-M+3 or y>H-8:
            raise ValueError(f'Texto fuera de márgenes: {text!r} x={left}, ancho={tw}, y={y}')
        self.c.setFillColor(HexColor(color));self.c.setFont('Bold' if bold else 'Body',size)
        self.c.drawString(left,H-y,text)
        self.svg.append(f'<text x="{left:.3f}" y="{y}" font-family="{FONT_FAMILY},Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(text)}</text>')
        self.text_records.append({'x':left,'y':y,'width':tw,'size':size,'text':text})
    def para(self,x,y,text,maxw,size=9.5,color=INK,bold=False,leading=None):
        leading=leading or size*1.25
        lines=[];line=''
        for word in text.split():
            candidate=(line+' '+word).strip()
            if width(candidate,size,bold)>maxw and line:
                lines.append(line);line=word
            else:line=candidate
        if line:lines.append(line)
        for j,line in enumerate(lines):self.text(x,y+j*leading,line,size,color,bold)
        return y+len(lines)*leading
    def path(self,points,color=NAVY,lw=1.4,fill=None):
        self.c.saveState();p=self.c.beginPath();p.moveTo(points[0][0],H-points[0][1])
        for x,y in points[1:]:p.lineTo(x,H-y)
        if fill:p.close();self.c.setFillColor(HexColor(fill))
        self.c.setStrokeColor(HexColor(color));self.c.setLineWidth(lw)
        self.c.drawPath(p,stroke=int(not bool(fill)),fill=int(bool(fill)));self.c.restoreState()
        pts=' '.join(f'{x:.3f},{y:.3f}' for x,y in points)
        tag='polygon' if fill else 'polyline'
        self.svg.append(f'<{tag} points="{pts}" stroke="{color if not fill else "none"}" stroke-width="{lw}" fill="{fill or "none"}" stroke-linejoin="round"/>')
    def dot(self,x,y,r,color):
        self.c.setFillColor(HexColor(color));self.c.circle(x,H-y,r,fill=1,stroke=0)
        self.svg.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')
    def finish(self,svgpath=None):
        self.c.showPage();self.c.save()
        if svgpath:
            svgpath.write_text('\n'.join(self.svg+['</svg>']),encoding='utf-8')
            (OUT/'verificacion_textos.json').write_text(json.dumps(self.text_records,ensure_ascii=False,indent=2)+'\n')

series=pd.read_csv(DATA/'serie_total_mensual.csv',parse_dates=['Fecha']).set_index('Fecha').Ingresos
profile=pd.read_csv(DATA/'perfil_mensual_2009_2019.csv').set_index('Mes').Promedio_ingresos
models=pd.read_csv(DATA/'modelos_total.csv').sort_values('RMSE')
evidence=pd.read_csv(DATA/'evidencia_series.csv')
pred=pd.read_csv(DATA/'pronostico_prophet_intervalo95.csv',parse_dates=['Fecha'])
summary=json.loads((DATA/'resumen_lab1.json').read_text())
meta=json.loads((DATA/'metadatos_intervalo.json').read_text())
creditfile=ROOT/'creditos.json'
credits=json.loads(creditfile.read_text()) if creditfile.exists() else {'autores':[],'grupo':''}

def section(a,n,title,y):
    a.text(M,y,n,12,TEAL,True)
    a.text(M+28,y,title,13.8,NAVY,True)

def grid(a,x,y,w,h,ymax,ticks):
    for value in ticks:
        yy=y+h*(1-value/ymax)
        a.line(x,yy,x+w,yy,GRID,.55)
        a.text(x-9,yy+2.7,fmt(value/1000),8.6,MUTED,align='right')
    a.line(x,y+h,x+w,y+h,'#B5BEC6',.7)

def plotline(a,values,x,y,w,h,ymax,color=NAVY,lw=1.3):
    pts=[(x+w*i/(len(values)-1),y+h*(1-float(v)/ymax)) for i,v in enumerate(values)]
    a.path(pts,color,lw)
    return pts

def draw(a):
    a.rect(0,0,W,H,WHITE)
    a.text(M,29,'GUATEMALA  /  INGRESOS DE VISITANTES',10,TEAL,True)
    a.text(W-M,29,'2009 A JUNIO DE 2026',9.2,MUTED,align='right')
    a.text(M,75,'El turismo en Guatemala',36,NAVY,True)
    a.text(M,111,'se mueve por temporadas y depende de sus vecinos',26,NAVY,True)
    a.text(M,137,'17 años y medio de datos para planificar temporadas, mercados y capacidad.',11.6,INK)
    a.text(M,155,'Turista + Excursionista  |  210 meses  |  Ingresos registrados o estimados, no personas únicas',9.2,MUTED)

    cards=[('46,71 M','ingresos acumulados','Ene 2009 a jun 2026',NAVY),
        ('-74,4 %','caída del volumen en 2020','Frente al año 2019',ORANGE),
        ('59,1 %','ingresó por vía terrestre','Del acumulado comparable',TEAL),
        ('71,3 %','provino de Centroamérica','Del acumulado comparable',NAVY)]
    for i,(value,label,context,color) in enumerate(cards):
        x=M+(i%2)*387;y=171+(i//2)*67
        a.rect(x,y,369,59,PALE,r=3)
        a.text(x+13,y+39,value,30,color,True)
        a.text(x+183,y+25,label,9.6,INK,True)
        a.text(x+183,y+41,context,8.5,MUTED)

    section(a,'01','La pandemia interrumpió una trayectoria de crecimiento',323)
    a.text(M,343,'Evolución mensual del total comparable',10.3,INK,True)
    a.line(483,340,503,340,NAVY,1.5);a.text(509,343,'Observado',9.2,NAVY)
    a.line(608,340,628,340,TEAL,2);a.text(634,343,'Media móvil de 12 meses',9.2,TEAL)
    x,y,w,h=79,366,719,91
    a.text(M,361,'Miles',8.4,MUTED)
    # Las anotaciones se sitúan en las fechas reales del registro mensual.
    idx=lambda date: series.index.get_loc(pd.Timestamp(date))
    xp=lambda i:x+w*i/(len(series)-1)
    a.rect(xp(idx('2020-03-01')),y,xp(idx('2021-12-01'))-xp(idx('2020-03-01')),h,ORANGE_PALE)
    grid(a,x,y,w,h,500000,[0,250000,500000])
    plotline(a,series.values,x,y,w,h,500000,NAVY,1.25)
    ma=series.rolling(12).mean()
    ma_pts=[(xp(i),y+h*(1-v/500000)) for i,v in enumerate(ma) if pd.notna(v)]
    a.path(ma_pts,TEAL,1.9)
    for year in [2009,2013,2017,2020,2023,2026]:
        xx=xp(idx(f'{year}-01-01'));a.text(xx,472,str(year),8.9,MUTED,align='center')
    xx=xp(idx('2023-01-01'));a.line(xx,y,xx,y+h,MUTED,.7,2)
    a.text(xx-4,360,'2023: cambio de registro',8.5,MUTED,align='right')
    xx=xp(idx('2019-12-01'));yy=y+h*(1-series.loc['2019-12-01']/500000)
    a.dot(xx,yy,2.5,ORANGE)
    a.line(xx,yy-3,xx-25,yy-13,ORANGE,.7)
    a.text(xx-29,yy-14,'Dic 2019: 449 mil',8.8,ORANGE,True,align='right')
    a.text(M,491,'2020: colapso pandémico',9.4,ORANGE,True)
    a.text(284,491,'2022: recuperación del volumen',9.4,NAVY,True)
    a.text(571,491,'2026: solo enero a junio',9.4,NAVY,True)
    a.text(M,506,'La suma comparable mejora la continuidad; el cambio metodológico de 2023 aún limita la comparación de niveles.',9.1,MUTED)

    section(a,'02','El calendario y el punto de entrada cambian la planificación',531)
    a.text(M,552,'Diciembre concentra el mayor promedio mensual',10.2,INK,True)
    a.text(439,552,'Extremos entre las siete series analizadas',10.2,INK,True)
    x,y,w,h=79,583,334,94
    grid(a,x,y,w,h,350000,[0,150000,300000])
    a.text(M,576,'Miles',8.4,MUTED)
    months=['E','F','M','A','M','J','J','A','S','O','N','D']
    for i,(month,value) in enumerate(profile.items()):
        bx=x+i*w/12+4;bw=w/12-8;bh=value/350000*h
        a.rect(bx,y+h-bh,bw,bh,ORANGE if month in [3,7,12] else TEAL)
        a.text(bx+bw/2,y+h+14,months[i],8.8,MUTED,align='center')
        if month in [3,7,12]:a.text(bx+bw/2,y+h-bh-6,fmt(value/1000),8.8,ORANGE,True,align='center')
    a.text(M,709,'Promedio 2009-2019. Marzo/abril: Semana Santa;',8.9,MUTED)
    a.text(M,722,'julio: bono 14; diciembre: fin de año. Contexto, no causalidad.',8.9,MUTED)
    entries=[('Mayor estacionalidad','La Aurora','Fuerza STL 0,547'),
        ('Mayor crecimiento*','San Cristóbal','13,31 % anualizado'),
        ('Mayor volatilidad','El Salvador','1,142 en cambios logarítmicos'),
        ('Mayor caída en 2020','Valle Nuevo','-80,7 % frente a 2019')]
    for i,(label,name,metric) in enumerate(entries):
        bx=439+(i%2)*185;by=564+(i//2)*67
        a.rect(bx,by,174,60,PALE,r=2)
        a.text(bx+9,by+15,label,8.7,MUTED)
        a.text(bx+9,by+34,name,12.6,NAVY,True)
        a.text(bx+9,by+50,metric,8.3,ORANGE if i==3 else TEAL,True)
    a.text(439,709,'*Tendencia anterior a 2020. STL: escala de 0 a 1.',8.5,MUTED)
    a.text(439,722,'Volatilidad: desviación de cambios mensuales de log(1+x).',8.5,MUTED)

    section(a,'03','Prophet reduce el error del total en 68,5 % frente a la referencia',748)
    a.text(M,769,'Misma serie y mismos 63 meses de prueba para todos los modelos. Menor error es mejor.',9.5,MUTED)
    tx=M;tw=306;rowh=20
    a.rect(tx,783,tw,22,NAVY)
    a.text(tx+8,798,'Modelo',9.3,WHITE,True)
    a.text(tx+217,798,'MAE',9.1,WHITE,True,align='right')
    a.text(tx+297,798,'RMSE',9.1,WHITE,True,align='right')
    names={'Suavizamiento exponencial simple':'Suavizamiento simple','SARIMA seleccionado':'SARIMA','Seasonal naive':'Seasonal naïve (referencia)'}
    for i,row in enumerate(models.itertuples()):
        yy=805+i*rowh
        a.rect(tx,yy,tw,rowh,'#E9F2F2' if i==0 else WHITE if i%2 else PALE)
        name=names.get(row.modelo,row.modelo)
        a.text(tx+8,yy+14,name,9.3,TEAL if i==0 else INK,i==0)
        a.text(tx+217,yy+14,fmt(row.MAE),9.3,TEAL if i==0 else INK,i==0,align='right')
        a.text(tx+297,yy+14,fmt(row.RMSE),9.3,TEAL if i==0 else INK,i==0,align='right')
    a.text(tx,940,'MAE y RMSE en ingresos por mes.',8.6,MUTED)

    a.text(377,797,'Estimación de Prophet sobre el período de prueba',10.2,INK,True)
    a.line(377,811,391,811,NAVY,1.4);a.text(396,814,'Observado',8.8,NAVY)
    a.line(467,811,481,811,ORANGE,1.5);a.text(486,814,'Estimación',8.8,ORANGE)
    a.rect(564,805,13,8,ORANGE_PALE);a.text(583,814,'Intervalo nominal 95 %',8.8,MUTED)
    x,y,w,h=406,834,392,88
    maximum=max(float(pred.Superior_95.max()),float(pred.Real.max()))
    ymax=math.ceil(maximum/100000)*100000
    grid(a,x,y,w,h,ymax,[0,ymax/2,ymax])
    a.text(377,829,'Miles',8.3,MUTED)
    xs=np.linspace(x,x+w,len(pred))
    top=[(xx,y+h*(1-v/ymax)) for xx,v in zip(xs,pred.Superior_95)]
    bottom=[(xx,y+h*(1-v/ymax)) for xx,v in zip(xs,pred.Inferior_95)]
    a.path(top+bottom[::-1],ORANGE_PALE,fill=ORANGE_PALE)
    plotline(a,pred.Real,x,y,w,h,ymax,NAVY,1.3)
    plotline(a,pred.Estimacion_Prophet,x,y,w,h,ymax,ORANGE,1.7)
    for date,label in [('2021-04-01','Abr 2021'),('2023-01-01','2023'),('2024-07-01','2024'),('2026-06-01','Jun 2026')]:
        i=pred.index[pred.Fecha==pd.Timestamp(date)][0]
        align='left' if i==0 else 'right' if i==len(pred)-1 else 'center'
        a.text(xs[i],939,label,8.6,MUTED,align=align)
    a.text(M,959,'Entrenamiento: ene 2009 a mar 2021. Prueba: abr 2021 a jun 2026. Evaluación retrospectiva, no proyección más allá de la base.',8.9,MUTED)
    a.text(M,973,'Prophet gana 5 de 7 series y SARIMA 2. El desempeño de este corte no garantiza el futuro ni anticipa todos los choques.',8.9,MUTED)

    section(a,'04','Cinco decisiones para INGUAT',1000)
    recs=[(M,1024,'Anticipar temporadas','Reforzar atención y transporte antes de diciembre; revisar marzo y julio.'),
        (M,1062,'Coordinar la capacidad terrestre','Priorizar coordinación en pasos terrestres: concentran 59,1 % del acumulado.'),
        (M,1100,'Preparar escenarios ante choques','Acordar ajustes de capacidad y promoción frente a caídas como la de 2020.'),
        (439,1024,'Vigilar y diversificar mercados','Monitorear Centroamérica (71,3 %) y evaluar la respuesta de otros mercados.'),
        (439,1062,'Actualizar modelos y catálogos','Reevaluar por serie y documentar el cambio de registro de 2023.')]
    for xx,yy,title,body in recs:
        a.text(xx,yy,title,10,NAVY,True)
        a.para(xx,yy+14,body,355,9.2,MUTED,leading=11.6)
    a.para(439,1100,'2026 parcial y cambios de metodología deben acompañar cualquier lectura de crecimiento.',355,9.2,TEAL,True,leading=11.6)

    a.line(M,1140,W-M,1140,GRID,.8)
    a.text(M,1154,'Fuente: Base de Migración 2009 a jun 2026, INGUAT/IGM. Uso exclusivamente académico; no son cifras oficiales.',8.1,MUTED)
    a.text(M,1166,'Elaboración con resultados del Laboratorio 1. Guatemala deja de reportarse como país desde 2023; no se interpreta como cero.',7.9,MUTED)
    names=credits.get('autores',[])
    group=credits.get('grupo','')
    author='Créditos: '+(' · '.join(names) if names else 'Equipo del Laboratorio 1')
    if group:author+=' · Grupo '+str(group)
    a.para(M,1178,author,756,8.1,NAVY)

def main():
    for name,size in [('Infografia_Turismo_Guatemala_A3.pdf',A3),('Infografia_Turismo_Guatemala_11x17.pdf',(11*72,17*72))]:
        a=Artwork(OUT/name,size);draw(a)
        a.finish(OUT/'Infografia_Turismo_Guatemala_Editable.svg' if 'A3' in name else None)
    doc=pdfium.PdfDocument(str(OUT/'Infografia_Turismo_Guatemala_A3.pdf'))
    page=doc[0];im=page.render(scale=2400/page.get_width()).to_pil().convert('RGB')
    im.save(OUT/'Infografia_Turismo_Guatemala.png',dpi=(205.25,205.25),optimize=True)
    assert im.width>=1200 and im.height>=2400
    print('PNG:',im.size,flush=True)
    print('Salidas:',OUT,flush=True)

if __name__=='__main__':main()
