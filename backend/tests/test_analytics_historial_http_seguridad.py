"""MVP-01-F.4: JWT real + HTTP + PostgreSQL Testing (rollback externo).

Usa cliente_analytics/db_testing de las pruebas existentes; nunca crea un engine.
No correr contra la base principal. Ningún TRUNCATE ni DROP.
"""
from tests.test_analytics_resumen_integracion import (
    cliente_analytics, autenticar, datos_venta, escenario, PARAMS,
)
from tests.test_pedido_service import _escenario_confirmacion

BASE = '/api/analytics/historial'


def payload_estadistico():
    return {**PARAMS, 'nombre': 'Cierre estadístico MVP'}


def payload_probabilidad():
    return {**PARAMS, 'umbral_importe': '100.00'}


def test_post_estadistico_sin_jwt(cliente_analytics):
    r = cliente_analytics.post(BASE + '/estadisticos', json=payload_estadistico())
    assert r.status_code == 401, r.text


def test_post_probabilidades_sin_jwt(cliente_analytics):
    r = cliente_analytics.post(BASE + '/probabilidades', json=payload_probabilidad())
    assert r.status_code == 401, r.text


def test_get_historial_sin_jwt(cliente_analytics):
    assert cliente_analytics.get(BASE).status_code == 401


def test_post_estadistico_sin_analitica_ejecutar(cliente_analytics, db_testing):
    e = _escenario_confirmacion(db_testing, permisos=('ventas.ver',))
    r = cliente_analytics.post(BASE + '/estadisticos', json=payload_estadistico(),
                               headers=autenticar(db_testing, e))
    assert r.status_code == 403, r.text


def test_post_probabilidad_sin_ventas_ver(cliente_analytics, db_testing):
    e = _escenario_confirmacion(db_testing, permisos=('analitica.ejecutar',))
    r = cliente_analytics.post(BASE + '/probabilidades', json=payload_probabilidad(),
                               headers=autenticar(db_testing, e))
    assert r.status_code == 403, r.text


def test_post_estadistico_calcula_y_recupera(cliente_analytics, db_testing):
    e = _escenario_confirmacion(db_testing, permisos=('ventas.ver', 'analitica.ejecutar'))
    # El escenario comercial de autorización puede carecer de Cliente; el cálculo vacío
    # sigue siendo un dato legítimo y permite comprobar la persistencia y el JWT.
    headers = autenticar(db_testing, e)
    r = cliente_analytics.post(BASE + '/estadisticos', json=payload_estadistico(), headers=headers)
    assert r.status_code == 201, r.text
    j = r.json()
    assert j['empresa_id'] == e['empresa_id']
    assert j['estado'] == 'COMPLETADO'
    assert j['tipo'] == 'estadistico'
    assert 'contenido' in j['resultados']
    g = cliente_analytics.get(f"{BASE}/estadistico/{j['id']}", headers=headers)
    assert g.status_code == 200, g.text
    assert g.json()['id'] == j['id']
    assert g.json()['resultados'] == j['resultados']


def test_post_probabilidad_calcula_y_recupera(cliente_analytics, db_testing):
    e = _escenario_confirmacion(db_testing, permisos=('ventas.ver', 'analitica.ejecutar'))
    headers = autenticar(db_testing, e)
    r = cliente_analytics.post(BASE + '/probabilidades', json=payload_probabilidad(), headers=headers)
    assert r.status_code == 201, r.text
    j = r.json()
    assert j['empresa_id'] == e['empresa_id']
    assert j['tipo'] == 'probabilidad'
    assert j['resultados']['total_observaciones'] == 0
    assert j['resultados']['probabilidad_pagado'] is None
    g = cliente_analytics.get(f"{BASE}/probabilidad/{j['id']}", headers=headers)
    assert g.status_code == 200, g.text
    assert g.json()['id'] == j['id']


def test_listado_aislado_y_registro_ajeno_es_404(cliente_analytics, db_testing):
    a = _escenario_confirmacion(db_testing, permisos=('ventas.ver', 'analitica.ejecutar'))
    b = _escenario_confirmacion(db_testing, permisos=('ventas.ver', 'analitica.ejecutar'))
    ha, hb = autenticar(db_testing, a), autenticar(db_testing, b)
    ra = cliente_analytics.post(BASE + '/estadisticos', json=payload_estadistico(), headers=ha)
    rb = cliente_analytics.post(BASE + '/estadisticos', json=payload_estadistico(), headers=hb)
    assert ra.status_code == 201, ra.text
    assert rb.status_code == 201, rb.text
    id_a, id_b = ra.json()['id'], rb.json()['id']
    r = cliente_analytics.get(BASE, params={'tipo': 'estadistico'}, headers=ha)
    assert r.status_code == 200, r.text
    ids = [x['id'] for x in r.json()['items']]
    assert id_a in ids and id_b not in ids
    ajeno = cliente_analytics.get(f'{BASE}/estadistico/{id_b}', headers=ha)
    assert ajeno.status_code == 404, ajeno.text


def test_entrada_invalida_no_escribe(cliente_analytics, db_testing):
    e = _escenario_confirmacion(db_testing, permisos=('ventas.ver', 'analitica.ejecutar'))
    h = autenticar(db_testing, e)
    antes = cliente_analytics.get(BASE, headers=h)
    assert antes.status_code == 200, antes.text
    r = cliente_analytics.post(BASE + '/estadisticos', json={**payload_estadistico(),
                               'fecha_inicio': '2026-11-01', 'fecha_fin': '2026-10-01'}, headers=h)
    assert r.status_code == 422, r.text
    despues = cliente_analytics.get(BASE, headers=h)
    assert despues.status_code == 200, despues.text
    assert [x['id'] for x in despues.json()['items']] == [x['id'] for x in antes.json()['items']]
