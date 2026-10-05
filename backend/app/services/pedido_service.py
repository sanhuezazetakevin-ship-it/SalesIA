
"""
SalesIA Enterprise — FASE 08-C.2

Servicio empresarial de pedidos: borradores, consultas y confirmacion.
La confirmacion reserva stock, pero no descuenta existencias fisicas.
"""

from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.cliente import Cliente
from app.models.producto import Producto
from app.models.impuesto import Impuesto
from app.models.pedido import Pedido
from app.models.pedido_detalle import PedidoDetalle
from app.models.auditoria import Auditoria

from app.models.inventario import Inventario
from app.models.reserva_stock import ReservaStock
from app.schemas.pedidos import PedidoCreate
from app.services.role_service import _obtener_permisos_efectivos
from app.services.calculo_comercial import (
    CalculoComercialError,
    calcular_linea,
    calcular_resumen,
)


PERMISO_CREAR = "pedidos.crear"
PERMISO_VER = "pedidos.ver"
PERMISO_CONFIRMAR = "pedidos.confirmar"
PERMISO_CANCELAR = "pedidos.cancelar"

class PedidoServiceError(Exception):
    """Error controlado del modulo de pedidos."""


def _validar_operador(
    db: Session,
    *,
    usuario_id: int,
    permiso: str,
) -> tuple[Usuario, Empresa]:
    if type(usuario_id) is not int or usuario_id <= 0:
        raise PedidoServiceError(
            "Identificador de usuario invalido."
        )

    usuario = db.scalar(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.activo.is_(True),
        )
    )

    if usuario is None:
        raise PedidoServiceError(
            "El usuario no existe o esta inactivo."
        )

    empresa = db.scalar(
        select(Empresa).where(
            Empresa.id == usuario.empresa_id,
            Empresa.activo.is_(True),
        )
    )

    if empresa is None:
        raise PedidoServiceError(
            "La empresa no existe o esta inactiva."
        )

    permisos = _obtener_permisos_efectivos(
        db,
        usuario_id=usuario.id,
        empresa_id=empresa.id,
    )

    if permiso not in permisos:
        raise PedidoServiceError(
            "No tiene autorizacion para esta operacion."
        )

    return usuario, empresa


def _obtener_tasa_activa(
    db: Session,
    *,
    empresa_id: int,
):
    """
    Una empresa debe tener un unico impuesto activo
    para la creacion de borradores de esta etapa.
    """

    impuestos = db.scalars(
        select(Impuesto)
        .where(
            Impuesto.empresa_id == empresa_id,
            Impuesto.activo.is_(True),
            Impuesto.incluido_en_precio.is_(True),
        )
        .order_by(Impuesto.id.asc())
        .limit(2)
    ).all()

    if len(impuestos) != 1:
        raise PedidoServiceError(
            "La empresa debe tener exactamente un "
            "impuesto activo incluido en el precio."
        )

    return impuestos[0].tasa


def crear_pedido(
    db: Session,
    *,
    usuario_id: int,
    datos: PedidoCreate,
) -> dict:
    """
    Crea cabecera, detalles y auditoria atomicamente.

    Devuelve:
        {
            "pedido": Pedido,
            "detalles": list[PedidoDetalle],
        }
    """

    try:
        if not isinstance(datos, PedidoCreate):
            raise PedidoServiceError(
                "Los datos del pedido son invalidos."
            )

        usuario, empresa = _validar_operador(
            db,
            usuario_id=usuario_id,
            permiso=PERMISO_CREAR,
        )

        cliente = db.scalar(
            select(Cliente).where(
                Cliente.id == datos.cliente_id,
                Cliente.empresa_id == empresa.id,
                Cliente.activo.is_(True),
            )
        )

        if cliente is None:
            raise PedidoServiceError(
                "El cliente no existe, esta inactivo "
                "o no pertenece a la empresa."
            )

        tasa = _obtener_tasa_activa(
            db,
            empresa_id=empresa.id,
        )

        ids = [
            detalle.producto_id
            for detalle in datos.detalles
        ]

        productos = db.scalars(
            select(Producto).where(
                Producto.empresa_id == empresa.id,
                Producto.id.in_(ids),
                Producto.activo.is_(True),
            )
        ).all()

        productos_por_id = {
            producto.id: producto
            for producto in productos
        }

        if len(productos_por_id) != len(ids):
            raise PedidoServiceError(
                "Uno o mas productos no existen, "
                "estan inactivos o pertenecen a otra empresa."
            )

        lineas = []

        for detalle in datos.detalles:
            producto = productos_por_id[detalle.producto_id]

            try:
                linea = calcular_linea(
                    producto_id=producto.id,
                    cantidad=detalle.cantidad,
                    precio_unitario=producto.precio_venta,
                    descuento=detalle.descuento,
                    tasa_impuesto=tasa,
                )
            except CalculoComercialError as exc:
                raise PedidoServiceError(
                    f"Importes invalidos para el producto "
                    f"{producto.id}: {exc}"
                ) from exc

            lineas.append(linea)

        try:
            resumen = calcular_resumen(lineas)
        except CalculoComercialError as exc:
            raise PedidoServiceError(
                f"No se pudo calcular el pedido: {exc}"
            ) from exc

        # Codigo suficientemente corto para String(40).
        # Su unicidad efectiva tambien esta protegida por
        # uq_pedido_codigo_empresa en PostgreSQL.
        codigo = f"PED-{uuid4().hex.upper()}"

        pedido = Pedido(
            empresa_id=empresa.id,
            cliente_id=cliente.id,
            usuario_id=usuario.id,
            codigo=codigo,
            estado="BORRADOR",
            subtotal=resumen.subtotal,
            impuesto_total=resumen.impuesto_total,
            total=resumen.total,
            observaciones=datos.observaciones,
        )

        db.add(pedido)
        db.flush()

        detalles_creados = []

        for linea in resumen.lineas:
            producto = productos_por_id[linea.producto_id]

            detalle = PedidoDetalle(
                empresa_id=empresa.id,
                pedido_id=pedido.id,
                producto_id=producto.id,
                descripcion=producto.nombre[:255],
                cantidad=linea.cantidad,
                precio_unitario=linea.precio_unitario,
                descuento=linea.descuento,
                subtotal=linea.subtotal,
                impuesto=linea.impuesto,
                total=linea.total,
                tasa_impuesto=linea.tasa_impuesto,
            )

            db.add(detalle)
            detalles_creados.append(detalle)

        db.flush()

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="CREAR",
                entidad="pedidos",
                entidad_id=pedido.id,
                descripcion="Creacion de borrador empresarial.",
                datos_anteriores=None,
                datos_nuevos={
                    "pedido_id": pedido.id,
                    "cliente_id": cliente.id,
                    "estado": "BORRADOR",
                    "codigo": codigo,
                    "subtotal": str(resumen.subtotal),
                    "impuesto_total": str(resumen.impuesto_total),
                    "total": str(resumen.total),
                    "tasa_impuesto_borrador": str(tasa),
                    "detalle_ids_producto": ids,
                    "numero_detalles": len(detalles_creados),
                },
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()

        db.refresh(pedido)

        for detalle in detalles_creados:
            db.refresh(detalle)

        return {
            "pedido": pedido,
            "detalles": detalles_creados,
        }

    except IntegrityError as exc:
        db.rollback()
        raise PedidoServiceError(
            "No fue posible registrar el pedido. "
            "Compruebe sus referencias y restricciones."
        ) from exc

    except Exception:
        db.rollback()
        raise


# ==========================================================
# FASE 08-C.4 — CONSULTA Y LISTADO DE PEDIDOS
# ==========================================================


def obtener_pedido(
    db: Session,
    *,
    usuario_id: int,
    pedido_id: int,
) -> dict:
    """
    Obtiene un pedido y sus detalles.

    El identificador de empresa siempre se deriva
    del usuario autenticado.
    """

    if type(pedido_id) is not int or pedido_id <= 0:
        raise PedidoServiceError(
            "Identificador de pedido invalido."
        )

    _, empresa = _validar_operador(
        db,
        usuario_id=usuario_id,
        permiso=PERMISO_VER,
    )

    pedido = db.scalar(
        select(Pedido).where(
            Pedido.id == pedido_id,
            Pedido.empresa_id == empresa.id,
        )
    )

    if pedido is None:
        raise PedidoServiceError(
            "El pedido no existe en esta empresa."
        )

    detalles = db.scalars(
        select(PedidoDetalle)
        .where(
            PedidoDetalle.pedido_id == pedido.id,
            PedidoDetalle.empresa_id == empresa.id,
        )
        .order_by(PedidoDetalle.id.asc())
    ).all()

    return {
        "pedido": pedido,
        "detalles": detalles,
    }


def listar_pedidos(
    db: Session,
    *,
    usuario_id: int,
    pagina: int = 1,
    limite: int = 20,
    estado: str | None = None,
    cliente_id: int | None = None,
    busqueda: str | None = None,
) -> dict:
    """
    Lista pedidos de la empresa con filtros y paginacion.

    busqueda: coincidencia parcial del codigo del pedido.
    """

    if type(pagina) is not int or pagina < 1:
        raise PedidoServiceError(
            "La pagina debe ser un entero positivo."
        )

    if type(limite) is not int or not 1 <= limite <= 100:
        raise PedidoServiceError(
            "El limite debe estar entre 1 y 100."
        )

    estados_validos = {
        "BORRADOR",
        "CONFIRMADO",
        "COMPLETADO",
        "CANCELADO",
    }

    if estado is not None:
        if not isinstance(estado, str) or estado not in estados_validos:
            raise PedidoServiceError(
                "El estado del pedido es invalido."
            )

    if cliente_id is not None:
        if type(cliente_id) is not int or cliente_id <= 0:
            raise PedidoServiceError(
                "El identificador del cliente es invalido."
            )

    if busqueda is not None:
        if not isinstance(busqueda, str):
            raise PedidoServiceError(
                "La busqueda debe ser texto."
            )

        busqueda = busqueda.strip()

        if len(busqueda) > 40:
            raise PedidoServiceError(
                "La busqueda supera los 40 caracteres."
            )

        if not busqueda:
            busqueda = None

    _, empresa = _validar_operador(
        db,
        usuario_id=usuario_id,
        permiso=PERMISO_VER,
    )

    condiciones = [
        Pedido.empresa_id == empresa.id,
    ]

    if estado is not None:
        condiciones.append(Pedido.estado == estado)

    if cliente_id is not None:
        condiciones.append(Pedido.cliente_id == cliente_id)

    if busqueda is not None:
        condiciones.append(
            Pedido.codigo.icontains(
                busqueda,
                autoescape=True,
            )
        )

    total = db.scalar(
        select(func.count(Pedido.id)).where(
            *condiciones
        )
    )

    pedidos = db.scalars(
        select(Pedido)
        .where(*condiciones)
        .order_by(Pedido.id.desc())
        .offset((pagina - 1) * limite)
        .limit(limite)
    ).all()

    return {
        "total": total,
        "pagina": pagina,
        "limite": limite,
        "pedidos": pedidos,
    }
# ==========================================================
# FASE 08-C.6 — CONFIRMACION Y RESERVA DE STOCK
# ==========================================================


def confirmar_pedido(
    db: Session,
    *,
    usuario_id: int,
    pedido_id: int,
) -> Pedido:
    """Confirma integramente un borrador y reserva stock atomicamente.

    No descuenta existencias fisicas; eso corresponde a la entrega.
    Todos los escritores de inventario deben respetar este protocolo
    de bloqueo para mantener la proteccion contra sobreventa.
    """
    try:
        if type(pedido_id) is not int or pedido_id <= 0:
            raise PedidoServiceError("Identificador de pedido invalido.")

        usuario, empresa = _validar_operador(
            db, usuario_id=usuario_id, permiso=PERMISO_CONFIRMAR
        )

        pedido = db.scalar(
            select(Pedido)
            .where(Pedido.id == pedido_id, Pedido.empresa_id == empresa.id)
            .with_for_update()
        )
        if pedido is None:
            raise PedidoServiceError("El pedido no existe en esta empresa.")
        if pedido.estado != "BORRADOR":
            raise PedidoServiceError(
                "Solo se pueden confirmar pedidos en BORRADOR."
            )

        detalles = db.scalars(
            select(PedidoDetalle)
            .where(
                PedidoDetalle.pedido_id == pedido.id,
                PedidoDetalle.empresa_id == empresa.id,
            )
            .order_by(PedidoDetalle.id.asc())
        ).all()
        if not detalles:
            raise PedidoServiceError("No se puede confirmar un pedido sin detalles.")

        tasa_vigente = _obtener_tasa_activa(db, empresa_id=empresa.id)
        for detalle in detalles:
            if detalle.tasa_impuesto is None:
                raise PedidoServiceError(
                    "El pedido no contiene una tasa tributaria historica "
                    "valida. Debe actualizarse."
                )
            if detalle.tasa_impuesto != tasa_vigente:
                raise PedidoServiceError(
                    "La configuracion tributaria ha cambiado. "
                    "Debe actualizarse el borrador antes de confirmar."
                )

        subtotal = sum((d.subtotal for d in detalles), Decimal("0.00"))
        impuesto = sum((d.impuesto for d in detalles), Decimal("0.00"))
        total = sum((d.total for d in detalles), Decimal("0.00"))
        if (
            pedido.subtotal != subtotal
            or pedido.impuesto_total != impuesto
            or pedido.total != total
            or subtotal + impuesto != total
        ):
            raise PedidoServiceError("Los importes del pedido son inconsistentes.")

        ids_producto = sorted({d.producto_id for d in detalles})
        productos = db.scalars(
            select(Producto).where(
                Producto.empresa_id == empresa.id,
                Producto.id.in_(ids_producto),
                Producto.activo.is_(True),
            )
        ).all()
        productos_por_id = {p.id: p for p in productos}
        if len(productos_por_id) != len(ids_producto):
            raise PedidoServiceError(
                "Uno o mas productos ya no estan disponibles."
            )

        cantidades_requeridas = {}
        for detalle in detalles:
            producto = productos_por_id[detalle.producto_id]
            if producto.controla_stock:
                cantidades_requeridas[producto.id] = (
                    cantidades_requeridas.get(producto.id, Decimal("0.000"))
                    + detalle.cantidad
                )

        if cantidades_requeridas:
            inventarios = db.scalars(
                select(Inventario)
                .where(
                    Inventario.empresa_id == empresa.id,
                    Inventario.producto_id.in_(sorted(cantidades_requeridas)),
                )
                .order_by(Inventario.id.asc())
                .with_for_update()
            ).all()
            inventario_por_producto = {i.producto_id: i for i in inventarios}
            if len(inventario_por_producto) != len(cantidades_requeridas):
                raise PedidoServiceError(
                    "Uno o mas productos no tienen un registro de inventario."
                )

            # Consultar reservas solo despues de adquirir los bloqueos.
            for inventario in inventarios:
                reservado = db.scalar(
                    select(
                        func.coalesce(
                            func.sum(ReservaStock.cantidad_reservada), 0
                        )
                    ).where(
                        ReservaStock.empresa_id == empresa.id,
                        ReservaStock.inventario_id == inventario.id,
                        ReservaStock.estado == "ACTIVA",
                    )
                )
                disponible = inventario.cantidad_disponible - reservado
                requerido = cantidades_requeridas[inventario.producto_id]
                if disponible < requerido:
                    raise PedidoServiceError(
                        "Stock insuficiente para el producto "
                        f"{inventario.producto_id}. "
                        f"Disponible: {disponible}. Requerido: {requerido}."
                    )

            # Crear reservas solamente cuando todos los productos pasaron.
            for detalle in detalles:
                producto = productos_por_id[detalle.producto_id]
                if not producto.controla_stock:
                    continue
                inventario = inventario_por_producto[producto.id]
                db.add(
                    ReservaStock(
                        empresa_id=empresa.id,
                        pedido_id=pedido.id,
                        producto_id=producto.id,
                        inventario_id=inventario.id,
                        cantidad_reservada=detalle.cantidad,
                        estado="ACTIVA",
                    )
                )
            db.flush()

        pedido.estado = "CONFIRMADO"
        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="CONFIRMAR",
                entidad="pedidos",
                entidad_id=pedido.id,
                descripcion=(
                    "Confirmacion empresarial y reserva "
                    "transaccional de existencias."
                ),
                datos_anteriores={"estado": "BORRADOR"},
                datos_nuevos={
                    "estado": "CONFIRMADO",
                    "tasa_impuesto": str(tasa_vigente),
                    "productos_reservados": {
                        str(producto_id): str(cantidad)
                        for producto_id, cantidad in cantidades_requeridas.items()
                    },
                },
                origen="SISTEMA",
            )
        )
        db.flush()
        db.commit()
        db.refresh(pedido)
        return pedido

    except IntegrityError as exc:
        db.rollback()
        raise PedidoServiceError(
            "No fue posible confirmar el pedido. "
            "Verifique sus reservas y restricciones."
        ) from exc
    except Exception:
        db.rollback()
        raise

# ==========================================================
# FASE 08-C.9 — CANCELACION Y LIBERACION DE RESERVAS
# ==========================================================


def cancelar_pedido(
    db: Session,
    *,
    usuario_id: int,
    pedido_id: int,
) -> Pedido:
    """Cancela un pedido y libera sus reservas activas atomicamente.

    Reglas:
    - BORRADOR -> CANCELADO, sin modificar inventario.
    - CONFIRMADO -> CANCELADO, liberando reservas ACTIVAS.
    - COMPLETADO no puede cancelarse desde este flujo.
    - CANCELADO no puede cancelarse nuevamente.
    - Nunca modifica cantidad_disponible ni crea movimientos fisicos.

    Para pedidos confirmados se respeta el mismo orden de bloqueo
    de inventario utilizado por confirmar_pedido, evitando que una
    liberacion compita de forma insegura con nuevas reservas.
    """
    try:
        if type(pedido_id) is not int or pedido_id <= 0:
            raise PedidoServiceError(
                "Identificador de pedido invalido."
            )

        usuario, empresa = _validar_operador(
            db,
            usuario_id=usuario_id,
            permiso=PERMISO_CANCELAR,
        )

        # Serializa las operaciones de estado sobre el mismo pedido.
        pedido = db.scalar(
            select(Pedido)
            .where(
                Pedido.id == pedido_id,
                Pedido.empresa_id == empresa.id,
            )
            .with_for_update()
        )

        if pedido is None:
            raise PedidoServiceError(
                "El pedido no existe en esta empresa."
            )

        if pedido.estado == "CANCELADO":
            raise PedidoServiceError(
                "El pedido ya se encuentra CANCELADO."
            )

        if pedido.estado == "COMPLETADO":
            raise PedidoServiceError(
                "Un pedido COMPLETADO no puede cancelarse. "
                "Debe utilizarse el proceso empresarial de devolucion."
            )

        if pedido.estado not in {"BORRADOR", "CONFIRMADO"}:
            raise PedidoServiceError(
                "El estado actual del pedido no permite cancelacion."
            )

        estado_anterior = pedido.estado
        reservas_liberadas = {}
        numero_reservas_liberadas = 0

        # Una cancelacion de BORRADOR no deberia encontrar reservas.
        if estado_anterior == "BORRADOR":
            reserva_inconsistente = db.scalar(
                select(ReservaStock.id)
                .where(
                    ReservaStock.empresa_id == empresa.id,
                    ReservaStock.pedido_id == pedido.id,
                    ReservaStock.estado == "ACTIVA",
                )
                .limit(1)
            )

            if reserva_inconsistente is not None:
                raise PedidoServiceError(
                    "El pedido BORRADOR contiene reservas activas "
                    "inconsistentes y no puede cancelarse automaticamente."
                )

        if estado_anterior == "CONFIRMADO":
            # Primera lectura para conocer las filas de inventario que
            # deben bloquearse. El pedido ya esta bloqueado, por lo que
            # otro flujo correcto sobre este mismo pedido no puede cambiar
            # sus reservas mientras esta transaccion permanezca activa.
            reservas_candidatas = db.scalars(
                select(ReservaStock)
                .where(
                    ReservaStock.empresa_id == empresa.id,
                    ReservaStock.pedido_id == pedido.id,
                    ReservaStock.estado == "ACTIVA",
                )
                .order_by(
                    ReservaStock.inventario_id.asc(),
                    ReservaStock.id.asc(),
                )
            ).all()

            inventario_ids = sorted({
                reserva.inventario_id
                for reserva in reservas_candidatas
            })

            if inventario_ids:
                # Mismo orden global que confirmar_pedido: inventario
                # ascendente antes de modificar reservas.
                inventarios = db.scalars(
                    select(Inventario)
                    .where(
                        Inventario.empresa_id == empresa.id,
                        Inventario.id.in_(inventario_ids),
                    )
                    .order_by(Inventario.id.asc())
                    .with_for_update()
                ).all()

                if len(inventarios) != len(inventario_ids):
                    raise PedidoServiceError(
                        "No fue posible bloquear todos los inventarios "
                        "asociados a las reservas del pedido."
                    )

                reservas = db.scalars(
                    select(ReservaStock)
                    .where(
                        ReservaStock.empresa_id == empresa.id,
                        ReservaStock.pedido_id == pedido.id,
                        ReservaStock.estado == "ACTIVA",
                    )
                    .order_by(
                        ReservaStock.inventario_id.asc(),
                        ReservaStock.id.asc(),
                    )
                    .with_for_update()
                ).all()

                for reserva in reservas:
                    reservas_liberadas[str(reserva.producto_id)] = str(
                        reserva.cantidad_reservada
                    )
                    reserva.estado = "LIBERADA"
                    numero_reservas_liberadas += 1

                db.flush()

        pedido.estado = "CANCELADO"

        db.add(
            Auditoria(
                empresa_id=empresa.id,
                usuario_id=usuario.id,
                accion="CANCELAR",
                entidad="pedidos",
                entidad_id=pedido.id,
                descripcion=(
                    "Cancelacion empresarial del pedido y liberacion "
                    "de reservas activas cuando corresponde."
                ),
                datos_anteriores={
                    "estado": estado_anterior,
                },
                datos_nuevos={
                    "estado": "CANCELADO",
                    "reservas_liberadas": reservas_liberadas,
                    "numero_reservas_liberadas": (
                        numero_reservas_liberadas
                    ),
                },
                origen="SISTEMA",
            )
        )

        db.flush()
        db.commit()
        db.refresh(pedido)

        return pedido

    except IntegrityError as exc:
        db.rollback()
        raise PedidoServiceError(
            "No fue posible cancelar el pedido. "
            "Verifique su estado y sus reservas."
        ) from exc

    except Exception:
        db.rollback()
        raise

