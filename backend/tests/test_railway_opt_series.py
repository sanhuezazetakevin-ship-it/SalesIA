"""Regresión del optimizador de series: ninguna dependencia de PostgreSQL real."""
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.services.dashboard_series_service import obtener_serie_ventas


class FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.calls = 0
        self.stmt = None

    def execute(self, stmt):
        self.calls += 1
        self.stmt = stmt
        return SimpleNamespace(all=lambda: self.rows)


def test_serie_optimizada_una_consulta_y_dias_vacios():
    db = FakeDB([(datetime(2026, 10, 1), 2, Decimal('20.10')),
                 (datetime(2026, 10, 3), 1, Decimal('9.90'))])
    with patch('app.services.dashboard_series_service._validar_operador',
               return_value=(object(), SimpleNamespace(id=7))):
        result = obtener_serie_ventas(db, usuario_id=2, fecha_inicio=date(2026,10,1),
                                      fecha_fin=date(2026,10,3))
    assert db.calls == 1
    assert [x['cantidad_ventas'] for x in result['puntos']] == [2,0,1]
    assert [x['total_ventas'] for x in result['puntos']] == ['20.10','0.00','9.90']
    sql = str(db.stmt.compile())
    assert 'GROUP BY' in sql
    assert 'ventas' in sql.lower()


def test_serie_optimizada_meses_vacios():
    db = FakeDB([(datetime(2026,11,1), 1, Decimal('12.50'))])
    with patch('app.services.dashboard_series_service._validar_operador',
               return_value=(object(), SimpleNamespace(id=7))):
        result = obtener_serie_ventas(db, usuario_id=2, fecha_inicio=date(2026,11,20),
                                      fecha_fin=date(2027,1,3), agrupacion='mes')
    assert [p['fecha'] for p in result['puntos']] == ['2026-11-01','2026-12-01','2027-01-01']
    assert [p['cantidad_ventas'] for p in result['puntos']] == [1,0,0]


def test_serie_respeta_maximo_registros():
    import pytest
    from app.services.analytics_resumen_service import AnalyticsResumenError, MAX_VENTAS
    db = FakeDB([(datetime(2026,10,1), MAX_VENTAS + 1, Decimal('800.00'))])
    with patch('app.services.dashboard_series_service._validar_operador',
               return_value=(object(), SimpleNamespace(id=7))):
        with pytest.raises(AnalyticsResumenError):
            obtener_serie_ventas(db, usuario_id=2, fecha_inicio=date(2026,10,1),
                                  fecha_fin=date(2026,10,3))


def test_serie_filtra_tenant_y_estado_confirmado():
    db = FakeDB([])
    with patch('app.services.dashboard_series_service._validar_operador',
               return_value=(object(), SimpleNamespace(id=7))):
        obtener_serie_ventas(db, usuario_id=2, fecha_inicio=date(2026,10,1),
                             fecha_fin=date(2026,10,3))
    query = db.stmt.compile(compile_kwargs={'literal_binds': True})
    sql = str(query)
    assert 'empresa_id' in sql
    assert 'CONFIRMADA' in sql
    assert '7' in sql
