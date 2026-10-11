"""FASE 13: lectura protegida del registro de auditoría."""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.services.auditoria_consulta_service import consultar_auditoria, AuditoriaConsultaError

router = APIRouter(prefix='/api/auditoria', tags=['Auditoría'])

class EntradaAuditoria(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: int
    usuario_id: int | None
    accion: str
    entidad: str
    entidad_id: int | None
    descripcion: str | None
    origen: str
    created_at: datetime

class HistorialAuditoria(BaseModel):
    total: int
    limite: int
    desplazamiento: int
    items: list[EntradaAuditoria]

@router.get('', response_model=HistorialAuditoria)
def listar_auditoria(
    limite: int = Query(25, ge=1, le=100),
    desplazamiento: int = Query(0, ge=0, le=100000),
    accion: Literal['CREAR','ACTUALIZAR','ELIMINAR','CONFIRMAR','CANCELAR','ANULAR','CONSULTAR','OTRO'] | None = None,
    entidad: str | None = Query(None, min_length=1, max_length=80, pattern=r'^[A-Za-z_][A-Za-z_0-9]*$'),
    desde: datetime | None = None,
    hasta: datetime | None = None,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if desde is not None and desde.tzinfo is None or hasta is not None and hasta.tzinfo is None:
        raise HTTPException(status_code=422, detail='Las fechas deben incluir zona horaria.')
    if desde is not None and hasta is not None and desde > hasta:
        raise HTTPException(status_code=422, detail='El intervalo de fechas no es válido.')
    try:
        return consultar_auditoria(db, usuario_id=usuario.id, limite=limite,
            desplazamiento=desplazamiento, accion=accion, entidad=entidad,
            desde=desde, hasta=hasta)
    except AuditoriaConsultaError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
