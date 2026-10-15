"""Administración de plataforma: opt-in explícito y control de acceso separado del RBAC empresarial."""
import os
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_active_user
from app.api.routes.alta_empresas import SolicitudAltaEmpresa
from app.core.security import hash_password
from app.database.connection import get_db
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.configuracion_empresa import ConfiguracionEmpresa
from app.models.asociaciones import usuarios_roles, roles_permisos
from scripts.seed_roles_permisos import ROLES, TODOS_LOS_PERMISOS

router = APIRouter(prefix='/api/plataforma/empresas', tags=['Administración de plataforma'])


def exigir_operador(user: Usuario = Depends(get_current_active_user)) -> Usuario:
    # Nunca confiar en headers de rol o empresa; el usuario proviene de JWT y sesión validados.
    authorized = {v.strip().casefold() for v in os.environ.get('SALESIA_PLATFORM_ADMIN_EMAILS', '').split(',') if v.strip()}
    if not authorized or user.email.casefold() not in authorized:
        raise HTTPException(status_code=403, detail='Acceso de plataforma no autorizado')
    return user


class AprobarSolicitud(BaseModel):
    email_administrador: EmailStr
    nombre_administrador: str = Field(min_length=2, max_length=120)
    password_inicial: str = Field(min_length=12, max_length=128)


@router.get('/solicitudes')
def listar_solicitudes(estado: str | None = None, limit: int = 100,
                       _: Usuario = Depends(exigir_operador), db: Session = Depends(get_db)):
    if estado and estado not in ('PENDIENTE', 'APROBADA', 'RECHAZADA'):
        raise HTTPException(422, 'Estado inválido')
    query = select(SolicitudAltaEmpresa).order_by(SolicitudAltaEmpresa.id.desc()).limit(max(1, min(limit, 100)))
    if estado:
        query = query.where(SolicitudAltaEmpresa.estado == estado)
    return [{'id': s.id, 'razon_social': s.razon_social, 'ruc': s.ruc, 'nombre_contacto': s.nombre_contacto,
             'email_contacto': s.email_contacto, 'estado': s.estado} for s in db.scalars(query)]


@router.post('/solicitudes/{solicitud_id}/rechazar')
def rechazar(solicitud_id: int, _: Usuario = Depends(exigir_operador), db: Session = Depends(get_db)):
    with db.begin_nested():
        solicitud = db.scalar(select(SolicitudAltaEmpresa).where(SolicitudAltaEmpresa.id == solicitud_id).with_for_update())
        if not solicitud:
            raise HTTPException(404, 'Solicitud no encontrada')
        if solicitud.estado != 'PENDIENTE':
            raise HTTPException(409, 'La solicitud ya fue procesada')
        solicitud.estado = 'RECHAZADA'
    db.commit()
    return {'id': solicitud_id, 'estado': 'RECHAZADA'}


@router.post('/solicitudes/{solicitud_id}/aprobar', status_code=201)
def aprobar(solicitud_id: int, datos: AprobarSolicitud,
            _: Usuario = Depends(exigir_operador), db: Session = Depends(get_db)):
    try:
        # Una sola transacción PostgreSQL protege empresa, configuración, RBAC, usuario y solicitud.
        solicitud = db.scalar(select(SolicitudAltaEmpresa).where(SolicitudAltaEmpresa.id == solicitud_id).with_for_update())
        if not solicitud:
            raise HTTPException(404, 'Solicitud no encontrada')
        if solicitud.estado != 'PENDIENTE':
            raise HTTPException(409, 'La solicitud ya fue procesada')
        if db.scalar(select(Empresa.id).where(Empresa.ruc == solicitud.ruc)):
            raise HTTPException(409, 'Empresa ya registrada')
        correo = str(datos.email_administrador).strip().lower()
        if db.scalar(select(Usuario.id).where(Usuario.email == correo)):
            raise HTTPException(409, 'Correo de administrador ya registrado')
        empresa = Empresa(razon_social=solicitud.razon_social, ruc=solicitud.ruc, activo=True)
        db.add(empresa)
        db.flush()
        db.add(ConfiguracionEmpresa(empresa_id=empresa.id))
        # Idempotente respecto del catálogo global; roles exclusivos por empresa.
        for codigo in sorted(TODOS_LOS_PERMISOS):
            db.execute(pg_insert(Permiso.__table__).values(codigo=codigo, descripcion=codigo)
                       .on_conflict_do_nothing(index_elements=['codigo']))
        permisos = {p.codigo: p.id for p in db.scalars(select(Permiso).where(Permiso.codigo.in_(TODOS_LOS_PERMISOS)))}
        if len(permisos) != len(TODOS_LOS_PERMISOS):
            raise RuntimeError('Catálogo de permisos incompleto')
        roles = {}
        for nombre, conf in ROLES.items():
            rol = Rol(empresa_id=empresa.id, nombre=nombre, descripcion=conf['descripcion'])
            db.add(rol)
            db.flush()
            roles[nombre] = rol
            for codigo in sorted(conf['permisos']):
                db.execute(roles_permisos.insert().values(rol_id=rol.id, permiso_id=permisos[codigo]))
        admin = Usuario(empresa_id=empresa.id, nombre=datos.nombre_administrador.strip(), email=correo,
                        password_hash=hash_password(datos.password_inicial), activo=True)
        db.add(admin)
        db.flush()
        db.execute(usuarios_roles.insert().values(usuario_id=admin.id, rol_id=roles['ADMIN_EMPRESA'].id,
                                                 empresa_id=empresa.id))
        solicitud.estado = 'APROBADA'
        empresa_id, usuario_id = empresa.id, admin.id
        db.commit()
        return {'empresa_id': empresa_id, 'administrador_id': usuario_id, 'estado': 'APROBADA'}
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Datos empresariales o usuario duplicados')
    except Exception:
        db.rollback()
        raise


@router.get('')
def listar_empresas(_: Usuario = Depends(exigir_operador), db: Session = Depends(get_db)):
    return [{'id': e.id, 'razon_social': e.razon_social, 'ruc': e.ruc, 'activo': e.activo}
            for e in db.scalars(select(Empresa).order_by(Empresa.id))]


@router.patch('/{empresa_id}/estado')
def cambiar_estado(empresa_id: int, activo: bool, _: Usuario = Depends(exigir_operador), db: Session = Depends(get_db)):
    empresa = db.get(Empresa, empresa_id)
    if empresa is None:
        raise HTTPException(404, 'Empresa no encontrada')
    if empresa.activo == activo:
        return {'empresa_id': empresa_id, 'activo': activo}
    empresa.activo = activo
    db.commit()
    return {'empresa_id': empresa_id, 'activo': activo}
