"""Series de ventas read-only. Aislamiento tenant + RBAC antes de consultar."""
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select, func

from app.models.venta import Venta
from app.services.venta_service import _validar_operador, VentaServiceError
from app.services.analytics_resumen_service import AnalyticsResumenError, MAX_VENTAS


def _mes_siguiente(fecha: date) -> date:
    return date(fecha.year + (fecha.month == 12), (fecha.month % 12) + 1, 1)


def calcular_serie(registros, *, fecha_inicio: date, fecha_fin: date, agrupacion='dia'):
    """Transforma (fecha UTC, Decimal) en puntos ordenados; incluye períodos sin ventas."""
    if agrupacion not in ('dia', 'mes'):
        raise ValueError('Agrupación inválida.')
    acumulado = defaultdict(lambda: [0, Decimal('0.00')])
    for instante, importe in registros:
        if instante.tzinfo is None:
            # PostgreSQL timestamptz es aware; evitar asumir TZ local silenciosamente.
            raise ValueError('Se requieren fechas con zona horaria.')
        fecha = instante.astimezone(timezone.utc).date()
        if not fecha_inicio <= fecha <= fecha_fin:
            continue
        clave = fecha if agrupacion == 'dia' else fecha.replace(day=1)
        valor = Decimal(str(importe))
        if not valor.is_finite() or valor < 0:
            raise ValueError('Importe inválido.')
        acumulado[clave][0] += 1
        acumulado[clave][1] += valor
    actual = fecha_inicio if agrupacion == 'dia' else fecha_inicio.replace(day=1)
    puntos = []
    while actual <= fecha_fin:
        cantidad, total = acumulado[actual]
        puntos.append({'fecha': actual.isoformat(), 'cantidad_ventas': cantidad,
                       'total_ventas': str(total.quantize(Decimal('0.01')))})
        actual = actual + timedelta(days=1) if agrupacion == 'dia' else _mes_siguiente(actual)
    return puntos


def obtener_serie_ventas(db, *, usuario_id: int, fecha_inicio: date, fecha_fin: date, agrupacion='dia'):
    if fecha_fin < fecha_inicio or (fecha_fin - fecha_inicio).days > 366:
        raise AnalyticsResumenError('Periodo inválido o mayor al máximo permitido de 367 días.')
    if agrupacion not in ('dia', 'mes'):
        raise AnalyticsResumenError('Agrupación no admitida.')
    try:
        _, empresa = _validar_operador(db, usuario_id=usuario_id, permiso='ventas.ver')
    except VentaServiceError as exc:
        raise AnalyticsResumenError('No autorizado para consultar Analytics.') from exc
    inicio = datetime.combine(fecha_inicio, time.min, tzinfo=timezone.utc)
    fin = datetime.combine(fecha_fin + timedelta(days=1), time.min, tzinfo=timezone.utc)
    filtros = (Venta.empresa_id == empresa.id, Venta.estado == 'CONFIRMADA',
               Venta.created_at >= inicio, Venta.created_at < fin)
    # PostgreSQL agrupa antes de enviar resultados: máximo 367 días o 13 meses,
    # en lugar de transferir hasta 50 000 filas a Python. Zona horaria explícita.
    fecha_utc = func.timezone('UTC', Venta.created_at)
    periodo = func.date_trunc(agrupacion == 'dia' and 'day' or 'month', fecha_utc).label('periodo')
    consulta = (select(periodo, func.count(Venta.id), func.coalesce(func.sum(Venta.total), 0))
                .where(*filtros).group_by(periodo).order_by(periodo))
    filas = db.execute(consulta).all()
    cantidad_total = sum(int(fila[1]) for fila in filas)
    if cantidad_total > MAX_VENTAS:
        raise AnalyticsResumenError('El periodo excede el límite de 50000 ventas.')
    # Un solo recorrido para completar los períodos vacíos, sin perder centavos.
    agregados = {}
    for instante, cantidad, total in filas:
        if isinstance(instante, datetime):
            fecha = instante.date()
        else:
            fecha = instante
        agregados[fecha] = (int(cantidad), Decimal(str(total)))
    actual = fecha_inicio if agrupacion == 'dia' else fecha_inicio.replace(day=1)
    puntos = []
    while actual <= fecha_fin:
        n, total = agregados.get(actual, (0, Decimal('0.00')))
        puntos.append({'fecha': actual.isoformat(), 'cantidad_ventas': n,
                       'total_ventas': str(total.quantize(Decimal('0.01')))})
        actual = actual + timedelta(days=1) if agrupacion == 'dia' else _mes_siguiente(actual)
    return {'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin, 'agrupacion': agrupacion,
            'criterio_estado': 'CONFIRMADA', 'zona_horaria': 'UTC', 'moneda': 'PEN',
            'puntos': puntos}
