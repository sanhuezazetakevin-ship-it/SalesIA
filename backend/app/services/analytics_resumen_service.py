"""MVP-01-B: métricas descriptivas sobre ventas CONFIRMADAS, sin escritura."""
from datetime import datetime, date, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from sqlalchemy import select, func
from app.models.venta import Venta
from app.services.venta_service import _validar_operador, VentaServiceError

CENTS = Decimal('0.01')
MAX_VENTAS = 50000

class AnalyticsResumenError(Exception):
    pass

def calcular_metricas(importes):
    """Decimal end-to-end; no confundir ventas con pagos/cobros."""
    valores = [Decimal(str(v)) for v in importes]
    if any(not v.is_finite() or v < 0 for v in valores):
        raise ValueError('Importes de venta inválidos')
    if not valores:
        return {'cantidad_ventas': 0, 'total_ventas': '0.00', 'ticket_promedio': None, 'mediana_ventas': None}
    total = sum(valores, Decimal('0'))
    promedio = (total / len(valores)).quantize(CENTS, rounding=ROUND_HALF_UP)
    central = Decimal(median(valores)).quantize(CENTS, rounding=ROUND_HALF_UP)
    return {'cantidad_ventas': len(valores), 'total_ventas': str(total.quantize(CENTS)),
            'ticket_promedio': str(promedio), 'mediana_ventas': str(central)}

def obtener_resumen(db, *, usuario_id: int, fecha_inicio: date, fecha_fin: date):
    if fecha_fin < fecha_inicio:
        raise AnalyticsResumenError('La fecha final debe ser igual o posterior a la inicial.')
    if (fecha_fin - fecha_inicio).days > 366:
        raise AnalyticsResumenError('El período máximo por consulta es de 367 días.')
    try:
        _, empresa = _validar_operador(db, usuario_id=usuario_id, permiso='ventas.ver')
    except VentaServiceError as exc:
        raise AnalyticsResumenError('No autorizado para consultar Analytics.') from exc
    inicio = datetime.combine(fecha_inicio, time.min, tzinfo=timezone.utc)
    fin_exclusivo = datetime.combine(fecha_fin + timedelta(days=1), time.min, tzinfo=timezone.utc)
    filtros = (Venta.empresa_id == empresa.id, Venta.estado == 'CONFIRMADA',
               Venta.created_at >= inicio, Venta.created_at < fin_exclusivo)
    cantidad = db.scalar(select(func.count(Venta.id)).where(*filtros)) or 0
    if cantidad > MAX_VENTAS:
        raise AnalyticsResumenError('El período excede el límite de 50000 ventas; reduzca el rango.')
    importes = db.scalars(select(Venta.total).where(*filtros).order_by(Venta.id)).all()
    return {'periodo': {'fecha_inicio': fecha_inicio.isoformat(), 'fecha_fin': fecha_fin.isoformat()},
            'moneda': 'PEN', 'criterio_estado': 'CONFIRMADA', 'zona_horaria': 'UTC',
            **calcular_metricas(importes)}
