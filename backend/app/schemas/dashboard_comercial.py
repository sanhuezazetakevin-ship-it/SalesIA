"""Contratos para FASE 10; los importes se transmiten como strings decimales."""
from datetime import date
from typing import Literal
from pydantic import BaseModel, Field

class Periodo(BaseModel):
    fecha_inicio: date
    fecha_fin: date

class KPIs(BaseModel):
    cantidad_ventas: int = Field(ge=0)
    total_ventas: str
    ticket_promedio: str | None

class ProductoTop(BaseModel):
    producto_id: int
    nombre: str
    unidades: str
    total_ventas: str

class ClienteTop(BaseModel):
    cliente_id: int
    nombre: str
    cantidad_ventas: int
    total_ventas: str

class VendedorTop(BaseModel):
    usuario_id: int
    cantidad_ventas: int
    total_ventas: str

class DashboardComercialResponse(BaseModel):
    periodo: Periodo
    periodo_anterior: Periodo
    moneda: Literal['PEN'] = 'PEN'
    zona_horaria: Literal['UTC'] = 'UTC'
    criterio_estado: Literal['CONFIRMADA'] = 'CONFIRMADA'
    kpis: KPIs
    kpis_periodo_anterior: KPIs
    variacion_porcentual_ventas: str | None
    pedidos_por_estado: dict[str, int]
    productos_destacados: list[ProductoTop]
    clientes_destacados: list[ClienteTop]
    vendedores_destacados: list[VendedorTop]
