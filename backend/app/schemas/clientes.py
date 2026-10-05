
"""
SalesIA Enterprise
FASE 06-B.1

Esquemas de validacion para la gestion
empresarial de clientes.
"""

from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


TipoDocumento = Literal[
    "DNI",
    "RUC",
    "CE",
    "PASAPORTE",
]


class ClienteBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    nombre: str = Field(
        min_length=2,
        max_length=200,
    )

    tipo_documento: TipoDocumento | None = None

    numero_documento: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    email: str | None = Field(
        default=None,
        max_length=255,
    )

    telefono: str | None = Field(
        default=None,
        max_length=30,
    )

    direccion: str | None = Field(
        default=None,
        max_length=255,
    )

    @field_validator(
        "numero_documento",
        "email",
        "telefono",
        "direccion",
    )
    @classmethod
    def validar_campos_opcionales(cls, valor):
        if valor is not None:
            valor = valor.strip()

            if not valor:
                raise ValueError(
                    "El campo no puede contener solo espacios."
                )

        return valor

    @model_validator(mode="after")
    def validar_documento_completo(self):
        tiene_tipo = self.tipo_documento is not None
        tiene_numero = self.numero_documento is not None

        if tiene_tipo != tiene_numero:
            raise ValueError(
                "Debe proporcionar el tipo y numero "
                "de documento conjuntamente."
            )

        return self


class ClienteCreate(ClienteBase):
    """Datos necesarios para registrar un cliente."""
    pass


class ClienteUpdate(BaseModel):
    """
    Actualizacion parcial.

    Los campos omitidos no deben reemplazar
    los valores existentes en PostgreSQL.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    nombre: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    tipo_documento: TipoDocumento | None = None

    numero_documento: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )

    email: str | None = Field(
        default=None,
        max_length=255,
    )

    telefono: str | None = Field(
        default=None,
        max_length=30,
    )

    direccion: str | None = Field(
        default=None,
        max_length=255,
    )

    @field_validator(
        "nombre",
        "numero_documento",
        "email",
        "telefono",
        "direccion",
    )
    @classmethod
    def validar_texto(cls, valor):
        if valor is not None:
            valor = valor.strip()

            if not valor:
                raise ValueError(
                    "No se permiten cadenas vacias."
                )

        return valor


class ClienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int

    nombre: str

    tipo_documento: TipoDocumento | None
    numero_documento: str | None

    email: str | None
    telefono: str | None
    direccion: str | None

    activo: bool
    created_at: datetime


class ClienteListadoResponse(BaseModel):
    total: int = Field(ge=0)
    pagina: int = Field(ge=1)
    limite: int = Field(ge=1)
    clientes: list[ClienteResponse]
