# ClimaChile — Dashboard de datos meteorológicos

Proyecto académico de Visualización de Datos · Evaluación N.º 3.

- **Aplicación pública:** https://climachile.vercel.app/
- **Vista de detalle:** https://climachile.vercel.app/detalle/
- **Repositorio público:** https://github.com/renato1505/ClimaChile
- **Estado:** producción publicada y validada sin credenciales el 24 de noviembre de 2026 (America/Santiago).

## 1. Tema

**Tema:** comparación meteorológica de ciudades de Chile para ayudar a personas que planifican viajes, actividades al aire libre o decisiones logísticas. **Preguntas:** ¿cómo cambia la temperatura entre ciudades y días? ¿Dónde se acumula más lluvia? ¿Cómo se relacionan temperatura, precipitación y viento? ¿Qué días y ciudades presentan condiciones diferentes?

## 2. API

Se usa [Open-Meteo Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) a través de `https://archive-api.open-meteo.com/v1/archive`, con coordenadas para Santiago, Valparaíso, Concepción, Temuco y Puerto Montt. Variables diarias: `temperature_2m_mean` (°C), `precipitation_sum` (mm), `wind_speed_10m_max` (km/h). Acceso HTTP(S) sin clave para uso no comercial dentro de sus límites. Datos históricos procedentes de modelos/reanálisis: **no son mediciones directas certificadas de estaciones de superficie**. La actualización y disponibilidad pueden retrasarse; la aplicación consulta hasta siete días antes del día actual. Se deben respetar los [términos](https://open-meteo.com/en/terms). No se usan datos ficticios.

## 3. Decisiones de visualización

| Gráfico | Pregunta | Elección |
|---|---|---|
| Línea: temperatura por ciudad y día | ¿Cómo evoluciona la temperatura? | Las líneas permiten observar tendencias temporales. Tres variables: ciudad, fecha y temperatura. |
| Barras: precipitación por ciudad | ¿Dónde llovió más? | Las barras permiten comparar cantidades entre categorías. |
| Burbujas: temperatura, lluvia, viento y ciudad | ¿Se asocian lluvia y temperatura, considerando viento? | Ejes X/Y para dos métricas, tamaño para viento, color para ciudad. Cuatro variables. |
| Mapa de calor: ciudad, fecha, temperatura y lluvia | ¿Dónde y cuándo hubo diferencias térmicas y lluvia? | Matriz ciudad×fecha codificada por temperatura; círculos indican días con precipitación ≥2 mm. Cuatro variables. |
| Línea: viento por ciudad y día | ¿Cuándo se producen vientos fuertes? | Línea temporal facilita la lectura de máximos diarios. |

**Gráfico descartado:** circular (pie chart) para temperatura; la temperatura es continua, no representa partes de un total.

## 4. Preparación de datos

En `tablero/views.py`, `consultar` solicita JSON con un tiempo máximo de espera de 18 segundos por petición y unidades explícitas. Valida el estado HTTP, estructura, fechas consecutivas y las tres series completas. Si hay valores nulos, no numéricos o lluvia/viento negativos, muestra el estado de datos no disponibles; no convierte datos faltantes en cero ni presenta KPI parciales. `numero` convierte valores válidos en `float`.

La lluvia es el **promedio por ciudad del acumulado del período**. Las solicitudes correctas se conservan en una caché LRU en memoria de hasta 256 combinaciones ciudad/fechas; no es persistente ni tiene vencimiento temporal. Los errores no se almacenan. Las fechas usan `America/Santiago` y terminan siete días atrás.

La vista `/` genera dos gráficos (temperatura y precipitación); `/detalle/` genera tres (burbujas, mapa de calor y viento). Ambas incluyen los tres KPI y conservan los filtros en los enlaces. Matplotlib usa `Agg`, imágenes PNG embebidas y una carpeta temporal para su caché. La generación se serializa por proceso para evitar conflictos entre solicitudes concurrentes.

## 5. Indicadores

| KPI | Fórmula | Unidad | Referencia |
|---|---|---|---|
| Temperatura media | Promedio de las observaciones ciudad-día válidas | °C | Igual duración inmediatamente anterior |
| Lluvia acumulada media por ciudad | Suma por ciudad para el período y promedio entre ciudades | mm | Igual duración inmediatamente anterior |
| Viento máximo medio | Promedio de velocidades máximas diarias ciudad-día | km/h | Igual duración inmediatamente anterior |

Los filtros seleccionan ciudad y duración (7, 14 o 30 días). Los gráficos y KPI se regeneran desde el servidor usando Matplotlib.

## 6. Propuesta de valor y ética

**Decisión facilitada:** comparar ciudades y fechas para seleccionar ventanas y lugares con condiciones históricas más favorables para actividades o desplazamientos. **Beneficiarios:** personas, organizadores de eventos y pequeños operadores turísticos. **Afectados:** quienes dependen de decisiones condicionadas por el clima y quienes podrían interpretar promedios como pronósticos. **Dilema ético:** mostrar datos históricos modelados como si fueran observaciones exactas o pronósticos seguros puede provocar decisiones riesgosas. **Decisión:** declarar fuente, rango, tipo de dato, limitaciones y advertencia de que no sustituye alertas meteorológicas oficiales; no inventar datos si la API falla.

---

## Ejecución local

Requiere Python 3.14, también declarado en `.python-version` para Vercel.
Desde PowerShell en la carpeta del proyecto:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DEBUG = "true"
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

`python` debe apuntar a Python 3.14 al crear el entorno; si tienes varias versiones, utiliza su ruta completa. No es necesario activar el entorno ni cambiar la política de PowerShell. Abrir `http://127.0.0.1:8000/` y `http://127.0.0.1:8000/detalle/`. El CSS local requiere `DEBUG=true`. Detener con Ctrl+C.

## Verificación

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py test tablero
.\.venv\Scripts\python.exe scripts/verify_live.py
.\.venv\Scripts\python.exe scripts/verify_public.py https://climachile.vercel.app
.\.venv\Scripts\python.exe manage.py collectstatic --noinput
```

Las pruebas de errores no necesitan conexión: simulan timeout, desconexión, HTTP fallido, JSON inválido, series incompletas y filtros inválidos. No suministran observaciones meteorológicas inventadas.

`verify_live.py` exige conexión real: descarga 60 días de las cinco ciudades, inspecciona los canales visuales de los cinco gráficos y valida sus PNG. Reutiliza esas respuestas reales exclusivamente dentro de la prueba para comprobar las 36 combinaciones de dos vistas, seis opciones de ciudad y tres duraciones. Recalcula independientemente los tres KPI y sus referencias, con tolerancia de 0,05 por el redondeo mostrado a un decimal. No modifica la fuente de datos de la aplicación ni guarda datos de respaldo. Una interrupción de Open-Meteo hace fallar esta verificación.

## Despliegue en Vercel

Configuración utilizada en el despliegue de producción con soporte nativo de Django:

- `.python-version`: Python 3.14.
- `.vercelignore`: excluye credenciales, entornos, caché, pruebas y archivos generados del paquete enviado por CLI.
- `vercel.json`: preset Django, entrada `climachile/wsgi.py` y duración máxima de 300 segundos para las consultas y gráficos. La duración efectiva depende del plan.
- `WSGI_APPLICATION`: `climachile.wsgi.application`; detección mediante `manage.py`.
- `STATIC_ROOT` y `STATIC_URL`: Vercel ejecuta `collectstatic` y sirve el CSS desde su CDN. No se necesitan rutas manuales `/api` ni WhiteNoise.
- `MPLCONFIGDIR`: directorio temporal escribible; no se escriben imágenes en el sistema de archivos del despliegue.
- En Vercel se fuerza `DEBUG=false`, HTTPS y cookies seguras. Falta de `DJANGO_SECRET_KEY` detiene el arranque con un error explícito.

### Publicación y actualización

Se publicó mediante Vercel CLI en el proyecto `clima-chile/climachile`. El repositorio GitHub es público y su rama es `main`. El despliegue actual se realizó por CLI: no se configuró el despliegue automático mediante GitHub.

En Vercel están definidas `DJANGO_SECRET_KEY`, `DEBUG=false` y `ALLOWED_HOSTS=.vercel.app` para Production y Preview. El secreto se generó en memoria y se almacenó en Vercel, nunca en el repositorio. `.env.example` documenta las variables; el programa no carga archivos `.env` automáticamente. No se deben versionar los archivos locales que genere Vercel CLI.

Para publicar cambios desde la carpeta del proyecto:

```powershell
git add <archivos-revisados>
git commit -m "Descripción del cambio"
git push origin main
npx.cmd --yes vercel@latest login
npx.cmd --yes vercel@latest link --yes --project climachile --scope clima-chile
npx.cmd --yes vercel@latest deploy --prod --yes --scope clima-chile
```

La autenticación y vinculación solo son necesarias si no existe una sesión/proyecto local. No hace falta iniciar sesión nuevamente en cada publicación. La documentación exige Vercel CLI 50.38.0 o posterior; la publicación se realizó con la versión 66.6.0.

### Resultado de la validación de entrega

Validación del 24 de noviembre de 2026:

- GitHub y README accesibles sin autenticación; `main` sincronizada.
- Build Linux exitoso con Python 3.14 y Django 5.2.19; función Django de 68,33 MB, según la inspección del primer despliegue.
- `collectstatic` exitoso y `/static/tablero/site.css` accesible por HTTPS.
- Estado de producción **Ready**, dominio `https://climachile.vercel.app/`.
- 36 combinaciones públicas correctas: dos vistas × seis opciones de ciudad × tres períodos. Verificación mediante solicitudes HTTP sin tokens, cookies ni bypass de protección.
- 90 imágenes PNG válidas entre esas páginas. Los cinco tipos de gráfico están disponibles: dos en la vista general y tres en detalle.
- Tres KPI y sus períodos anteriores contrastados con consultas independientes reales a Open-Meteo, con tolerancia de 0,05 por el redondeo a un decimal.
- Cinco pruebas locales de manejo de fallos superadas: timeout, desconexión, HTTP fallido, JSON inválido, series faltantes y fechas/filtros inválidos.
- Diseño y CSS conservados; no se añadieron datos ficticios ni funcionalidades al tablero.

La comprobación pública reproducible está en `scripts/verify_public.py`. Esa prueba requiere que Vercel y Open-Meteo estén disponibles y puede tardar varios minutos. No modifica la aplicación desplegada. La revisión visual completa en navegador no forma parte de estas pruebas HTTP; se inspeccionaron imágenes de los gráficos durante la revisión local.

La aplicación no usa base de datos ni requiere migraciones. La caché en memoria puede desaparecer entre invocaciones y la disponibilidad futura depende de Vercel y Open-Meteo. No quedan tareas técnicas bloqueantes para la entrega; la integración de despliegue automático con GitHub es opcional.

Fuentes de configuración: [Django en Vercel](https://vercel.com/docs/frameworks/full-stack/django), [runtime Python](https://vercel.com/docs/functions/runtimes/python) y [API histórica Open-Meteo](https://open-meteo.com/en/docs/historical-weather-api).

`check --deploy` puede advertir sobre HSTS para subdominios y precarga (W005/W021). No se activan sin confirmar el control y HTTPS de todos los subdominios; no impiden el despliegue.
