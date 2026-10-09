"""SalesIA 09-D.4: pagos a proveedores; transacciones atómicas y aislamiento multiempresa.

Mutaciones confirman o revierten la sesión, siguiendo la convención del backend.
El llamador HTTP debe inyectar la sesión autenticada; nunca aceptar empresa_id del cliente.
"""
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.pago_proveedor import PagoProveedor
from app.models.orden_compra import OrdenCompra
from app.models.auditoria import Auditoria
from app.services.orden_compra_service import _actor, _orden, OrdenCompraServiceError

PERMISO_VER = 'pagos_proveedores.ver'
PERMISO_REGISTRAR = 'pagos_proveedores.registrar'
PERMISO_ANULAR = 'pagos_proveedores.anular'
CENT = Decimal('0.01')

class PagoProveedorServiceError(Exception):
    pass

def _usuario(db, usuario_id, permiso):
    try:
        return _actor(db, usuario_id, permiso)
    except OrdenCompraServiceError as exc:
        raise PagoProveedorServiceError(str(exc)) from exc

def _orden_empresa(db, empresa_id, orden_id, *, bloqueo=False):
    try:
        return _orden(db, empresa_id, orden_id, bloqueo=bloqueo)
    except OrdenCompraServiceError as exc:
        raise PagoProveedorServiceError(str(exc)) from exc

def _texto(valor, campo, maximo, opcional=False):
    if opcional and valor is None:
        return None
    if not isinstance(valor, str) or not valor.strip() or len(valor.strip()) > maximo:
        raise PagoProveedorServiceError(f'{campo} inválido.')
    return valor.strip()

def _monto(valor):
    try:
        v = Decimal(str(valor))
        if not v.is_finite() or v <= 0 or v != v.quantize(CENT) or v > Decimal('999999999999.99'):
            raise ValueError
        return v
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise PagoProveedorServiceError('Monto inválido.') from exc

def _pagado(db, empresa_id, orden_id):
    valor = db.scalar(select(func.sum(PagoProveedor.monto)).where(
        PagoProveedor.empresa_id == empresa_id,
        PagoProveedor.orden_id == orden_id,
        PagoProveedor.estado == 'REGISTRADO'))
    return Decimal(valor or 0)

def _actualizar_estado(orden, pagado):
    if pagado < 0 or pagado > orden.total:
        raise PagoProveedorServiceError('Inconsistencia entre pagos y total de orden.')
    orden.estado_pago = 'PENDIENTE' if pagado == 0 else ('PAGADO' if pagado == orden.total else 'PARCIAL')

def _auditar(db, pago, usuario_id, accion, anterior, nuevo):
    db.add(Auditoria(empresa_id=pago.empresa_id, usuario_id=usuario_id,
        accion=accion, entidad='pagos_proveedores', entidad_id=pago.id,
        descripcion=f'{accion} pago a proveedor.', datos_anteriores=anterior,
        datos_nuevos=nuevo, origen='SISTEMA'))

def registrar_pago_proveedor(db: Session, *, usuario_id: int, orden_id: int,
                            monto, medio_pago: str, codigo: str | None = None,
                            referencia_externa: str | None = None,
                            idempotency_key: str | None = None) -> PagoProveedor:
    """Registra un pago. Clave idempotente repetida requiere mismos atributos de pago."""
    try:
        usuario, empresa = _usuario(db, usuario_id, PERMISO_REGISTRAR)
        valor = _monto(monto)
        medio = _texto(medio_pago, 'Medio de pago', 40)
        codigo_solicitado = _texto(codigo, 'Código', 50, opcional=True)
        codigo = codigo_solicitado or ('PP-' + uuid4().hex[:20].upper())
        referencia = _texto(referencia_externa, 'Referencia externa', 120, opcional=True)
        key = _texto(idempotency_key, 'Idempotency key', 120, opcional=True)
        # Todo pago y anulación bloquean la misma fila de orden antes de sumar importes.
        orden = _orden_empresa(db, empresa.id, orden_id, bloqueo=True)
        if key is not None:
            anterior = db.scalar(select(PagoProveedor).where(
                PagoProveedor.empresa_id == empresa.id, PagoProveedor.idempotency_key == key))
            if anterior is not None:
                if (anterior.orden_id != orden.id or anterior.monto != valor or
                    anterior.medio_pago != medio or anterior.referencia_externa != referencia or
                    (codigo_solicitado is not None and anterior.codigo != codigo_solicitado)):
                    raise PagoProveedorServiceError('Idempotency key reutilizada con datos distintos.')
                return anterior
        if orden.estado not in ('CONFIRMADA', 'PARCIALMENTE_RECIBIDA', 'RECIBIDA'):
            raise PagoProveedorServiceError('La orden no permite pagos en su estado actual.')
        if db.scalar(select(PagoProveedor.id).where(
            PagoProveedor.empresa_id == empresa.id, PagoProveedor.codigo == codigo)) is not None:
            raise PagoProveedorServiceError('Código de pago duplicado.')
        pagado = _pagado(db, empresa.id, orden.id)
        if pagado + valor > orden.total:
            raise PagoProveedorServiceError('El pago excede el saldo pendiente.')
        pago = PagoProveedor(empresa_id=empresa.id, orden_id=orden.id, usuario_id=usuario.id,
                            codigo=codigo, monto=valor, medio_pago=medio,
                            referencia_externa=referencia, idempotency_key=key, estado='REGISTRADO')
        db.add(pago)
        db.flush()
        previo = orden.estado_pago
        _actualizar_estado(orden, pagado + valor)
        _auditar(db, pago, usuario.id, 'CREAR', None,
                 {'orden_id': orden.id, 'monto': str(valor), 'estado_pago': orden.estado_pago})
        db.commit()
        db.refresh(pago)
        return pago
    except Exception:
        db.rollback()
        raise

def anular_pago_proveedor(db: Session, *, usuario_id: int, pago_id: int) -> PagoProveedor:
    """Anula registro de pago, sin borrar historia; no altera inventario ni recepciones."""
    try:
        usuario, empresa = _usuario(db, usuario_id, PERMISO_ANULAR)
        # Primero se localiza la orden y después se bloquea (mismo orden de locks que registro).
        if type(pago_id) is not int or pago_id <= 0:
            raise PagoProveedorServiceError('Pago no encontrado.')
        identificador_orden = db.scalar(select(PagoProveedor.orden_id).where(
            PagoProveedor.id == pago_id, PagoProveedor.empresa_id == empresa.id))
        if identificador_orden is None:
            raise PagoProveedorServiceError('Pago no encontrado.')
        orden = _orden_empresa(db, empresa.id, identificador_orden, bloqueo=True)
        pago = db.scalar(select(PagoProveedor).where(PagoProveedor.id == pago_id,
                                                    PagoProveedor.empresa_id == empresa.id).with_for_update())
        if pago is None or pago.estado != 'REGISTRADO':
            raise PagoProveedorServiceError('Pago inexistente o ya anulado.')
        pago.estado = 'ANULADO'
        db.flush()
        pagado = _pagado(db, empresa.id, orden.id)
        _actualizar_estado(orden, pagado)
        _auditar(db, pago, usuario.id, 'ANULAR', {'estado': 'REGISTRADO'},
                 {'estado': 'ANULADO', 'estado_pago': orden.estado_pago})
        db.commit()
        db.refresh(pago)
        return pago
    except Exception:
        db.rollback()
        raise

def obtener_pago_proveedor(db: Session, *, usuario_id: int, pago_id: int) -> PagoProveedor:
    _, empresa = _usuario(db, usuario_id, PERMISO_VER)
    if type(pago_id) is not int or pago_id <= 0:
        raise PagoProveedorServiceError('Pago no encontrado.')
    pago = db.scalar(select(PagoProveedor).where(PagoProveedor.id == pago_id,
                                                PagoProveedor.empresa_id == empresa.id))
    if pago is None:
        raise PagoProveedorServiceError('Pago no encontrado.')
    return pago

def listar_pagos_proveedor(db: Session, *, usuario_id: int, orden_id: int | None = None,
                           estado: str | None = None, pagina: int = 1, limite: int = 20) -> dict:
    _, empresa = _usuario(db, usuario_id, PERMISO_VER)
    if type(pagina) is not int or pagina < 1 or type(limite) is not int or not 1 <= limite <= 100:
        raise PagoProveedorServiceError('Paginación inválida.')
    filtros = [PagoProveedor.empresa_id == empresa.id]
    if orden_id is not None:
        if type(orden_id) is not int or orden_id <= 0:
            raise PagoProveedorServiceError('Orden inválida.')
        filtros.append(PagoProveedor.orden_id == orden_id)
    if estado is not None:
        if estado not in ('REGISTRADO', 'ANULADO'):
            raise PagoProveedorServiceError('Estado inválido.')
        filtros.append(PagoProveedor.estado == estado)
    total = db.scalar(select(func.count()).select_from(PagoProveedor).where(*filtros))
    items = db.scalars(select(PagoProveedor).where(*filtros)
        .order_by(PagoProveedor.id.desc()).offset((pagina-1)*limite).limit(limite)).all()
    return {'total': total, 'pagina': pagina, 'limite': limite, 'items': items}
