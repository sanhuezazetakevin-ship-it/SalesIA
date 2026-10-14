"""Consultas y ajustes de inventario con control RBAC y aislamiento empresarial."""
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.api.dependencies import get_current_active_user
from app.database.connection import get_db
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.auditoria import Auditoria
from app.services.role_service import _obtener_permisos_efectivos

router = APIRouter(prefix='/api/inventario-operativo', tags=['Inventario operativo'])

class Ajuste(BaseModel):
    producto_id: int = Field(gt=0)
    cantidad_delta: Decimal = Field(max_digits=14, decimal_places=3)
    motivo: str = Field(min_length=8, max_length=255)
    referencia: str | None = Field(default=None, max_length=100)


def exigir(db, usuario, codigo):
    permisos = _obtener_permisos_efectivos(db, usuario_id=usuario.id, empresa_id=usuario.empresa_id)
    if codigo not in permisos:
        raise HTTPException(status_code=403, detail='No tienes permiso para esta operación de inventario.')


def serializar(i, p):
    return {'inventario_id': i.id if i else None, 'producto_id': p.id, 'producto': p.nombre,
            'sku': p.sku, 'cantidad_disponible': str(i.cantidad_disponible if i else Decimal('0')),
            'controla_stock': p.controla_stock}

@router.get('')
def listar(pagina: int = Query(1, ge=1), limite: int = Query(20, ge=1, le=100),
           busqueda: str = Query('', max_length=100), usuario: Usuario = Depends(get_current_active_user),
           db: Session = Depends(get_db)):
    exigir(db, usuario, 'inventario.ver')
    consulta = select(Producto).where(Producto.empresa_id == usuario.empresa_id, Producto.activo.is_(True), Producto.controla_stock.is_(True))
    if busqueda.strip():
        consulta = consulta.where(Producto.nombre.ilike(f'%{busqueda.strip()}%') | Producto.sku.ilike(f'%{busqueda.strip()}%'))
    total = db.scalar(select(func.count()).select_from(consulta.subquery())) or 0
    productos = db.scalars(consulta.order_by(Producto.id).offset((pagina-1)*limite).limit(limite)).all()
    ids = [p.id for p in productos]
    invs = db.scalars(select(Inventario).where(Inventario.empresa_id == usuario.empresa_id, Inventario.producto_id.in_(ids))).all() if ids else []
    index = {i.producto_id:i for i in invs}
    return {'total': total, 'pagina': pagina, 'limite': limite, 'items':[serializar(index.get(p.id),p) for p in productos]}

@router.get('/movimientos')
def movimientos(pagina: int = Query(1, ge=1), limite: int = Query(20,ge=1,le=100),
                producto_id: int | None = Query(None, gt=0), usuario: Usuario = Depends(get_current_active_user),
                db: Session = Depends(get_db)):
    exigir(db, usuario, 'inventario.ver')
    q = select(MovimientoInventario).where(MovimientoInventario.empresa_id == usuario.empresa_id)
    if producto_id is not None: q=q.where(MovimientoInventario.producto_id==producto_id)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(q.order_by(MovimientoInventario.created_at.desc(),MovimientoInventario.id.desc()).offset((pagina-1)*limite).limit(limite)).all()
    return {'total':total,'pagina':pagina,'limite':limite,'items':[
        {'id':m.id,'producto_id':m.producto_id,'tipo':m.tipo_movimiento,'cantidad_delta':str(m.cantidad_delta),
         'motivo':m.motivo,'referencia':m.referencia,'fecha':m.created_at.isoformat()} for m in rows]}

@router.post('/ajustes')
def ajustar(data: Ajuste, usuario: Usuario=Depends(get_current_active_user), db: Session=Depends(get_db)):
    exigir(db,usuario,'inventario.ajustar')
    if data.cantidad_delta == 0: raise HTTPException(422, 'El ajuste debe ser distinto de cero.')
    if not data.motivo.strip() or len(data.motivo.strip()) < 8:
        raise HTTPException(422, 'El motivo debe tener al menos 8 caracteres útiles.')
    try:
        producto = db.scalar(select(Producto).where(Producto.id==data.producto_id,
            Producto.empresa_id==usuario.empresa_id, Producto.activo.is_(True), Producto.controla_stock.is_(True)))
        if not producto: raise HTTPException(404,'Producto con control de stock no encontrado.')
        # Serializar ajustes manuales por producto antes de crear o modificar el inventario.
        db.scalar(select(Producto).where(Producto.id==producto.id).with_for_update())
        inv = db.scalar(select(Inventario).where(Inventario.empresa_id==usuario.empresa_id,
            Inventario.producto_id==producto.id).with_for_update())
        if not inv:
            # La venta/recepción también puede crear inventario: bloquear producto antes de crear.
            db.scalar(select(Producto).where(Producto.id==producto.id).with_for_update())
            inv = db.scalar(select(Inventario).where(Inventario.empresa_id==usuario.empresa_id,
                Inventario.producto_id==producto.id).with_for_update())
            if not inv:
                inv=Inventario(empresa_id=usuario.empresa_id,producto_id=producto.id,cantidad_disponible=Decimal('0'))
                db.add(inv); db.flush()
        anterior = inv.cantidad_disponible
        nuevo = anterior + data.cantidad_delta
        if nuevo < 0: raise HTTPException(409, 'El ajuste dejaría el stock negativo.')
        inv.cantidad_disponible=nuevo
        movimiento=MovimientoInventario(empresa_id=usuario.empresa_id,producto_id=producto.id,
            inventario_id=inv.id,tipo_movimiento='AJUSTE',cantidad_delta=data.cantidad_delta,
            motivo=data.motivo.strip(),referencia=data.referencia)
        db.add(movimiento)
        db.add(Auditoria(empresa_id=usuario.empresa_id,usuario_id=usuario.id,accion='ACTUALIZAR',
            entidad='inventario',entidad_id=inv.id,descripcion='Ajuste manual de stock',
            datos_anteriores={'stock':str(anterior)},datos_nuevos={'stock':str(nuevo),'delta':str(data.cantidad_delta)},origen='API'))
        db.commit()
        return {'producto_id':producto.id,'stock_anterior':str(anterior),'stock_actual':str(nuevo),'delta':str(data.cantidad_delta)}
    except Exception:
        db.rollback()
        raise
