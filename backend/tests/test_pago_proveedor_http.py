"""6 pruebas HTTP sobre fixture db_testing transaccional.
Requiere tests/test_orden_compra_service.py y tests/conftest.py ya presentes.
"""
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.main import app
from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.models.orden_compra import OrdenCompra
from app.models.pago_proveedor import PagoProveedor
from app.models.movimiento_inventario import MovimientoInventario
from app.services.orden_compra_service import crear_orden_compra, confirmar_orden_compra
from tests.test_orden_compra_service import preparar

BASE = '/api/compras/pagos'
PERMISOS = ('proveedores.ver', 'proveedores.crear', 'proveedores.editar',
           'compras.ver', 'compras.crear', 'compras.confirmar', 'compras.cancelar',
           'pagos_proveedores.ver', 'pagos_proveedores.registrar', 'pagos_proveedores.anular')

@pytest.fixture
def cliente_pagos(db_testing):
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

def autenticar(db, escenario):
    usuario = db.get(Usuario, escenario['usuario_id'])
    app.dependency_overrides[get_current_user] = lambda: usuario

def escenario_pago(db, permisos=PERMISOS):
    e, proveedor, producto = preparar(db, permisos=permisos)
    orden = crear_orden_compra(db, usuario_id=e['usuario_id'], proveedor_id=proveedor.id,
        detalles=[{'producto_id': producto.id, 'cantidad': '2',
                   'precio_unitario': '30.00', 'impuesto': '10.80'}])
    confirmar_orden_compra(db, usuario_id=e['usuario_id'], orden_id=orden.id)
    return e, orden

def payload(orden, monto='20.00', **kwargs):
    return {'orden_id': orden.id, 'monto': monto, 'medio_pago': 'TRANSFERENCIA', **kwargs}

def test_pagos_exigen_autenticacion(cliente_pagos):
    assert cliente_pagos.get(BASE).status_code == 401
    assert cliente_pagos.post(BASE, json={}).status_code == 401

def test_pagos_parciales_completos_sin_inventario(cliente_pagos, db_testing):
    e, orden = escenario_pago(db_testing)
    autenticar(db_testing, e)
    antes = db_testing.scalar(select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.empresa_id == e['empresa_id']))
    a = cliente_pagos.post(BASE, json=payload(orden))
    assert a.status_code == 201, a.text
    assert a.json()['monto'] == '20.00'
    db_testing.refresh(orden)
    assert orden.estado_pago == 'PARCIAL'
    b = cliente_pagos.post(BASE, json=payload(orden, '50.80'))
    assert b.status_code == 201, b.text
    db_testing.refresh(orden)
    assert orden.estado_pago == 'PAGADO' and orden.estado == 'CONFIRMADA'
    despues = db_testing.scalar(select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.empresa_id == e['empresa_id']))
    assert antes == despues

def test_consultar_y_listar_pagos(cliente_pagos, db_testing):
    e, orden = escenario_pago(db_testing)
    autenticar(db_testing, e)
    a = cliente_pagos.post(BASE, json=payload(orden))
    assert a.status_code == 201, a.text
    r = cliente_pagos.get(BASE, params={'orden_id': orden.id, 'estado': 'REGISTRADO'})
    assert r.status_code == 200 and r.json()['total'] == 1, r.text
    consulta = cliente_pagos.get(f"{BASE}/{a.json()['id']}")
    assert consulta.status_code == 200 and consulta.json()['id'] == a.json()['id'], consulta.text

def test_idempotencia_y_sobrepago(cliente_pagos, db_testing):
    e, orden = escenario_pago(db_testing)
    autenticar(db_testing, e)
    p = payload(orden, '60.00', idempotency_key='http-pago-unico')
    a = cliente_pagos.post(BASE, json=p)
    b = cliente_pagos.post(BASE, json=p)
    assert a.status_code == 201 and b.status_code == 201, (a.text, b.text)
    assert a.json()['id'] == b.json()['id']
    conflicto = cliente_pagos.post(BASE, json=payload(orden, '30.00', idempotency_key='http-pago-unico'))
    assert conflicto.status_code == 409, conflicto.text
    exceso = cliente_pagos.post(BASE, json=payload(orden, '20.00'))
    assert exceso.status_code == 409, exceso.text
    assert db_testing.scalar(select(func.count()).select_from(PagoProveedor).where(
        PagoProveedor.orden_id == orden.id)) == 1

def test_anular_pago_recalcula_estado(cliente_pagos, db_testing):
    e, orden = escenario_pago(db_testing)
    autenticar(db_testing, e)
    r = cliente_pagos.post(BASE, json=payload(orden, '70.80'))
    assert r.status_code == 201, r.text
    pago_id = r.json()['id']
    anular = cliente_pagos.post(f'{BASE}/{pago_id}/anular')
    assert anular.status_code == 200 and anular.json()['estado'] == 'ANULADO', anular.text
    db_testing.refresh(orden)
    assert orden.estado_pago == 'PENDIENTE'
    repetido = cliente_pagos.post(f'{BASE}/{pago_id}/anular')
    assert repetido.status_code == 409, repetido.text

def test_validaciones_permisos_y_multiempresa(cliente_pagos, db_testing):
    a, orden_a = escenario_pago(db_testing)
    b, orden_b = escenario_pago(db_testing)
    autenticar(db_testing, b)
    nuevo = cliente_pagos.post(BASE, json=payload(orden_b))
    assert nuevo.status_code == 201, nuevo.text
    autenticar(db_testing, a)
    assert cliente_pagos.get(f"{BASE}/{nuevo.json()['id']}").status_code == 404
    assert cliente_pagos.post(f"{BASE}/{nuevo.json()['id']}/anular").status_code == 404
    assert cliente_pagos.get(BASE).json()['total'] == 0
    assert cliente_pagos.post(BASE, json=payload(orden_b)).status_code == 404
    assert cliente_pagos.post(BASE, json=payload(orden_a, '-1')).status_code == 422
    assert cliente_pagos.get(BASE, params={'estado': 'DESCONOCIDO'}).status_code == 400
