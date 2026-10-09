"""MVP-01-D.1 — pruebas HTTP sobre Supabase Testing exclusivamente.

Reutiliza db_testing y los helpers ya aprobados en MVP-01-C; nunca usa DATABASE_URL.
"""
from decimal import Decimal

from tests.test_analytics_resumen_integracion import (
    cliente_analytics, autenticar, datos_venta, escenario, PARAMS,
)
from tests.test_pedido_service import _escenario_confirmacion

URL = '/api/analytics/distribuciones'


def consultar(client, headers=None, **params):
    return client.get(URL, params={**PARAMS, **params}, headers=headers or {})


def test_distribuciones_sin_jwt_rechazado(cliente_analytics):
    r = consultar(cliente_analytics)
    assert r.status_code == 401, r.text


def test_distribuciones_vacias_jwt_real(cliente_analytics, db_testing):
    e = escenario(db_testing)
    r = consultar(cliente_analytics, autenticar(db_testing, e))
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['total_observaciones'] == 0
    assert j['variable'] == 'importe_venta'
    assert j['distribucion'] == []


def test_distribuciones_intervalos_y_estados_venta(cliente_analytics, db_testing):
    e = escenario(db_testing)
    for total in ('10.00', '20.00', '30.00', '40.00'):
        datos_venta(db_testing, e, total=total)
    datos_venta(db_testing, e, total='999.00', estado='CANCELADA')
    datos_venta(db_testing, e, total='888.00', estado='REGISTRADA')
    r = consultar(cliente_analytics, autenticar(db_testing, e), intervalos=3)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['tipo_variable'] == 'cuantitativa_continua'
    assert j['total_observaciones'] == 4
    assert [f['frecuencia_absoluta'] for f in j['distribucion']] == [1, 1, 2]
    assert sum(f['frecuencia_absoluta'] for f in j['distribucion']) == 4
    assert all(Decimal(f['frecuencia_relativa']) >= 0 for f in j['distribucion'])


def test_distribuciones_estado_pago_categorias(cliente_analytics, db_testing):
    e = escenario(db_testing)
    for estado in ('PENDIENTE', 'PARCIAL', 'PAGADO', 'PAGADO'):
        v = datos_venta(db_testing, e, total='10.00')
        v.estado_pago = estado
        db_testing.commit()
    r = consultar(cliente_analytics, autenticar(db_testing, e), variable='estado_pago')
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['tipo_variable'] == 'cualitativa_nominal'
    assert j['total_observaciones'] == 4
    por_categoria = {f['categoria']: f for f in j['distribucion']}
    assert {k: por_categoria[k]['frecuencia_absoluta'] for k in ('PENDIENTE', 'PARCIAL', 'PAGADO')} == {
        'PENDIENTE': 1, 'PARCIAL': 1, 'PAGADO': 2,
    }
    assert por_categoria['PAGADO']['frecuencia_relativa'] == '0.5000'


def test_distribuciones_filtro_utc(cliente_analytics, db_testing):
    e = escenario(db_testing)
    datos_venta(db_testing, e, total='10.00', fecha='2026-10-01T00:00:00+00:00')
    datos_venta(db_testing, e, total='20.00', fecha='2026-10-31T23:59:59+00:00')
    datos_venta(db_testing, e, total='30.00', fecha='2026-11-01T00:00:00+00:00')
    r = consultar(cliente_analytics, autenticar(db_testing, e), intervalos=2)
    assert r.status_code == 200, r.text
    assert r.json()['total_observaciones'] == 2
    assert sum(x['frecuencia_absoluta'] for x in r.json()['distribucion']) == 2


def test_distribuciones_aislamiento_multiempresa(cliente_analytics, db_testing):
    a, b = escenario(db_testing), escenario(db_testing)
    datos_venta(db_testing, a, total='10.00')
    datos_venta(db_testing, b, total='999.00')
    r = consultar(cliente_analytics, autenticar(db_testing, a), intervalos=2)
    assert r.status_code == 200, r.text
    assert r.json()['total_observaciones'] == 1
    assert r.json()['distribucion'][0]['desde'] == '10.00'


def test_distribuciones_sin_permiso(cliente_analytics, db_testing):
    e = _escenario_confirmacion(db_testing, permisos=('pedidos.crear',))
    r = consultar(cliente_analytics, autenticar(db_testing, e))
    assert r.status_code == 403, r.text


def test_distribuciones_validacion_periodo(cliente_analytics, db_testing):
    e = escenario(db_testing)
    r = consultar(cliente_analytics, autenticar(db_testing, e), fecha_inicio='2026-11-01', fecha_fin='2026-10-01')
    assert r.status_code == 422, r.text


def test_distribuciones_validacion_parametros(cliente_analytics, db_testing):
    e = escenario(db_testing)
    headers = autenticar(db_testing, e)
    for query in ({'variable': 'desconocida'}, {'intervalos': 0}, {'intervalos': 21}):
        r = consultar(cliente_analytics, headers, **query)
        assert r.status_code == 422, (query, r.text)
