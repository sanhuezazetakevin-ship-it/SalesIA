from app.services.semana08_calculos import resumen_semana08, tabla_probabilidades
import pytest

def test_serie_conocida():
    r=resumen_semana08([1,2,3,4,5])
    assert r['media']==3 and r['mediana']==3
    assert r['varianza_poblacional']==2
    assert r['varianza_muestral']==2.5
    assert r['esperanza_empirica']==3
    assert sum(r['histograma']['valores'])==5

def test_sin_datos():
    assert resumen_semana08([])['sin_datos']

def test_una_observacion():
    assert resumen_semana08([50],hipotesis_media=10)['contraste']['estado']=='INSUFICIENTE'

def test_constantes():
    assert resumen_semana08([10,10,10],hipotesis_media=10)['contraste']['estado']=='NO_CALCULABLE'

def test_hipotesis_t():
    pytest.importorskip('scipy')
    r=resumen_semana08([10,11,12,13,14],hipotesis_media=10)
    assert r['contraste']['estado']=='CALCULADO'
    assert 0<=r['contraste']['valor_p']<=1
    assert r['contraste']['rechazar_hipotesis_nula'] is True

def test_invalidos():
    for valores in [[float('nan')],[-1],[float('inf')]]:
        with pytest.raises(ValueError): resumen_semana08(valores)
    with pytest.raises(ValueError): resumen_semana08([1],alfa=1)

def test_probabilidad():
    p=tabla_probabilidades({'PAGADO':3,'PENDIENTE':1})
    assert p['valores']==[0.75,0.25]
    assert tabla_probabilidades({})['sin_datos']
