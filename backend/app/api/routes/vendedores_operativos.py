"""Directorio de vendedores basado en usuarios y roles, sin duplicar identidades."""
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.services.role_service import _obtener_permisos_efectivos

router=APIRouter(prefix='/api/vendedores-operativos',tags=['Vendedores'])

@router.get('')
def listar(pagina:int=Query(1,ge=1),limite:int=Query(20,ge=1,le=100),busqueda:str=Query('',max_length=100),
           usuario:Usuario=Depends(get_current_active_user), db:Session=Depends(get_db)):
    permisos=_obtener_permisos_efectivos(db,usuario_id=usuario.id,empresa_id=usuario.empresa_id)
    if 'usuarios.ver' not in permisos: raise HTTPException(403,'Permiso insuficiente.')
    q=select(Usuario).where(Usuario.empresa_id==usuario.empresa_id,Usuario.roles.any(
      (Rol.empresa_id==usuario.empresa_id)&(Rol.nombre=='VENDEDOR')))
    if busqueda.strip(): q=q.where(Usuario.nombre.ilike(f'%{busqueda.strip()}%'))
    total=db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows=db.scalars(q.order_by(Usuario.nombre,Usuario.id).offset((pagina-1)*limite).limit(limite)).all()
    return {'total':total,'pagina':pagina,'limite':limite,'items':[
      {'id':u.id,'nombre':u.nombre,'email':u.email,'activo':u.activo} for u in rows]}
