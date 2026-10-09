"""Integración PostgreSQL Testing: nunca usar con la base principal."""
from decimal import Decimal
import pytest
from sqlalchemy import select, func

from app.models.orden_compra import OrdenCompra
from app.models.orden_compra_detalle import OrdenCompraDetalle
from app.models.recepcion_compra_detalle import RecepcionCompraDetalle
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.auditoria import Auditoria
from app.services.orden_compra_service import confirmar_orden_compra
from app.services.recepcion_compra_service import (
    recibir_compra, obtener_recepcion_compra, listar_recepciones_compra,
    RecepcionCompraServiceError,
)
from tests.test_orden_compra_service import preparar, crear, PERMISOS

PERMISOS_REC = (*PERMISOS, 'recepciones.crear', 'recepciones.ver')


def escenario(db):
    e, p, producto = preparar(db, permisos=PERMISOS_REC)
    orden = crear(db, e, p, producto)
    confirmar_orden_compra(db, usuario_id=e['usuario_id'], orden_id=orden.id)
    detalle = db.scalar(select(OrdenCompraDetalle).where(OrdenCompraDetalle.orden_id == orden.id))
    return e, producto, orden, detalle


def recibir(db, e, orden, detalle, cantidad, **extra):
    return recibir_compra(db, usuario_id=e['usuario_id'], orden_id=orden.id,
        detalles=[{'orden_detalle_id': detalle.id, 'cantidad_recibida': cantidad}], **extra)


def test_parcial_y_total_stock_y_movimientos(db_testing):
    e, producto, orden, detalle = escenario(db_testing)
    r1 = recibir(db_testing, e, orden, detalle, '0.500')
    assert db_testing.get(OrdenCompra, orden.id).estado == 'PARCIALMENTE_RECIBIDA'
    r2 = recibir(db_testing, e, orden, detalle, '1.500')
    assert r1.id != r2.id
    assert db_testing.get(OrdenCompra, orden.id).estado == 'RECIBIDA'
    stock = db_testing.scalar(select(Inventario).where(Inventario.empresa_id == e['empresa_id'], Inventario.producto_id == producto.id))
    assert stock.cantidad_disponible == Decimal('2.000')
    movimientos = db_testing.scalars(select(MovimientoInventario).where(
        MovimientoInventario.recepcion_compra_id.in_([r1.id, r2.id]))).all()
    assert len(movimientos) == 2
    assert sum((x.cantidad_delta for x in movimientos), Decimal('0')) == Decimal('2.000')
    assert db_testing.scalar(select(func.count()).select_from(RecepcionCompraDetalle).where(
        RecepcionCompraDetalle.orden_id == orden.id)) == 2


def test_no_sobrerrecepcion_y_rollback(db_testing):
    e, producto, orden, detalle = escenario(db_testing)
    recibir(db_testing, e, orden, detalle, '1.000')
    with pytest.raises(RecepcionCompraServiceError, match='excede'):
        recibir(db_testing, e, orden, detalle, '1.001')
    assert db_testing.get(OrdenCompra, orden.id).estado == 'PARCIALMENTE_RECIBIDA'
    assert db_testing.scalar(select(Inventario.cantidad_disponible).where(
        Inventario.empresa_id == e['empresa_id'], Inventario.producto_id == producto.id)) == Decimal('1.000')


def test_idempotencia_no_duplica_entrada(db_testing):
    e, producto, orden, detalle = escenario(db_testing)
    r1 = recibir(db_testing, e, orden, detalle, '1.000', idempotency_key='rc-idempotente-1')
    r2 = recibir(db_testing, e, orden, detalle, '1.000', idempotency_key='rc-idempotente-1')
    assert r1.id == r2.id
    assert db_testing.scalar(select(func.count()).select_from(MovimientoInventario).where(
        MovimientoInventario.recepcion_compra_id == r1.id)) == 1


def test_rechazo_borrador_y_detalle_incorrecto(db_testing):
    e, p, producto = preparar(db_testing, permisos=PERMISOS_REC)
    orden = crear(db_testing, e, p, producto)
    detalle = db_testing.scalar(select(OrdenCompraDetalle).where(OrdenCompraDetalle.orden_id == orden.id))
    with pytest.raises(RecepcionCompraServiceError, match='estado'):
        recibir(db_testing, e, orden, detalle, '1.000')
    confirmar_orden_compra(db_testing, usuario_id=e['usuario_id'], orden_id=orden.id)
    with pytest.raises(RecepcionCompraServiceError, match='no pertenece'):
        recibir_compra(db_testing, usuario_id=e['usuario_id'], orden_id=orden.id,
            detalles=[{'orden_detalle_id': 99999999, 'cantidad_recibida': '1.000'}])


def test_consulta_y_auditoria(db_testing):
    e, producto, orden, detalle = escenario(db_testing)
    r = recibir(db_testing, e, orden, detalle, '1.000')
    assert obtener_recepcion_compra(db_testing, usuario_id=e['usuario_id'], recepcion_id=r.id).id == r.id
    assert listar_recepciones_compra(db_testing, usuario_id=e['usuario_id'], orden_id=orden.id)['total'] == 1
    assert db_testing.scalar(select(func.count()).select_from(Auditoria).where(
        Auditoria.entidad == 'recepciones_compra', Auditoria.entidad_id == r.id)) == 1


def test_multiempresa_aislada(db_testing):
    a, _, _, _ = escenario(db_testing)
    b, producto_b, orden_b, detalle_b = escenario(db_testing)
    r = recibir(db_testing, b, orden_b, detalle_b, '1.000')
    with pytest.raises(RecepcionCompraServiceError, match='no encontrada'):
        obtener_recepcion_compra(db_testing, usuario_id=a['usuario_id'], recepcion_id=r.id)
    assert listar_recepciones_compra(db_testing, usuario_id=a['usuario_id'])['total'] == 0
