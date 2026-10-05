
"""
SalesIA Enterprise
FASE 05-A.4-C

Auditoría de estructura de la base de pruebas.
Solo lectura. No crea, modifica ni elimina tablas.
"""

from sqlalchemy import create_engine, inspect

from app.core.config import settings
from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)


def main():
    print("=== Auditoría de PostgreSQL TESTING ===")

    if not settings.TEST_DATABASE_URL:
        raise SystemExit(
            "ERROR: TEST_DATABASE_URL no configurada."
        )

    principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    if principal == testing:
        raise SystemExit(
            "ERROR: testing apunta al proyecto principal."
        )

    engine = create_engine(
        settings.TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as connection:
            inspector = inspect(connection)

            tablas = sorted(
                inspector.get_table_names(schema="public")
            )

            print("Proyecto Supabase: TESTING")
            print("Esquema: public")
            print("Total de tablas:", len(tablas))

            if tablas:
                print("\nTablas encontradas:")
                for tabla in tablas:
                    print(" -", tabla)
            else:
                print("No existen tablas en el esquema public.")

            if "alembic_version" in tablas:
                print(
                    "\nATENCIÓN: existe una tabla "
                    "alembic_version."
                )
            else:
                print("\nAlembic: sin tabla de versiones.")

            if tablas:
                print(
                    "\nRESULTADO: REQUIERE REVISIÓN "
                    "ANTES DE MIGRAR."
                )
            else:
                print(
                    "\nRESULTADO: ESQUEMA PUBLIC VACÍO."
                )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
