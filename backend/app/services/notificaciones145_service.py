"""Centro de notificaciones persistentes. Generación manual, idempotente y tenant-scoped."""
from datetime import date,datetime,timezone
from sqlalchemy import select,func,update
from sqlalchemy.dialects.postgresql import insert
from app.models.notificacion_empresarial import NotificacionEmpresarial as Notificacion
from app.services.mejoras145_service import _empresa,notificaciones_visual


def _serializar(n):
    return {'id':n.id,'codigo':n.codigo,'titulo':n.titulo,'descripcion':n.descripcion,
            'nivel':n.nivel,'leida':n.leida,'created_at':n.created_at.isoformat(),
            'leida_at':n.leida_at.isoformat() if n.leida_at else None}


def sincronizar(db,usuario_id,inicio:date,fin:date):
    eid=_empresa(db,usuario_id,permiso='ventas.ver')
    alertas=notificaciones_visual(db,usuario_id,inicio,fin)['items']
    nuevas=0
    # INSERT ON CONFLICT evita duplicados incluso ante dos peticiones simultáneas.
    for a in alertas:
        clave=f"{a['codigo']}:{a.get('referencia') or 0}"
        stmt=insert(Notificacion).values(empresa_id=eid,clave=clave,codigo=a['codigo'],
             titulo=a['titulo'],descripcion=a['descripcion'],nivel=a['nivel'])
        stmt=stmt.on_conflict_do_nothing(index_elements=['empresa_id','clave'])
        result=db.execute(stmt)
        nuevas+=max(result.rowcount or 0,0)
    db.commit()
    return {'nuevas':nuevas,'detectadas':len(alertas),
            'explicacion':'Se guardaron únicamente alertas nuevas. La sincronización no borra ni reabre alertas leídas.'}


def listar(db,usuario_id,solo_no_leidas=False,limite=50):
    eid=_empresa(db,usuario_id,permiso='ventas.ver')
    filtros=[Notificacion.empresa_id==eid]
    if solo_no_leidas: filtros.append(Notificacion.leida.is_(False))
    items=db.scalars(select(Notificacion).where(*filtros)
       .order_by(Notificacion.created_at.desc(),Notificacion.id.desc()).limit(limite)).all()
    return {'items':[_serializar(n) for n in items],'total_mostrado':len(items),
            'sin_datos':not items,'limite':limite}


def marcar_leida(db,usuario_id,notificacion_id):
    eid=_empresa(db,usuario_id,permiso='ventas.ver')
    n=db.scalar(select(Notificacion).where(Notificacion.empresa_id==eid,Notificacion.id==notificacion_id))
    if n is None: return None
    if not n.leida:
        n.leida=True; n.leida_at=datetime.now(timezone.utc); db.commit(); db.refresh(n)
    return _serializar(n)
