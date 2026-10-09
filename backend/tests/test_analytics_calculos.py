from decimal import Decimal
import pytest
from app.services.analytics_resumen_service import calcular_metricas

def test_vacio():
    r=calcular_metricas([])
    assert r['cantidad_ventas']==0 and r['ticket_promedio'] is None and r['mediana_ventas'] is None

def test_media_mediana_impares():
    r=calcular_metricas(['10.00','20.00','90.00'])
    assert r['total_ventas']=='120.00' and r['ticket_promedio']=='40.00' and r['mediana_ventas']=='20.00'

def test_media_mediana_pares():
    r=calcular_metricas(['10.00','20.00'])
    assert r['mediana_ventas']=='15.00'

def test_precision_decimal():
    r=calcular_metricas(['0.10','0.20','0.20'])
    assert r['total_ventas']=='0.50' and r['ticket_promedio']=='0.17'

def test_importe_invalido():
    with pytest.raises(ValueError): calcular_metricas(['NaN'])

def test_importe_negativo():
    with pytest.raises(ValueError): calcular_metricas([Decimal('-1')])
