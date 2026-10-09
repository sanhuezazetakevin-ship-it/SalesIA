"""SalesIA Enterprise — FASE 08-F.3: integración de entregas.

Todas las pruebas utilizan db_testing, que comprueba el aislamiento de
PostgreSQL y revierte la transacción exterior al finalizar cada caso.
"""
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.auditoria import Auditoria
from app.models.entrega import Entrega
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.reserva_stock import ReservaStock
from app.models.venta import Venta
from app.services.entrega_service import EntregaServiceError, confirmar_entrega
from app.services.pedido_service import confirmar_pedido
from app.services.venta_service import crear_venta_desde_pedido
from tests.test_pedido_service import _escenario_confirmacion, _crear_borrador_confirmacion, contar


PERMISOS = (
    "pedidos.crear", "pedidos.confirmar", "ventas.crear", "ventas.ver",
    "entregas.confirmar", "entregas.ver",
)


def preparar_entrega(db, *, permisos=PERMISOS, controla_stock=True, cantidad="2.000"):
    e = _escenario_confirmacion(db, permisos=permisos)
    if not controla_stock:
        producto = db.get(Producto, e["producto_id"])
        producto.controla_stock = False
        db.commit()
    pedido = _crear_borrador_confirmacion(db, e, cantidad=cantidad)
    confirmar_pedido(db, usuario_id=e["usuario_id"], pedido_id=pedido.id)
    venta = crear_venta_desde_pedido(
        db, usuario_id=e["usuario_id"], pedido_id=pedido.id
    )["venta"]
    return e, pedido.id, venta.id


def reservas_de(db, empresa_id, pedido_id):
    return db.scalars(select(ReservaStock).where(
        ReservaStock.empresa_id == empresa_id,
        ReservaStock.pedido_id == pedido_id,
    )).all()


def movimientos_de(db, empresa_id, entrega_id):
    return db.scalars(select(MovimientoInventario).where(
        MovimientoInventario.empresa_id == empresa_id,
        MovimientoInventario.entrega_id == entrega_id,
    )).all()


def test_confirmar_entrega_descuenta_inventario_y_consume_reserva(db_testing):
    db = db_testing
    e, pedido_id, venta_id = preparar_entrega(db)
    resultado = confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)
    entrega = resultado["entrega"]
    assert entrega.estado == "CONFIRMADA"
    assert entrega.fecha_confirmacion is not None
    assert entrega.venta_id == venta_id
    assert entrega.empresa_id == e["empresa_id"]
    db.expire_all()
    assert db.get(Inventario, e["inventario_id"]).cantidad_disponible == Decimal("8.000")
    reservas = reservas_de(db, e["empresa_id"], pedido_id)
    assert len(reservas) == 1
    assert reservas[0].estado == "CONSUMIDA"
    assert reservas[0].cantidad_reservada == Decimal("2.000")
    movimientos = movimientos_de(db, e["empresa_id"], entrega.id)
    assert len(movimientos) == 1
    assert movimientos[0].tipo_movimiento == "SALIDA"
    assert movimientos[0].cantidad_delta == Decimal("-2.000")
    assert movimientos[0].inventario_id == e["inventario_id"]


def test_entrega_registra_una_auditoria(db_testing):
    db = db_testing
    e, _, venta_id = preparar_entrega(db)
    entrega = confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)["entrega"]
    auditorias = db.scalars(select(Auditoria).where(
        Auditoria.empresa_id == e["empresa_id"],
        Auditoria.entidad == "entregas",
        Auditoria.entidad_id == entrega.id,
        Auditoria.accion == "CONFIRMAR",
    )).all()
    assert len(auditorias) == 1
    assert auditorias[0].usuario_id == e["usuario_id"]
    assert auditorias[0].datos_nuevos["estado"] == "CONFIRMADA"
    assert auditorias[0].datos_nuevos["movimientos"] == 1


def test_no_permite_entregar_dos_veces(db_testing):
    db = db_testing
    e, _, venta_id = preparar_entrega(db)
    confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)
    with pytest.raises(EntregaServiceError, match="ya tiene una entrega"):
        confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)
    db.expire_all()
    assert contar(db, Entrega, e["empresa_id"]) == 1
    assert contar(db, MovimientoInventario, e["empresa_id"]) == 1
    assert db.get(Inventario, e["inventario_id"]).cantidad_disponible == Decimal("8.000")


def test_rechaza_stock_fisico_insuficiente_sin_efectos(db_testing):
    db = db_testing
    e, pedido_id, venta_id = preparar_entrega(db)
    inventario = db.get(Inventario, e["inventario_id"])
    inventario.cantidad_disponible = Decimal("1.000")
    db.commit()
    with pytest.raises(EntregaServiceError, match="Stock fisico insuficiente"):
        confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)
    db.expire_all()
    assert contar(db, Entrega, e["empresa_id"]) == 0
    assert contar(db, MovimientoInventario, e["empresa_id"]) == 0
    assert reservas_de(db, e["empresa_id"], pedido_id)[0].estado == "ACTIVA"
    assert db.get(Inventario, e["inventario_id"]).cantidad_disponible == Decimal("1.000")


def test_rechaza_reserva_inconsistente(db_testing):
    db = db_testing
    e, pedido_id, venta_id = preparar_entrega(db)
    reserva = reservas_de(db, e["empresa_id"], pedido_id)[0]
    reserva.cantidad_reservada = Decimal("1.000")
    db.commit()
    with pytest.raises(EntregaServiceError, match="Reserva inconsistente"):
        confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)
    assert contar(db, Entrega, e["empresa_id"]) == 0
    assert contar(db, MovimientoInventario, e["empresa_id"]) == 0


def test_rechaza_reserva_que_ya_no_esta_activa(db_testing):
    db = db_testing
    e, pedido_id, venta_id = preparar_entrega(db)
    reserva = reservas_de(db, e["empresa_id"], pedido_id)[0]
    reserva.estado = "LIBERADA"
    db.commit()
    with pytest.raises(EntregaServiceError, match="Reserva inconsistente"):
        confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)
    assert contar(db, Entrega, e["empresa_id"]) == 0


def test_rechaza_usuario_sin_permiso_entregar(db_testing):
    db = db_testing
    permisos = tuple(p for p in PERMISOS if p != "entregas.confirmar")
    e, _, venta_id = preparar_entrega(db, permisos=permisos)
    with pytest.raises(EntregaServiceError, match="autorizacion"):
        confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)
    assert contar(db, Entrega, e["empresa_id"]) == 0


def test_no_permite_entrega_de_otra_empresa(db_testing):
    db = db_testing
    a, _, _ = preparar_entrega(db)
    b, _, venta_b_id = preparar_entrega(db)
    with pytest.raises(EntregaServiceError, match="no existe en esta empresa"):
        confirmar_entrega(db, usuario_id=a["usuario_id"], venta_id=venta_b_id)
    assert contar(db, Entrega, b["empresa_id"]) == 0


def test_producto_sin_control_stock_no_descuenta_ni_crea_movimiento(db_testing):
    db = db_testing
    e, pedido_id, venta_id = preparar_entrega(db, controla_stock=False)
    assert reservas_de(db, e["empresa_id"], pedido_id) == []
    entrega = confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)["entrega"]
    assert entrega.estado == "CONFIRMADA"
    db.expire_all()
    assert db.get(Inventario, e["inventario_id"]).cantidad_disponible == Decimal("10.000")
    assert contar(db, MovimientoInventario, e["empresa_id"]) == 0


def test_no_entrega_venta_cancelada(db_testing):
    db = db_testing
    e, pedido_id, venta_id = preparar_entrega(db)
    venta = db.get(Venta, venta_id)
    venta.estado = "CANCELADA"
    db.commit()
    with pytest.raises(EntregaServiceError, match="venta cancelada"):
        confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)
    assert contar(db, Entrega, e["empresa_id"]) == 0
    assert reservas_de(db, e["empresa_id"], pedido_id)[0].estado == "ACTIVA"


@pytest.mark.parametrize("venta_id", [0, -1, True, "1"])
def test_rechaza_identificador_de_venta_invalido(db_testing, venta_id):
    db = db_testing
    e = _escenario_confirmacion(db, permisos=("entregas.confirmar",))
    with pytest.raises(EntregaServiceError, match="Identificador de venta invalido"):
        confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id)


def test_rechaza_observaciones_muy_largas(db_testing):
    db = db_testing
    e, _, venta_id = preparar_entrega(db)
    with pytest.raises(EntregaServiceError, match="Observaciones invalidas"):
        confirmar_entrega(db, usuario_id=e["usuario_id"], venta_id=venta_id, observaciones="x" * 501)
    assert contar(db, Entrega, e["empresa_id"]) == 0
