"""Distribuciones descriptivas: lecturas aisladas por empresa, sin escrituras."""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, func
from app.models.venta import Venta
from app.services.venta_service import _validar_operador, VentaServiceError
from app.services.analytics_resumen_service import AnalyticsResumenError, MAX_VENTAS


def frecuencias_categoricas(valores, *, categorias=None):
    """Conteos ordenados con proporciones calculadas sobre la población total."""
    conteos = {v: 0 for v in (categorias or [])}
    for v in valores:
        if v not in conteos:
            conteos[v] = 0
        conteos[v] += 1
    n = len(valores)
    return [{'categoria': str(k), 'frecuencia_absoluta': v,
             'frecuencia_relativa': str((Decimal(v)/Decimal(n)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)) if n else '0.0000'}
            for k, v in conteos.items()]


def frecuencias_intervalos(importes, *, intervalos=5):
    """Intervalos [desde, hasta) excepto el último, que incluye hasta."""
    if not 1 <= intervalos <= 20:
        raise ValueError('El número de intervalos debe estar entre 1 y 20.')
    valores = [Decimal(str(x)) for x in importes]
    if any(not x.is_finite() or x < 0 for x in valores):
        raise ValueError('Importes inválidos.')
    if not valores:
        return []
    menor, mayor = min(valores), max(valores)
    if menor == mayor:
        return [{'desde': str(menor), 'hasta': str(mayor), 'frecuencia_absoluta': len(valores), 'frecuencia_relativa': '1.0000'}]
    ancho = (mayor-menor)/Decimal(intervalos)
    conteos = [0]*intervalos
    for v in valores:
        indice = min(int((v-menor)/ancho),intervalos-1)
        conteos[indice] += 1
    total = Decimal(len(valores))
    return [{'desde': str(menor+ancho*i), 'hasta': str(menor+ancho*(i+1)),
             'frecuencia_absoluta': conteos[i],
             'frecuencia_relativa': str((Decimal(conteos[i])/total).quantize(Decimal('0.0001'),rounding=ROUND_HALF_UP))}
            for i in range(intervalos)]


def obtener_distribuciones(db, *, usuario_id:int, fecha_inicio:date, fecha_fin:date,
                          variable:str='importe_venta', intervalos:int=5):
    if fecha_fin < fecha_inicio or (fecha_fin-fecha_inicio).days > 366:
        raise AnalyticsResumenError('Periodo inválido o mayor al máximo permitido de 367 días.')
    if variable not in ('importe_venta','estado_pago'):
        raise AnalyticsResumenError('Variable estadística no admitida.')
    if not 1 <= intervalos <= 20:
        raise AnalyticsResumenError('Los intervalos deben estar entre 1 y 20.')
    try:
        _,empresa = _validar_operador(db, usuario_id=usuario_id, permiso='ventas.ver')
    except VentaServiceError as exc:
        raise AnalyticsResumenError('No autorizado para consultar Analytics.') from exc
    inicio=datetime.combine(fecha_inicio,time.min,tzinfo=timezone.utc)
    fin=datetime.combine(fecha_fin+timedelta(days=1),time.min,tzinfo=timezone.utc)
    filtros=(Venta.empresa_id==empresa.id,Venta.estado=='CONFIRMADA',Venta.created_at>=inicio,Venta.created_at<fin)
    cantidad=db.scalar(select(func.count(Venta.id)).where(*filtros)) or 0
    if cantidad > MAX_VENTAS:
        raise AnalyticsResumenError('El periodo excede el límite de 50000 ventas.')
    campo=Venta.total if variable=='importe_venta' else Venta.estado_pago
    valores=db.scalars(select(campo).where(*filtros).order_by(Venta.id)).all()
    if variable=='importe_venta':
        detalle=frecuencias_intervalos(valores,intervalos=intervalos)
        tipo='cuantitativa_continua'
    else:
        detalle=frecuencias_categoricas(valores,categorias=['PENDIENTE','PARCIAL','PAGADO'])
        tipo='cualitativa_nominal'
    return {'periodo':{'fecha_inicio':fecha_inicio.isoformat(),'fecha_fin':fecha_fin.isoformat()},
            'variable':variable,'tipo_variable':tipo,'criterio_estado':'CONFIRMADA',
            'zona_horaria':'UTC','total_observaciones':len(valores),'distribucion':detalle}
