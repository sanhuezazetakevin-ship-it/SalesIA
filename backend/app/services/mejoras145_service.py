"""Consultas acotadas multiempresa para visualizaciones y alertas no persistentes."""
from datetime import date, timedelta
from sqlalchemy import select, func
from app.models.venta import Venta
from app.models.venta_detalle import VentaDetalle
from app.models.producto import Producto
from app.models.inventario import Inventario
from app.models.cliente import Cliente
from app.models.evento_auth import EventoAuth
from app.models.pedido import Pedido
from app.services.dashboard_comercial_service import obtener_dashboard_comercial, _ventana, _filtro_ventas
from app.services.venta_service import _validar_operador, VentaServiceError
from app.services.mejoras145_calculos import analizar_stock, segmento_cliente, presentacion_kpi, tarjeta_alerta, rfm_cliente


class Mejoras145Error(ValueError):
    def __init__(self, message, status_code=422):
        super().__init__(message)
        self.status_code = status_code


def _empresa(db, usuario_id, permiso='ventas.ver'):
    try:
        _, empresa = _validar_operador(db, usuario_id=usuario_id, permiso=permiso)
        return empresa.id
    except VentaServiceError as exc:
        raise Mejoras145Error('No autorizado.', 403) from exc


def _periodo(inicio, fin):
    if fin < inicio or (fin-inicio).days > 366 or fin > date.today():
        raise Mejoras145Error('Rango inválido; máximo 367 días y sin fechas futuras.')


def dashboard_visual(db, usuario_id, inicio, fin):
    _periodo(inicio, fin)
    original = obtener_dashboard_comercial(db, usuario_id=usuario_id, fecha_inicio=inicio, fecha_fin=fin, limite=10)
    k, a = original['kpis'], original['kpis_periodo_anterior']
    tarjetas = [presentacion_kpi(k['total_ventas'], a['total_ventas'], titulo='Ventas confirmadas'),
                presentacion_kpi(k['cantidad_ventas'], a['cantidad_ventas'], unidad='ventas', titulo='Operaciones')]
    return {'periodo': original['periodo'], 'moneda': original['moneda'], 'tarjetas': tarjetas,
            'graficos': [{'tipo':'barra','titulo':'Estados de pedidos',
                         'etiquetas':list(original['pedidos_por_estado']),
                         'valores':list(original['pedidos_por_estado'].values())},
                        {'tipo':'barra','titulo':'Productos destacados',
                         'etiquetas':[p['nombre'] for p in original['productos_destacados']],
                         'valores':[float(p['total_ventas']) for p in original['productos_destacados']]}],
            'explicacion': 'Solo se incluyen ventas confirmadas; estos importes no representan cobros.',
            'sin_datos': k['cantidad_ventas'] == 0}


def inventario_visual(db, usuario_id, inicio, fin, horizonte=14, limite=30):
    _periodo(inicio, fin)
    eid = _empresa(db, usuario_id)
    a,b = _ventana(inicio, fin)
    vendidos = dict(db.execute(select(VentaDetalle.producto_id,func.coalesce(func.sum(VentaDetalle.cantidad),0))
        .join(Venta, (Venta.id==VentaDetalle.venta_id)&(Venta.empresa_id==VentaDetalle.empresa_id))
        .where(Venta.empresa_id==eid,Venta.estado=='CONFIRMADA',Venta.created_at>=a,Venta.created_at<b)
        .group_by(VentaDetalle.producto_id)).all())
    productos = db.execute(select(Producto.id,Producto.nombre,Inventario.cantidad_disponible)
        .join(Inventario,(Inventario.producto_id==Producto.id)&(Inventario.empresa_id==Producto.empresa_id))
        .where(Producto.empresa_id==eid,Producto.activo.is_(True),Producto.controla_stock.is_(True))
        .order_by(Producto.id).limit(limite)).all()
    dias=(fin-inicio).days+1
    items=[]
    for pid,nombre,stock in productos:
        calculo=analizar_stock(stock,vendidos.get(pid,0),dias,horizonte)
        items.append({'producto_id':pid,'nombre':nombre,**calculo})
    return {'periodo':{'inicio':inicio,'fin':fin},'horizonte_dias':horizonte,'items':items,
            'metodo':'promedio_historico_simple','sin_datos':not items,
            'aviso':'Resultados estimativos; la ausencia de ventas no demuestra ausencia de demanda.'}


def clientes_visual(db, usuario_id, inicio, fin, limite=50):
    _periodo(inicio,fin)
    eid=_empresa(db,usuario_id)
    # Histórico real hasta la fecha de referencia, sin limitar el cálculo al periodo de la pantalla.
    _,b=_ventana(inicio,fin)
    ventas=select(Venta.cliente_id.label('cid'),func.count(Venta.id).label('compras'),
                  func.coalesce(func.sum(Venta.total),0).label('gasto'),func.max(Venta.created_at).label('ultima'))        .where(Venta.empresa_id==eid,Venta.estado=='CONFIRMADA',Venta.created_at<b)        .group_by(Venta.cliente_id).subquery()
    filas=db.execute(select(Cliente.id,Cliente.nombre,ventas.c.compras,ventas.c.gasto,ventas.c.ultima)
        .outerjoin(ventas,ventas.c.cid==Cliente.id)
        .where(Cliente.empresa_id==eid,Cliente.activo.is_(True))
        .order_by(Cliente.id).limit(limite)).all()
    items=[]; conteos={c:0 for c in ('SIN_COMPRAS','REACTIVACION','ALTO_VALOR','FRECUENTE','OCASIONAL')}
    for cid,nombre,compras,gasto,ultima in filas:
        rfm=rfm_cliente(ultima.date() if ultima else None,compras or 0,gasto or 0,fin)
        conteos[rfm['segmento']]+=1
        items.append({'cliente_id':cid,'nombre':nombre,**rfm})
    return {'periodo':{'inicio':inicio.isoformat(),'fin':fin.isoformat()},
            'metodo':'RFM histórico hasta la fecha final',
            'umbrales':{'recencia_dias':[30,60,90,180], 'frecuencia_compras':[1,2,3,5,10],
                        'importe_pen':[100,500,2000,5000]},
            'grafico':{'tipo':'barra','titulo':'Segmentación RFM de clientes',
                       'etiquetas':list(conteos),'valores':list(conteos.values())},
            'items':items,'sin_datos':not items,'limite':limite,
            'aviso':'Se presenta una muestra de clientes activos ordenada por ID; los conteos del gráfico corresponden a esa misma muestra. Los umbrales son reglas descriptivas configuradas, no un modelo entrenado.'}


def notificaciones_visual(db, usuario_id, inicio, fin):
    _periodo(inicio,fin)
    eid=_empresa(db,usuario_id)
    a,b=_ventana(inicio,fin)
    alertas=[]
    pendientes=db.scalar(select(func.count(Pedido.id)).where(Pedido.empresa_id==eid,Pedido.estado=='BORRADOR',Pedido.created_at>=a,Pedido.created_at<b)) or 0
    if pendientes:
        alertas.append(tarjeta_alerta('PEDIDOS_PENDIENTES','Pedidos pendientes',f'{pendientes} pedidos siguen en borrador.','INFORMATIVO'))
    stock=db.execute(select(Producto.id,Producto.nombre).join(Inventario,(Inventario.producto_id==Producto.id)&(Inventario.empresa_id==Producto.empresa_id))
        .where(Producto.empresa_id==eid,Producto.activo.is_(True),Producto.controla_stock.is_(True),Inventario.cantidad_disponible==0)
        .order_by(Producto.id).limit(20)).all()
    for pid,nombre in stock:
        alertas.append(tarjeta_alerta('SIN_STOCK','Producto sin stock',nombre,'ALTO',pid))
    return {'items':alertas,'total':len(alertas),'tipo':'alertas_calculadas',
            'explicacion':'Estas alertas se calculan al consultar; no están persistidas ni tienen estado leído.'}


def seguridad_visual(db, usuario_id, inicio, fin):
    _periodo(inicio,fin)
    eid=_empresa(db,usuario_id,permiso='auditoria.ver')
    a,b=_ventana(inicio,fin)
    filas=db.execute(select(EventoAuth.resultado,func.count(EventoAuth.id)).where(
        EventoAuth.empresa_id==eid,EventoAuth.created_at>=a,EventoAuth.created_at<b)
        .group_by(EventoAuth.resultado)).all()
    valores={str(x):int(n) for x,n in filas}
    return {'grafico':{'tipo':'barra','titulo':'Resultados de autenticación','etiquetas':list(valores),
                      'valores':list(valores.values())},'sin_datos':not valores,
            'explicacion':'Solo eventos asociados a su empresa; no se muestran credenciales ni detalles sensibles.'}
