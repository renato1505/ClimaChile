from django.urls import path
from tablero.views import tablero
urlpatterns=[path('',tablero,name='inicio'),path('detalle/',tablero,{'detalle':True},name='detalle')]
