from decimal import Decimal
from app.services.dashboard_comercial_service import _money, _rate, _ventana
from datetime import date, timezone

def test_dinero_redondeo():
    assert _money(Decimal('10.125')) == '10.13'

def test_porcentaje():
    assert _rate('150', '100') == '50.00'
    assert _rate('50', '100') == '-50.00'

def test_base_cero():
    assert _rate('10', '0') is None

def test_intervalo_utc_exclusivo():
    a, b = _ventana(date(2026, 1, 1), date(2026, 1, 31))
    assert a.tzinfo == timezone.utc
    assert b.date() == date(2026, 2, 1)
