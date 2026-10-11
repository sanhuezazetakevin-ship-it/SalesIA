from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import pytest
from app.services.dashboard_series_service import calcular_serie


def test_dias_sin_ventas_y_suma_decimal():
    r = [(datetime(2026, 10, 1, 20, tzinfo=timezone.utc), Decimal('0.10')),
         (datetime(2026, 10, 1, 22, tzinfo=timezone.utc), Decimal('0.20')),
         (datetime(2026, 10, 3, 1, tzinfo=timezone.utc), Decimal('10.00'))]
    salida = calcular_serie(r, fecha_inicio=date(2026, 10, 1), fecha_fin=date(2026, 10, 3))
    assert [(p['cantidad_ventas'], p['total_ventas']) for p in salida] == [(2, '0.30'), (0, '0.00'), (1, '10.00')]


def test_meses_incluidos_aun_sin_ventas():
    salida = calcular_serie([], fecha_inicio=date(2026, 11, 20), fecha_fin=date(2027, 1, 3), agrupacion='mes')
    assert [p['fecha'] for p in salida] == ['2026-11-01', '2026-12-01', '2027-01-01']


def test_convierte_fecha_con_offset_a_utc():
    instante = datetime(2026, 10, 1, 23, 0, tzinfo=timezone(timedelta(hours=-5)))
    salida = calcular_serie([(instante, Decimal('1.00'))], fecha_inicio=date(2026, 10, 2), fecha_fin=date(2026, 10, 2))
    assert salida[0]['total_ventas'] == '1.00'


def test_importe_invalido():
    with pytest.raises(ValueError):
        calcular_serie([(datetime.now(timezone.utc), Decimal('-1'))], fecha_inicio=date(2026, 1, 1), fecha_fin=date(2027, 1, 1))
