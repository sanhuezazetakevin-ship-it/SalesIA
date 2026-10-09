"""FASE 09-F.3: concurrencia REAL con sesiones PostgreSQL independientes.

SOLO TEST_DATABASE_URL. Cada prueba crea un schema desechable y lo elimina
al terminar. No utiliza la fixture db_testing porque sus filas no son visibles
para otras conexiones antes del commit de la transaccion externa.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, func, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.database.base import Base
import app.models  # noqa: F401 - registra los modelos SQLAlchemy
from scripts.verificar_aislamiento_real import obtener_referencia_supabase
from app.models.orden_compra import OrdenCompra
from app.models.orden_compra_detalle import OrdenCompraDetalle
from app.models.recepcion_compra import RecepcionCompra
from app.models.recepcion_compra_detalle import RecepcionCompraDetalle
from app.models.pago_proveedor import PagoProveedor
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.services.orden_compra_service import confirmar_orden_compra
from app.services.recepcion_compra_service import recibir_compra, RecepcionCompraServiceError
from app.services.pago_proveedor_service import (
    registrar_pago_proveedor, anular_pago_proveedor, PagoProveedorServiceError,
)
from tests.test_orden_compra_service import preparar, crear, PERMISOS

TODOS_PERMISOS = tuple(dict.fromkeys((
    *PERMISOS,
    'recepciones.crear', 'recepciones.ver',
    'pagos_proveedores.ver', 'pagos_proveedores.registrar', 'pagos_proveedores.anular',
)))


@pytest.fixture
def pg_competencia():
    """Schema separado por prueba; ninguna tabla de negocio pública es alterada."""
    principal = obtener_referencia_supabase(settings.DATABASE_URL)
    testing_url = settings.TEST_DATABASE_URL
    if not testing_url:
        pytest.fail('SEGURIDAD: TEST_DATABASE_URL no configurada.')
    testing = obtener_referencia_supabase(testing_url)
    if not principal or not testing or principal == testing:
        pytest.fail('SEGURIDAD: Supabase principal y testing no estan aisladas.')

    esquema = 'salesia_09f3_' + uuid4().hex[:20]
    administracion = create_engine(testing_url, pool_pre_ping=True,
                                   connect_args={'connect_timeout': 10})
    motor = None
    creado = False
    try:
        assert administracion.dialect.name == 'postgresql'
        with administracion.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{esquema}"'))
            creado = True
        # Solo el schema desechable. No hacer fallback a public: evita
        # leer/escribir tablas de negocio compartidas por error.
        motor = create_engine(testing_url, pool_pre_ping=True,
            pool_size=4, max_overflow=0,
            connect_args={'connect_timeout': 10})

        # El pooler de Supabase puede ignorar las opciones de inicio
        # (PGOPTIONS). Forzar el esquema al comienzo de CADA transaccion.
        # SET LOCAL es transaccional: no contamina otras conexiones del pool.
        @event.listens_for(motor, 'begin')
        def _aislar_cada_transaccion(conn):
            conn.exec_driver_sql(f'SET LOCAL search_path TO "{esquema}"')
            conn.exec_driver_sql("SET LOCAL lock_timeout = '15s'")
            conn.exec_driver_sql("SET LOCAL statement_timeout = '30s'")
            actual = conn.exec_driver_sql('SELECT current_schema()').scalar_one()
            if actual != esquema:
                raise RuntimeError(
                    'SEGURIDAD: search_path no apunta al esquema de testing '
                    f'({actual!r} != {esquema!r}). Operacion abortada.'
                )

        # Revalidacion explicita ANTES de ejecutar CREATE TABLE.
        with motor.connect() as conn:
            assert conn.exec_driver_sql('SELECT current_schema()').scalar_one() == esquema
        # Todos los modelos deben existir dentro del schema de prueba.
        Base.metadata.create_all(motor, checkfirst=False)
        fabrica = sessionmaker(bind=motor, autoflush=False, expire_on_commit=False)
        yield fabrica
    finally:
        if motor is not None:
            motor.dispose()
        if creado:
            # Solo elimina el schema aleatorio que esta prueba creó.
            with administracion.begin() as conn:
                conn.execute(text(f'DROP SCHEMA IF EXISTS "{esquema}" CASCADE'))
        administracion.dispose()


def _escenario(fabrica):
    with fabrica() as db:
        e, proveedor, producto = preparar(db, permisos=TODOS_PERMISOS)
        orden = crear(db, e, proveedor, producto)
        confirmar_orden_compra(db, usuario_id=e['usuario_id'], orden_id=orden.id)
        detalle = db.scalar(select(OrdenCompraDetalle).where(OrdenCompraDetalle.orden_id == orden.id))
        return e['usuario_id'], e['empresa_id'], producto.id, orden.id, detalle.id


def _paralelo(fabrica, trabajos):
    barrera = Barrier(len(trabajos), timeout=20)
    def ejecutar(trabajo):
        with fabrica() as db:
            barrera.wait()
            try:
                return ('OK', trabajo(db))
            except (RecepcionCompraServiceError, PagoProveedorServiceError) as exc:
                return ('RECHAZADO', str(exc))
    with ThreadPoolExecutor(max_workers=len(trabajos)) as pool:
        futuros = [pool.submit(ejecutar, tarea) for tarea in trabajos]
        return [f.result(timeout=40) for f in futuros]


def test_dos_recepciones_concurrentes_no_sobrerreciben(pg_competencia):
    fabrica = pg_competencia
    usuario, empresa, producto, orden, linea = _escenario(fabrica)
    def recibir(db):
        return recibir_compra(db, usuario_id=usuario, orden_id=orden,
            detalles=[{'orden_detalle_id': linea, 'cantidad_recibida': '1.500'}]).id
    resultados = _paralelo(fabrica, [recibir, recibir])
    assert sorted(r[0] for r in resultados) == ['OK', 'RECHAZADO'], resultados
    with fabrica() as db:
        total = db.scalar(select(func.sum(RecepcionCompraDetalle.cantidad_recibida))
            .where(RecepcionCompraDetalle.orden_id == orden))
        stock = db.scalar(select(Inventario.cantidad_disponible)
            .where(Inventario.empresa_id == empresa, Inventario.producto_id == producto))
        cantidad_mov = db.scalar(select(func.sum(MovimientoInventario.cantidad_delta))
            .where(MovimientoInventario.empresa_id == empresa,
                   MovimientoInventario.recepcion_compra_id.is_not(None)))
        assert total == stock == cantidad_mov == Decimal('1.500')
        assert db.get(OrdenCompra, orden).estado == 'PARCIALMENTE_RECIBIDA'


def test_misma_idempotencia_recepcion_en_dos_conexiones(pg_competencia):
    fabrica = pg_competencia
    usuario, empresa, producto, orden, linea = _escenario(fabrica)
    def recibir(db):
        return recibir_compra(db, usuario_id=usuario, orden_id=orden,
            detalles=[{'orden_detalle_id': linea, 'cantidad_recibida': '1.000'}],
            idempotency_key='repeticion-rc-09f3').id
    resultados = _paralelo(fabrica, [recibir, recibir])
    assert [r[0] for r in resultados] == ['OK', 'OK'], resultados
    assert resultados[0][1] == resultados[1][1]
    with fabrica() as db:
        assert db.scalar(select(func.count()).select_from(RecepcionCompra)
            .where(RecepcionCompra.orden_id == orden)) == 1
        assert db.scalar(select(Inventario.cantidad_disponible)
            .where(Inventario.empresa_id == empresa, Inventario.producto_id == producto)) == Decimal('1.000')


def test_pagos_concurrentes_no_superan_total(pg_competencia):
    fabrica = pg_competencia
    usuario, empresa, _, orden, _ = _escenario(fabrica)
    def pagar(db):
        return registrar_pago_proveedor(db, usuario_id=usuario, orden_id=orden,
            monto='50.00', medio_pago='TRANSFERENCIA').id
    resultados = _paralelo(fabrica, [pagar, pagar])
    assert sorted(r[0] for r in resultados) == ['OK', 'RECHAZADO'], resultados
    with fabrica() as db:
        importe = db.scalar(select(func.sum(PagoProveedor.monto)).where(
            PagoProveedor.orden_id == orden, PagoProveedor.estado == 'REGISTRADO'))
        assert importe == Decimal('50.00')
        assert db.get(OrdenCompra, orden).estado_pago == 'PARCIAL'


def test_pago_y_anulacion_concurrentes_consistentes(pg_competencia):
    fabrica = pg_competencia
    usuario, empresa, _, orden, _ = _escenario(fabrica)
    with fabrica() as db:
        pago = registrar_pago_proveedor(db, usuario_id=usuario, orden_id=orden,
            monto='20.00', medio_pago='TRANSFERENCIA')
        pago_id = pago.id
    def registrar(db):
        return registrar_pago_proveedor(db, usuario_id=usuario, orden_id=orden,
            monto='30.00', medio_pago='TRANSFERENCIA').id
    def anular(db):
        return anular_pago_proveedor(db, usuario_id=usuario, pago_id=pago_id).id
    resultados = _paralelo(fabrica, [registrar, anular])
    assert all(r[0] == 'OK' for r in resultados), resultados
    with fabrica() as db:
        pagos = db.scalars(select(PagoProveedor).where(PagoProveedor.orden_id == orden)).all()
        suma = sum((p.monto for p in pagos if p.estado == 'REGISTRADO'), Decimal('0'))
        assert suma == Decimal('30.00')
        assert db.get(OrdenCompra, orden).estado_pago == 'PARCIAL'


def test_idempotencia_pago_concurrente_misma_clave(pg_competencia):
    fabrica = pg_competencia
    usuario, _, _, orden, _ = _escenario(fabrica)
    def pagar(db):
        return registrar_pago_proveedor(db, usuario_id=usuario, orden_id=orden,
            monto='15.00', medio_pago='TRANSFERENCIA',
            idempotency_key='repeticion-pg-09f3').id
    resultados = _paralelo(fabrica, [pagar, pagar])
    assert [r[0] for r in resultados] == ['OK', 'OK'], resultados
    assert resultados[0][1] == resultados[1][1]
    with fabrica() as db:
        assert db.scalar(select(func.count()).select_from(PagoProveedor)
            .where(PagoProveedor.orden_id == orden)) == 1
