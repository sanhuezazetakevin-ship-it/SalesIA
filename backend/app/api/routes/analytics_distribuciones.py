"""Endpoint independiente para evitar reemplazar el router Analytics existente."""
from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.schemas.analytics_distribuciones import AnalyticsDistribucionesResponse
from app.services.analytics_distribuciones_service import obtener_distribuciones, AnalyticsResumenError

router = APIRouter(prefix='/api/analytics', tags=['Analytics'])

@router.get('/distribuciones',response_model=AnalyticsDistribucionesResponse)
def consultar_distribuciones(
    fecha_inicio:date=Query(...),fecha_fin:date=Query(...),
    variable:Literal['importe_venta','estado_pago']=Query('importe_venta'),
    intervalos:int=Query(5,ge=1,le=20),
    usuario:Usuario=Depends(get_current_active_user),
    db:Session=Depends(get_db),
):
    try:
        return obtener_distribuciones(db,usuario_id=usuario.id,fecha_inicio=fecha_inicio,
                                      fecha_fin=fecha_fin,variable=variable,intervalos=intervalos)
    except AnalyticsResumenError as exc:
        raise HTTPException(status_code=403 if 'No autorizado' in str(exc) else 422, detail=str(exc)) from exc
