
"""
SalesIA Enterprise
FASE 05-A.4-C

Configuración protegida para pruebas PostgreSQL.

Las pruebas de integración deben solicitar explícitamente
la fixture db_testing.
"""

import pytest

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)


@pytest.fixture
def db_testing():
    """
    Abre una sesión exclusivamente en TEST_DATABASE_URL.

    Cada prueba utiliza su propia transacción y se revierte
    al finalizar, incluso si el servicio ejecuta commit().
    """

    if not settings.TEST_DATABASE_URL:
        pytest.fail(
            "TEST_DATABASE_URL no está configurada."
        )

    referencia_principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    referencia_testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    if (
    not referencia_principal
    or not referencia_testing
    or referencia_principal == referencia_testing
):
        pytest.fail(
        "SEGURIDAD: no se pudo verificar el aislamiento "
        "entre PostgreSQL principal y Testing."
    )

    engine = create_engine(
        settings.TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as connection:
            transaction = connection.begin()

            try:
                # Verifica que la conexión funciona.
                connection.execute(text("SELECT 1"))

                TestingSession = sessionmaker(
                    bind=connection,
                    autoflush=False,
                    autocommit=False,
                    join_transaction_mode="create_savepoint",
                )

                db = TestingSession()

                try:
                    yield db
                finally:
                    db.close()

            finally:
                transaction.rollback()

    finally:
        engine.dispose()
