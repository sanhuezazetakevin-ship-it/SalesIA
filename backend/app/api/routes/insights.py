"""FASE 11: insights explicables y trazables."""
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.schemas.insights import (GenerarInsightsRequest, CambiarEstadoInsightRequest,
                                  InsightResponse, InsightsListado)
from app.services.insights_service import (InsightsError, generar_insights,
    listar_insights, obtener_insight, actualizar_estado)

router = APIRouter(prefix='/api/insights', tags=['Insights'])

def _error(exc):
    return HTTPException(status_code=exc.status_code, detail=str(exc))

@router.post('/generar', response_model=list[InsightResponse], status_code=status.HTTP_201_CREATED)
def generar(entrada: GenerarInsightsRequest, usuario: Usuario = Depends(get_current_active_user),
            db: Session = Depends(get_db)):
    try:
        resultado = generar_insights(db, usuario_id=usuario.id, tipo=entrada.tipo, analisis_id=entrada.analisis_id)
        db.commit()
        for r in resultado:
            db.refresh(r)
        return resultado
    except InsightsError as exc:
        db.rollback()
        raise _error(exc) from exc
    except Exception:
        db.rollback()
        raise

@router.get('', response_model=InsightsListado)
def listar(limite: int = Query(20, ge=1, le=100),
           estado: Literal['NUEVO','REVISADO','DESCARTADO'] | None = Query(None),
           tipo: Literal['VENTAS','INVENTARIO','CLIENTES','RENDIMIENTO','PREDICCION','GENERAL'] | None = Query(None),
           usuario: Usuario = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        return {'limite': limite, 'items': listar_insights(db, usuario_id=usuario.id, limite=limite, estado=estado, tipo=tipo)}
    except InsightsError as exc:
        raise _error(exc) from exc

@router.get('/{insight_id}', response_model=InsightResponse)
def detalle(insight_id: int, usuario: Usuario = Depends(get_current_active_user),
            db: Session = Depends(get_db)):
    try:
        registro = obtener_insight(db, usuario_id=usuario.id, insight_id=insight_id)
    except InsightsError as exc:
        raise _error(exc) from exc
    if registro is None:
        raise HTTPException(status_code=404, detail='Insight no encontrado.')
    return registro

@router.patch('/{insight_id}/estado', response_model=InsightResponse)
def cambiar_estado(insight_id: int, entrada: CambiarEstadoInsightRequest,
                   usuario: Usuario = Depends(get_current_active_user), db: Session = Depends(get_db)):
    try:
        registro = actualizar_estado(db, usuario_id=usuario.id, insight_id=insight_id, estado=entrada.estado)
        db.commit()
        db.refresh(registro)
        return registro
    except InsightsError as exc:
        db.rollback()
        raise _error(exc) from exc
    except Exception:
        db.rollback()
        raise
