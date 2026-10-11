"""Contrato HTTP sin conectarse a PostgreSQL; la autorización real se prueba en integración."""
from types import SimpleNamespace
from datetime import date
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.api.routes.dashboard import obtener_serie_ventas


def test_dashboard_endpoint_documentado():
    schema = app.openapi()
    assert '/api/dashboard/ventas/serie' in schema['paths']
    operation = schema['paths']['/api/dashboard/ventas/serie']['get']
    assert '200' in operation['responses']
    assert '401' in operation['responses'] or any(x.get('security') for x in [operation])


def test_dashboard_http_con_dependencias_simuladas(monkeypatch):
    from app.api.routes import dashboard
    def stub(db, *, usuario_id, fecha_inicio, fecha_fin, agrupacion):
        assert usuario_id == 71
        assert agrupacion == 'dia'
        return {'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'agrupacion': agrupacion,
                'puntos': [{'fecha': fecha_inicio, 'cantidad_ventas': 2, 'total_ventas': '23.50'}]}
    monkeypatch.setattr(dashboard, 'obtener_serie_ventas', stub)
    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=71, activo=True)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            res = client.get('/api/dashboard/ventas/serie', params={'fecha_inicio':'2026-10-01','fecha_fin':'2026-10-01'})
        assert res.status_code == 200, res.text
        assert res.json()['puntos'][0]['total_ventas'] == '23.50'
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
