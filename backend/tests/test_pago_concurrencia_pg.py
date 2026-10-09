"""FASE 08-E.6-B: prueba aislada de bloqueo real de filas en PostgreSQL.

Esta prueba verifica dos conexiones independientes y SELECT FOR UPDATE.
NO es aun una prueba extremo a extremo de registrar_pago.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from scripts.verificar_aislamiento_real import obtener_referencia_supabase


@pytest.fixture
def engine_concurrencia_testing():
    principal = obtener_referencia_supabase(settings.DATABASE_URL)
    testing = obtener_referencia_supabase(settings.TEST_DATABASE_URL)
    if not principal or not testing or principal == testing:
        pytest.fail("SEGURIDAD: DATABASE_URL y TEST_DATABASE_URL no estan aisladas")

    engine = create_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True, pool_size=3,
                           max_overflow=0, connect_args={"connect_timeout": 10})
    try:
        if engine.dialect.name != "postgresql":
            pytest.fail("Esta prueba requiere PostgreSQL")
        yield engine
    finally:
        engine.dispose()


def test_bloqueo_fila_entre_conexiones_independientes(engine_concurrencia_testing):
    engine = engine_concurrencia_testing
    # Identificador SQL producido internamente y validado; no hay entrada externa.
    tabla = "salesia_lock_" + uuid4().hex
    bloqueada = Event()
    liberar = Event()

    with engine.begin() as conn:
        conn.execute(text(f'CREATE TABLE "{tabla}" (id integer PRIMARY KEY, monto numeric(14,2))'))
        conn.execute(text(f'INSERT INTO "{tabla}" VALUES (1, 200.00)'))

    def transaccion_a():
        with engine.connect() as conn:
            with conn.begin():
                conn.execute(text(f'SELECT id FROM "{tabla}" WHERE id=1 FOR UPDATE')).scalar_one()
                bloqueada.set()
                if not liberar.wait(timeout=15):
                    raise AssertionError("No llego la senal de liberacion del test")

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            futuro = executor.submit(transaccion_a)
            assert bloqueada.wait(timeout=15), "La transaccion A no obtuvo el bloqueo"
            try:
                # Otra conexion intenta obtener el mismo bloqueo sin esperar.
                # PostgreSQL debe rechazar NOWAIT mientras A mantiene el bloqueo.
                with engine.connect() as conn:
                    with pytest.raises(DBAPIError) as error:
                        with conn.begin():
                            conn.execute(text(
                                f'SELECT id FROM "{tabla}" WHERE id=1 FOR UPDATE NOWAIT'
                            )).scalar_one()
                assert getattr(error.value.orig, "sqlstate", None) == "55P03"
            finally:
                liberar.set()
            futuro.result(timeout=20)

        # Al terminar A, la misma fila se puede bloquear nuevamente.
        with engine.begin() as conn:
            assert conn.execute(text(
                f'SELECT id FROM "{tabla}" WHERE id=1 FOR UPDATE NOWAIT'
            )).scalar_one() == 1
    finally:
        liberar.set()
        with engine.begin() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS "{tabla}"'))
