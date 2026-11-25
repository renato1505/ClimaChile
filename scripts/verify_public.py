"""Verifica el sitio público sin credenciales y contrasta sus KPI con Open-Meteo.
Uso: .venv/Scripts/python.exe scripts/verify_public.py https://climachile.vercel.app
Realiza 36 solicitudes de páginas y 5 consultas reales a la API.
"""
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from statistics import mean
from zoneinfo import ZoneInfo
import base64
import re
import sys
import requests
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tablero.views import API, CAMPOS, CIUDADES

base=(sys.argv[1] if len(sys.argv)>1 else 'https://climachile.vercel.app').rstrip('/')
end=datetime.now(ZoneInfo('America/Santiago')).date()-timedelta(days=7)
start=end-timedelta(days=59)
real={}
for slug,(_,latitude,longitude) in CIUDADES.items():
    response=requests.get(API,params={'latitude':latitude,'longitude':longitude,'start_date':start.isoformat(),'end_date':end.isoformat(),'daily':CAMPOS,'timezone':'America/Santiago','temperature_unit':'celsius','wind_speed_unit':'kmh','precipitation_unit':'mm'},timeout=30)
    response.raise_for_status()
    daily=response.json()['daily']
    assert len(daily['time'])==60
    real[slug]=daily
    print(f'API real de referencia: {slug}',flush=True)

def values(cities, first, last):
    rows=[]
    for city in cities:
        daily=real[city]
        for i,day in enumerate(daily['time']):
            if first.isoformat()<=day<=last.isoformat():
                rows.append(tuple(float(daily[key][i]) for key in CAMPOS.split(',')))
    return [mean(row[0] for row in rows), sum(row[1] for row in rows)/len(cities), mean(row[2] for row in rows)]

css=requests.get(base+'/static/tablero/site.css',timeout=30)
css.raise_for_status()
assert '--ink:#17283c' in css.text
cases=0
images_checked=0
for slug in ('todas', *CIUDADES):
    cities=list(CIUDADES) if slug=='todas' else [slug]
    for days in (7,14,30):
        first=end-timedelta(days=days-1)
        expected=values(cities,first,end)
        references=values(cities,first-timedelta(days=days),first-timedelta(days=1))
        for path,count in (('/',2),('/detalle/',3)):
            # No sesión autenticada, token, cookie ni cabecera de bypass.
            response=requests.get(base+path,params={'ciudad':slug,'dias':days},timeout=240)
            response.raise_for_status()
            assert response.url.startswith(base+'/'), response.url
            html=response.text
            assert 'Datos no disponibles' not in html
            assert 'ClimaChile' in html
            assert f'{first:%d/%m/%Y} — {end:%d/%m/%Y}' in html
            assert f'value="{slug}" selected' in html
            assert f'value="{days}" selected' in html
            assert f'ciudad={slug}&dias={days}' in html or f'ciudad={slug}&amp;dias={days}' in html
            charts=re.findall(r'src="data:image/png;base64,([^" ]+)"',html)
            assert len(charts)==count, (path,slug,days,len(charts))
            for encoded in charts:
                with Image.open(BytesIO(base64.b64decode(encoded))) as image:
                    assert image.format=='PNG'
                    image.verify()
                images_checked+=1
            kpis=re.findall(r'<article class="kpi">(.*?)</article>',html,re.S)
            assert len(kpis)==3
            for block,value,previous in zip(kpis,expected,references):
                shown=float(re.search(r'class="k-val">(-?[0-9.]+)',block).group(1))
                reference=float(re.search(r'Período anterior: <strong>(-?[0-9.]+)',block).group(1))
                assert abs(shown-value)<=0.05000000001, (slug,days,shown,value)
                assert abs(reference-previous)<=0.05000000001, (slug,days,reference,previous)
            cases+=1
        print(f'OK público: {slug}, {days} días, ambas vistas y tres KPI',flush=True)
print(f'RESULTADO: {cases} páginas correctas sin credenciales, {images_checked} PNG válidos, CSS disponible y KPI contrastados con Open-Meteo.',flush=True)
