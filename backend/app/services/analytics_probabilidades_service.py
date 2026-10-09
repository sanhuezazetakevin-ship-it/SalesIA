"""MVP-01-E.2. Consulta solo lectura de ventas confirmadas por empresa y período."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.models.venta import Venta
from app.services.analytics_resumen_service import AnalyticsResumenError, MAX_VENTAS
from app.services.analytics_probabilidades_calculos import calcular_probabilidades
from app.services.venta_service import VentaServiceError, _validar_operador


def obtener_probabilidades(db, *, usuario_id: int, fecha_inicio: date,
                           fecha_fin: date, umbral_importe: Decimal = Decimal('100.00')):
    if fecha_fin < fecha_inicio or (fecha_fin - fecha_inicio).days > 366:
        raise AnalyticsResumenError('Periodo inválido o mayor al máximo permitido de 367 días.')
    if not umbral_importe.is_finite() or umbral_importe < 0:
        raise AnalyticsResumenError('El umbral debe ser finito y no negativo.')
    try:
        _, empresa = _validar_operador(db, usuario_id=usuario_id, permiso='ventas.ver')
    except VentaServiceError as exc:
        raise AnalyticsResumenError('No autorizado para consultar Analytics.') from exc

    inicio = datetime.combine(fecha_inicio, time.min, tzinfo=timezone.utc)
    fin_exclusivo = datetime.combine(fecha_fin + timedelta(days=1), time.min, tzinfo=timezone.utc)
    filtros = (
        Venta.empresa_id == empresa.id,
        Venta.estado == 'CONFIRMADA',
        Venta.created_at >= inicio,
        Venta.created_at < fin_exclusivo,
    )
    # Solo se extraen MAX_VENTAS+1 filas. No se efectúa una consulta de conteo
    # independiente que pueda diferir del conjunto utilizado para el cálculo.
    ventas = db.execute(
        select(Venta.total, Venta.estado_pago)
        .where(*filtros).order_by(Venta.id).limit(MAX_VENTAS + 1)
    ).all()
    if len(ventas) > MAX_VENTAS:
        raise AnalyticsResumenError('El periodo excede el límite de 50000 ventas.')
    try:
        resultado = calcular_probabilidades(ventas, umbral_importe=umbral_importe)
    except ValueError as exc:
        raise AnalyticsResumenError('Los datos de ventas contienen valores inválidos.') from exc
    return {
        'periodo': {'fecha_inicio': fecha_inicio.isoformat(), 'fecha_fin': fecha_fin.isoformat()},
        'criterio_estado': 'CONFIRMADA',
        'zona_horaria': 'UTC',
        'moneda': 'PEN',
        **resultado,
    }
