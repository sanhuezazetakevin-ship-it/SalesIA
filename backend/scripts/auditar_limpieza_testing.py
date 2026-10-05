"""
SalesIA Enterprise
FASE 05-B.5

Auditoría de limpieza posterior a las pruebas.
Exclusivamente lectura en PostgreSQL Testing.
"""

from sqlalchemy import create_engine, text

from app.core.config import settings
from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)


TABLAS_AUDITADAS = (
    "empresas",
    "usuarios",
    "sesiones",
    "invitaciones_usuario",
    "roles",
    "usuarios_roles",
    "roles_permisos",
    "auditoria",
)


def main():
    print("=== Auditoría ampliada de limpieza TESTING ===")

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

    if not principal or not testing or principal == testing:
        raise SystemExit(
            "SEGURIDAD: no se pudo verificar el aislamiento "
            "entre PostgreSQL principal y Testing."
        )

    engine = create_engine(
        settings.TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as connection:
            connection.execute(
                text("SET TRANSACTION READ ONLY")
            )

            resultados = {}

            for tabla in TABLAS_AUDITADAS:
                cantidad = connection.execute(
                    text(f"SELECT COUNT(*) FROM public.{tabla}")
                ).scalar_one()

                resultados[tabla] = cantidad
                print(f"{tabla}: {cantidad}")

            if all(
                cantidad == 0
                for cantidad in resultados.values()
            ):
                print("\nRESULTADO: LIMPIEZA VERIFICADA.")
                print(
                    "No permanecen registros en las "
                    "ocho tablas auditadas."
                )
            else:
                print("\nRESULTADO: EXISTEN REGISTROS.")
                print(
                    "Revisar su procedencia antes de continuar."
                )
                raise SystemExit(1)

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()