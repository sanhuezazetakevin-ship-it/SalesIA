"""Pruebas HTTP sobre fixture PostgreSQL aislada db_testing.
Requiere tests.test_orden_compra_service y tests.test_proveedor_service existentes.
"""
import pytest
from decimal import Decimal
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.models.orden_compra_detalle import OrdenCompraDetalle
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.services.orden_compra_service import crear_orden_compra, confirmar_orden_compra
from tests.test_orden_compra_service import preparar

BASE = '/api/compras/recepciones'
PERMISOS = ('proveedores.ver','proveedores.crear','proveedores.editar',
           'compras.ver','compras.crear','compras.confirmar','compras.cancelar',
           'recepciones.ver','recepciones.crear')

@pytest.fixture
def cliente_recepciones(db_testing):
    originales = app.dependency_overrides.copy()
    def db_override():
        yield db_testing
    app.dependency_overrides[get_db] = db_override
    try:
        with TestClient(app) as cliente:
            yield cliente
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(originales)

def autenticar(db, e):
    usuario = db.get(Usuario, e['usuario_id'])
    app.dependency_overrides[get_current_user] = lambda: usuario

def escenario(db, permisos=PERMISOS):
    e, proveedor, producto = preparar(db, permisos=permisos)
    orden = crear_orden_compra(db, usuario_id=e['usuario_id'], proveedor_id=proveedor.id,
        detalles=[{'producto_id': producto.id, 'cantidad': '10.000', 'precio_unitario': '30.00'}])
    confirmar_orden_compra(db, usuario_id=e['usuario_id'], orden_id=orden.id)
    linea_id = db.scalar(select(OrdenCompraDetalle.id).where(OrdenCompraDetalle.orden_id == orden.id))
    return e, orden, producto, linea_id

def payload(orden, linea_id, cantidad='4.000', key=None):
    return {'orden_id': orden.id, 'detalles': [
        {'orden_detalle_id': linea_id, 'cantidad_recibida': cantidad}], 'idempotency_key': key}

def test_recepciones_exigen_autenticacion(cliente_recepciones):
    assert cliente_recepciones.get(BASE).status_code == 401
    assert cliente_recepciones.post(BASE, json={}).status_code == 401

def test_recepcion_parcial_y_total_actualiza_inventario(cliente_recepciones, db_testing):
    e, orden, producto, linea = escenario(db_testing)
    autenticar(db_testing, e)
    r1 = cliente_recepciones.post(BASE, json=payload(orden, linea, '4.000'))
    assert r1.status_code == 201, r1.text
    assert r1.json()['estado'] == 'CONFIRMADA'
    assert r1.json()['detalles'][0]['cantidad_recibida'] == '4.000'
    r2 = cliente_recepciones.post(BASE, json=payload(orden, linea, '6.000'))
    assert r2.status_code == 201, r2.text
    stock = db_testing.scalar(select(Inventario).where(Inventario.empresa_id == e['empresa_id'], Inventario.producto_id == producto.id))
    assert Decimal(stock.cantidad_disponible) == Decimal('10.000')
    assert db_testing.scalar(select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.recepcion_compra_id.in_([r1.json()['id'], r2.json()['id']]))) == 2

def test_listar_y_consultar_detalles(cliente_recepciones, db_testing):
    e, orden, producto, linea = escenario(db_testing)
    autenticar(db_testing, e)
    creado = cliente_recepciones.post(BASE, json=payload(orden, linea))
    assert creado.status_code == 201, creado.text
    r = cliente_recepciones.get(BASE, params={'orden_id': orden.id})
    assert r.status_code == 200 and r.json()['total'] == 1, r.text
    detalle = cliente_recepciones.get(f"{BASE}/{creado.json()['id']}")
    assert detalle.status_code == 200 and len(detalle.json()['detalles']) == 1, detalle.text

def test_idempotencia_sin_nueva_entrada(cliente_recepciones, db_testing):
    e, orden, producto, linea = escenario(db_testing)
    autenticar(db_testing, e)
    p = payload(orden, linea, key='recepcion-http-123')
    primero = cliente_recepciones.post(BASE, json=p)
    segundo = cliente_recepciones.post(BASE, json=p)
    assert primero.status_code == 201 and segundo.status_code == 201, (primero.text, segundo.text)
    assert primero.json()['id'] == segundo.json()['id']
    stock = db_testing.scalar(select(Inventario.cantidad_disponible).where(Inventario.empresa_id == e['empresa_id'], Inventario.producto_id == producto.id))
    assert Decimal(stock) == Decimal('4.000')

def test_excedentes_y_validaciones(cliente_recepciones, db_testing):
    e, orden, producto, linea = escenario(db_testing)
    autenticar(db_testing, e)
    assert cliente_recepciones.post(BASE, json=payload(orden, linea, '-1')).status_code == 422
    respuesta = cliente_recepciones.post(BASE, json=payload(orden, linea, '11.000'))
    assert respuesta.status_code == 409, respuesta.text

def test_aislamiento_multiempresa(cliente_recepciones, db_testing):
    a, orden_a, producto_a, linea_a = escenario(db_testing)
    b, orden_b, producto_b, linea_b = escenario(db_testing)
    autenticar(db_testing, b)
    creado = cliente_recepciones.post(BASE, json=payload(orden_b, linea_b))
    assert creado.status_code == 201, creado.text
    autenticar(db_testing, a)
    assert cliente_recepciones.get(f"{BASE}/{creado.json()['id']}").status_code == 404
    assert cliente_recepciones.get(BASE).json()['total'] == 0
    assert cliente_recepciones.post(BASE, json=payload(orden_b, linea_b)).status_code == 404
