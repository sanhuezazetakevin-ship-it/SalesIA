"""Consulta acotada y aislada por empresa: importes confirmados."""
from datetime import date, datetime, time, timedelta, timezone
from sqlalchemy import select, func
from app.models.venta import Venta
from app.services.venta_service import _validar_operador, VentaServiceError
from app.services.semana08_calculos import resumen_semana08, tabla_probabilidades

class Semana08Error(ValueError):
    def __init__(self,mensaje,status_code=422):
        super().__init__(mensaje); self.status_code=status_code


def obtener_semana08(db, *, usuario_id, inicio:date, fin:date, media_hipotetica=None, alfa=0.05):
    if inicio>fin or (fin-inicio).days>366 or fin>date.today():
        raise Semana08Error('Periodo inválido, máximo 367 días y sin fechas futuras.')
    try:
        _, empresa=_validar_operador(db,usuario_id=usuario_id,permiso='analitica.ver')
    except VentaServiceError as exc:
        raise Semana08Error('No autorizado para Analytics.',403) from exc
    a=datetime.combine(inicio,time.min,tzinfo=timezone.utc)
    b=datetime.combine(fin+timedelta(days=1),time.min,tzinfo=timezone.utc)
    filtros=(Venta.empresa_id==empresa.id,Venta.estado=='CONFIRMADA',Venta.created_at>=a,Venta.created_at<b)
    n=db.scalar(select(func.count(Venta.id)).where(*filtros)) or 0
    if n>50000:
        raise Semana08Error('Demasiadas ventas; reduzca el periodo.')
    filas=db.execute(select(Venta.total,Venta.estado_pago).where(*filtros).order_by(Venta.id)).all()
    importes=[float(f[0]) for f in filas]
    resultados=resumen_semana08(importes,hipotesis_media=media_hipotetica,alfa=alfa)
    conteos={estado:0 for estado in ('PENDIENTE','PARCIAL','PAGADO')}
    for _,estado in filas:
        conteos[estado]=conteos.get(estado,0)+1
    return {'periodo':{'inicio':inicio.isoformat(),'fin':fin.isoformat()},'moneda':'PEN',
            'criterio':'CONFIRMADA','zona_horaria':'UTC', 'metodologia':'Estadística descriptiva y prueba t exploratoria',
            'resultados':resultados,'distribucion_estados_pago':tabla_probabilidades(conteos)}
