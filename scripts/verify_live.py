"""Consulta 5 series reales; reutiliza solo esas respuestas para probar 36 filtros/vistas.
Ejecutar: .venv/Scripts/python.exe scripts/verify_live.py
No crea datos de respaldo en la aplicación. Falla si la API no responde.
"""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'climachile.settings')
import django
django.setup()
from datetime import timedelta
from io import BytesIO
import base64
from statistics import mean
from unittest.mock import patch
from PIL import Image
from django.test import Client, override_settings
from django.test.utils import setup_test_environment
from django.utils import timezone
from tablero import views

setup_test_environment()
end=timezone.localdate()-timedelta(days=7)
start=end-timedelta(days=59)
real={}
for slug in views.CIUDADES:
    real[slug]=views.consultar(slug, start.isoformat(), end.isoformat())
    assert len(real[slug])==60
    print(f'API real: {slug}, 60 días, {start} a {end}', flush=True)

def replay(slug, first, last):
    return [row for row in real[slug] if first<=row['fecha']<=last]

# Inspeccionar los canales visuales y verificar que las cinco imágenes son PNG.
figures=[]
original=views.grafico
def inspect(fig):
    figures.append(fig)
    return original(fig)
all_data={views.CIUDADES[slug][0]:rows for slug,rows in real.items()}
with patch.object(views, 'grafico', side_effect=inspect):
    images=views.dibujar(all_data, False)+views.dibujar(all_data, True)
assert len(images)==5
assert len(figures[0].axes[0].lines)==5  # ciudad, fecha, temperatura
assert len(figures[2].axes[0].collections)==5  # ciudad, temperatura, lluvia, viento
assert figures[3].axes[0].images[0].get_array().shape==(5,60)
assert len(figures[4].axes[0].lines)==5  # ciudad, fecha, viento
# Conservar gráficos reales en TEMP para inspección, fuera de la aplicación.
import tempfile
plot_dir=Path(tempfile.mkdtemp(prefix='climachile-verificacion-'))
for i, encoded in enumerate(images):
    (plot_dir/f'grafico-{i+1}.png').write_bytes(base64.b64decode(encoded))
    with Image.open(BytesIO(base64.b64decode(encoded))) as image:
        assert image.format=='PNG'
        image.verify()
print(f'Gráficos de verificación: {plot_dir}',flush=True)
print('Cinco PNG válidos; líneas, burbujas y mapa de calor multivariables verificados.', flush=True)

cases=0
with override_settings(ALLOWED_HOSTS=['testserver']), patch.object(views, 'consultar', side_effect=replay):
    client=Client()
    for slug in ('todas', *views.CIUDADES):
        for days in (7,14,30):
            first=end-timedelta(days=days-1)
            previous_first=first-timedelta(days=days)
            previous_end=first-timedelta(days=1)
            cities=list(real) if slug=='todas' else [slug]
            current=[row for city in cities for row in replay(city,first.isoformat(),end.isoformat())]
            previous=[row for city in cities for row in replay(city,previous_first.isoformat(),previous_end.isoformat())]
            expected=[mean(row['temperatura'] for row in current),sum(row['lluvia'] for row in current)/len(cities),mean(row['viento'] for row in current)]
            references=[mean(row['temperatura'] for row in previous),sum(row['lluvia'] for row in previous)/len(cities),mean(row['viento'] for row in previous)]
            for path, count in (('/',2),('/detalle/',3)):
                response=client.get(path, {'ciudad':slug,'dias':days})
                assert response.status_code==200
                context=response.context
                assert context['error'] is None, context['error']
                assert context['ciudad']==slug and context['dias']==days
                assert context['desde']==first and context['hasta']==end
                assert len(context['graficos'])==count
                html=response.content.decode()
                assert html.count('data:image/png;base64,')==count
                assert len(context['kpis'])==3
                for kpi,value,reference in zip(context['kpis'],expected,references):
                    assert abs(float(kpi['valor'])-value)<=0.05000000001, (kpi,value)
                    assert abs(float(kpi['referencia'])-reference)<=0.05000000001, (kpi,reference)
                assert f'ciudad={slug}&amp;dias={days}' in html or f'ciudad={slug}&dias={days}' in html
                cases+=1
            print(f'OK filtros: {slug}, {days} días, ambas vistas y KPI',flush=True)
assert not views.plt.get_fignums(), 'Figuras sin cerrar'
print(f'RESULTADO: {cases} combinaciones correctas con datos reales, 3 KPI y períodos anteriores verificados.',flush=True)
