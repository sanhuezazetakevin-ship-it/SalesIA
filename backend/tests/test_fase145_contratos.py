"""FASE 14.5: contrato publico y autenticacion declarada en el router."""
from fastapi.routing import APIRoute
from app.main import app
from app.api.dependencies import get_current_active_user
from app.api.routes.mejoras145 import router as mejoras_router


def _operaciones_publicadas():
    return {
        (path, method.upper())
        for path, operations in app.openapi().get('paths', {}).items()
        for method in operations
        if method.lower() in {'get', 'post', 'put', 'patch', 'delete'}
    }


def test_rutas_nuevas_registradas():
    rutas = _operaciones_publicadas()
    for ruta in ('dashboard', 'inventario', 'clientes', 'notificaciones', 'seguridad'):
        assert (f'/api/mejoras/{ruta}', 'GET') in rutas, f'Ruta no publicada: {ruta}'


def test_nuevas_rutas_requieren_autenticacion():
    rutas = [r for r in mejoras_router.routes if isinstance(r, APIRoute)]
    assert rutas, 'Router de mejoras sin operaciones'
    for ruta in rutas:
        assert any(dep.call is get_current_active_user for dep in ruta.dependant.dependencies), ruta.path
