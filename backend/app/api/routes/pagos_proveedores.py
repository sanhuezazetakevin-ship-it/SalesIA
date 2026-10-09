"""API 09-E.4: pagos a proveedores. JWT por dependencia y RBAC por servicio."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.dependencies import get_current_active_user
from app.models.usuario import Usuario
from app.schemas.pagos_proveedores import PagoProveedorCrear, PagoProveedorRespuesta, PagoProveedorPagina
from app.services.pago_proveedor_service import (
    PagoProveedorServiceError, registrar_pago_proveedor, anular_pago_proveedor,
    obtener_pago_proveedor, listar_pagos_proveedor,
)

router = APIRouter(prefix='/api/compras/pagos', tags=['Pagos a proveedores'])

def _http_error(exc: PagoProveedorServiceError):
    mensaje = str(exc)
    texto = mensaje.lower()
    if 'autorización' in texto or 'usuario inactivo' in texto or 'empresa inactiva' in texto:
        codigo = status.HTTP_403_FORBIDDEN
    elif 'no encontrada' in texto or 'no encontrado' in texto:
        codigo = status.HTTP_404_NOT_FOUND
    elif any(parte in texto for parte in (
        'excede', 'duplicad', 'idempotency key reutilizada',
        'ya anulado', 'no permite pagos', 'inconsistencia',
    )):
        codigo = status.HTTP_409_CONFLICT
    else:
        codigo = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=codigo, detail=mensaje) from exc

@router.post('', response_model=PagoProveedorRespuesta, status_code=status.HTTP_201_CREATED)
def crear_pago_proveedor_http(datos: PagoProveedorCrear,
                             usuario: Usuario = Depends(get_current_active_user),
                             db: Session = Depends(get_db)):
    try:
        return registrar_pago_proveedor(db, usuario_id=usuario.id, **datos.model_dump())
    except PagoProveedorServiceError as exc:
        _http_error(exc)

@router.get('', response_model=PagoProveedorPagina)
def listar_pagos_proveedores_http(
    orden_id: int | None = Query(default=None, gt=0),
    estado: str | None = Query(default=None),
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=100),
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return listar_pagos_proveedor(db, usuario_id=usuario.id, orden_id=orden_id,
                                     estado=estado, pagina=pagina, limite=limite)
    except PagoProveedorServiceError as exc:
        _http_error(exc)

@router.get('/{pago_id}', response_model=PagoProveedorRespuesta)
def obtener_pago_proveedor_http(pago_id: int,
                               usuario: Usuario = Depends(get_current_active_user),
                               db: Session = Depends(get_db)):
    try:
        return obtener_pago_proveedor(db, usuario_id=usuario.id, pago_id=pago_id)
    except PagoProveedorServiceError as exc:
        _http_error(exc)

@router.post('/{pago_id}/anular', response_model=PagoProveedorRespuesta)
def anular_pago_proveedor_http(pago_id: int,
                              usuario: Usuario = Depends(get_current_active_user),
                              db: Session = Depends(get_db)):
    try:
        return anular_pago_proveedor(db, usuario_id=usuario.id, pago_id=pago_id)
    except PagoProveedorServiceError as exc:
        _http_error(exc)
