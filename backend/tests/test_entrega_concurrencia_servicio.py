"""SalesIA FASE 08-F.6-A: doble confirmacion real de una entrega.

SOLO TEST_DATABASE_URL, aislado en un esquema desechable. Cada trabajador
utiliza una sesion y una conexion PostgreSQL distintas.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401 - carga las tablas registradas en SQLAlchemy
from app.core.config import settings
from app.database.base import Base
from app.models.auditoria import Auditoria
from app.models.entrega import Entrega
from app.models.inventario import Inventario
from app.models.movimiento_inventario import MovimientoInventario
from app.models.reserva_stock import ReservaStock
from app.services.entrega_service import EntregaServiceError, confirmar_entrega
from scripts.verificar_aislamiento_real import obtener_referencia_supabase
from tests.test_entrega_service import preparar_entrega


def _url_testing_protegida():
    principal = settings.DATABASE_URL
    testing = settings.TEST_DATABASE_URL
    if not principal or not testing:
        pytest.fail("SEGURIDAD: se requieren DATABASE_URL y TEST_DATABASE_URL.")
    ref_principal = obtener_referencia_supabase(principal)
    ref_testing = obtener_referencia_supabase(testing)
    if not ref_principal or not ref_testing or ref_principal == ref_testing:
        pytest.fail("SEGURIDAD: aislamiento de Supabase no confirmado.")
    return testing


def test_dos_confirmaciones_concurrentes_descontan_solo_una_vez():
    url = _url_testing_protegida()
    esquema = "salesia_entrega_conc_" + uuid4().hex[:16]
    admin_engine = create_engine(url, pool_pre_ping=True)
    engine = admin_engine.execution_options(schema_translate_map={None: esquema})
    SesionTesting = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    esquema_creado = False
    try:
        with admin_engine.begin() as conn:
            if conn.dialect.name != "postgresql":
                pytest.fail("Esta prueba requiere PostgreSQL.")
            conn.execute(text(f'CREATE SCHEMA "{esquema}"'))
            esquema_creado = True

        Base.metadata.create_all(bind=engine)

        with SesionTesting() as db:
            escenario, pedido_id, venta_id = preparar_entrega(
                db, controla_stock=True, cantidad="2.000"
            )
            usuario_id = escenario["usuario_id"]
            empresa_id = escenario["empresa_id"]
            inventario_id = escenario["inventario_id"]
            assert db.get(Inventario, inventario_id).cantidad_disponible == Decimal("10.000")
            db.commit()  # Necesario para que otras conexiones vean los registros.

        barrera = Barrier(2, timeout=20)

        def trabajador(n):
            with SesionTesting() as db:
                barrera.wait()
                try:
                    resultado = confirmar_entrega(
                        db,
                        usuario_id=usuario_id,
                        venta_id=venta_id,
                        observaciones=f"Concurrencia prueba {n}",
                    )
                    return ("confirmada", resultado["entrega"].id)
                except EntregaServiceError as exc:
                    return ("rechazada", str(exc))

        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(trabajador, 1)
            b = pool.submit(trabajador, 2)
            resultados = [a.result(timeout=60), b.result(timeout=60)]

        confirmadas = [x for x in resultados if x[0] == "confirmada"]
        rechazadas = [x for x in resultados if x[0] == "rechazada"]
        assert len(confirmadas) == 1, resultados
        assert len(rechazadas) == 1, resultados
        assert "ya tiene una entrega" in rechazadas[0][1].lower(), resultados

        with SesionTesting() as db:
            entregas = db.scalars(select(Entrega).where(
                Entrega.empresa_id == empresa_id, Entrega.venta_id == venta_id
            )).all()
            assert len(entregas) == 1
            assert entregas[0].estado == "CONFIRMADA"
            assert entregas[0].fecha_confirmacion is not None

            reservas = db.scalars(select(ReservaStock).where(
                ReservaStock.empresa_id == empresa_id,
                ReservaStock.pedido_id == pedido_id,
            )).all()
            assert len(reservas) == 1
            assert reservas[0].estado == "CONSUMIDA"
            assert reservas[0].cantidad_reservada == Decimal("2.000")

            inventario = db.get(Inventario, inventario_id)
            assert inventario.cantidad_disponible == Decimal("8.000")

            movimientos = db.scalars(select(MovimientoInventario).where(
                MovimientoInventario.empresa_id == empresa_id,
                MovimientoInventario.entrega_id == entregas[0].id,
            )).all()
            assert len(movimientos) == 1
            assert movimientos[0].tipo_movimiento == "SALIDA"
            assert movimientos[0].cantidad_delta == Decimal("-2.000")

            auditorias = db.scalar(select(func.count()).select_from(Auditoria).where(
                Auditoria.empresa_id == empresa_id,
                Auditoria.entidad == "entregas",
                Auditoria.entidad_id == entregas[0].id,
                Auditoria.accion == "CONFIRMAR",
            ))
            assert auditorias == 1
    finally:
        engine.dispose()
        try:
            if esquema_creado:
                with admin_engine.begin() as conn:
                    conn.execute(text(f'DROP SCHEMA IF EXISTS "{esquema}" CASCADE'))
        finally:
            admin_engine.dispose()
