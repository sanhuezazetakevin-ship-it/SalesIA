"""Contratos de integración de React verificados mediante OpenAPI real, sin BD.

Ejecutar: python -m pytest tests/test_frontend_contract_ready.py -q
"""
from app.main import app
from app.schemas.dashboard_comercial import DashboardComercialResponse
from app.schemas.dashboard_series import SerieVentasResponse
from app.schemas.auth import LoginRequest, LoginResponse


def _operation(path, method):
    spec = app.openapi()
    assert path in spec['paths'], f'Ruta ausente: {path}'
    assert method in spec['paths'][path], f'Metodo ausente: {method} {path}'
    return spec['paths'][path][method]


def test_login_json_y_respuesta_token():
    op = _operation('/api/auth/login', 'post')
    assert 'application/json' in op['requestBody']['content']
    assert '200' in op['responses']
    assert {'email', 'password'} <= set(LoginRequest.model_fields)
    assert {'access_token', 'refresh_token', 'usuario'} <= set(LoginResponse.model_fields)


def test_dashboard_y_serie_con_filtros_requeridos():
    for path in ('/api/dashboard/comercial', '/api/dashboard/ventas/serie'):
        op = _operation(path, 'get')
        required = {p['name'] for p in op.get('parameters', []) if p.get('required')}
        assert {'fecha_inicio', 'fecha_fin'} <= required
        assert '200' in op['responses']


def test_dashboard_importes_decimales_y_kpis():
    kpis = DashboardComercialResponse.model_fields
    assert {'kpis', 'kpis_periodo_anterior', 'productos_destacados',
            'clientes_destacados', 'vendedores_destacados', 'variacion_porcentual_ventas'} <= set(kpis)
    from app.schemas.dashboard_comercial import KPIs
    assert KPIs.model_fields['total_ventas'].annotation is str
    assert SerieVentasResponse.model_fields['puntos'] is not None
    from app.schemas.dashboard_series import PuntoSerie
    assert PuntoSerie.model_fields['total_ventas'].annotation is str


def test_analytics_resumen_y_distribuciones_publicados():
    for path in ('/api/analytics/resumen', '/api/analytics/distribuciones'):
        op = _operation(path, 'get')
        assert '200' in op['responses']


def test_pdf_directo_parametros_enum_y_respuesta_binaria():
    op = _operation('/api/reportes/pdf-directo', 'get')
    required = {p['name'] for p in op.get('parameters', []) if p.get('required')}
    assert {'tipo', 'fecha_inicio', 'fecha_fin'} <= required
    from app.api.routes.reportes import Tipo
    assert set(Tipo.__args__) == {'VENTAS','ESTADISTICO','INVENTARIO','CLIENTES','RENDIMIENTO'}
    from app.api.routes.reportes import pdf_directo
    import inspect
    src = inspect.getsource(pdf_directo)
    assert "media_type='application/pdf'" in src
    assert 'generar_pdf_directo' in src


def test_rutas_requieren_dependencia_autenticacion():
    from app.api.dependencies import get_current_active_user
    from app.api.routes import dashboard, reportes, analytics_distribuciones
    import inspect
    for fn in (dashboard.dashboard_comercial, dashboard.serie_ventas,
               reportes.pdf_directo, analytics_distribuciones.consultar_distribuciones):
        assert 'usuario' in inspect.signature(fn).parameters
        dep = inspect.signature(fn).parameters['usuario'].default
        assert dep.dependency is get_current_active_user


def test_health_publicado():
    assert '200' in _operation('/health', 'get')['responses']
