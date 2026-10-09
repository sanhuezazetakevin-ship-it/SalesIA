"""API FASE 09-E.3: recepciones confirmadas de compras."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.dependencies import get_current_active_user
from app.models.usuario import Usuario
from app.models.recepcion_compra_detalle import RecepcionCompraDetalle
from app.schemas.recepciones_compra import (RecepcionCrear, RecepcionRespuesta,
    RecepcionPagina, RecepcionLineaRespuesta)
from app.services.recepcion_compra_service import (RecepcionCompraServiceError,
    recibir_compra, obtener_recepcion_compra, listar_recepciones_compra)

router = APIRouter(prefix='/api/compras/recepciones', tags=['Recepciones de compra'])

def _http_error(exc: RecepcionCompraServiceError):
    mensaje = str(exc)
    texto = mensaje.lower()
    if 'autorización' in texto or 'usuario inactivo' in texto or 'empresa inactiva' in texto:
        codigo = status.HTTP_403_FORBIDDEN
    elif 'no encontrada' in texto or 'no encontrado' in texto:
        codigo = status.HTTP_404_NOT_FOUND
    elif any(x in texto for x in ('duplicad', 'excede', 'idempotency key utilizada', 'no admite recepciones')):
        codigo = status.HTTP_409_CONFLICT
    else:
        codigo = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=codigo, detail=mensaje) from exc

def _con_detalles(db: Session, recepcion):
    detalles = db.scalars(select(RecepcionCompraDetalle).where(
        RecepcionCompraDetalle.empresa_id == recepcion.empresa_id,
        RecepcionCompraDetalle.recepcion_id == recepcion.id
    ).order_by(RecepcionCompraDetalle.id)).all()
    return RecepcionRespuesta.model_validate({
        **{campo: getattr(recepcion, campo) for campo in RecepcionRespuesta.model_fields if campo != 'detalles'},
        'detalles': [RecepcionLineaRespuesta.model_validate(item) for item in detalles]
    })

@router.post('', response_model=RecepcionRespuesta, status_code=status.HTTP_201_CREATED)
def crear_recepcion_http(datos: RecepcionCrear,
                         usuario: Usuario = Depends(get_current_active_user),
                         db: Session = Depends(get_db)):
    try:
        recepcion = recibir_compra(db, usuario_id=usuario.id, **datos.model_dump())
        return _con_detalles(db, recepcion)
    except RecepcionCompraServiceError as exc:
        _http_error(exc)

@router.get('', response_model=RecepcionPagina)
def listar_recepciones_http(orden_id: int | None = Query(default=None, gt=0),
                              pagina: int = Query(default=1, ge=1),
                              limite: int = Query(default=20, ge=1, le=100),
                              usuario: Usuario = Depends(get_current_active_user),
                              db: Session = Depends(get_db)):
    try:
        resultado = listar_recepciones_compra(db, usuario_id=usuario.id,
            orden_id=orden_id, pagina=pagina, limite=limite)
        return {**resultado, 'items': [_con_detalles(db, r) for r in resultado['items']]}
    except RecepcionCompraServiceError as exc:
        _http_error(exc)

@router.get('/{recepcion_id}', response_model=RecepcionRespuesta)
def obtener_recepcion_http(recepcion_id: int,
                           usuario: Usuario = Depends(get_current_active_user),
                           db: Session = Depends(get_db)):
    try:
        return _con_detalles(db, obtener_recepcion_compra(db, usuario_id=usuario.id,
                                                            recepcion_id=recepcion_id))
    except RecepcionCompraServiceError as exc:
        _http_error(exc)
