"""FASE 14: pruebas no destructivas de contratos públicos y protección HTTP."""
from collections import Counter
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from app.main import app
from app.api.dependencies import get_current_active_user


def _routes():
    return {(method, route.path): route for route in app.routes if isinstance(route, APIRoute) for method in route.methods if method not in {'HEAD','OPTIONS'}}


def test_rutas_unicas():
    routes = [(m, r.path) for r in app.routes if isinstance(r, APIRoute) for m in r.methods if m not in {'HEAD','OPTIONS'}]
    duplicadas = [route for route, n in Counter(routes).items() if n > 1]
    assert not duplicadas, f'Rutas HTTP repetidas: {duplicadas}'


def test_endpoints_ultimas_fases_registrados():
    # La especificación OpenAPI expone los métodos públicos tal como los consume el frontend.
    # Además, test_rutas_unicas verifica directamente el registro ASGI de FastAPI.
    schema_paths = app.openapi()["paths"]
    routes = {
        (metodo.upper(), ruta)
        for ruta, operaciones in schema_paths.items()
        for metodo in operaciones
        if metodo.lower() in {"get", "post", "put", "patch", "delete"}
    }
    requeridas = [
        ('GET','/api/dashboard/ventas/serie'), ('GET','/api/dashboard/comercial'),
        ('POST','/api/insights/generar'), ('GET','/api/insights'),
        ('GET','/api/insights/{insight_id}'), ('PATCH','/api/insights/{insight_id}/estado'),
        ('GET','/api/reportes/previsualizar'), ('POST','/api/reportes/generar'),
        ('GET','/api/reportes'), ('GET','/api/reportes/{reporte_id}'),
        ('GET','/api/reportes/{reporte_id}/descargar'), ('GET','/api/reportes/imprimible'),
        ('GET','/api/auditoria'),
    ]
    faltantes = [ruta for ruta in requeridas if ruta not in routes]
    assert not faltantes, f"Endpoints que faltan en OpenAPI: {faltantes}"


def test_endpoints_sensibles_requieren_usuario_autenticado():
    for (method, path), route in _routes().items():
        if path.startswith(('/api/dashboard','/api/insights','/api/reportes','/api/auditoria')):
            deps = [dep.call for dep in route.dependant.dependencies]
            assert get_current_active_user in deps, f'Falta dependencia de autenticación: {method} {path}'


def test_openapi_contiene_ultimas_fases_y_sin_duplicados():
    spec = app.openapi()
    assert spec['openapi'].startswith('3.')
    for path in ('/api/dashboard/comercial', '/api/insights', '/api/reportes', '/api/auditoria'):
        assert path in spec['paths']
    ids = [op.get('operationId') for data in spec['paths'].values() for op in data.values() if isinstance(op, dict) and 'operationId' in op]
    assert len(ids) == len(set(ids)), 'OperationId duplicados'


def test_cabeceras_de_seguridad_health_y_sin_operaciones_db():
    with TestClient(app) as client:
        response = client.get('/health')
    assert response.status_code == 200
    assert response.headers.get('x-content-type-options') == 'nosniff'
    assert response.headers.get('x-frame-options') == 'DENY'
    assert response.headers.get('cache-control') == 'no-store'


def test_limites_de_validacion_con_autenticacion_simulada():
    from app.database.connection import get_db
    from types import SimpleNamespace
    anteriores = app.dependency_overrides.copy()
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=1)
    app.dependency_overrides[get_db] = lambda: object()
    try:
        with TestClient(app) as client:
            assert client.get('/api/dashboard/comercial?fecha_inicio=2026-01-01&fecha_fin=2026-01-31&limite=21').status_code == 422
            assert client.get('/api/reportes?limite=101').status_code == 422
            assert client.get('/api/auditoria?limite=101').status_code == 422
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)
