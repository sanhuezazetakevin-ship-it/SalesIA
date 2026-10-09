"""Esquemas HTTP de proveedores — SalesIA Enterprise FASE 09-E.1."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ProveedorCrear(BaseModel):
    model_config = ConfigDict(extra='forbid')
    razon_social: str = Field(min_length=1, max_length=200)
    tipo_documento: str | None = Field(default=None, max_length=20)
    numero_documento: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=254)
    telefono: str | None = Field(default=None, max_length=40)


class ProveedorActualizar(BaseModel):
    model_config = ConfigDict(extra='forbid')
    razon_social: str | None = Field(default=None, min_length=1, max_length=200)
    tipo_documento: str | None = Field(default=None, max_length=20)
    numero_documento: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=254)
    telefono: str | None = Field(default=None, max_length=40)


class ProveedorRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    razon_social: str
    tipo_documento: str | None
    numero_documento: str | None
    email: str | None
    telefono: str | None
    activo: bool
    created_at: datetime


class ProveedorPagina(BaseModel):
    items: list[ProveedorRespuesta]
    total: int
    pagina: int
    limite: int
