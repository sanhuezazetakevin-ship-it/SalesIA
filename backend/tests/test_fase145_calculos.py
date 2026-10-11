from datetime import date
import pytest
from app.services.mejoras145_calculos import cambio_porcentual, presentacion_kpi, analizar_stock, segmento_cliente


def test_variacion_base_cero():
    assert cambio_porcentual(12, 0) is None


def test_variacion_positiva():
    assert cambio_porcentual(125, 100) == 25.0


def test_tarjeta_para_grafico():
    item = presentacion_kpi('120.00', '100.00')
    assert item['grafico']['valores'] == [100.0, 120.0]
    assert 'Aumentó' in item['explicacion']


def test_analisis_stock():
    item = analizar_stock(4, 30, 30, 14)
    assert item['riesgo'] == 'ALTO'
    assert item['demanda_estimada'] == 14
    assert item['es_modelo_entrenado'] is False


def test_sin_historial_no_inventa_demanda():
    item = analizar_stock(10, 0, 30)
    assert item['riesgo'] == 'SIN_HISTORIAL'
    assert item['dias_cobertura'] is None


def test_stock_invalido():
    with pytest.raises(ValueError):
        analizar_stock(-1, 10, 30)


def test_segmentos():
    hoy = date(2026, 10, 10)
    assert segmento_cliente(hoy, 5, 100, hoy) == 'FRECUENTE'
    assert segmento_cliente(hoy, 1, 100, hoy) == 'NUEVO'
    assert segmento_cliente(date(2026, 1, 1), 1, 50, hoy) == 'INACTIVO'
    assert segmento_cliente(None, 0, 0, hoy) == 'SIN_COMPRAS'
