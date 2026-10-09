"""MVP-01-E.2: solo Supabase Testing vía db_testing; ninguna escritura en DATABASE_URL.

Reutiliza las fixtures y helpers validados de MVP-01-C.
"""
from tests.test_analytics_resumen_integracion import (
    cliente_analytics, autenticar, datos_venta, escenario, PARAMS,
)
from tests.test_pedido_service import _escenario_confirmacion

URL = '/api/analytics/probabilidades'


def consultar(cliente, headers=None, **params):
    return cliente.get(URL, params={**PARAMS, **params}, headers=headers or {})


def crear(db, e, importe, *, pago='PENDIENTE', estado='CONFIRMADA', fecha=None):
    args = {'total': importe, 'estado': estado}
    if fecha is not None:
        args['fecha'] = fecha
    v = datos_venta(db, e, **args)
    v.estado_pago = pago
    db.commit()
    return v


def test_probabilidades_rechaza_sin_jwt(cliente_analytics):
    assert consultar(cliente_analytics).status_code == 401


def test_probabilidades_dataset_vacio(cliente_analytics, db_testing):
    e = escenario(db_testing)
    r = consultar(cliente_analytics, autenticar(db_testing, e))
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['total_observaciones'] == 0
    assert j['probabilidad_pagado'] is None
    assert j['probabilidad_pagado_dado_alto'] is None
    assert j['bayes_importe_alto_dado_pagado'] is None
    assert [x['frecuencia_absoluta'] for x in j['variable_aleatoria_estado_pago']] == [0, 0, 0]


def test_probabilidades_conteos_condicional_y_bayes(cliente_analytics, db_testing):
    e = escenario(db_testing)
    for importe, pago in [('50.00', 'PENDIENTE'), ('100.00', 'PAGADO'),
                          ('150.00', 'PAGADO'), ('200.00', 'PARCIAL')]:
        crear(db_testing, e, importe, pago=pago)
    crear(db_testing, e, '1000.00', pago='PAGADO', estado='CANCELADA')
    crear(db_testing, e, '2000.00', pago='PAGADO', estado='REGISTRADA')
    r = consultar(cliente_analytics, autenticar(db_testing, e), umbral_importe='100.00')
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['total_observaciones'] == 4
    assert j['conteos'] == {'importe_alto': 3, 'pagado': 2, 'importe_alto_y_pagado': 2}
    assert j['probabilidad_pagado'] == '0.5000'
    assert j['probabilidad_importe_alto'] == '0.7500'
    assert j['probabilidad_conjunta_alto_y_pagado'] == '0.5000'
    assert j['probabilidad_pagado_dado_alto'] == '0.6667'
    assert j['bayes_importe_alto_dado_pagado'] == '1.0000'
    assert [(x['estado'], x['frecuencia_absoluta']) for x in j['variable_aleatoria_estado_pago']] == [
        ('PENDIENTE', 1), ('PARCIAL', 1), ('PAGADO', 2)]


def test_probabilidades_cero_denominador_condicional(cliente_analytics, db_testing):
    e = escenario(db_testing)
    crear(db_testing, e, '10.00', pago='PENDIENTE')
    r = consultar(cliente_analytics, autenticar(db_testing, e), umbral_importe='1000.00')
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['probabilidad_pagado_dado_alto'] is None
    assert j['bayes_importe_alto_dado_pagado'] is None
    assert j['probabilidad_pagado'] == '0.0000'


def test_probabilidades_periodo_utc(cliente_analytics, db_testing):
    e = escenario(db_testing)
    crear(db_testing, e, '100.00', pago='PAGADO', fecha='2026-10-01T00:00:00+00:00')
    crear(db_testing, e, '100.00', pago='PENDIENTE', fecha='2026-10-31T23:59:59+00:00')
    crear(db_testing, e, '100.00', pago='PAGADO', fecha='2026-11-01T00:00:00+00:00')
    r = consultar(cliente_analytics, autenticar(db_testing, e))
    assert r.status_code == 200, r.text
    assert r.json()['total_observaciones'] == 2
    assert r.json()['probabilidad_pagado'] == '0.5000'


def test_probabilidades_aislamiento_multiempresa(cliente_analytics, db_testing):
    a, b = escenario(db_testing), escenario(db_testing)
    crear(db_testing, a, '100.00', pago='PENDIENTE')
    crear(db_testing, b, '100.00', pago='PAGADO')
    r = consultar(cliente_analytics, autenticar(db_testing, a))
    assert r.status_code == 200, r.text
    assert r.json()['total_observaciones'] == 1
    assert r.json()['probabilidad_pagado'] == '0.0000'


def test_probabilidades_rbac(cliente_analytics, db_testing):
    e = _escenario_confirmacion(db_testing, permisos=('pedidos.crear',))
    r = consultar(cliente_analytics, autenticar(db_testing, e))
    assert r.status_code == 403, r.text


def test_probabilidades_periodo_invalido(cliente_analytics, db_testing):
    e = escenario(db_testing)
    r = consultar(cliente_analytics, autenticar(db_testing, e),
                  fecha_inicio='2026-11-01', fecha_fin='2026-10-01')
    assert r.status_code == 422, r.text


def test_probabilidades_umbral_invalido(cliente_analytics, db_testing):
    e = escenario(db_testing)
    headers = autenticar(db_testing, e)
    for umbral in ('-1', 'abc', 'NaN', 'Infinity'):
        r = consultar(cliente_analytics, headers, umbral_importe=umbral)
        assert r.status_code == 422, (umbral, r.text)
