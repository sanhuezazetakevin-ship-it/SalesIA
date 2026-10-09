"""Pruebas sin conexiones a bases. PostgreSQL Testing se validará en MVP-01-F.2."""
from datetime import date
from decimal import Decimal
import pytest
from app.services.analytics_historial_service import (
    AnalyticsHistorialError, _json_seguro, _periodo, guardar_estadistico,
    guardar_probabilidad, listar_historial, obtener_historial,
)

D1, D2 = date(2026, 10, 1), date(2026, 10, 31)


def test_json_decimal_preservado():
    assert _json_seguro({'x': Decimal('0.2000')}) == {'x': '0.2000'}


def test_json_anidado():
    assert _json_seguro({'a': [1, {'b': True}]}) == {'a': [1, {'b': True}]}

@pytest.mark.parametrize('valor', [float('nan'), float('inf'), 0.1, Decimal('NaN'), set([1])])
def test_json_rechaza_tipos_inseguros(valor):
    with pytest.raises(AnalyticsHistorialError):
        _json_seguro({'dato': valor})


def test_periodo_inclusivo():
    inicio, fin = _periodo(D1, D2)
    assert inicio.isoformat() == '2026-10-01T00:00:00+00:00'
    assert fin.isoformat() == '2026-10-31T23:59:59.999999+00:00'


def test_periodo_invertido():
    with pytest.raises(AnalyticsHistorialError):
        _periodo(D2, D1)


def test_periodo_excesivo():
    with pytest.raises(AnalyticsHistorialError):
        _periodo(D1, date(2028, 1, 1))

@pytest.mark.parametrize('nombre', ['', ' ', 'x' * 151])
def test_nombre_se_valida_antes_del_acceso(nombre):
    with pytest.raises(AnalyticsHistorialError):
        guardar_estadistico(None, usuario_id=1, nombre=nombre, fecha_inicio=D1, fecha_fin=D2, resultados={})


def test_resultados_se_validan():
    with pytest.raises(AnalyticsHistorialError):
        guardar_probabilidad(None, usuario_id=1, fecha_inicio=D1, fecha_fin=D2,
                             resultados=[], umbral_importe='100')

@pytest.mark.parametrize('umbral', ['NaN', '-1', 'Infinity', 'abc'])
def test_umbral_se_valida(umbral):
    with pytest.raises(AnalyticsHistorialError):
        guardar_probabilidad(None, usuario_id=1, fecha_inicio=D1, fecha_fin=D2,
                             resultados={}, umbral_importe=umbral)


def test_tipo_invalido_listado():
    with pytest.raises(AnalyticsHistorialError):
        listar_historial(None, usuario_id=1, tipo='otro')


def test_limite_fuera_de_rango():
    with pytest.raises(AnalyticsHistorialError):
        listar_historial(None, usuario_id=1, limite=101)


def test_id_invalido():
    with pytest.raises(AnalyticsHistorialError):
        obtener_historial(None, usuario_id=1, tipo='estadistico', analisis_id=0)
