"""FASE 09-D.4: pruebas PostgreSQL Testing mediante fixture db_testing."""
from decimal import Decimal
import pytest
from sqlalchemy import select, func
from app.models.orden_compra import OrdenCompra
from app.models.pago_proveedor import PagoProveedor
from app.models.movimiento_inventario import MovimientoInventario
from app.models.auditoria import Auditoria
from app.services.orden_compra_service import crear_orden_compra, confirmar_orden_compra
from app.services.pago_proveedor_service import (
    PagoProveedorServiceError, registrar_pago_proveedor, anular_pago_proveedor,
    obtener_pago_proveedor, listar_pagos_proveedor,
)
from tests.test_orden_compra_service import preparar as preparar_orden

PERMISOS = ('proveedores.ver', 'proveedores.crear', 'proveedores.editar',
            'compras.ver', 'compras.crear', 'compras.confirmar', 'compras.cancelar',
            'pagos_proveedores.ver', 'pagos_proveedores.registrar', 'pagos_proveedores.anular')

def escenario(db, permisos=PERMISOS):
    e, proveedor, producto = preparar_orden(db, permisos=permisos)
    orden = crear_orden_compra(db, usuario_id=e['usuario_id'], proveedor_id=proveedor.id,
        detalles=[{'producto_id': producto.id, 'cantidad': '2', 'precio_unitario': '30.00', 'impuesto': '10.80'}])
    confirmar_orden_compra(db, usuario_id=e['usuario_id'], orden_id=orden.id)
    return e, orden

def pagar(db, e, orden, monto='20.00', **kwargs):
    return registrar_pago_proveedor(db, usuario_id=e['usuario_id'], orden_id=orden.id,
                                   monto=monto, medio_pago='TRANSFERENCIA', **kwargs)

def test_pagos_parciales_completo_sin_inventario(db_testing):
    e, orden = escenario(db_testing)
    antes = db_testing.scalar(select(func.count()).select_from(MovimientoInventario).where(MovimientoInventario.empresa_id == e['empresa_id']))
    p1 = pagar(db_testing, e, orden)
    assert p1.monto == Decimal('20.00')
    assert db_testing.get(OrdenCompra, orden.id).estado_pago == 'PARCIAL'
    pagar(db_testing, e, orden, '50.80')
    db_testing.refresh(orden)
    assert orden.estado_pago == 'PAGADO' and orden.estado == 'CONFIRMADA'
    assert db_testing.scalar(select(func.count()).select_from(MovimientoInventario).where(MovimientoInventario.empresa_id == e['empresa_id'])) == antes

def test_sobrepago_rollback_y_estado(db_testing):
    e, orden = escenario(db_testing)
    pagar(db_testing, e, orden, '60.00')
    with pytest.raises(PagoProveedorServiceError, match='excede'):
        pagar(db_testing, e, orden, '20.00')
    db_testing.refresh(orden)
    assert orden.estado_pago == 'PARCIAL'
    assert db_testing.scalar(select(func.count()).select_from(PagoProveedor).where(PagoProveedor.orden_id == orden.id)) == 1

def test_idempotencia_repetida_y_conflicto(db_testing):
    e, orden = escenario(db_testing)
    p = pagar(db_testing, e, orden, '15.00', idempotency_key='pago-09d4-1')
    repetido = pagar(db_testing, e, orden, '15.00', idempotency_key='pago-09d4-1')
    assert p.id == repetido.id
    with pytest.raises(PagoProveedorServiceError, match='Idempotency key'):
        pagar(db_testing, e, orden, '16.00', idempotency_key='pago-09d4-1')
    assert db_testing.scalar(select(func.count()).select_from(PagoProveedor).where(PagoProveedor.orden_id == orden.id)) == 1

def test_anular_recalcula_y_protege_duplicado(db_testing):
    e, orden = escenario(db_testing)
    p = pagar(db_testing, e, orden, '70.80')
    assert anular_pago_proveedor(db_testing, usuario_id=e['usuario_id'], pago_id=p.id).estado == 'ANULADO'
    db_testing.refresh(orden)
    assert orden.estado_pago == 'PENDIENTE'
    with pytest.raises(PagoProveedorServiceError, match='ya anulado'):
        anular_pago_proveedor(db_testing, usuario_id=e['usuario_id'], pago_id=p.id)

def test_consulta_auditoria_y_validacion(db_testing):
    e, orden = escenario(db_testing)
    p = pagar(db_testing, e, orden)
    assert obtener_pago_proveedor(db_testing, usuario_id=e['usuario_id'], pago_id=p.id).id == p.id
    assert listar_pagos_proveedor(db_testing, usuario_id=e['usuario_id'], orden_id=orden.id)['total'] == 1
    assert db_testing.scalar(select(func.count()).select_from(Auditoria).where(Auditoria.empresa_id == e['empresa_id'], Auditoria.entidad == 'pagos_proveedores')) == 1
    with pytest.raises(PagoProveedorServiceError, match='Monto'):
        pagar(db_testing, e, orden, '-10')

def test_multiempresa_no_ve_ni_anula(db_testing):
    a, orden_a = escenario(db_testing)
    b, orden_b = escenario(db_testing)
    pago_b = pagar(db_testing, b, orden_b)
    with pytest.raises(PagoProveedorServiceError, match='no encontrado'):
        obtener_pago_proveedor(db_testing, usuario_id=a['usuario_id'], pago_id=pago_b.id)
    with pytest.raises(PagoProveedorServiceError, match='no encontrado'):
        anular_pago_proveedor(db_testing, usuario_id=a['usuario_id'], pago_id=pago_b.id)
    assert listar_pagos_proveedor(db_testing, usuario_id=a['usuario_id'])['total'] == 0
