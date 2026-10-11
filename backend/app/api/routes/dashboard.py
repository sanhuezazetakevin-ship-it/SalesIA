"""FASE 10: series temporales para el dashboard empresarial."""
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.schemas.dashboard_series import SerieVentasResponse
from app.services.dashboard_series_service import obtener_serie_ventas
from app.services.analytics_resumen_service import AnalyticsResumenError

router = APIRouter(prefix='/api/dashboard', tags=['Dashboard'])

@router.get('/ventas/serie', response_model=SerieVentasResponse)
def serie_ventas(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    agrupacion: Literal['dia', 'mes'] = Query('dia'),
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return obtener_serie_ventas(db, usuario_id=usuario.id, fecha_inicio=fecha_inicio,
                                    fecha_fin=fecha_fin, agrupacion=agrupacion)
    except AnalyticsResumenError as exc:
        mensaje = str(exc)
        raise HTTPException(status_code=403 if 'No autorizado' in mensaje else 422, detail=mensaje) from exc

from app.schemas.dashboard_comercial import DashboardComercialResponse
from app.services.dashboard_comercial_service import obtener_dashboard_comercial

@router.get('/comercial', response_model=DashboardComercialResponse)
def dashboard_comercial(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    limite: int = Query(10, ge=1, le=20),
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return obtener_dashboard_comercial(db, usuario_id=usuario.id,
            fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, limite=limite)
    except AnalyticsResumenError as exc:
        mensaje = str(exc)
        raise HTTPException(status_code=403 if 'No autorizado' in mensaje else 422, detail=mensaje) from exc
