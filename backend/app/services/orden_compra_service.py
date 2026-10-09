"""SalesIA 09-D.2 — Órdenes de compra (sin movimientos de inventario)."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from app.models.empresa import Empresa
from app.models.usuario import Usuario
from app.models.proveedor import Proveedor
from app.models.producto import Producto
from app.models.orden_compra import OrdenCompra
from app.models.orden_compra_detalle import OrdenCompraDetalle
from app.models.rol import Rol
from app.models.permiso import Permiso
from app.models.asociaciones import usuarios_roles, roles_permisos
from app.models.auditoria import Auditoria

class OrdenCompraServiceError(Exception):
    pass

PERMISO_VER = 'compras.ver'
PERMISO_CREAR = 'compras.crear'
PERMISO_CONFIRMAR = 'compras.confirmar'
PERMISO_CANCELAR = 'compras.cancelar'
CENT = Decimal('0.01')
MIL = Decimal('0.001')

def _decimal(valor, campo, precision):
    try:
        d = Decimal(str(valor))
        if not d.is_finite() or d <= 0 or d != d.quantize(precision):
            raise ValueError()
        return d
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise OrdenCompraServiceError(f'{campo} inválido.') from exc

def _monto(valor, campo):
    try:
        d = Decimal(str(valor))
        if not d.is_finite() or d < 0 or d != d.quantize(CENT):
            raise ValueError()
        return d
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise OrdenCompraServiceError(f'{campo} inválido.') from exc

def _actor(db, usuario_id, permiso):
    if type(usuario_id) is not int or usuario_id <= 0:
        raise OrdenCompraServiceError('Usuario inválido.')
    usuario = db.scalar(select(Usuario).where(Usuario.id == usuario_id, Usuario.activo.is_(True)))
    if usuario is None:
        raise OrdenCompraServiceError('Usuario inactivo o inexistente.')
    empresa = db.scalar(select(Empresa).where(Empresa.id == usuario.empresa_id, Empresa.activo.is_(True)))
    if empresa is None:
        raise OrdenCompraServiceError('Empresa inactiva o inexistente.')
    autorizado = db.scalar(select(Permiso.id).select_from(usuarios_roles)
        .join(Rol, and_(Rol.id == usuarios_roles.c.rol_id, Rol.empresa_id == usuarios_roles.c.empresa_id))
        .join(roles_permisos, roles_permisos.c.rol_id == Rol.id)
        .join(Permiso, Permiso.id == roles_permisos.c.permiso_id)
        .where(usuarios_roles.c.usuario_id == usuario_id,
               usuarios_roles.c.empresa_id == empresa.id,
               Permiso.codigo == permiso).limit(1))
    if autorizado is None:
        raise OrdenCompraServiceError('No tiene autorización para esta operación.')
    return usuario, empresa

def _orden(db, empresa_id, orden_id, *, bloqueo=False):
    if type(orden_id) is not int or orden_id <= 0:
        raise OrdenCompraServiceError('Orden no encontrada.')
    q = select(OrdenCompra).where(OrdenCompra.id == orden_id, OrdenCompra.empresa_id == empresa_id)
    if bloqueo:
        q = q.with_for_update()
    orden = db.scalar(q)
    if orden is None:
        raise OrdenCompraServiceError('Orden no encontrada.')
    return orden

def _registrar_auditoria(db, orden, usuario_id, accion, anterior, nuevo):
    db.add(Auditoria(empresa_id=orden.empresa_id, usuario_id=usuario_id,
        accion=accion, entidad='ordenes_compra', entidad_id=orden.id,
        descripcion=f'{accion} orden de compra.', datos_anteriores=anterior,
        datos_nuevos=nuevo, origen='SISTEMA'))

def crear_orden_compra(db: Session, *, usuario_id: int, proveedor_id: int, detalles: list[dict], codigo: str | None = None, moneda: str = 'PEN') -> OrdenCompra:
    """Crea BORRADOR, registra detalle y auditoría. NO modifica inventario."""
    try:
        usuario, empresa = _actor(db, usuario_id, PERMISO_CREAR)
        if type(proveedor_id) is not int or proveedor_id <= 0:
            raise OrdenCompraServiceError('Proveedor inválido.')
        proveedor = db.scalar(select(Proveedor).where(Proveedor.id == proveedor_id,
            Proveedor.empresa_id == empresa.id, Proveedor.activo.is_(True)))
        if proveedor is None:
            raise OrdenCompraServiceError('Proveedor no encontrado o inactivo.')
        if not isinstance(detalles, list) or not detalles:
            raise OrdenCompraServiceError('Debe indicar detalles de compra.')
        if not isinstance(moneda, str) or len(moneda) != 3 or not moneda.isalpha():
            raise OrdenCompraServiceError('Moneda inválida.')
        if codigo is None:
            codigo = 'OC-' + uuid4().hex[:20].upper()
        if not isinstance(codigo, str) or not codigo.strip() or len(codigo) > 50:
            raise OrdenCompraServiceError('Código inválido.')
        if db.scalar(select(OrdenCompra.id).where(OrdenCompra.empresa_id == empresa.id, OrdenCompra.codigo == codigo)):
            raise OrdenCompraServiceError('Código de orden duplicado.')
        ids = set()
        preparadas = []
        subtotal = Decimal('0.00')
        impuestos = Decimal('0.00')
        for item in detalles:
            if not isinstance(item, dict):
                raise OrdenCompraServiceError('Detalle inválido.')
            pid = item.get('producto_id')
            if type(pid) is not int or pid <= 0 or pid in ids:
                raise OrdenCompraServiceError('Producto duplicado o inválido.')
            ids.add(pid)
            producto = db.scalar(select(Producto).where(Producto.id == pid,
                Producto.empresa_id == empresa.id, Producto.activo.is_(True)))
            if producto is None:
                raise OrdenCompraServiceError('Producto no encontrado o inactivo.')
            cantidad = _decimal(item.get('cantidad'), 'Cantidad', MIL)
            precio = _decimal(item.get('precio_unitario'), 'Precio unitario', CENT)
            impuesto = _monto(item.get('impuesto', '0'), 'Impuesto')
            linea = (cantidad * precio).quantize(CENT, rounding=ROUND_HALF_UP)
            subtotal += linea
            impuestos += impuesto
            preparadas.append((producto, cantidad, precio, impuesto, linea))
        orden = OrdenCompra(empresa_id=empresa.id, proveedor_id=proveedor.id,
            usuario_id=usuario.id, codigo=codigo.strip(), estado='BORRADOR',
            estado_pago='PENDIENTE', moneda=moneda.upper(), subtotal=subtotal,
            impuesto_total=impuestos, total=subtotal + impuestos)
        db.add(orden)
        db.flush()
        for p, cant, precio, imp, linea in preparadas:
            db.add(OrdenCompraDetalle(empresa_id=empresa.id, orden_id=orden.id,
                producto_id=p.id, cantidad_solicitada=cant, precio_unitario=precio,
                impuesto=imp, subtotal=linea, total=linea + imp,
                controla_stock_snapshot=p.controla_stock))
        _registrar_auditoria(db, orden, usuario.id, 'CREAR', None, {'estado': 'BORRADOR'})
        db.commit()
        db.refresh(orden)
        return orden
    except Exception:
        db.rollback()
        raise

def obtener_orden_compra(db: Session, *, usuario_id: int, orden_id: int) -> OrdenCompra:
    _, empresa = _actor(db, usuario_id, PERMISO_VER)
    return _orden(db, empresa.id, orden_id)

def listar_ordenes_compra(db: Session, *, usuario_id: int, estado: str | None = None, proveedor_id: int | None = None, pagina: int = 1, limite: int = 20) -> dict:
    _, empresa = _actor(db, usuario_id, PERMISO_VER)
    if type(pagina) is not int or pagina < 1 or type(limite) is not int or not 1 <= limite <= 100:
        raise OrdenCompraServiceError('Paginación inválida.')
    filtros = [OrdenCompra.empresa_id == empresa.id]
    if estado is not None:
        filtros.append(OrdenCompra.estado == estado)
    if proveedor_id is not None:
        filtros.append(OrdenCompra.proveedor_id == proveedor_id)
    total = db.scalar(select(func.count()).select_from(OrdenCompra).where(*filtros))
    items = db.scalars(select(OrdenCompra).where(*filtros)
        .order_by(OrdenCompra.id.desc()).offset((pagina-1)*limite).limit(limite)).all()
    return {'total': total, 'pagina': pagina, 'limite': limite, 'items': items}

def confirmar_orden_compra(db: Session, *, usuario_id: int, orden_id: int) -> OrdenCompra:
    try:
        usuario, empresa = _actor(db, usuario_id, PERMISO_CONFIRMAR)
        orden = _orden(db, empresa.id, orden_id, bloqueo=True)
        if orden.estado != 'BORRADOR':
            raise OrdenCompraServiceError('Solo se puede confirmar una orden en BORRADOR.')
        if not db.scalar(select(OrdenCompraDetalle.id).where(OrdenCompraDetalle.orden_id == orden.id).limit(1)):
            raise OrdenCompraServiceError('Orden sin detalles.')
        if not db.scalar(select(Proveedor.id).where(Proveedor.id == orden.proveedor_id,
                                                    Proveedor.empresa_id == empresa.id, Proveedor.activo.is_(True))):
            raise OrdenCompraServiceError('Proveedor inactivo.')
        orden.estado = 'CONFIRMADA'
        orden.confirmed_at = datetime.now(timezone.utc)
        _registrar_auditoria(db, orden, usuario.id, 'CONFIRMAR', {'estado': 'BORRADOR'}, {'estado': 'CONFIRMADA'})
        db.commit()
        db.refresh(orden)
        return orden
    except Exception:
        db.rollback()
        raise

def cancelar_orden_compra(db: Session, *, usuario_id: int, orden_id: int) -> OrdenCompra:
    """Por seguridad solo cancela BORRADOR; cancelaciones posteriores requieren conciliar recepciones y pagos."""
    try:
        usuario, empresa = _actor(db, usuario_id, PERMISO_CANCELAR)
        orden = _orden(db, empresa.id, orden_id, bloqueo=True)
        if orden.estado != 'BORRADOR':
            raise OrdenCompraServiceError('Solo se puede cancelar una orden en BORRADOR.')
        orden.estado = 'CANCELADA'
        _registrar_auditoria(db, orden, usuario.id, 'CANCELAR', {'estado': 'BORRADOR'}, {'estado': 'CANCELADA'})
        db.commit()
        db.refresh(orden)
        return orden
    except Exception:
        db.rollback()
        raise
