"""Contrato HTTP aislado; no sustituye pruebas PostgreSQL reales."""
from datetime import date
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.services.analytics_resumen_service import AnalyticsResumenError


def _respuesta(inicio, fin):
    kpi = {'cantidad_ventas': 1, 'total_ventas': '10.00', 'ticket_promedio': '10.00'}
    return {'periodo': {'fecha_inicio': inicio, 'fecha_fin': fin},
            'periodo_anterior': {'fecha_inicio': date(2026, 9, 1), 'fecha_fin': date(2026, 9, 1)},
            'kpis': kpi, 'kpis_periodo_anterior': kpi,
            'variacion_porcentual_ventas': '0.00',
            'pedidos_por_estado': {'BORRADOR': 0, 'CONFIRMADO': 1, 'COMPLETADO': 0, 'CANCELADO': 0},
            'productos_destacados': [], 'clientes_destacados': [], 'vendedores_destacados': []}


def test_dashboard_comercial_en_openapi():
    operation = app.openapi()['paths']['/api/dashboard/comercial']['get']
    assert '200' in operation['responses']


def test_dashboard_comercial_respuesta(monkeypatch):
    from app.api.routes import dashboard
    def stub(db, *, usuario_id, fecha_inicio, fecha_fin, limite):
        assert usuario_id == 71
        assert limite == 3
        return _respuesta(fecha_inicio, fecha_fin)
    monkeypatch.setattr(dashboard, 'obtener_dashboard_comercial', stub)
    before = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=71, activo=True)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            r = client.get('/api/dashboard/comercial', params={
                'fecha_inicio':'2026-10-01','fecha_fin':'2026-10-01','limite':3})
        assert r.status_code == 200, r.text
        assert r.json()['kpis']['total_ventas'] == '10.00'
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)


def test_dashboard_comercial_error_permiso(monkeypatch):
    from app.api.routes import dashboard
    def stub(*args, **kwargs):
        raise AnalyticsResumenError('No autorizado para consultar Dashboard.')
    monkeypatch.setattr(dashboard, 'obtener_dashboard_comercial', stub)
    before = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=71, activo=True)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            r = client.get('/api/dashboard/comercial', params={
                'fecha_inicio':'2026-10-01','fecha_fin':'2026-10-01'})
        assert r.status_code == 403
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)


def test_dashboard_comercial_parametros_invalidos():
    before = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=71, activo=True)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get('/api/dashboard/comercial', params={
                'fecha_inicio': '2026-10-01', 'fecha_fin': '2026-10-31', 'limite': 21})
        assert response.status_code == 422, response.text
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(before)
