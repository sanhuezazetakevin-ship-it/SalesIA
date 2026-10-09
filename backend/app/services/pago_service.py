"""SalesIA Enterprise - FASE 08-E. Servicio transaccional de pagos."""
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.pago import Pago
from app.models.venta import Venta
from app.services.role_service import _obtener_permisos_efectivos
from app.models.usuario import Usuario
from app.models.empresa import Empresa

PERMISO_REGISTRAR = "pagos.registrar"
PERMISO_VER = "pagos.ver"
PERMISO_ANULAR = "pagos.anular"
MEDIOS = frozenset({"EFECTIVO", "TARJETA", "TRANSFERENCIA", "YAPE", "PLIN", "OTRO"})
CENTIMO = Decimal("0.01")


class PagoServiceError(Exception):
    """Error de negocio controlado del modulo de pagos."""


def _operador(db: Session, usuario_id: int, permiso: str) -> tuple[Usuario, Empresa]:
    if type(usuario_id) is not int or usuario_id <= 0:
        raise PagoServiceError("Identificador de usuario invalido.")
    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id, Usuario.activo.is_(True)))
    if usuario is None:
        raise PagoServiceError("El usuario no existe o esta inactivo.")
    empresa = db.scalar(select(Empresa).where(Empresa.id == usuario.empresa_id, Empresa.activo.is_(True)))
    if empresa is None:
        raise PagoServiceError("La empresa no existe o esta inactiva.")
    permisos = _obtener_permisos_efectivos(db, usuario_id=usuario.id, empresa_id=empresa.id)
    if permiso not in permisos:
        raise PagoServiceError("No tiene autorizacion para esta operacion.")
    return usuario, empresa


def _venta(db: Session, venta_id: int, empresa_id: int, *, bloquear: bool) -> Venta:
    if type(venta_id) is not int or venta_id <= 0:
        raise PagoServiceError("Identificador de venta invalido.")
    consulta = select(Venta).where(Venta.id == venta_id, Venta.empresa_id == empresa_id)
    if bloquear:
        consulta = consulta.with_for_update()
    venta = db.scalar(consulta)
    if venta is None:
        raise PagoServiceError("La venta no existe en esta empresa.")
    return venta


def _pagos(db: Session, venta_id: int, empresa_id: int) -> list[Pago]:
    return list(db.scalars(select(Pago).where(
        Pago.empresa_id == empresa_id, Pago.venta_id == venta_id
    ).order_by(Pago.id.asc())).all())


def _totales(venta: Venta, pagos: list[Pago]) -> tuple[Decimal, Decimal, str]:
    abonado = sum((p.monto for p in pagos if p.estado == "REGISTRADO"), Decimal("0.00"))
    saldo = venta.total - abonado
    if saldo < 0:
        raise PagoServiceError("Los pagos exceden el total de la venta; revise los datos.")
    estado = "PAGADO" if saldo == 0 else ("PARCIAL" if abonado > 0 else "PENDIENTE")
    return abonado, saldo, estado


def _importe(monto: Decimal) -> Decimal:
    if not isinstance(monto, Decimal) or not monto.is_finite():
        raise PagoServiceError("Monto de pago invalido.")
    if monto <= 0 or monto != monto.quantize(CENTIMO) or monto >= Decimal("1000000000000"):
        raise PagoServiceError("El monto debe ser positivo y tener como maximo dos decimales.")
    return monto


def registrar_pago(
    db: Session, *, usuario_id: int, venta_id: int, monto: Decimal,
    medio_pago: str, referencia_externa: str | None = None,
    observaciones: str | None = None,
    idempotency_key: str | None = None,
) -> Pago:
    """Un solo commit para pago, estado de venta y auditoria."""
    try:
        monto = _importe(monto)
        if medio_pago not in MEDIOS:
            raise PagoServiceError("Medio de pago invalido.")
        if referencia_externa is not None and len(referencia_externa) > 120:
            raise PagoServiceError("Referencia externa demasiado larga.")
        if observaciones is not None and len(observaciones) > 500:
            raise PagoServiceError("Observaciones demasiado largas.")
        if idempotency_key is not None:
            if (
                not isinstance(idempotency_key, str)
                or not 16 <= len(idempotency_key) <= 128
                or not idempotency_key.isascii()
                or not all(c.isalnum() or c in "-_" for c in idempotency_key)
            ):
                raise PagoServiceError("Clave de idempotencia invalida.")
        usuario, empresa = _operador(db, usuario_id, PERMISO_REGISTRAR)
        venta = _venta(db, venta_id, empresa.id, bloquear=True)
        codigo_idempotente = None
        if idempotency_key is not None:
            # La restriccion UNIQUE(empresa_id, codigo) protege la unicidad
            # incluso entre sesiones que operen sobre ventas diferentes.
            digest = sha256(f"{empresa.id}:{idempotency_key}".encode("utf-8")).hexdigest()
            codigo_idempotente = "PAG-" + digest[:36]
            existente = db.scalar(select(Pago).where(
                Pago.empresa_id == empresa.id,
                Pago.codigo == codigo_idempotente,
            ))
            if existente is not None:
                if (
                    existente.venta_id != venta.id
                    or existente.registrado_por_id != usuario.id
                    or existente.monto != monto
                    or existente.medio_pago != medio_pago
                    or existente.referencia_externa != referencia_externa
                    or existente.observaciones != observaciones
                    or existente.estado != "REGISTRADO"
                ):
                    raise PagoServiceError("Conflicto de clave de idempotencia.")
                # No se crea pago ni auditoria nuevos; la operacion previa
                # se devuelve sin mutar el estado de la venta.
                db.commit()
                return existente
        if venta.estado == "CANCELADA":
            raise PagoServiceError("No se permiten pagos de ventas canceladas.")
        _, saldo, _ = _totales(venta, _pagos(db, venta.id, empresa.id))
        if saldo <= 0:
            raise PagoServiceError("La venta ya esta pagada.")
        if monto > saldo:
            raise PagoServiceError("El monto excede el saldo pendiente.")
        pago = Pago(
            empresa_id=empresa.id, venta_id=venta.id, registrado_por_id=usuario.id,
            codigo=codigo_idempotente or f"PAG-{uuid4().hex[:20].upper()}", monto=monto,
            medio_pago=medio_pago, estado="REGISTRADO",
            referencia_externa=referencia_externa, observaciones=observaciones,
        )
        db.add(pago)
        db.flush()
        anterior = venta.estado_pago
        venta.estado_pago = "PAGADO" if monto == saldo else "PARCIAL"
        db.add(Auditoria(
            empresa_id=empresa.id, usuario_id=usuario.id, accion="CREAR",
            entidad="pagos", entidad_id=pago.id,
            descripcion="Registro de pago de venta.",
            datos_anteriores={"estado_pago": anterior, "saldo": str(saldo)},
            datos_nuevos={"pago_id": pago.id, "monto": str(monto), "medio_pago": medio_pago,
                          "estado_pago": venta.estado_pago}, origen="SISTEMA",
        ))
        db.commit()
        db.refresh(pago)
        return pago
    except IntegrityError as exc:
        db.rollback()
        raise PagoServiceError("No fue posible registrar el pago por un conflicto de integridad.") from exc
    except Exception:
        db.rollback()
        raise


def anular_pago(db: Session, *, usuario_id: int, pago_id: int, motivo: str) -> Pago:
    """Anulacion logica: no elimina el pago ni su trazabilidad."""
    try:
        if type(pago_id) is not int or pago_id <= 0:
            raise PagoServiceError("Identificador de pago invalido.")
        if not isinstance(motivo, str) or not 3 <= len(motivo.strip()) <= 500:
            raise PagoServiceError("El motivo debe contener entre 3 y 500 caracteres.")
        usuario, empresa = _operador(db, usuario_id, PERMISO_ANULAR)
        # Primero obtener venta_id sin bloqueo; siempre bloquear la venta antes de mutar pagos.
        identificador_venta = db.scalar(select(Pago.venta_id).where(
            Pago.id == pago_id, Pago.empresa_id == empresa.id
        ))
        if identificador_venta is None:
            raise PagoServiceError("El pago no existe en esta empresa.")
        venta = _venta(db, identificador_venta, empresa.id, bloquear=True)
        pago = db.scalar(select(Pago).where(
            Pago.id == pago_id, Pago.empresa_id == empresa.id,
            Pago.venta_id == venta.id).with_for_update())
        if pago is None or pago.estado != "REGISTRADO":
            raise PagoServiceError("El pago no existe o ya esta anulado.")
        anterior = venta.estado_pago
        pago.estado = "ANULADO"
        db.flush()
        _, saldo, nuevo_estado = _totales(venta, _pagos(db, venta.id, empresa.id))
        venta.estado_pago = nuevo_estado
        db.add(Auditoria(
            empresa_id=empresa.id, usuario_id=usuario.id, accion="ANULAR",
            entidad="pagos", entidad_id=pago.id,
            descripcion=motivo.strip(),
            datos_anteriores={"estado": "REGISTRADO", "estado_pago_venta": anterior},
            datos_nuevos={"estado": "ANULADO", "estado_pago_venta": nuevo_estado,
                          "saldo_pendiente": str(saldo)}, origen="SISTEMA",
        ))
        db.commit()
        db.refresh(pago)
        return pago
    except IntegrityError as exc:
        db.rollback()
        raise PagoServiceError("No fue posible anular el pago por un conflicto de integridad.") from exc
    except Exception:
        db.rollback()
        raise


def resumen_pagos(db: Session, *, usuario_id: int, venta_id: int) -> dict:
    _, empresa = _operador(db, usuario_id, PERMISO_VER)
    venta = _venta(db, venta_id, empresa.id, bloquear=False)
    pagos = _pagos(db, venta.id, empresa.id)
    abonado, saldo, estado = _totales(venta, pagos)
    return {"venta_id": venta.id, "total_venta": venta.total,
            "total_pagado": abonado, "saldo_pendiente": saldo,
            "estado_pago": estado, "pagos": pagos}
