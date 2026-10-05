
"""
SalesIA Enterprise
FASE 07-B.1

Esquemas empresariales de productos.

Los importes utilizan Decimal para evitar
errores de precision de punto flotante.
"""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


TipoItem = Literal[
    "PRODUCTO",
    "SERVICIO",
    "INSUMO",
    "MISCELANEO",
]


class ProductoBase(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    categoria_id: int | None = Field(
        default=None,
        gt=0,
    )

    sku: str = Field(
        min_length=1,
        max_length=80,
    )

    nombre: str = Field(
        min_length=2,
        max_length=200,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=500,
    )

    tipo_item: TipoItem

    precio_venta: Decimal = Field(
        ge=Decimal("0"),
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    )

    costo_referencia: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0"),
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    )

    controla_stock: bool = True

    @field_validator("sku", "nombre")
    @classmethod
    def validar_texto_obligatorio(cls, valor):
        if not valor.strip():
            raise ValueError(
                "El campo no puede estar vacio."
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


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    categoria_id: int | None = Field(
        default=None,
        gt=0,
    )

    sku: str | None = Field(
        default=None,
        min_length=1,
        max_length=80,
    )

    nombre: str | None = Field(
        default=None,
        min_length=2,
        max_length=200,
    )

    descripcion: str | None = Field(
        default=None,
        max_length=500,
    )

    tipo_item: TipoItem | None = None

    precio_venta: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    )

    costo_referencia: Decimal | None = Field(
        default=None,
        ge=Decimal("0"),
        max_digits=14,
        decimal_places=2,
        allow_inf_nan=False,
    )

    controla_stock: bool | None = None

    @field_validator("sku", "nombre")
    @classmethod
    def validar_texto_obligatorio(cls, valor):
        if valor is None or not valor.strip():
            raise ValueError(
                "El campo no puede estar vacio."
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

    @model_validator(mode="after")
    def validar_campos_no_anulables(self):
        # Pydantic distingue un campo omitido de uno enviado
        # explicitamente con null.
        obligatorios = {
            "sku",
            "nombre",
            "tipo_item",
            "precio_venta",
            "costo_referencia",
            "controla_stock",
        }

        for campo in obligatorios & self.model_fields_set:
            if getattr(self, campo) is None:
                raise ValueError(
                    f"El campo {campo} no admite null."
                )

        return self


class ProductoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    empresa_id: int
    categoria_id: int | None

    sku: str
    nombre: str
    descripcion: str | None
    tipo_item: TipoItem

    precio_venta: Decimal
    costo_referencia: Decimal

    controla_stock: bool
    activo: bool
    created_at: datetime


class ProductoListadoResponse(BaseModel):
    total: int = Field(ge=0)
    pagina: int = Field(ge=1)
    limite: int = Field(ge=1)
    productos: list[ProductoResponse]
