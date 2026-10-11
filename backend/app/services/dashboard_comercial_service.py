"""FASE 10: dashboard comercial de solo lectura, acotado por tenant y RBAC.

Ventas: únicamente CONFIRMADA (no confundir con pagos recibidos).
Fechas: created_at en UTC, límites inclusivos por fecha de calendario.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, func
from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle
from app.models.pedido import Pedido
from app.models.producto import Producto
from app.models.cliente import Cliente
from app.services.venta_service import _validar_operador, VentaServiceError
from app.services.analytics_resumen_service import AnalyticsResumenError, MAX_VENTAS

CENT = Decimal('0.01')


def _money(value):
    return str(Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP))


def _rate(actual, anterior):
    """Porcentaje de cambio; None si la base anterior es cero."""
    previo = Decimal(str(anterior))
    if previo == 0:
        return None
    return str(((Decimal(str(actual)) - previo) * 100 / previo).quantize(CENT, rounding=ROUND_HALF_UP))


def _ventana(inicio, fin):
    return (datetime.combine(inicio, time.min, tzinfo=timezone.utc),
            datetime.combine(fin + timedelta(days=1), time.min, tzinfo=timezone.utc))


def _filtro_ventas(empresa_id, inicio, fin):
    a, b = _ventana(inicio, fin)
    return (Venta.empresa_id == empresa_id, Venta.estado == 'CONFIRMADA',
            Venta.created_at >= a, Venta.created_at < b)


def _agregado_ventas(db, empresa_id, inicio, fin):
    filtros = _filtro_ventas(empresa_id, inicio, fin)
    cantidad, total = db.execute(select(func.count(Venta.id), func.coalesce(func.sum(Venta.total), 0)).where(*filtros)).one()
    cantidad = int(cantidad)
    if cantidad > MAX_VENTAS:
        raise AnalyticsResumenError('El período excede el límite de 50000 ventas; reduzca el rango.')
    total = Decimal(str(total))
    return {'cantidad_ventas': cantidad, 'total_ventas': _money(total),
            'ticket_promedio': _money(total / cantidad) if cantidad else None}


def _agregados_periodos(db, empresa_id, inicio_actual, fin_actual, inicio_previo, fin_previo):
    """KPIs de dos ventanas consecutivas mediante una sola consulta SQL.

    No reutiliza datos entre empresas y mantiene el límite MAX_VENTAS
    independientemente para cada período. COUNT FILTER es compatible con
    PostgreSQL y evita recuperar filas individuales en Python.
    """
    actual_desde, actual_hasta = _ventana(inicio_actual, fin_actual)
    previo_desde, previo_hasta = _ventana(inicio_previo, fin_previo)
    condicion_actual = (Venta.created_at >= actual_desde) & (Venta.created_at < actual_hasta)
    condicion_previa = (Venta.created_at >= previo_desde) & (Venta.created_at < previo_hasta)
    consulta = select(
        func.count(Venta.id).filter(condicion_actual),
        func.coalesce(func.sum(Venta.total).filter(condicion_actual), 0),
        func.count(Venta.id).filter(condicion_previa),
        func.coalesce(func.sum(Venta.total).filter(condicion_previa), 0),
    ).where(
        Venta.empresa_id == empresa_id,
        Venta.estado == 'CONFIRMADA',
        Venta.created_at >= previo_desde,
        Venta.created_at < actual_hasta,
    )
    n_actual, total_actual, n_previo, total_previo = db.execute(consulta).one()

    def empaquetar(cantidad, total):
        cantidad = int(cantidad)
        if cantidad > MAX_VENTAS:
            raise AnalyticsResumenError('El período excede el límite de 50000 ventas; reduzca el rango.')
        total = Decimal(str(total))
        return {'cantidad_ventas': cantidad, 'total_ventas': _money(total),
                'ticket_promedio': _money(total / cantidad) if cantidad else None}

    return empaquetar(n_actual, total_actual), empaquetar(n_previo, total_previo)


def obtener_dashboard_comercial(db, *, usuario_id: int, fecha_inicio: date, fecha_fin: date, limite: int = 10):
    if fecha_fin < fecha_inicio or (fecha_fin - fecha_inicio).days > 366:
        raise AnalyticsResumenError('Período inválido o mayor a 367 días.')
    if not 1 <= limite <= 20:
        raise AnalyticsResumenError('El límite debe estar entre 1 y 20.')
    try:
        _, empresa = _validar_operador(db, usuario_id=usuario_id, permiso='ventas.ver')
    except VentaServiceError as exc:
        raise AnalyticsResumenError('No autorizado para consultar Dashboard.') from exc
    eid = empresa.id
    dias = (fecha_fin - fecha_inicio).days + 1
    fin_previo = fecha_inicio - timedelta(days=1)
    inicio_previo = fin_previo - timedelta(days=dias-1)
    kpis, anterior = _agregados_periodos(db, eid, fecha_inicio, fecha_fin, inicio_previo, fin_previo)
    inicio_utc, fin_utc = _ventana(fecha_inicio, fecha_fin)
    estados = {estado: 0 for estado in ('BORRADOR', 'CONFIRMADO', 'COMPLETADO', 'CANCELADO')}
    for estado, n in db.execute(select(Pedido.estado, func.count(Pedido.id)).where(
        Pedido.empresa_id == eid, Pedido.created_at >= inicio_utc, Pedido.created_at < fin_utc
    ).group_by(Pedido.estado)).all():
        estados[estado] = int(n)

    # Joins por empresa_id evitan contaminación cruzada incluso con IDs malformados.
    productos = []
    consulta_productos = (select(
        Producto.id, Producto.nombre, func.sum(VentaDetalle.cantidad).label('unidades'),
        func.sum(VentaDetalle.total).label('importe'))
        .join(VentaDetalle, (VentaDetalle.producto_id == Producto.id) & (VentaDetalle.empresa_id == Producto.empresa_id))
        .join(Venta, (Venta.id == VentaDetalle.venta_id) & (Venta.empresa_id == VentaDetalle.empresa_id))
        .where(*_filtro_ventas(eid, fecha_inicio, fecha_fin))
        .group_by(Producto.id, Producto.nombre)
        .order_by(func.sum(VentaDetalle.total).desc(), Producto.id.asc()).limit(limite))
    for pid, nombre, unidades, importe in db.execute(consulta_productos):
        productos.append({'producto_id': pid, 'nombre': nombre, 'unidades': str(unidades), 'total_ventas': _money(importe)})

    clientes = []
    consulta_clientes = (select(Cliente.id, Cliente.nombre, func.count(Venta.id), func.sum(Venta.total))
        .join(Venta, (Venta.cliente_id == Cliente.id) & (Venta.empresa_id == Cliente.empresa_id))
        .where(*_filtro_ventas(eid, fecha_inicio, fecha_fin))
        .group_by(Cliente.id, Cliente.nombre)
        .order_by(func.sum(Venta.total).desc(), Cliente.id.asc()).limit(limite))
    for cid, nombre, n, total in db.execute(consulta_clientes):
        clientes.append({'cliente_id': cid, 'nombre': nombre, 'cantidad_ventas': int(n), 'total_ventas': _money(total)})

    vendedores = []
    consulta_vendedores = (select(Venta.usuario_id, func.count(Venta.id), func.sum(Venta.total))
        .where(*_filtro_ventas(eid, fecha_inicio, fecha_fin))
        .group_by(Venta.usuario_id)
        .order_by(func.sum(Venta.total).desc(), Venta.usuario_id.asc()).limit(limite))
    for uid, n, total in db.execute(consulta_vendedores):
        vendedores.append({'usuario_id': uid, 'cantidad_ventas': int(n), 'total_ventas': _money(total)})

    return {'periodo': {'fecha_inicio': fecha_inicio, 'fecha_fin': fecha_fin},
            'periodo_anterior': {'fecha_inicio': inicio_previo, 'fecha_fin': fin_previo},
            'moneda': 'PEN', 'zona_horaria': 'UTC', 'criterio_estado': 'CONFIRMADA',
            'kpis': kpis, 'kpis_periodo_anterior': anterior,
            'variacion_porcentual_ventas': _rate(kpis['total_ventas'], anterior['total_ventas']),
            'pedidos_por_estado': estados, 'productos_destacados': productos,
            'clientes_destacados': clientes, 'vendedores_destacados': vendedores}
