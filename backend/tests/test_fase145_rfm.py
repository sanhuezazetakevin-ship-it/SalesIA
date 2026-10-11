from datetime import date,timedelta
from app.services.mejoras145_calculos import rfm_cliente
from pytest import raises


def test_rfm_cero():
    assert rfm_cliente(None,0,0,date(2026,10,10))['segmento']=='SIN_COMPRAS'

def test_rfm_alto_valor():
    r=rfm_cliente(date(2026,10,1),12,6000,date(2026,10,10))
    assert (r['r'],r['f'],r['m'])==(5,5,5)
    assert r['segmento']=='ALTO_VALOR'

def test_rfm_reactivacion():
    r=rfm_cliente(date(2025,1,1),3,700,date(2026,10,10))
    assert r['segmento']=='REACTIVACION'

def test_rfm_invalidos():
    with raises(ValueError): rfm_cliente(date(2026,10,11),1,100,date(2026,10,10))
    with raises(ValueError): rfm_cliente(date(2026,10,1),-1,100,date(2026,10,10))
