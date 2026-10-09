"""FASE 08-E.6-C: dos pagos reales concurrentes en un esquema desechable.

SOLO PostgreSQL de testing. NO utiliza la fixture db_testing porque sus
transacciones sin confirmar no son visibles en otras conexiones.
"""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal, ROUND_HALF_UP
from threading import Barrier
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401 - registra todos los modelos de SQLAlchemy
from app.core.config import settings
from app.database.base import Base
from app.models.auditoria import Auditoria
from app.models.pago import Pago
from app.models.venta import Venta
from app.services.pago_service import PagoServiceError, registrar_pago
from app.services.pedido_service import confirmar_pedido
from app.services.venta_service import crear_venta_desde_pedido
from scripts.verificar_aislamiento_real import obtener_referencia_supabase
from tests.test_pedido_service import _escenario_confirmacion, _crear_borrador_confirmacion


def _validar_destino():
    principal = settings.DATABASE_URL
    testing = settings.TEST_DATABASE_URL
    if not principal or not testing:
        pytest.fail("SEGURIDAD: DATABASE_URL o TEST_DATABASE_URL no configurada.")
    ref_principal = obtener_referencia_supabase(principal)
    ref_testing = obtener_referencia_supabase(testing)
    if not ref_principal or not ref_testing or ref_principal == ref_testing:
        pytest.fail("SEGURIDAD: no hay aislamiento confirmado entre principal y testing.")
    return testing


def test_dos_registros_concurrentes_no_superan_saldo():
    url = _validar_destino()
    esquema = "salesia_conc_" + uuid4().hex[:16]
    # Identificador generado internamente: letras, dígitos y guion bajo únicamente.
    admin_engine = create_engine(url, pool_pre_ping=True)
    engine = admin_engine.execution_options(schema_translate_map={None: esquema})
    SessionTesting = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    esquema_creado = False
    try:
        with admin_engine.begin() as conn:
            if conn.dialect.name != "postgresql":
                pytest.fail("Esta prueba requiere PostgreSQL.")
            conn.execute(text(f'CREATE SCHEMA "{esquema}"'))
            esquema_creado = True

        # No modifica tablas ni registros del esquema público de testing.
        Base.metadata.create_all(bind=engine)

        with SessionTesting() as db:
            e = _escenario_confirmacion(
                db,
                permisos=(
                    "pedidos.crear", "pedidos.ver", "pedidos.confirmar",
                    "ventas.crear", "ventas.ver", "pagos.registrar", "pagos.ver",
                ),
            )
            pedido = _crear_borrador_confirmacion(db, e, cantidad="2.000")
            confirmar_pedido(db, usuario_id=e["usuario_id"], pedido_id=pedido.id)
            venta = crear_venta_desde_pedido(
                db, usuario_id=e["usuario_id"], pedido_id=pedido.id,
            )["venta"]
            usuario_id, empresa_id, venta_id = e["usuario_id"], e["empresa_id"], venta.id
            total = Decimal(venta.total)
            assert total > Decimal("0.01")
            monto = (total * Decimal("0.75")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            assert Decimal("0.00") < monto <= total and monto * 2 > total
            db.commit()  # Datos visibles desde ambas conexiones de trabajadores.

        barrera = Barrier(2, timeout=15)

        def solicitar_pago(indice):
            with SessionTesting() as db:
                barrera.wait()
                try:
                    pago = registrar_pago(
                        db,
                        usuario_id=usuario_id,
                        venta_id=venta_id,
                        monto=monto,
                        medio_pago="TRANSFERENCIA",
                        referencia_externa=f"concurrencia-{indice}",
                        idempotency_key=f"salesia_concurrencia_{uuid4().hex}",
                    )
                    return ("aceptado", pago.id)
                except PagoServiceError as exc:
                    return ("rechazado", str(exc))

        with ThreadPoolExecutor(max_workers=2) as pool:
            futuro_a = pool.submit(solicitar_pago, 1)
            futuro_b = pool.submit(solicitar_pago, 2)
            resultados = [futuro_a.result(timeout=40), futuro_b.result(timeout=40)]

        aceptados = [x for x in resultados if x[0] == "aceptado"]
        rechazados = [x for x in resultados if x[0] == "rechazado"]
        assert len(aceptados) == 1, resultados
        assert len(rechazados) == 1, resultados
        assert "saldo" in rechazados[0][1].lower() or "pagada" in rechazados[0][1].lower(), resultados

        with SessionTesting() as db:
            db.expire_all()
            venta_final = db.get(Venta, venta_id)
            pagos = db.scalars(select(Pago).where(
                Pago.empresa_id == empresa_id, Pago.venta_id == venta_id,
                Pago.estado == "REGISTRADO",
            )).all()
            auditorias = db.scalar(select(func.count()).select_from(Auditoria).where(
                Auditoria.empresa_id == empresa_id,
                Auditoria.entidad == "pagos",
                Auditoria.accion == "CREAR",
            ))
            assert len(pagos) == 1
            assert pagos[0].monto == monto
            assert venta_final.estado_pago == "PARCIAL"
            assert sum((p.monto for p in pagos), Decimal("0.00")) <= total
            assert auditorias == 1
    finally:
        # Primero se cierran las conexiones del pool; después se elimina
        # EXCLUSIVAMENTE el esquema con nombre aleatorio creado por este test.
        engine.dispose()
        if esquema_creado:
            try:
                with admin_engine.begin() as conn:
                    conn.execute(text(f'DROP SCHEMA IF EXISTS "{esquema}" CASCADE'))
            finally:
                admin_engine.dispose()
        else:
            admin_engine.dispose()
