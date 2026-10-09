"""SalesIA 09-D.3: recepciones confirmadas de órdenes de compra.

Operaciones mutantes hacen commit/rollback siguiendo la convención del backend.
Usar solamente con la configuración de DB correcta; las pruebas usan db_testing.
"""
from decimal import Decimal, InvalidOperation
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.orden_compra import OrdenCompra
from app.models.orden_compra_detalle import OrdenCompraDetalle
from app.models.recepcion_compra import RecepcionCompra
from app.models.recepcion_compra_detalle import RecepcionCompraDetalle
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.auditoria import Auditoria
from app.services.orden_compra_service import _actor, _orden, OrdenCompraServiceError

PERMISO_RECIBIR = 'recepciones.crear'
PERMISO_VER = 'recepciones.ver'
MIL = Decimal('0.001')


class RecepcionCompraServiceError(Exception):
    pass


def _actor_recepcion(db, usuario_id, permiso):
    try:
        return _actor(db, usuario_id, permiso)
    except OrdenCompraServiceError as exc:
        raise RecepcionCompraServiceError(str(exc)) from exc


def _cantidad(valor):
    try:
        cantidad = Decimal(str(valor))
        if not cantidad.is_finite() or cantidad <= 0 or cantidad != cantidad.quantize(MIL):
            raise ValueError
        if cantidad > Decimal('99999999999.999'):
            raise ValueError
        return cantidad
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise RecepcionCompraServiceError('Cantidad recibida inválida.') from exc


def _texto_opcional(valor, campo, limite):
    if valor is None:
        return None
    if not isinstance(valor, str) or not valor.strip() or len(valor.strip()) > limite:
        raise RecepcionCompraServiceError(f'{campo} inválido.')
    return valor.strip()


def recibir_compra(db: Session, *, usuario_id: int, orden_id: int,
                   detalles: list[dict], codigo: str | None = None,
                   idempotency_key: str | None = None) -> RecepcionCompra:
    """Confirma una recepción parcial/completa de manera atómica.

    detalles: [{'orden_detalle_id': int, 'cantidad_recibida': '1.000'}, ...].
    Idempotency key repetida devuelve la recepción original para la MISMA orden;
    una reutilización en otra orden se rechaza. No compara el contenido del payload.
    """
    try:
        usuario, empresa = _actor_recepcion(db, usuario_id, PERMISO_RECIBIR)
        codigo = _texto_opcional(codigo, 'Código', 50) or ('RC-' + uuid4().hex[:20].upper())
        key = _texto_opcional(idempotency_key, 'Idempotency key', 120)
        if not isinstance(detalles, list) or not detalles:
            raise RecepcionCompraServiceError('Debe indicar detalles de recepción.')
        preparadas = {}
        for item in detalles:
            if not isinstance(item, dict):
                raise RecepcionCompraServiceError('Detalle de recepción inválido.')
            linea_id = item.get('orden_detalle_id')
            if type(linea_id) is not int or linea_id <= 0 or linea_id in preparadas:
                raise RecepcionCompraServiceError('Detalle duplicado o inválido.')
            preparadas[linea_id] = _cantidad(item.get('cantidad_recibida'))

        # SERIALIZA recepciones concurrentes de esta orden y evita sobre-recepción.
        try:
            orden = _orden(db, empresa.id, orden_id, bloqueo=True)
        except OrdenCompraServiceError as exc:
            raise RecepcionCompraServiceError(str(exc)) from exc

        if key is not None:
            existente = db.scalar(select(RecepcionCompra).where(
                RecepcionCompra.empresa_id == empresa.id,
                RecepcionCompra.idempotency_key == key))
            if existente is not None:
                if existente.orden_id != orden.id:
                    raise RecepcionCompraServiceError('Idempotency key utilizada en otra orden.')
                return existente

        if orden.estado not in ('CONFIRMADA', 'PARCIALMENTE_RECIBIDA'):
            raise RecepcionCompraServiceError('La orden no admite recepciones en su estado actual.')
        if db.scalar(select(RecepcionCompra.id).where(
            RecepcionCompra.empresa_id == empresa.id, RecepcionCompra.codigo == codigo)) is not None:
            raise RecepcionCompraServiceError('Código de recepción duplicado.')

        lineas = db.scalars(select(OrdenCompraDetalle).where(
            OrdenCompraDetalle.empresa_id == empresa.id,
            OrdenCompraDetalle.orden_id == orden.id).order_by(OrdenCompraDetalle.id)).all()
        mapa = {x.id: x for x in lineas}
        if not mapa or not set(preparadas).issubset(mapa):
            raise RecepcionCompraServiceError('Detalle no pertenece a la orden.')

        recibidas = dict(db.execute(
            select(RecepcionCompraDetalle.orden_detalle_id,
                   func.sum(RecepcionCompraDetalle.cantidad_recibida))
            .where(RecepcionCompraDetalle.empresa_id == empresa.id,
                   RecepcionCompraDetalle.orden_id == orden.id)
            .group_by(RecepcionCompraDetalle.orden_detalle_id)).all())
        for lid, cant in preparadas.items():
            if Decimal(recibidas.get(lid) or 0) + cant > mapa[lid].cantidad_solicitada:
                raise RecepcionCompraServiceError('Cantidad excede lo pendiente de recibir.')

        recepcion = RecepcionCompra(empresa_id=empresa.id, orden_id=orden.id,
            usuario_id=usuario.id, codigo=codigo, idempotency_key=key, estado='CONFIRMADA')
        db.add(recepcion)
        db.flush()

        for lid, cantidad in preparadas.items():
            linea = mapa[lid]
            db.add(RecepcionCompraDetalle(empresa_id=empresa.id, orden_id=orden.id,
                recepcion_id=recepcion.id, orden_detalle_id=lid, cantidad_recibida=cantidad))
            if not linea.controla_stock_snapshot:
                continue
            # Primero crear fila en conflicto (sin perder existencias), luego bloquearla.
            stmt = pg_insert(Inventario).values(empresa_id=empresa.id,
                producto_id=linea.producto_id, cantidad_disponible=Decimal('0.000'))
            stmt = stmt.on_conflict_do_nothing(index_elements=['producto_id', 'empresa_id'])
            db.execute(stmt)
            stock = db.scalar(select(Inventario).where(
                Inventario.empresa_id == empresa.id,
                Inventario.producto_id == linea.producto_id).with_for_update())
            if stock is None:
                raise RecepcionCompraServiceError('No se pudo bloquear el inventario.')
            stock.cantidad_disponible = Decimal(stock.cantidad_disponible) + cantidad
            db.add(MovimientoInventario(empresa_id=empresa.id, producto_id=linea.producto_id,
                inventario_id=stock.id, tipo_movimiento='ENTRADA', cantidad_delta=cantidad,
                motivo='RECEPCION_COMPRA', referencia=recepcion.codigo,
                recepcion_compra_id=recepcion.id))

        nuevo_estado = 'RECIBIDA' if all(
            Decimal(recibidas.get(linea.id) or 0) + preparadas.get(linea.id, Decimal('0'))
            == linea.cantidad_solicitada for linea in lineas
        ) else 'PARCIALMENTE_RECIBIDA'
        anterior = orden.estado
        orden.estado = nuevo_estado
        db.add(Auditoria(empresa_id=empresa.id, usuario_id=usuario.id,
            accion='CONFIRMAR', entidad='recepciones_compra', entidad_id=recepcion.id,
            descripcion='Confirmar recepción de compra.',
            datos_anteriores={'orden_estado': anterior},
            datos_nuevos={'orden_id': orden.id, 'estado': nuevo_estado,
                          'lineas': len(preparadas)}, origen='SISTEMA'))
        db.commit()
        db.refresh(recepcion)
        return recepcion
    except Exception:
        db.rollback()
        raise


def obtener_recepcion_compra(db: Session, *, usuario_id: int, recepcion_id: int) -> RecepcionCompra:
    _, empresa = _actor_recepcion(db, usuario_id, PERMISO_VER)
    if type(recepcion_id) is not int or recepcion_id <= 0:
        raise RecepcionCompraServiceError('Recepción no encontrada.')
    recibo = db.scalar(select(RecepcionCompra).where(
        RecepcionCompra.id == recepcion_id, RecepcionCompra.empresa_id == empresa.id))
    if recibo is None:
        raise RecepcionCompraServiceError('Recepción no encontrada.')
    return recibo


def listar_recepciones_compra(db: Session, *, usuario_id: int, orden_id: int | None = None,
                              pagina: int = 1, limite: int = 20) -> dict:
    _, empresa = _actor_recepcion(db, usuario_id, PERMISO_VER)
    if type(pagina) is not int or pagina < 1 or type(limite) is not int or not 1 <= limite <= 100:
        raise RecepcionCompraServiceError('Paginación inválida.')
    filtros = [RecepcionCompra.empresa_id == empresa.id]
    if orden_id is not None:
        if type(orden_id) is not int or orden_id <= 0:
            raise RecepcionCompraServiceError('Orden inválida.')
        filtros.append(RecepcionCompra.orden_id == orden_id)
    total = db.scalar(select(func.count()).select_from(RecepcionCompra).where(*filtros))
    items = db.scalars(select(RecepcionCompra).where(*filtros)
        .order_by(RecepcionCompra.id.desc()).offset((pagina-1)*limite).limit(limite)).all()
    return {'total': total, 'pagina': pagina, 'limite': limite, 'items': items}
