from decimal import Decimal
import pytest
from app.services.analytics_probabilidades_calculos import calcular_probabilidades


VENTAS = [('50.00', 'PENDIENTE'), ('100.00', 'PAGADO'),
          ('150.00', 'PAGADO'), ('200.00', 'PARCIAL')]


def test_probabilidad_simple():
    r = calcular_probabilidades(VENTAS)
    assert r['probabilidad_pagado'] == '0.5000'
    assert r['probabilidad_importe_alto'] == '0.7500'


def test_probabilidad_conjunta():
    r = calcular_probabilidades(VENTAS)
    assert r['probabilidad_conjunta_alto_y_pagado'] == '0.5000'
    assert r['conteos']['importe_alto_y_pagado'] == 2


def test_probabilidad_condicional():
    assert calcular_probabilidades(VENTAS)['probabilidad_pagado_dado_alto'] == '0.6667'


def test_bayes_sin_redondeo_intermedio():
    assert calcular_probabilidades(VENTAS)['bayes_importe_alto_dado_pagado'] == '1.0000'


def test_umbral_inclusivo():
    r = calcular_probabilidades([('100', 'PAGADO'), ('99.99', 'PENDIENTE')], umbral_importe=100)
    assert r['conteos']['importe_alto'] == 1


def test_variable_aleatoria():
    filas = calcular_probabilidades(VENTAS)['variable_aleatoria_estado_pago']
    assert [(f['estado'], f['frecuencia_absoluta']) for f in filas] == [
        ('PENDIENTE', 1), ('PARCIAL', 1), ('PAGADO', 2)]
    assert [f['probabilidad'] for f in filas] == ['0.2500', '0.2500', '0.5000']


def test_muestra_vacia_indefinida():
    r = calcular_probabilidades([])
    assert r['total_observaciones'] == 0
    assert r['probabilidad_pagado'] is None
    assert r['bayes_importe_alto_dado_pagado'] is None
    assert all(f['probabilidad'] is None for f in r['variable_aleatoria_estado_pago'])


def test_sin_importes_altos_condicional_indefinida():
    r = calcular_probabilidades([('10', 'PAGADO')], umbral_importe='100')
    assert r['probabilidad_pagado_dado_alto'] is None
    assert r['bayes_importe_alto_dado_pagado'] == '0.0000'


def test_sin_pagados_bayes_indefinido():
    r = calcular_probabilidades([('100', 'PENDIENTE')])
    assert r['bayes_importe_alto_dado_pagado'] is None
    assert r['probabilidad_pagado_dado_alto'] == '0.0000'


@pytest.mark.parametrize('importe', ['NaN', 'Infinity', '-1', 'abc', None, True])
def test_rechaza_importes_invalidos(importe):
    with pytest.raises(ValueError):
        calcular_probabilidades([(importe, 'PAGADO')])


@pytest.mark.parametrize('umbral', ['NaN', '-1', 'Infinity', None, False])
def test_rechaza_umbral_invalido(umbral):
    with pytest.raises(ValueError):
        calcular_probabilidades(VENTAS, umbral_importe=umbral)


def test_rechaza_estado_desconocido():
    with pytest.raises(ValueError):
        calcular_probabilidades([('10', 'ANULADO')])


def test_precision_decimal():
    r = calcular_probabilidades([(Decimal('0.10'), 'PAGADO'), (Decimal('0.20'), 'PARCIAL')], umbral_importe='0.10')
    assert r['probabilidad_pagado'] == '0.5000'
    assert r['conteos']['importe_alto'] == 2


def test_no_modifica_entrada():
    ventas = list(VENTAS)
    calcular_probabilidades(ventas)
    assert ventas == VENTAS
