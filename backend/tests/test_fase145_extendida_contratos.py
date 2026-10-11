"""FASE 14.5 Semana 08 y notificaciones: contratos y dependencias."""
from fastapi.routing import APIRoute
from app.main import app
from app.api.dependencies import get_current_active_user
from app.api.routes.semana08 import router as semana08_router
from app.api.routes.notificaciones145 import router as notificaciones_router


def test_rutas_extensiones_presentes():
    routes = {
        (path, method.upper())
        for path, operations in app.openapi().get('paths', {}).items()
        for method in operations
        if method.lower() in {'get', 'post', 'put', 'patch', 'delete'}
    }
    requeridas = {
        ('/api/analytics/semana08', 'GET'),
        ('/api/mejoras/notificaciones-persistentes/sincronizar', 'POST'),
        ('/api/mejoras/notificaciones-persistentes', 'GET'),
        ('/api/mejoras/notificaciones-persistentes/{notificacion_id}/leida', 'PATCH'),
    }
    assert requeridas <= routes, f'Rutas ausentes en OpenAPI: {requeridas-routes}'


def test_rutas_extensiones_autenticadas():
    for router in (semana08_router, notificaciones_router):
        rutas = [r for r in router.routes if isinstance(r, APIRoute)]
        assert rutas, 'Router sin operaciones declaradas'
        for ruta in rutas:
            assert any(dep.call is get_current_active_user for dep in ruta.dependant.dependencies), ruta.path
