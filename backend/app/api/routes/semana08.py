"""Estadística Semana 08, solo usuario autorizado de su empresa."""
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.services.semana08_service import obtener_semana08, Semana08Error
router=APIRouter(prefix='/api/analytics',tags=['Analytics Semana 08'])

@router.get('/semana08')
def estadistica_semana08(fecha_inicio:date,fecha_fin:date,
        media_hipotetica:float|None=Query(None,ge=0),alfa:float=Query(0.05,gt=0,lt=1),
        usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    try:
        return obtener_semana08(db,usuario_id=usuario.id,inicio=fecha_inicio,fin=fecha_fin,
                                media_hipotetica=media_hipotetica,alfa=alfa)
    except Semana08Error as exc:
        raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc
