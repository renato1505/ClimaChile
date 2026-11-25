"""Tablero con datos exclusivamente obtenidos en línea desde Open-Meteo."""
from datetime import date,timedelta
from functools import lru_cache
from io import BytesIO
import base64
import logging
from pathlib import Path
import os
import tempfile
from threading import RLock
from django.utils import timezone

# Vercel solo permite escribir archivos temporales durante la ejecución.
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "climachile-matplotlib"))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import requests
from django.shortcuts import render

CIUDADES={
 'santiago':('Santiago',-33.45,-70.66),
 'valparaiso':('Valparaíso',-33.05,-71.62),
 'concepcion':('Concepción',-36.83,-73.05),
 'temuco':('Temuco',-38.74,-72.60),
 'puerto_montt':('Puerto Montt',-41.47,-72.94),
}
API='https://archive-api.open-meteo.com/v1/archive'
CAMPOS='temperature_2m_mean,precipitation_sum,wind_speed_10m_max'
logger = logging.getLogger(__name__)
PLOT_LOCK = RLock()

@lru_cache(maxsize=256)
def consultar(slug,desde,hasta):
 nombre,lat,lon=CIUDADES[slug]
 respuesta=requests.get(API,params={'latitude':lat,'longitude':lon,'start_date':desde,'end_date':hasta,'daily':CAMPOS,'timezone':'America/Santiago','temperature_unit':'celsius','wind_speed_unit':'kmh','precipitation_unit':'mm'},timeout=18)
 respuesta.raise_for_status()
 info=respuesta.json()
 if not isinstance(info, dict): raise ValueError('Respuesta JSON inválida.')
 if info.get('error'):
  raise ValueError(info.get('reason','Error de la API'))
 diario=info.get('daily')
 if not isinstance(diario, dict): raise ValueError('Faltan series diarias.')
 fechas=diario.get('time')
 inicio=date.fromisoformat(desde)
 fin=date.fromisoformat(hasta)
 esperadas=[(inicio+timedelta(days=i)).isoformat() for i in range((fin-inicio).days+1)]
 if not esperadas or fechas != esperadas: raise ValueError('Fechas incompletas o desordenadas.')
 valores=[diario.get(k) for k in CAMPOS.split(',')]
 if any(not isinstance(v,list) or len(v)!=len(fechas) for v in valores):
  raise ValueError('La API devolvió series incompletas.')
 if any(not np.isfinite(numero(v)) for serie in valores for v in serie):
  raise ValueError('Hay observaciones faltantes o no numéricas.')
 if any(numero(v)<0 for serie in valores[1:] for v in serie):
  raise ValueError('La lluvia y el viento no pueden ser negativos.')
 return [{'fecha':f,'temperatura':v[0],'lluvia':v[1],'viento':v[2],'ciudad':nombre} for f,v in zip(fechas,zip(*valores))]


def numero(v):
 try: return float(v) if v is not None else float('nan')
 except (TypeError,ValueError): return float('nan')

def grafico(fig):
 io=BytesIO()
 try:
  fig.savefig(io,format='png',dpi=125,bbox_inches='tight',facecolor='white')
 finally:
  plt.close(fig)
 return base64.b64encode(io.getvalue()).decode('ascii')

def estilo(ax):
 ax.spines[['top','right']].set_visible(False)
 ax.grid(alpha=.16)
 ax.tick_params(labelsize=8)

def dibujar(datos,detalle):
 colores=['#2563eb','#d94662','#0d9488','#b45309','#7c3aed']
 nombres=list(datos)
 figs=[]
 if not detalle:
  # 1: temperatura por ciudad y tiempo (tres variables: ciudad, fecha, temperatura)
  fig,ax=plt.subplots(figsize=(8.1,3.1))
  for i,n in enumerate(nombres): ax.plot([r['fecha'][5:] for r in datos[n]],[numero(r['temperatura']) for r in datos[n]],label=n,color=colores[i],linewidth=2)
  ax.set_title('Temperatura media diaria por ciudad',loc='left',fontweight='bold',fontsize=12);ax.set_ylabel('°C');estilo(ax);ax.tick_params(axis='x',rotation=45);ax.legend(fontsize=7,ncol=min(3,len(nombres)))
  figs.append(grafico(fig))
  # 2: precipitación total por ciudad
  fig,ax=plt.subplots(figsize=(8.1,3.1))
  totales=[sum(numero(r['lluvia']) for r in datos[n] if np.isfinite(numero(r['lluvia']))) for n in nombres]
  bars=ax.bar(nombres,totales,color=[colores[i] for i in range(len(nombres))]);ax.bar_label(bars,fmt='%.1f',padding=3,fontsize=8)
  ax.set_title('Precipitación acumulada por ciudad',loc='left',fontweight='bold',fontsize=12);ax.set_ylabel('mm');estilo(ax);ax.tick_params(axis='x',rotation=10)
  figs.append(grafico(fig))
  return figs
 # 3: burbujas con cuatro dimensiones: temperatura, lluvia, viento, ciudad
 fig,ax=plt.subplots(figsize=(8.1,3.4))
 for i,n in enumerate(nombres):
  rows=[r for r in datos[n] if all(np.isfinite(numero(r[x])) for x in ('temperatura','lluvia','viento'))]
  ax.scatter([numero(r['temperatura']) for r in rows],[numero(r['lluvia']) for r in rows],s=[25+numero(r['viento'])*2.4 for r in rows],alpha=.55,c=colores[i],label=n,edgecolors='white',linewidths=.5)
 ax.set_title('Lluvia vs. temperatura · tamaño = velocidad del viento',loc='left',fontweight='bold',fontsize=11);ax.set_xlabel('Temperatura media (°C)');ax.set_ylabel('Precipitación (mm)');estilo(ax);ax.legend(fontsize=7,ncol=min(3,len(nombres)))
 figs.append(grafico(fig))
 # 4: heatmap ciudad x día x temperatura; lluvia anotada con punto cuando >= 2 mm
 fig,ax=plt.subplots(figsize=(8.1,3.5))
 matriz=np.array([[numero(r['temperatura']) for r in datos[n]] for n in nombres],dtype=float)
 mapa=ax.imshow(matriz,aspect='auto',cmap='coolwarm')
 ax.set_yticks(range(len(nombres)),nombres,fontsize=8)
 dias=[r['fecha'][5:] for r in datos[nombres[0]]]
 pasos=max(1,len(dias)//9);locs=list(range(0,len(dias),pasos));ax.set_xticks(locs,[dias[i] for i in locs],rotation=40,fontsize=7)
 for j,n in enumerate(nombres):
  for i,r in enumerate(datos[n]):
   if numero(r['lluvia'])>=2:ax.plot(i,j,'o',markerfacecolor='none',markeredgecolor='#111827',markersize=3)
 fig.colorbar(mapa,ax=ax,label='°C',fraction=.035,pad=.03)
 ax.set_title('Temperatura por ciudad y fecha · ○ lluvia ≥ 2 mm',loc='left',fontweight='bold',fontsize=11)
 figs.append(grafico(fig))
 # 5: velocidad de viento diaria por ciudad
 fig,ax=plt.subplots(figsize=(8.1,3.1))
 for i,n in enumerate(nombres):ax.plot([r['fecha'][5:] for r in datos[n]],[numero(r['viento']) for r in datos[n]],label=n,color=colores[i],linewidth=1.9)
 ax.set_title('Viento máximo diario por ciudad',loc='left',fontweight='bold',fontsize=12);ax.set_ylabel('km/h');estilo(ax);ax.tick_params(axis='x',rotation=45);ax.legend(fontsize=7,ncol=min(3,len(nombres)))
 figs.append(grafico(fig))
 return figs

def tablero(request,detalle=False):
 ciudad=request.GET.get('ciudad','todas')
 if ciudad!='todas' and ciudad not in CIUDADES: ciudad='todas'
 try: dias=int(request.GET.get('dias',14))
 except ValueError:dias=14
 if dias not in (7,14,30):dias=14
 # Histórico termina 7 días atrás para evitar fechas sin datos en la API de archivo.
 hasta=timezone.localdate()-timedelta(days=7)
 desde=hasta-timedelta(days=dias-1)
 antes_desde=desde-timedelta(days=dias)
 antes_hasta=desde-timedelta(days=1)
 lista=list(CIUDADES) if ciudad=='todas' else [ciudad]
 context={'detalle':detalle,'ciudad':ciudad,'dias':dias,'ciudades':CIUDADES,'desde':desde,'hasta':hasta,'error':None,'graficos':[],'kpis':[],'fuente':API}
 try:
  datos={CIUDADES[k][0]:consultar(k,str(desde),str(hasta)) for k in lista}
  prev={CIUDADES[k][0]:consultar(k,str(antes_desde),str(antes_hasta)) for k in lista}
  actual=[r for rows in datos.values() for r in rows]
  previo=[r for rows in prev.values() for r in rows]
  def media(rows,campo):
   arr=[numero(r[campo]) for r in rows if np.isfinite(numero(r[campo]))]
   if not arr:raise ValueError(f'Faltan datos para {campo}.')
   return float(np.mean(arr))
  def lluvia(rows):
   # Promedio de precipitación acumulada por ciudad; comparable al cambiar cantidad de ciudades
   return sum(sum(numero(r['lluvia']) for r in datos_ciudad if np.isfinite(numero(r['lluvia']))) for datos_ciudad in rows.values())/len(rows)
  met=[('Temperatura media',media(actual,'temperatura'),media(previo,'temperatura'),'°C'),('Lluvia acumulada media por ciudad',lluvia(datos),lluvia(prev),'mm'),('Viento máximo medio',media(actual,'viento'),media(previo,'viento'),'km/h')]
  context['kpis']=[{'nombre':nombre,'valor':f'{v:.1f}','referencia':f'{p:.1f}','unidad':unidad} for nombre,v,p,unidad in met]
  with PLOT_LOCK:
   try:
    context['graficos']=dibujar(datos,detalle)
   finally:
    plt.close('all')
 except (requests.RequestException,ValueError,KeyError,TypeError) as exc:
  logger.warning('No fue posible generar el tablero: %s', exc)
  context['kpis']=[]
  context['graficos']=[]
  context['error']='No fue posible obtener los datos en línea desde Open-Meteo. Intenta nuevamente más tarde.'
 return render(request,'tablero/dashboard.html',context)
