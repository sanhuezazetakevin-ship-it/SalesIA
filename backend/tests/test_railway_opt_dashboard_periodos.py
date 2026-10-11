"""Pruebas de optimización sin depender de la red ni de bases externas."""
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from sqlalchemy.dialects import postgresql
from app.services.dashboard_comercial_service import _agregados_periodos, _ventana
from app.services.analytics_resumen_service import AnalyticsResumenError
import pytest


class FakeDB:
    def __init__(self, result):
        self.result = result
        self.queries = []

    def execute(self, statement):
        self.queries.append(statement)
        return SimpleNamespace(one=lambda: self.result)


def test_kpis_ambos_periodos_una_consulta_y_precision():
    db = FakeDB((2, Decimal('55.01'), 1, Decimal('10.00')))
    actual, anterior = _agregados_periodos(db, 72, date(2026, 10, 1), date(2026, 10, 31),
                                            date(2026, 9, 1), date(2026, 9, 30))
    assert len(db.queries) == 1
    assert actual == {'cantidad_ventas': 2, 'total_ventas': '55.01', 'ticket_promedio': '27.51'}
    assert anterior == {'cantidad_ventas': 1, 'total_ventas': '10.00', 'ticket_promedio': '10.00'}


def test_kpis_periodos_vacios():
    db = FakeDB((0, 0, 0, 0))
    actual, anterior = _agregados_periodos(db, 72, date(2026, 10, 1), date(2026, 10, 31),
                                            date(2026, 9, 1), date(2026, 9, 30))
    assert actual['ticket_promedio'] is None and anterior['ticket_promedio'] is None
    assert actual['total_ventas'] == '0.00'


def test_consulta_exige_empresa_estado_y_fechas_en_sql():
    db = FakeDB((0, 0, 0, 0))
    _agregados_periodos(db, 999, date(2026, 10, 1), date(2026, 10, 31),
                        date(2026, 9, 1), date(2026, 9, 30))
    stmt = db.queries[0].compile(dialect=postgresql.dialect())
    sql = str(stmt)
    assert 'ventas.empresa_id' in sql
    assert 'ventas.estado' in sql
    assert 'FILTER (WHERE' in sql
    assert 'ventas.created_at' in sql
    assert 999 in stmt.params.values()


def test_ambos_periodos_conservan_limite(monkeypatch):
    import app.services.dashboard_comercial_service as service
    monkeypatch.setattr(service, 'MAX_VENTAS', 2)
    for datos in [(3, 0, 0, 0), (0, 0, 3, 0)]:
        with pytest.raises(AnalyticsResumenError):
            _agregados_periodos(FakeDB(datos), 1, date(2026, 10, 1), date(2026, 10, 31),
                                date(2026, 9, 1), date(2026, 9, 30))
