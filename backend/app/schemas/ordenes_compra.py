"""Contratos HTTP para órdenes de compra. FASE 09-E.2."""
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field

class DetalleCompraCrear(BaseModel):
    model_config = ConfigDict(extra='forbid')
    producto_id: int = Field(gt=0)
    cantidad: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    precio_unitario: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    impuesto: Decimal = Field(default=Decimal('0.00'), ge=0, max_digits=14, decimal_places=2)

class OrdenCompraCrear(BaseModel):
    model_config = ConfigDict(extra='forbid')
    proveedor_id: int = Field(gt=0)
    detalles: list[DetalleCompraCrear] = Field(min_length=1, max_length=200)
    codigo: str | None = Field(default=None, min_length=1, max_length=50)
    moneda: str = Field(default='PEN', min_length=3, max_length=3)

class DetalleCompraRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    producto_id: int
    cantidad_solicitada: Decimal
    precio_unitario: Decimal
    impuesto: Decimal
    subtotal: Decimal
    total: Decimal
    controla_stock_snapshot: bool

class OrdenCompraRespuesta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    empresa_id: int
    proveedor_id: int
    usuario_id: int
    codigo: str
    estado: str
    estado_pago: str
    moneda: str
    subtotal: Decimal
    impuesto_total: Decimal
    total: Decimal
    created_at: datetime
    confirmed_at: datetime | None
    detalles: list[DetalleCompraRespuesta]

class OrdenCompraPagina(BaseModel):
    items: list[OrdenCompraRespuesta]
    total: int
    pagina: int
    limite: int
