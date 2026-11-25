import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
BASE_DIR=Path(__file__).resolve().parent.parent
SECRET_KEY=os.environ.get('DJANGO_SECRET_KEY','local-dev-change-this-in-production')
VERCEL=os.environ.get('VERCEL')=='1'
if VERCEL and (not SECRET_KEY or SECRET_KEY=='local-dev-change-this-in-production'):
 raise ImproperlyConfigured('Configura DJANGO_SECRET_KEY en Vercel.')
DEBUG=not VERCEL and os.environ.get('DEBUG','false').lower()=='true'
ALLOWED_HOSTS=[x.strip() for x in os.environ.get('ALLOWED_HOSTS','.vercel.app,localhost,127.0.0.1').split(',') if x.strip()]
INSTALLED_APPS=['django.contrib.staticfiles','tablero']
MIDDLEWARE=['django.middleware.security.SecurityMiddleware','django.middleware.common.CommonMiddleware','django.middleware.csrf.CsrfViewMiddleware','django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF='climachile.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request']}}]
WSGI_APPLICATION='climachile.wsgi.application'
STATIC_URL='/static/'
STATIC_ROOT=BASE_DIR/'staticfiles'
DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'

TIME_ZONE='America/Santiago'
USE_TZ=True
LANGUAGE_CODE='es-cl'
if VERCEL:
 SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
 SECURE_SSL_REDIRECT=True
 SESSION_COOKIE_SECURE=True
 CSRF_COOKIE_SECURE=True
 SECURE_HSTS_SECONDS=31536000
