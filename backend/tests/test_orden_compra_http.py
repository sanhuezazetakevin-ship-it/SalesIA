"""HTTP órdenes de compra: PostgreSQL Testing, rollback externo obligatorio."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.connection import get_db
from app.api.dependencies import get_current_user
from app.models.usuario import Usuario
from app.models.inventario import Inventario
from sqlalchemy import select, func
from tests.test_orden_compra_service import preparar

BASE = '/api/compras/ordenes'
PERMISOS = ('proveedores.ver', 'proveedores.crear', 'proveedores.editar',
            'compras.ver', 'compras.crear', 'compras.confirmar', 'compras.cancelar')

@pytest.fixture
def cliente_compras(db_testing):
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


def autenticar(db, e):
    usuario = db.get(Usuario, e['usuario_id'])
    app.dependency_overrides[get_current_user] = lambda: usuario


def carga(p, producto, cantidad='2.000'):
    return {'proveedor_id': p.id, 'detalles': [
        {'producto_id': producto.id, 'cantidad': cantidad,
         'precio_unitario': '30.00', 'impuesto': '10.80'}]}


def test_exige_autenticacion(cliente_compras):
    assert cliente_compras.get(BASE).status_code == 401
    assert cliente_compras.post(BASE, json={}).status_code == 401


def test_crear_listar_obtener_detalles(cliente_compras, db_testing):
    e, p, prod = preparar(db_testing)
    autenticar(db_testing, e)
    r = cliente_compras.post(BASE, json=carga(p, prod))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body['estado'] == 'BORRADOR' and body['total'] == '70.80'
    assert len(body['detalles']) == 1 and body['detalles'][0]['producto_id'] == prod.id
    listado = cliente_compras.get(BASE, params={'estado': 'BORRADOR', 'proveedor_id': p.id})
    assert listado.status_code == 200 and listado.json()['total'] == 1, listado.text
    detalle = cliente_compras.get(f"{BASE}/{body['id']}")
    assert detalle.status_code == 200 and detalle.json()['detalles'][0]['producto_id'] == prod.id


def test_confirmar_sin_cambiar_inventario(cliente_compras, db_testing):
    e, p, prod = preparar(db_testing)
    autenticar(db_testing, e)
    r = cliente_compras.post(BASE, json=carga(p, prod))
    assert r.status_code == 201, r.text
    antes = db_testing.scalar(select(func.count()).select_from(Inventario).where(Inventario.empresa_id == e['empresa_id']))
    oid = r.json()['id']
    confirmada = cliente_compras.post(f'{BASE}/{oid}/confirmar')
    assert confirmada.status_code == 200 and confirmada.json()['estado'] == 'CONFIRMADA', confirmada.text
    assert cliente_compras.post(f'{BASE}/{oid}/confirmar').status_code == 409
    despues = db_testing.scalar(select(func.count()).select_from(Inventario).where(Inventario.empresa_id == e['empresa_id']))
    assert antes == despues


def test_cancelacion_solo_borrador(cliente_compras, db_testing):
    e, p, prod = preparar(db_testing)
    autenticar(db_testing, e)
    orden = cliente_compras.post(BASE, json=carga(p, prod))
    assert orden.status_code == 201, orden.text
    oid = orden.json()['id']
    assert cliente_compras.post(f'{BASE}/{oid}/cancelar').json()['estado'] == 'CANCELADA'
    assert cliente_compras.post(f'{BASE}/{oid}/confirmar').status_code == 409


def test_rechazo_validaciones_y_permiso(cliente_compras, db_testing):
    e, p, prod = preparar(db_testing)
    autenticar(db_testing, e)
    r = cliente_compras.post(BASE, json=carga(p, prod, cantidad='-1'))
    assert r.status_code == 422, r.text
    e2, p2, prod2 = preparar(db_testing, permisos=('compras.ver', 'proveedores.crear'))
    autenticar(db_testing, e2)
    r = cliente_compras.post(BASE, json=carga(p2, prod2))
    assert r.status_code == 403, r.text


def test_aislamiento_multiempresa(cliente_compras, db_testing):
    a, pa, prod_a = preparar(db_testing)
    b, pb, prod_b = preparar(db_testing)
    autenticar(db_testing, b)
    creado = cliente_compras.post(BASE, json=carga(pb, prod_b))
    assert creado.status_code == 201, creado.text
    oid = creado.json()['id']
    autenticar(db_testing, a)
    assert cliente_compras.get(f'{BASE}/{oid}').status_code == 404
    assert cliente_compras.get(BASE).json()['total'] == 0
    assert cliente_compras.post(f'{BASE}/{oid}/confirmar').status_code == 404
