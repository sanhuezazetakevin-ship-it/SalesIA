
"""
SalesIA Enterprise
FASE 07-B.1

Esquemas empresariales de categorias.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class CategoriaBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    nombre: str = Field(
        min_length=2,
        max_length=120,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=255,
    )

    @field_validator("descripcion")
    @classmethod
    def validar_descripcion(cls, valor):
        if valor is not None and not valor.strip():
            raise ValueError(
                "La descripcion no puede estar vacia."
            )
        return valor


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    nombre: str | None = Field(
        default=None,
        min_length=2,
        max_length=120,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=255,
    )

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, valor):
        if valor is None or not valor.strip():
            raise ValueError(
                "El nombre no puede estar vacio."
            )
        return valor

    @field_validator("descripcion")
    @classmethod
    def validar_descripcion(cls, valor):
        if valor is not None and not valor.strip():
            raise ValueError(
                "La descripcion no puede estar vacia."
            )
        return valor


class CategoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    nombre: str
    descripcion: str | None
    activo: bool


class CategoriaListadoResponse(BaseModel):
    total: int = Field(ge=0)
    pagina: int = Field(ge=1)
    limite: int = Field(ge=1)
    categorias: list[CategoriaResponse]
