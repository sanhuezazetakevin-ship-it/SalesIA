"""Solicitudes públicas de alta empresarial. Nunca aprovisiona cuentas ni concede roles."""
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, EmailStr, field_validator
from sqlalchemy import DateTime, Integer, String, select, func, Column, UniqueConstraint
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.base import Base
from app.database.connection import get_db

router = APIRouter(prefix='/api/publico', tags=['Alta empresarial'])

class SolicitudAltaEmpresa(Base):
    __tablename__ = 'solicitudes_alta_empresas'
    id = Column(Integer, primary_key=True)
    razon_social = Column(String(200), nullable=False)
    ruc = Column(String(11), nullable=False, unique=True)
    nombre_contacto = Column(String(120), nullable=False)
    email_contacto = Column(String(255), nullable=False)
    telefono = Column(String(25), nullable=True)
    estado = Column(String(20), nullable=False, server_default='PENDIENTE')
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

class SolicitudAltaIn(BaseModel):
    razon_social: str = Field(min_length=3, max_length=200)
    ruc: str = Field(pattern=r'^\d{11}$')
    nombre_contacto: str = Field(min_length=2, max_length=120)
    email_contacto: EmailStr
    telefono: str | None = Field(default=None, max_length=25)
    sitio_web: str = Field(default='', max_length=0, exclude=True)  # honeypot, debe quedar vacío

    @field_validator('razon_social','nombre_contacto')
    @classmethod
    def no_blancos(cls, value: str) -> str:
        value = value.strip()
        if not value: raise ValueError('Campo obligatorio')
        return value

@router.post('/solicitudes-empresa', status_code=status.HTTP_202_ACCEPTED)
def solicitar_alta(datos: SolicitudAltaIn, db: Session = Depends(get_db)):
    if datos.sitio_web:
        return {'mensaje': 'Solicitud recibida. El equipo revisará los datos antes de habilitar el acceso.'}
    from app.models.empresa import Empresa
    # Respuesta genérica también cuando el RUC existe: evita enumerar empresas.
    mensaje = {'mensaje': 'Solicitud recibida. El equipo revisará los datos antes de habilitar el acceso.'}
    if db.scalar(select(Empresa.id).where(Empresa.ruc == datos.ruc)):
        return mensaje
    solicitud = db.scalar(select(SolicitudAltaEmpresa).where(SolicitudAltaEmpresa.ruc == datos.ruc))
    if solicitud:
        return mensaje
    db.add(SolicitudAltaEmpresa(razon_social=datos.razon_social,ruc=datos.ruc,
      nombre_contacto=datos.nombre_contacto,email_contacto=str(datos.email_contacto).lower(),telefono=datos.telefono))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return mensaje
