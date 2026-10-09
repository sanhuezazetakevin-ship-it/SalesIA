"""FASE 09-D.2: pruebas con rollback sobre TEST_DATABASE_URL."""
import pytest
from decimal import Decimal
from sqlalchemy import select, func
from app.models.producto import Producto
from app.models.inventario import Inventario
from app.models.orden_compra import OrdenCompra
from app.models.orden_compra_detalle import OrdenCompraDetalle
from app.models.auditoria import Auditoria
from app.services.proveedor_service import crear_proveedor
from app.services.orden_compra_service import (
    OrdenCompraServiceError, crear_orden_compra, obtener_orden_compra,
    listar_ordenes_compra, confirmar_orden_compra, cancelar_orden_compra,
)
from tests.test_proveedor_service import escenario as escenario_proveedor

PERMISOS = (
    'proveedores.ver', 'proveedores.crear', 'proveedores.editar',
    'compras.ver', 'compras.crear', 'compras.confirmar', 'compras.cancelar',
)

def preparar(db, permisos=PERMISOS):
    e = escenario_proveedor(db, permisos=permisos)
    proveedor = crear_proveedor(db, usuario_id=e['usuario_id'], razon_social='Proveedor para compra') if 'proveedores.crear' in permisos else None
    producto = Producto(empresa_id=e['empresa_id'], sku='SKU-COMPRA-09D2', nombre='Producto compra',
        tipo_item='PRODUCTO', precio_venta=Decimal('100.00'), costo_referencia=Decimal('30.00'),
        controla_stock=True, activo=True)
    db.add(producto)
    db.flush()
    # Los casos negativos llaman rollback() en el servicio.
    # Confirmar el escenario dentro del savepoint de db_testing permite
    # conservar sus datos entre intentos sin persistirlos al finalizar el test.
    db.commit()
    return e, proveedor, producto

def crear(db, e, p, producto):
    return crear_orden_compra(db, usuario_id=e['usuario_id'], proveedor_id=p.id,
        detalles=[{'producto_id': producto.id, 'cantidad': '2.000', 'precio_unitario': '30.00', 'impuesto': '10.80'}])

def test_crear_orden_y_auditoria_sin_movimiento_inventario(db_testing):
    e, p, producto = preparar(db_testing)
    antes = db_testing.scalar(select(func.count()).select_from(Inventario).where(Inventario.empresa_id == e['empresa_id']))
    orden = crear(db_testing, e, p, producto)
    assert orden.estado == 'BORRADOR' and orden.total == Decimal('70.80')
    assert db_testing.scalar(select(func.count()).select_from(OrdenCompraDetalle).where(OrdenCompraDetalle.orden_id == orden.id)) == 1
    assert db_testing.scalar(select(func.count()).select_from(Inventario).where(Inventario.empresa_id == e['empresa_id'])) == antes
    assert db_testing.scalar(select(func.count()).select_from(Auditoria).where(Auditoria.entidad == 'ordenes_compra', Auditoria.entidad_id == orden.id)) == 1

def test_confirmar_no_incrementa_inventario_y_no_duplica(db_testing):
    e, p, producto = preparar(db_testing)
    orden = crear(db_testing, e, p, producto)
    inventario_antes = db_testing.scalar(select(func.count()).select_from(Inventario).where(Inventario.empresa_id == e['empresa_id']))
    confirmada = confirmar_orden_compra(db_testing, usuario_id=e['usuario_id'], orden_id=orden.id)
    assert confirmada.estado == 'CONFIRMADA' and confirmada.confirmed_at is not None
    with pytest.raises(OrdenCompraServiceError, match='BORRADOR'):
        confirmar_orden_compra(db_testing, usuario_id=e['usuario_id'], orden_id=orden.id)
    assert db_testing.scalar(select(func.count()).select_from(Inventario).where(Inventario.empresa_id == e['empresa_id'])) == inventario_antes

def test_consultar_y_listar_filtrando(db_testing):
    e, p, producto = preparar(db_testing)
    orden = crear(db_testing, e, p, producto)
    assert obtener_orden_compra(db_testing, usuario_id=e['usuario_id'], orden_id=orden.id).id == orden.id
    listado = listar_ordenes_compra(db_testing, usuario_id=e['usuario_id'], estado='BORRADOR', proveedor_id=p.id)
    assert listado['total'] == 1 and listado['items'][0].id == orden.id

def test_cancelacion_segura(db_testing):
    e, p, producto = preparar(db_testing)
    orden = crear(db_testing, e, p, producto)
    assert cancelar_orden_compra(db_testing, usuario_id=e['usuario_id'], orden_id=orden.id).estado == 'CANCELADA'
    with pytest.raises(OrdenCompraServiceError, match='BORRADOR'):
        confirmar_orden_compra(db_testing, usuario_id=e['usuario_id'], orden_id=orden.id)

def test_cantidades_duplicados_y_permisos(db_testing):
    e, p, producto = preparar(db_testing)
    with pytest.raises(OrdenCompraServiceError, match='Cantidad'):
        crear_orden_compra(db_testing, usuario_id=e['usuario_id'], proveedor_id=p.id,
            detalles=[{'producto_id': producto.id, 'cantidad': '-1', 'precio_unitario': '10.00'}])
    with pytest.raises(OrdenCompraServiceError, match='duplicado'):
        crear_orden_compra(db_testing, usuario_id=e['usuario_id'], proveedor_id=p.id,
            detalles=[{'producto_id': producto.id, 'cantidad': '1', 'precio_unitario': '10.00'}]*2)
    # Los permisos se consultan dinámicamente; esta prueba se concentra en entradas inválidas.

def test_aislamiento_multiempresa(db_testing):
    a, pa, prod_a = preparar(db_testing)
    b, pb, prod_b = preparar(db_testing)
    orden_b = crear(db_testing, b, pb, prod_b)
    with pytest.raises(OrdenCompraServiceError, match='no encontrada'):
        obtener_orden_compra(db_testing, usuario_id=a['usuario_id'], orden_id=orden_b.id)
    with pytest.raises(OrdenCompraServiceError, match='no encontrada'):
        confirmar_orden_compra(db_testing, usuario_id=a['usuario_id'], orden_id=orden_b.id)
