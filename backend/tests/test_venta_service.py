"""
SalesIA Enterprise
FASE 08-D.10

Pruebas de integración del servicio de ventas.
"""

from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.pedido import Pedido
from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle
from app.models.reserva_stock import ReservaStock
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario

from app.services.pedido_service import (
    confirmar_pedido,
)

from app.services.venta_service import (
    VentaServiceError,
    crear_venta_desde_pedido,
    obtener_venta,
    listar_ventas,
)

from tests.test_pedido_service import (
    _escenario_confirmacion,
    _crear_borrador_confirmacion,
    contar,
)


def preparar_venta(db):
    e = _escenario_confirmacion(
        db,
        permisos=(
            "pedidos.crear",
            "pedidos.ver",
            "pedidos.confirmar",
            "pedidos.cancelar",
            "ventas.crear",
            "ventas.ver",
        ),
    )

    pedido = _crear_borrador_confirmacion(
        db,
        e,
        cantidad="2.000",
    )

    confirmar_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    return e, pedido


def test_crear_venta_desde_pedido_confirmado(db_testing):
    db = db_testing

    e, pedido = preparar_venta(db)

    resultado = crear_venta_desde_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    venta = resultado["venta"]
    detalles = resultado["detalles"]

    assert venta.id > 0
    assert venta.empresa_id == e["empresa_id"]
    assert venta.pedido_id == pedido.id
    assert venta.cliente_id == pedido.cliente_id

    assert venta.estado == "REGISTRADA"
    assert venta.estado_pago == "PENDIENTE"

    assert len(detalles) == 1

    db.expire_all()

    pedido_db = db.get(
        Pedido,
        pedido.id,
    )

    assert pedido_db.estado == "COMPLETADO"


def test_venta_copia_snapshot_comercial(db_testing):
    db = db_testing

    e, pedido = preparar_venta(db)

    resultado = crear_venta_desde_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    venta = resultado["venta"]
    detalle = resultado["detalles"][0]

    assert venta.subtotal == pedido.subtotal
    assert venta.impuesto_total == pedido.impuesto_total
    assert venta.total == pedido.total

    assert detalle.cantidad == Decimal("2.000")
    assert detalle.precio_unitario == Decimal("118.00")
    assert detalle.tasa_impuesto == Decimal("18.0000")


def test_crear_venta_no_descuenta_inventario(db_testing):
    db = db_testing

    e, pedido = preparar_venta(db)

    crear_venta_desde_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    db.expire_all()

    inventario = db.get(
        Inventario,
        e["inventario_id"],
    )

    assert (
        inventario.cantidad_disponible
        == Decimal("10.000")
    )

    assert contar(
        db,
        MovimientoInventario,
        e["empresa_id"],
    ) == 0


def test_reserva_permanece_activa_tras_venta(db_testing):
    db = db_testing

    e, pedido = preparar_venta(db)

    crear_venta_desde_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    db.expire_all()

    reserva = db.scalar(
        select(ReservaStock).where(
            ReservaStock.empresa_id == e["empresa_id"],
            ReservaStock.pedido_id == pedido.id,
        )
    )

    assert reserva is not None
    assert reserva.estado == "ACTIVA"


def test_no_permite_doble_conversion(db_testing):
    db = db_testing

    e, pedido = preparar_venta(db)

    crear_venta_desde_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    with pytest.raises(VentaServiceError):
        crear_venta_desde_pedido(
            db,
            usuario_id=e["usuario_id"],
            pedido_id=pedido.id,
        )

    assert contar(
        db,
        Venta,
        e["empresa_id"],
    ) == 1


def test_no_convierte_borrador_en_venta(db_testing):
    db = db_testing

    e = _escenario_confirmacion(
        db,
        permisos=(
            "pedidos.crear",
            "ventas.crear",
        ),
    )

    pedido = _crear_borrador_confirmacion(
        db,
        e,
    )

    with pytest.raises(
        VentaServiceError,
        match="CONFIRMADO",
    ):
        crear_venta_desde_pedido(
            db,
            usuario_id=e["usuario_id"],
            pedido_id=pedido.id,
        )


def test_obtener_venta(db_testing):
    db = db_testing

    e, pedido = preparar_venta(db)

    creada = crear_venta_desde_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    resultado = obtener_venta(
        db,
        usuario_id=e["usuario_id"],
        venta_id=creada["venta"].id,
    )

    assert (
        resultado["venta"].id
        == creada["venta"].id
    )

    assert len(resultado["detalles"]) == 1


def test_listar_ventas(db_testing):
    db = db_testing

    e, pedido = preparar_venta(db)

    venta = crear_venta_desde_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )["venta"]

    resultado = listar_ventas(
        db,
        usuario_id=e["usuario_id"],
        estado="REGISTRADA",
        estado_pago="PENDIENTE",
    )

    assert resultado["total"] == 1
    assert resultado["ventas"][0].id == venta.id


def test_venta_aislada_multiempresa(db_testing):
    db = db_testing

    a, _ = preparar_venta(db)
    b, pedido_b = preparar_venta(db)

    venta_b = crear_venta_desde_pedido(
        db,
        usuario_id=b["usuario_id"],
        pedido_id=pedido_b.id,
    )["venta"]

    with pytest.raises(VentaServiceError):
        obtener_venta(
            db,
            usuario_id=a["usuario_id"],
            venta_id=venta_b.id,
        )

    listado = listar_ventas(
        db,
        usuario_id=a["usuario_id"],
    )

    assert listado["total"] == 0


def test_venta_requiere_permiso(db_testing):
    db = db_testing

    e = _escenario_confirmacion(
        db,
        permisos=(
            "pedidos.crear",
            "pedidos.confirmar",
        ),
    )

    pedido = _crear_borrador_confirmacion(
        db,
        e,
    )

    confirmar_pedido(
        db,
        usuario_id=e["usuario_id"],
        pedido_id=pedido.id,
    )

    with pytest.raises(
        VentaServiceError,
        match="autorizacion",
    ):
        crear_venta_desde_pedido(
            db,
            usuario_id=e["usuario_id"],
            pedido_id=pedido.id,
        )