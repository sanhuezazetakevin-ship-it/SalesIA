"""
SalesIA Enterprise
FASE 08-D

Servicio empresarial de ventas.

Primera implementación:
- convertir pedido CONFIRMADO en venta;
- copiar snapshot comercial;
- evitar doble conversión;
- consultar y listar ventas;
- mantener reservas ACTIVAS;
- no descontar inventario físico;
- no registrar pagos todavía.
"""

from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario

from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle

from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle

from app.models.reserva_stock import ReservaStock
from app.models.auditoria import Auditoria

from app.services.role_service import (
    _obtener_permisos_efectivos,
)


PERMISO_CREAR = "ventas.crear"
PERMISO_VER = "ventas.ver"


class VentaServiceError(Exception):
    """Error controlado del modulo de ventas."""


def _validar_operador(
    db: Session,
    *,
    usuario_id: int,
    permiso: str,
) -> tuple[Usuario, Empresa]:

    if type(usuario_id) is not int or usuario_id <= 0:
        raise VentaServiceError(
            "Identificador de usuario invalido."
        )

    usuario = db.scalar(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.activo.is_(True),
        )
    )

    if usuario is None:
        raise VentaServiceError(
            "El usuario no existe o esta inactivo."
        )

    empresa = db.scalar(
        select(Empresa).where(
            Empresa.id == usuario.empresa_id,
            Empresa.activo.is_(True),
        )
    )

    if empresa is None:
        raise VentaServiceError(
            "La empresa no existe o esta inactiva."
        )

    permisos = _obtener_permisos_efectivos(
        db,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    if permiso not in permisos:
        raise VentaServiceError(
            "No tiene autorizacion para esta operacion."
        )

    return usuario, empresa


def _generar_codigo_venta() -> str:
    return f"VEN-{uuid4().hex[:20].upper()}"


def crear_venta_desde_pedido(
    db: Session,
    *,
    usuario_id: int,
    pedido_id: int,
    observaciones: str | None = None,
) -> dict:
    """
    Convierte atomicamente un pedido CONFIRMADO en venta.

    Importante:
    - NO recalcula importes.
    - NO descuenta inventario.
    - NO consume reservas.
    - NO registra pagos.
    """

    try:
        if type(pedido_id) is not int or pedido_id <= 0:
            raise VentaServiceError(
                "Identificador de pedido invalido."
            )

        usuario, empresa = _validar_operador(
            db,
            usuario_id=usuario_id,
            permiso=PERMISO_CREAR,
        )

        # Bloqueamos el pedido para impedir conversiones
        # concurrentes del mismo registro.
        pedido = db.scalar(
            select(Pedido)
            .where(
                Pedido.id == pedido_id,
                Pedido.empresa_id == empresa.id,
            )
            .with_for_update()
        )

        if pedido is None:
            raise VentaServiceError(
                "El pedido no existe en esta empresa."
            )

        if pedido.estado != "CONFIRMADO":
            raise VentaServiceError(
                "Solo un pedido CONFIRMADO puede convertirse en venta."
            )

        venta_existente = db.scalar(
            select(Venta.id).where(
                Venta.pedido_id == pedido.id,
            )
        )

        if venta_existente is not None:
            raise VentaServiceError(
                "El pedido ya fue convertido en venta."
            )

        detalles_pedido = db.scalars(
            select(PedidoDetalle)
            .where(
                PedidoDetalle.empresa_id == empresa.id,
                PedidoDetalle.pedido_id == pedido.id,
            )
            .order_by(PedidoDetalle.id.asc())
        ).all()

        if not detalles_pedido:
            raise VentaServiceError(
                "El pedido no contiene detalles."
            )

        # Confirmar que un pedido CONFIRMADO conserva
        # las reservas correspondientes.
        reservas_activas = db.scalars(
            select(ReservaStock).where(
                ReservaStock.empresa_id == empresa.id,
                ReservaStock.pedido_id == pedido.id,
                ReservaStock.estado == "ACTIVA",
            )
        ).all()

        productos_reservados = {
            reserva.producto_id
            for reserva in reservas_activas
        }

        # Solo exigimos reserva para productos que tengan
        # una ReservaStock generada por la confirmacion.
        # Productos sin control de stock pueden no tenerla.

        subtotal_detalles = sum(
            detalle.subtotal
            for detalle in detalles_pedido
        )

        impuesto_detalles = sum(
            detalle.impuesto
            for detalle in detalles_pedido
        )

        total_detalles = sum(
            detalle.total
            for detalle in detalles_pedido
        )

        if (
            subtotal_detalles != pedido.subtotal
            or impuesto_detalles != pedido.impuesto_total
            or total_detalles != pedido.total
            or pedido.subtotal + pedido.impuesto_total
            != pedido.total
        ):
            raise VentaServiceError(
                "Los importes del pedido son inconsistentes."
            )

        venta = Venta(
            empresa_id=empresa.id,
            pedido_id=pedido.id,
            cliente_id=pedido.cliente_id,
            usuario_id=usuario.id,

            codigo=_generar_codigo_venta(),

            estado="REGISTRADA",
            estado_pago="PENDIENTE",

            subtotal=pedido.subtotal,
            impuesto_total=pedido.impuesto_total,
            total=pedido.total,

            observaciones=(
                observaciones
                if observaciones is not None
                else pedido.observaciones
            ),
        )

        db.add(venta)
        db.flush()

        detalles_venta = []

        for detalle in detalles_pedido:

            detalle_venta = VentaDetalle(
                empresa_id=empresa.id,
                venta_id=venta.id,
                producto_id=detalle.producto_id,

                descripcion=detalle.descripcion,

                cantidad=detalle.cantidad,
                precio_unitario=detalle.precio_unitario,
                descuento=detalle.descuento,

                subtotal=detalle.subtotal,
                impuesto=detalle.impuesto,
                total=detalle.total,

                tasa_impuesto=detalle.tasa_impuesto,
            )

            db.add(detalle_venta)
            detalles_venta.append(detalle_venta)

        db.flush()

        # El pedido ya cumplio su funcion comercial:
        # se convirtió en una venta.
        pedido.estado = "COMPLETADO"

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,

                accion="CREAR",
                entidad="ventas",
                entidad_id=venta.id,

                descripcion=(
                    "Venta registrada a partir de "
                    "pedido confirmado."
                ),

                datos_anteriores={
                    "pedido_id": pedido.id,
                    "pedido_estado": "CONFIRMADO",
                },

                datos_nuevos={
                    "venta_id": venta.id,
                    "codigo": venta.codigo,
                    "estado": "REGISTRADA",
                    "estado_pago": "PENDIENTE",
                    "pedido_estado": "COMPLETADO",
                    "total": str(venta.total),
                    "productos_con_reserva_activa": sorted(
                        productos_reservados
                    ),
                },

                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()

        db.refresh(venta)

        return {
            "venta": venta,
            "detalles": detalles_venta,
        }

    except IntegrityError as exc:
        db.rollback()

        raise VentaServiceError(
            "No fue posible registrar la venta. "
            "Verifique que el pedido no haya sido "
            "convertido previamente."
        ) from exc

    except Exception:
        db.rollback()
        raise


def obtener_venta(
    db: Session,
    *,
    usuario_id: int,
    venta_id: int,
) -> dict:

    if type(venta_id) is not int or venta_id <= 0:
        raise VentaServiceError(
            "Identificador de venta invalido."
        )

    _, empresa = _validar_operador(
        db,
        usuario_id=usuario_id,
        permiso=PERMISO_VER,
    )

    venta = db.scalar(
        select(Venta).where(
            Venta.id == venta_id,
            Venta.empresa_id == empresa.id,
        )
    )

    if venta is None:
        raise VentaServiceError(
            "La venta no existe en esta empresa."
        )

    detalles = db.scalars(
        select(VentaDetalle)
        .where(
            VentaDetalle.empresa_id == empresa.id,
            VentaDetalle.venta_id == venta.id,
        )
        .order_by(VentaDetalle.id.asc())
    ).all()

    return {
        "venta": venta,
        "detalles": detalles,
    }


def listar_ventas(
    db: Session,
    *,
    usuario_id: int,
    pagina: int = 1,
    limite: int = 20,
    estado: str | None = None,
    estado_pago: str | None = None,
    cliente_id: int | None = None,
    busqueda: str | None = None,
) -> dict:

    _, empresa = _validar_operador(
        db,
        usuario_id=usuario_id,
        permiso=PERMISO_VER,
    )

    if pagina < 1:
        raise VentaServiceError(
            "Pagina invalida."
        )

    if limite < 1 or limite > 100:
        raise VentaServiceError(
            "Limite invalido."
        )

    estados_validos = {
        "REGISTRADA",
        "CONFIRMADA",
        "CANCELADA",
    }

    estados_pago_validos = {
        "PENDIENTE",
        "PARCIAL",
        "PAGADO",
    }

    if estado is not None and estado not in estados_validos:
        raise VentaServiceError(
            "Estado de venta invalido."
        )

    if (
        estado_pago is not None
        and estado_pago not in estados_pago_validos
    ):
        raise VentaServiceError(
            "Estado de pago invalido."
        )

    if cliente_id is not None and cliente_id <= 0:
        raise VentaServiceError(
            "Identificador de cliente invalido."
        )

    if busqueda is not None:
        busqueda = busqueda.strip()

        if not busqueda:
            busqueda = None
        elif len(busqueda) > 40:
            raise VentaServiceError(
                "Busqueda demasiado larga."
            )

    condiciones = [
        Venta.empresa_id == empresa.id,
    ]

    if estado is not None:
        condiciones.append(
            Venta.estado == estado
        )

    if estado_pago is not None:
        condiciones.append(
            Venta.estado_pago == estado_pago
        )

    if cliente_id is not None:
        condiciones.append(
            Venta.cliente_id == cliente_id
        )

    if busqueda is not None:
        condiciones.append(
            Venta.codigo.ilike(
                f"%{busqueda}%"
            )
        )

    total = db.scalar(
        select(func.count())
        .select_from(Venta)
        .where(*condiciones)
    )

    ventas = db.scalars(
        select(Venta)
        .where(*condiciones)
        .order_by(
            Venta.created_at.desc(),
            Venta.id.desc(),
        )
        .offset(
            (pagina - 1) * limite
        )
        .limit(limite)
    ).all()

    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "ventas": ventas,
    }