"""FASE 14.5: respuestas listas para representar en React, sin gráficos rasterizados."""
from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.services.mejoras145_service import (dashboard_visual,inventario_visual,clientes_visual,
    notificaciones_visual,seguridad_visual,Mejoras145Error)
from app.services.analytics_resumen_service import AnalyticsResumenError

router=APIRouter(prefix='/api/mejoras',tags=['Mejoras empresariales'])


def _ejecutar(func, **kwargs):
    try:
        return func(**kwargs)
    except Mejoras145Error as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except AnalyticsResumenError as exc:
        raise HTTPException(status_code=403 if 'autorizado' in str(exc).lower() else 422,detail=str(exc)) from exc


@router.get('/dashboard')
def dashboard(fecha_inicio:date,fecha_fin:date,usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    return _ejecutar(dashboard_visual,db=db,usuario_id=usuario.id,inicio=fecha_inicio,fin=fecha_fin)


@router.get('/inventario')
def inventario(fecha_inicio:date,fecha_fin:date,horizonte:int=Query(14,ge=1,le=90),limite:int=Query(30,ge=1,le=100),
    usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    return _ejecutar(inventario_visual,db=db,usuario_id=usuario.id,inicio=fecha_inicio,fin=fecha_fin,horizonte=horizonte,limite=limite)


@router.get('/clientes')
def clientes(fecha_inicio:date,fecha_fin:date,limite:int=Query(50,ge=1,le=100),
    usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    return _ejecutar(clientes_visual,db=db,usuario_id=usuario.id,inicio=fecha_inicio,fin=fecha_fin,limite=limite)


@router.get('/notificaciones')
def notificaciones(fecha_inicio:date,fecha_fin:date,usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    return _ejecutar(notificaciones_visual,db=db,usuario_id=usuario.id,inicio=fecha_inicio,fin=fecha_fin)


@router.get('/seguridad')
def seguridad(fecha_inicio:date,fecha_fin:date,usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    return _ejecutar(seguridad_visual,db=db,usuario_id=usuario.id,inicio=fecha_inicio,fin=fecha_fin)
