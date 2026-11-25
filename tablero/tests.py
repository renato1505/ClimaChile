"""Pruebas de fallos sin red ni datos meteorológicos inventados."""
from unittest.mock import Mock, patch
from django.test import SimpleTestCase, override_settings
import requests
from . import views

@override_settings(ALLOWED_HOSTS=['testserver'])
class DashboardErrorsTests(SimpleTestCase):
    def tearDown(self):
        views.consultar.cache_clear()

    def test_network_errors_are_visible_in_both_views(self):
        for path in ('/', '/detalle/'):
            for error in (requests.Timeout('timeout'), requests.ConnectionError('offline'), requests.HTTPError('503')):
                with self.subTest(path=path, error=type(error).__name__):
                    views.consultar.cache_clear()
                    with patch.object(views.requests, 'get', side_effect=error):
                        response=self.client.get(path)
                    self.assertContains(response, 'Datos no disponibles')
                    self.assertEqual(response.context['graficos'], [])
                    self.assertEqual(response.context['kpis'], [])
                    self.assertNotContains(response, 'data:image/png')

    def test_bad_json_is_handled(self):
        with patch.object(views.requests, 'get', return_value=Mock(json=Mock(side_effect=ValueError('JSON')))):
            self.assertContains(self.client.get('/'), 'Datos no disponibles')

    def test_missing_data_is_rejected_instead_of_becoming_zero(self):
        payloads=[[], {}, {'daily': []}, {'daily': {'time': ['2026-11-17']}},
                  {'daily': {'time': ['2026-11-17'], **{key: [None] for key in views.CAMPOS.split(',')}}}]
        for payload in payloads:
            with self.subTest(payload=payload):
                views.consultar.cache_clear()
                with patch.object(views.requests, 'get', return_value=Mock(json=Mock(return_value=payload))):
                    with self.assertRaises(ValueError):
                        views.consultar('santiago', '2026-11-17', '2026-11-17')

    def test_invalid_filters_fall_back(self):
        for value in ('abc', '0', '-1', '999'):
            with patch.object(views, 'consultar', side_effect=requests.Timeout):
                response=self.client.get('/detalle/', {'ciudad': 'desconocida', 'dias': value})
            self.assertEqual(response.context['ciudad'], 'todas')
            self.assertEqual(response.context['dias'], 14)

    def test_unexpected_date_order_is_rejected(self):
        with patch.object(views.requests, 'get', return_value=Mock(json=Mock(return_value={'daily': {'time': ['2026-11-18','2026-11-17']}}))):
            with self.assertRaises(ValueError):
                views.consultar('santiago', '2026-11-17', '2026-11-18')
