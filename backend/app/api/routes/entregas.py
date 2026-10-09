"""SalesIA Enterprise - FASE 08-F.4: API HTTP de entregas."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.schemas.entregas import EntregaConfirmar, EntregaConMovimientosResponse, EntregaResponse
from app.services.entrega_service import (
    EntregaServiceError, confirmar_entrega, obtener_entrega, obtener_entrega_por_venta,
)

router = APIRouter(prefix="/api/entregas", tags=["Entregas"])


def _mapear_error(exc: EntregaServiceError):
    mensaje = str(exc)
    normalizado = mensaje.lower()
    if "autorizacion" in normalizado:
        raise HTTPException(status_code=403, detail="No tiene autorización para esta operación.") from exc
    if "no existe en esta empresa" in normalizado:
        raise HTTPException(status_code=404, detail="La entrega solicitada no está disponible.") from exc
    if any(t in normalizado for t in (
        "ya tiene una entrega", "ya consumida", "stock fisico insuficiente",
        "reservas del pedido no corresponden", "reserva inconsistente",
        "venta cancelada", "conflicto de integridad", "ventas directas",
        "estado de venta no permitido",
    )):
        raise HTTPException(status_code=409, detail=mensaje) from exc
    raise HTTPException(status_code=400, detail="No fue posible completar la operación de entregas.") from exc


def _respuesta(resultado: dict) -> EntregaConMovimientosResponse:
    entrega = EntregaResponse.model_validate(resultado["entrega"])
    return EntregaConMovimientosResponse(
        **entrega.model_dump(), movimientos=resultado["movimientos"]
    )


@router.post("/ventas/{venta_id}/confirmar", response_model=EntregaConMovimientosResponse,
             status_code=status.HTTP_201_CREATED)
def confirmar_entrega_http(
    venta_id: int, datos: EntregaConfirmar,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return _respuesta(confirmar_entrega(
            db, usuario_id=usuario_actual.id, venta_id=venta_id,
            observaciones=datos.observaciones,
        ))
    except EntregaServiceError as exc:
        _mapear_error(exc)


@router.get("/ventas/{venta_id}", response_model=EntregaConMovimientosResponse)
def obtener_entrega_venta_http(
    venta_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return _respuesta(obtener_entrega_por_venta(
            db, usuario_id=usuario_actual.id, venta_id=venta_id,
        ))
    except EntregaServiceError as exc:
        _mapear_error(exc)


@router.get("/{entrega_id}", response_model=EntregaConMovimientosResponse)
def obtener_entrega_http(
    entrega_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return _respuesta(obtener_entrega(
            db, usuario_id=usuario_actual.id, entrega_id=entrega_id,
        ))
    except EntregaServiceError as exc:
        _mapear_error(exc)
