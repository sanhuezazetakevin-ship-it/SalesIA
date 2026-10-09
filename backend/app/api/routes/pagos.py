"""SalesIA Enterprise - FASE 08-E.4: API REST de pagos."""
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.schemas.pagos import PagoCreate, PagoAnular, PagoResponse, ResumenPagosResponse
from app.services.pago_service import (
    PagoServiceError, registrar_pago, anular_pago, resumen_pagos,
)

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])


def _rechazar_operacion_pago(exc: PagoServiceError):
    mensaje = str(exc)
    normalizado = mensaje.lower()
    if "autorizacion" in normalizado or "autorización" in normalizado:
        raise HTTPException(status_code=403, detail="No tiene autorización para esta operación de pagos.") from exc
    if "no existe en esta empresa" in normalizado:
        raise HTTPException(status_code=404, detail="El recurso solicitado no está disponible.") from exc
    conflictos = (
        "excede el saldo", "ya esta pagada", "ventas canceladas",
        "conflicto de clave de idempotencia",
        "ya esta anulado", "los pagos exceden", "conflicto de integridad",
    )
    if any(texto in normalizado for texto in conflictos):
        raise HTTPException(status_code=409, detail=mensaje) from exc
    raise HTTPException(status_code=400, detail="No fue posible completar la operación de pagos.") from exc


@router.post("/ventas/{venta_id}", response_model=PagoResponse, status_code=status.HTTP_201_CREATED)
def registrar_pago_http(
    venta_id: int,
    datos: PagoCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return registrar_pago(
            db, usuario_id=usuario_actual.id, venta_id=venta_id,
            monto=datos.monto, medio_pago=datos.medio_pago,
            referencia_externa=datos.referencia_externa,
            observaciones=datos.observaciones,
            idempotency_key=idempotency_key,
        )
    except PagoServiceError as exc:
        _rechazar_operacion_pago(exc)


@router.get("/ventas/{venta_id}/resumen", response_model=ResumenPagosResponse)
def resumen_pagos_http(
    venta_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return resumen_pagos(db, usuario_id=usuario_actual.id, venta_id=venta_id)
    except PagoServiceError as exc:
        _rechazar_operacion_pago(exc)


@router.post("/{pago_id}/anular", response_model=PagoResponse)
def anular_pago_http(
    pago_id: int,
    datos: PagoAnular,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return anular_pago(db, usuario_id=usuario_actual.id, pago_id=pago_id, motivo=datos.motivo)
    except PagoServiceError as exc:
        _rechazar_operacion_pago(exc)
