"""Contrato de rutas aislado de PostgreSQL (no reemplaza test de integración real)."""
from datetime import datetime, timezone
from types import SimpleNamespace
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.services.insights_service import InsightsError


def _registro():
    now = datetime(2026, 10, 10, tzinfo=timezone.utc)
    return SimpleNamespace(id=10, empresa_id=4, analisis_estadistico_id=3,
        analisis_probabilidad_id=None, tipo_insight='VENTAS', prioridad='BAJA',
        titulo='Resumen del ticket', descripcion='Evidencia descriptiva.',
        recomendacion='Revisar resultados.', estado='NUEVO',
        datos_soporte={'regla':'TICKET_DESCRIPTIVO'}, created_at=now, updated_at=now)


def _overrides():
    original = dict(app.dependency_overrides)
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=7)
    app.dependency_overrides[get_db] = lambda: object()
    return original


def _restore(original):
    app.dependency_overrides.clear()
    app.dependency_overrides.update(original)


def test_insights_rutas_openapi():
    rutas = app.openapi()['paths']
    assert '/api/insights/generar' in rutas
    assert '/api/insights' in rutas
    assert '/api/insights/{insight_id}' in rutas
    assert '/api/insights/{insight_id}/estado' in rutas


def test_insights_http_listar_y_detalle(monkeypatch):
    from app.api.routes import insights
    monkeypatch.setattr(insights, 'listar_insights', lambda *a, **k: [_registro()])
    monkeypatch.setattr(insights, 'obtener_insight', lambda *a, **k: _registro())
    before = _overrides()
    try:
        with TestClient(app) as client:
            r = client.get('/api/insights')
            d = client.get('/api/insights/10')
        assert r.status_code == 200, r.text
        assert r.json()['items'][0]['datos_soporte']['regla'] == 'TICKET_DESCRIPTIVO'
        assert d.status_code == 200, d.text
    finally:
        _restore(before)


def test_insights_generar(monkeypatch):
    from app.api.routes import insights
    class FakeDB:
        def commit(self): pass
        def refresh(self, value): pass
        def rollback(self): pass
    monkeypatch.setattr(insights, 'generar_insights', lambda *a, **k: [_registro()])
    before = _overrides()
    app.dependency_overrides[get_db] = lambda: FakeDB()
    try:
        with TestClient(app) as client:
            r = client.post('/api/insights/generar', json={'tipo':'estadistico', 'analisis_id':3})
        assert r.status_code == 201, r.text
        assert r.json()[0]['id'] == 10
    finally:
        _restore(before)


def test_insights_error_permiso(monkeypatch):
    from app.api.routes import insights
    def denegar(*a, **k):
        raise InsightsError('No autorizado para Insights.', 403)
    monkeypatch.setattr(insights, 'listar_insights', denegar)
    before = _overrides()
    try:
        with TestClient(app) as client:
            r = client.get('/api/insights')
        assert r.status_code == 403
    finally:
        _restore(before)


def test_insights_parametros_incorrectos():
    before = _overrides()
    try:
        with TestClient(app) as client:
            r = client.get('/api/insights', params={'limite':101})
            p = client.post('/api/insights/generar', json={'tipo':'incorrecto', 'analisis_id':-1})
        assert r.status_code == 422
        assert p.status_code == 422
    finally:
        _restore(before)
