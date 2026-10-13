"""Configuracion tributaria por empresa, restringida al rol ADMIN_EMPRESA."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.models.empresa import Empresa
from app.models.rol import Rol
from app.models.asociaciones import usuarios_roles
from app.models.impuesto import Impuesto
from app.models.auditoria import Auditoria

router = APIRouter(prefix="/api/configuracion/tributaria", tags=["Configuracion empresarial"])

class ImpuestoActualizacion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tasa: Decimal = Field(ge=Decimal("0"), le=Decimal("100"), decimal_places=4)


def _autorizar(db: Session, usuario: Usuario):
    empresa = db.scalar(select(Empresa).where(Empresa.id == usuario.empresa_id, Empresa.activo.is_(True)))
    if not empresa or not usuario.activo:
        raise HTTPException(403, "Empresa o usuario inactivo.")
    es_admin = db.scalar(
        select(Rol.id).join(usuarios_roles, (usuarios_roles.c.rol_id == Rol.id) & (usuarios_roles.c.empresa_id == Rol.empresa_id))
        .where(Rol.empresa_id == empresa.id, Rol.nombre == "ADMIN_EMPRESA", usuarios_roles.c.usuario_id == usuario.id).limit(1)
    )
    if es_admin is None:
        raise HTTPException(403, "Esta configuracion requiere el rol ADMIN_EMPRESA.")
    return empresa


def _dto(i):
    return {"id": i.id, "codigo": i.codigo, "nombre": i.nombre, "tasa": str(i.tasa), "activo": i.activo, "incluido_en_precio": i.incluido_en_precio}

@router.get("/igv")
def consultar_igv(usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    empresa = _autorizar(db, usuario)
    impuestos = db.scalars(select(Impuesto).where(Impuesto.empresa_id == empresa.id, Impuesto.activo.is_(True), Impuesto.incluido_en_precio.is_(True)).order_by(Impuesto.id)).all()
    if len(impuestos) > 1:
        raise HTTPException(409, "Existen multiples impuestos activos incluidos en precio: requiere revision administrativa.")
    return _dto(impuestos[0]) if impuestos else None

@router.put("/igv")
def cambiar_igv(datos: ImpuestoActualizacion, usuario: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    empresa = _autorizar(db, usuario)
    try:
        impuestos = db.scalars(select(Impuesto).where(Impuesto.empresa_id == empresa.id, Impuesto.activo.is_(True), Impuesto.incluido_en_precio.is_(True)).with_for_update()).all()
        if len(impuestos) > 1:
            raise HTTPException(409, "Existen multiples impuestos activos; no se puede actualizar automaticamente.")
        impuesto = impuestos[0] if impuestos else db.scalar(select(Impuesto).where(Impuesto.empresa_id == empresa.id, Impuesto.codigo == "IGV").with_for_update())
        if impuesto is None:
            impuesto = Impuesto(empresa_id=empresa.id, codigo="IGV", nombre="Impuesto General a las Ventas", tasa=datos.tasa, activo=True, incluido_en_precio=True)
            db.add(impuesto)
            previo = None
        else:
            previo = {"tasa":str(impuesto.tasa), "activo":impuesto.activo, "incluido_en_precio":impuesto.incluido_en_precio}
            impuesto.tasa = datos.tasa
            impuesto.activo = True
            impuesto.incluido_en_precio = True
        db.flush()
        db.add(Auditoria(empresa_id=empresa.id, usuario_id=usuario.id, accion="ACTUALIZAR", entidad="impuestos", entidad_id=impuesto.id, descripcion="Cambio de configuracion tributaria empresarial.", datos_anteriores=previo, datos_nuevos={"tasa":str(impuesto.tasa),"incluido_en_precio":True,"activo":True}, origen="SISTEMA"))
        db.commit()
        db.refresh(impuesto)
        return _dto(impuesto)
    except Exception:
        db.rollback()
        raise
