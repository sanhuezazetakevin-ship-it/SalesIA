"""SalesIA Enterprise - FASE 08-F.2: confirmacion atomica de entregas.

Alcance inicial: ventas derivadas de pedidos con reservas de stock.
No modifica inventario para productos sin control de stock.
"""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.empresa import Empresa
from app.models.entrega import Entrega
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.producto import Producto
from app.models.reserva_stock import ReservaStock
from app.models.usuario import Usuario
from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle
from app.services.role_service import _obtener_permisos_efectivos

PERMISO_CONFIRMAR = "entregas.confirmar"
PERMISO_VER = "entregas.ver"


class EntregaServiceError(Exception):
    """Error controlado de las operaciones de entregas."""


def _operador(db: Session, usuario_id: int, permiso: str) -> tuple[Usuario, Empresa]:
    if type(usuario_id) is not int or usuario_id <= 0:
        raise EntregaServiceError("Identificador de usuario invalido.")
    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id, Usuario.activo.is_(True)))
    if usuario is None:
        raise EntregaServiceError("El usuario no existe o esta inactivo.")
    empresa = db.scalar(select(Empresa).where(Empresa.id == usuario.empresa_id, Empresa.activo.is_(True)))
    if empresa is None:
        raise EntregaServiceError("La empresa no existe o esta inactiva.")
    permisos = _obtener_permisos_efectivos(db, usuario_id=usuario.id, empresa_id=empresa.id)
    if permiso not in permisos:
        raise EntregaServiceError("No tiene autorizacion para esta operacion.")
    return usuario, empresa


def confirmar_entrega(
    db: Session, *, usuario_id: int, venta_id: int, observaciones: str | None = None
) -> dict:
    """Entrega completa con consumo de reservas, movimientos y auditoria en un commit.

    No gestiona ventas directas sin pedido. Ese flujo requiere una politica propia
    de asignacion/validacion de inventario y se implementara por separado.
    """
    try:
        if type(venta_id) is not int or venta_id <= 0:
            raise EntregaServiceError("Identificador de venta invalido.")
        if observaciones is not None and (not isinstance(observaciones, str) or len(observaciones) > 500):
            raise EntregaServiceError("Observaciones invalidas.")
        usuario, empresa = _operador(db, usuario_id, PERMISO_CONFIRMAR)
        venta = db.scalar(
            select(Venta).where(Venta.id == venta_id, Venta.empresa_id == empresa.id).with_for_update()
        )
        if venta is None:
            raise EntregaServiceError("La venta no existe en esta empresa.")
        if venta.estado == "CANCELADA":
            raise EntregaServiceError("No se puede entregar una venta cancelada.")
        if venta.estado not in {"REGISTRADA", "CONFIRMADA"}:
            raise EntregaServiceError("Estado de venta no permitido.")
        if venta.pedido_id is None:
            raise EntregaServiceError("Las ventas directas requieren un flujo de entrega especifico.")
        if db.scalar(select(Entrega.id).where(Entrega.empresa_id == empresa.id, Entrega.venta_id == venta.id)) is not None:
            raise EntregaServiceError("La venta ya tiene una entrega registrada.")

        detalles = db.scalars(
            select(VentaDetalle).where(VentaDetalle.empresa_id == empresa.id, VentaDetalle.venta_id == venta.id)
            .order_by(VentaDetalle.producto_id.asc())
        ).all()
        if not detalles:
            raise EntregaServiceError("La venta no tiene detalles.")
        ids_productos = sorted({d.producto_id for d in detalles})
        productos = db.scalars(
            select(Producto).where(Producto.empresa_id == empresa.id, Producto.id.in_(ids_productos))
        ).all()
        por_producto = {p.id: p for p in productos}
        if len(por_producto) != len(ids_productos):
            raise EntregaServiceError("Productos de la venta inexistentes en la empresa.")

        requeridos: dict[int, Decimal] = {}
        for d in detalles:
            if por_producto[d.producto_id].controla_stock:
                requeridos[d.producto_id] = requeridos.get(d.producto_id, Decimal("0.000")) + d.cantidad

        # Mantener el orden de bloqueo del servicio de pedidos: inventarios por ID,
        # seguidos de reservas. Bloquear ANTES de validar y modificar existencias.
        inventarios = []
        if requeridos:
            inventarios = db.scalars(
                select(Inventario)
                .where(Inventario.empresa_id == empresa.id, Inventario.producto_id.in_(sorted(requeridos)))
                .order_by(Inventario.id.asc())
                .with_for_update()
            ).all()
        inv_por_producto = {i.producto_id: i for i in inventarios}
        if len(inv_por_producto) != len(requeridos):
            raise EntregaServiceError("Falta inventario para algun producto de la venta.")

        reservas = db.scalars(
            select(ReservaStock)
            .where(ReservaStock.empresa_id == empresa.id, ReservaStock.pedido_id == venta.pedido_id)
            .order_by(ReservaStock.inventario_id.asc(), ReservaStock.id.asc())
            .with_for_update()
        ).all()
        reservas_por_producto = {r.producto_id: r for r in reservas}
        if len(reservas_por_producto) != len(reservas) or set(reservas_por_producto) != set(requeridos):
            raise EntregaServiceError("Las reservas del pedido no corresponden a los productos vendidos.")

        for producto_id, cantidad in requeridos.items():
            inventario = inv_por_producto[producto_id]
            reserva = reservas_por_producto[producto_id]
            if (reserva.estado != "ACTIVA"
                    or reserva.inventario_id != inventario.id
                    or reserva.cantidad_reservada != cantidad):
                raise EntregaServiceError("Reserva inconsistente o ya consumida.")
            if inventario.cantidad_disponible < cantidad:
                raise EntregaServiceError("Stock fisico insuficiente para completar la entrega.")

        entrega = Entrega(
            empresa_id=empresa.id, venta_id=venta.id, responsable_id=usuario.id,
            codigo=f"ENT-{uuid4().hex[:20].upper()}", estado="CONFIRMADA",
            fecha_confirmacion=datetime.now(timezone.utc), observaciones=observaciones,
        )
        db.add(entrega)
        db.flush()
        movimientos = []
        for producto_id in sorted(requeridos):
            cantidad = requeridos[producto_id]
            inv = inv_por_producto[producto_id]
            inv.cantidad_disponible -= cantidad
            reservas_por_producto[producto_id].estado = "CONSUMIDA"
            mov = MovimientoInventario(
                empresa_id=empresa.id, producto_id=producto_id, inventario_id=inv.id,
                entrega_id=entrega.id, tipo_movimiento="SALIDA", cantidad_delta=-cantidad,
                motivo="Entrega completa de venta", referencia=venta.codigo,
            )
            db.add(mov)
            movimientos.append(mov)

        db.add(Auditoria(
            empresa_id=empresa.id, usuario_id=usuario.id, accion="CONFIRMAR",
            entidad="entregas", entidad_id=entrega.id,
            descripcion="Entrega completa con consumo de reservas y salida fisica.",
            datos_anteriores={"venta_id": venta.id, "reservas": "ACTIVA"},
            datos_nuevos={"estado": "CONFIRMADA", "movimientos": len(movimientos),
                          "cantidades": {str(k): str(v) for k, v in requeridos.items()}},
            origen="SISTEMA",
        ))
        db.flush()
        db.commit()
        db.refresh(entrega)
        return {"entrega": entrega, "movimientos": movimientos}
    except IntegrityError as exc:
        db.rollback()
        raise EntregaServiceError("No fue posible confirmar la entrega por un conflicto de integridad.") from exc
    except Exception:
        db.rollback()
        raise


def obtener_entrega_por_venta(db: Session, *, usuario_id: int, venta_id: int) -> dict:
    """Consulta una entrega asociada a una venta de la empresa autenticada."""
    if type(venta_id) is not int or venta_id <= 0:
        raise EntregaServiceError("Identificador de venta invalido.")
    _, empresa = _operador(db, usuario_id, PERMISO_VER)
    entrega = db.scalar(select(Entrega).where(
        Entrega.empresa_id == empresa.id, Entrega.venta_id == venta_id
    ))
    if entrega is None:
        raise EntregaServiceError("La entrega no existe en esta empresa.")
    movimientos = list(db.scalars(select(MovimientoInventario).where(
        MovimientoInventario.empresa_id == empresa.id,
        MovimientoInventario.entrega_id == entrega.id,
    ).order_by(MovimientoInventario.id.asc())).all())
    return {"entrega": entrega, "movimientos": movimientos}


def obtener_entrega(db: Session, *, usuario_id: int, entrega_id: int) -> dict:
    """Consulta una entrega por identificador con aislamiento multiempresa."""
    if type(entrega_id) is not int or entrega_id <= 0:
        raise EntregaServiceError("Identificador de entrega invalido.")
    _, empresa = _operador(db, usuario_id, PERMISO_VER)
    entrega = db.scalar(select(Entrega).where(
        Entrega.empresa_id == empresa.id, Entrega.id == entrega_id
    ))
    if entrega is None:
        raise EntregaServiceError("La entrega no existe en esta empresa.")
    movimientos = list(db.scalars(select(MovimientoInventario).where(
        MovimientoInventario.empresa_id == empresa.id,
        MovimientoInventario.entrega_id == entrega.id,
    ).order_by(MovimientoInventario.id.asc())).all())
    return {"entrega": entrega, "movimientos": movimientos}
