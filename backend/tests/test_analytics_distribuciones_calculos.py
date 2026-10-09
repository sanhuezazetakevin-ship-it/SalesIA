from decimal import Decimal
import pytest
from app.services.analytics_distribuciones_service import frecuencias_categoricas,frecuencias_intervalos

def test_categorica_vacia():
    assert frecuencias_categoricas([],categorias=['PENDIENTE'])==[{'categoria':'PENDIENTE','frecuencia_absoluta':0,'frecuencia_relativa':'0.0000'}]

def test_categorica_conteos():
    filas=frecuencias_categoricas(['PAGADO','PENDIENTE','PAGADO'],categorias=['PENDIENTE','PARCIAL','PAGADO'])
    assert [f['frecuencia_absoluta'] for f in filas]==[1,0,2]

def test_categorica_proporciones():
    filas=frecuencias_categoricas(['A','A','B','B'])
    assert [f['frecuencia_relativa'] for f in filas]==['0.5000','0.5000']

def test_intervalos_vacios():
    assert frecuencias_intervalos([])==[]

def test_intervalos_iguales():
    assert frecuencias_intervalos([Decimal('12.00')]*3)==[{'desde':'12.00','hasta':'12.00','frecuencia_absoluta':3,'frecuencia_relativa':'1.0000'}]

def test_intervalos_extremos():
    filas=frecuencias_intervalos(['0','10','20','30'],intervalos=3)
    assert [f['frecuencia_absoluta'] for f in filas]==[1,1,2]
    assert sum(f['frecuencia_absoluta'] for f in filas)==4

def test_intervalos_rechaza_negativos():
    with pytest.raises(ValueError): frecuencias_intervalos([-1,1])

def test_intervalos_rechaza_nan():
    with pytest.raises(ValueError): frecuencias_intervalos(['NaN'])

def test_intervalos_rango_invalido():
    with pytest.raises(ValueError): frecuencias_intervalos([1,2],intervalos=0)
