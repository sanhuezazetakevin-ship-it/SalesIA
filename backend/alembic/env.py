
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.database.base import Base

from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)

import app.models


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata



def seleccionar_database_url() -> str:
    """
    Politica de seguridad SalesIA Enterprise.

    Alembic solo admite PostgreSQL Testing y requiere
    que el destino se indique explicitamente.

    La base principal nunca se selecciona desde este entorno.
    """

    argumentos = context.get_x_argument(as_dictionary=True)
    destino = argumentos.get("db")

    if destino != "testing":
        raise RuntimeError(
            "SEGURIDAD SALESIA: Alembic bloqueado. "
            "Debe indicar explicitamente -x db=testing. "
            "Las migraciones sobre la base principal "
            "estan deshabilitadas."
        )

    if not settings.DATABASE_URL or not settings.TEST_DATABASE_URL:
        raise RuntimeError(
            "SEGURIDAD SALESIA: faltan las URL de las bases "
            "principal o Testing."
        )

    principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    if not principal or not testing:
        raise RuntimeError(
            "SEGURIDAD SALESIA: no se pudo verificar "
            "la identidad de ambos proyectos Supabase."
        )

    if principal == testing:
        raise RuntimeError(
            "SEGURIDAD SALESIA: Testing y principal "
            "pertenecen al mismo proyecto Supabase."
        )

    print("[ALEMBIC] Destino seleccionado: TESTING")
    print("[ALEMBIC] Aislamiento Supabase: OK")
    print("[ALEMBIC] Base principal: BLOQUEADA")

    return settings.TEST_DATABASE_URL



database_url = seleccionar_database_url()

# ConfigParser interpreta % como interpolación.
config.set_main_option(
    "sqlalchemy.url",
    database_url.replace("%", "%%"),
)


def run_migrations_offline():
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {},
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
