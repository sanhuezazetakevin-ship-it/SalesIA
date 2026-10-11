from datetime import date
from fastapi import APIRouter,Depends,Query,HTTPException
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.services.notificaciones145_service import sincronizar,listar,marcar_leida
from app.services.mejoras145_service import Mejoras145Error
router=APIRouter(prefix='/api/mejoras/notificaciones-persistentes',tags=['Notificaciones empresariales'])

@router.post('/sincronizar')
def sincronizar_alertas(fecha_inicio:date,fecha_fin:date,usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    try: return sincronizar(db,usuario.id,fecha_inicio,fecha_fin)
    except Mejoras145Error as exc: raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc

@router.get('')
def historial(solo_no_leidas:bool=False,limite:int=Query(50,ge=1,le=100),usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    try: return listar(db,usuario.id,solo_no_leidas,limite)
    except Mejoras145Error as exc: raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc

@router.patch('/{notificacion_id}/leida')
def leida(notificacion_id:int,usuario:Usuario=Depends(get_current_active_user),db:Session=Depends(get_db)):
    try: resultado=marcar_leida(db,usuario.id,notificacion_id)
    except Mejoras145Error as exc: raise HTTPException(status_code=exc.status_code,detail=str(exc)) from exc
    if resultado is None: raise HTTPException(status_code=404,detail='Notificación no encontrada.')
    return resultado
