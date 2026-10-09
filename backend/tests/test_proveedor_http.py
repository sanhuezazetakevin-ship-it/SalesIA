"""HTTP proveedores: usa exclusivamente la fixture db_testing con rollback."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import get_db
from app.api.dependencies import get_current_user
from app.models.usuario import Usuario
from tests.test_pedido_service import preparar_empresa


@pytest.fixture
def cliente_proveedor(db_testing):
    anteriores = app.dependency_overrides.copy()

    def override_db():
        yield db_testing

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(anteriores)


def autenticar(db, escenario):
    usuario = db.get(Usuario, escenario['usuario_id'])
    app.dependency_overrides[get_current_user] = lambda: usuario
    return usuario


def test_requiere_jwt(cliente_proveedor):
    assert cliente_proveedor.get('/api/proveedores').status_code == 401
    assert cliente_proveedor.post('/api/proveedores', json={'razon_social': 'X'}).status_code == 401


def test_crear_listar_obtener(cliente_proveedor, db_testing):
    e = preparar_empresa(db_testing, permisos=('proveedores.ver', 'proveedores.crear', 'proveedores.editar'), con_impuesto=False)
    autenticar(db_testing, e)
    creado = cliente_proveedor.post('/api/proveedores', json={'razon_social':'Distribuidora Prueba', 'tipo_documento':'RUC', 'numero_documento':'20999999987'})
    assert creado.status_code == 201, creado.text
    pid = creado.json()['id']
    assert creado.json()['empresa_id'] == e['empresa_id']
    r = cliente_proveedor.get('/api/proveedores', params={'busqueda':'Distribuidora', 'pagina':1})
    assert r.status_code == 200 and r.json()['total'] == 1
    assert cliente_proveedor.get(f'/api/proveedores/{pid}').json()['id'] == pid


def test_actualizar_desactivar(cliente_proveedor, db_testing):
    e = preparar_empresa(db_testing, permisos=('proveedores.ver', 'proveedores.crear', 'proveedores.editar'), con_impuesto=False)
    autenticar(db_testing, e)
    creado = cliente_proveedor.post('/api/proveedores', json={'razon_social':'Original'})
    assert creado.status_code == 201, creado.text
    pid = creado.json()['id']
    cambiado = cliente_proveedor.patch(f'/api/proveedores/{pid}', json={'razon_social':'Actualizada'})
    assert cambiado.status_code == 200 and cambiado.json()['razon_social'] == 'Actualizada', cambiado.text
    borrado = cliente_proveedor.post(f'/api/proveedores/{pid}/desactivar')
    assert borrado.status_code == 200 and borrado.json()['activo'] is False, borrado.text


def test_rechaza_duplicado(cliente_proveedor, db_testing):
    e = preparar_empresa(db_testing, permisos=('proveedores.ver', 'proveedores.crear'), con_impuesto=False)
    autenticar(db_testing, e)
    data = {'razon_social':'Prueba', 'tipo_documento':'RUC', 'numero_documento':'20999999988'}
    assert cliente_proveedor.post('/api/proveedores', json=data).status_code == 201
    assert cliente_proveedor.post('/api/proveedores', json=data).status_code == 409


def test_sin_permiso(cliente_proveedor, db_testing):
    e = preparar_empresa(db_testing, permisos=('proveedores.ver',), con_impuesto=False)
    autenticar(db_testing, e)
    r = cliente_proveedor.post('/api/proveedores', json={'razon_social':'Denegado'})
    assert r.status_code == 403, r.text


def test_aislamiento_empresa(cliente_proveedor, db_testing):
    a = preparar_empresa(db_testing, permisos=('proveedores.ver', 'proveedores.crear'), con_impuesto=False)
    b = preparar_empresa(db_testing, permisos=('proveedores.ver', 'proveedores.crear'), con_impuesto=False)
    autenticar(db_testing, b)
    p = cliente_proveedor.post('/api/proveedores', json={'razon_social':'Empresa B'})
    assert p.status_code == 201, p.text
    autenticar(db_testing, a)
    assert cliente_proveedor.get(f"/api/proveedores/{p.json()['id']}").status_code == 404
    assert cliente_proveedor.get('/api/proveedores').json()['total'] == 0
