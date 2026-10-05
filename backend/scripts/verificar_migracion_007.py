
"""
SalesIA Enterprise
Auditoria de migracion 007.

Verifica exclusivamente PostgreSQL Testing.
No modifica datos ni estructura.
"""

from sqlalchemy import create_engine, inspect, text

from app.core.config import settings
from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)


def main():
    principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    if not principal or not testing or principal == testing:
        raise RuntimeError(
            "SEGURIDAD: aislamiento Supabase no verificado."
        )

    print("AISLAMIENTO SUPABASE: OK")
    print("DESTINO: POSTGRESQL TESTING")

    engine = create_engine(
        settings.TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as conexion:
            version = conexion.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()

            print("VERSION ALEMBIC:", version)

            assert version == "7a08c5000007", (
                "La migracion 007 no esta aplicada."
            )

            inspector = inspect(conexion)

            tablas = (
                "pedido_detalles",
                "venta_detalles",
            )

            for tabla in tablas:
                columnas = inspector.get_columns(
                    tabla,
                    schema="public",
                )

                columna = next(
                    (
                        item
                        for item in columnas
                        if item["name"] == "tasa_impuesto"
                    ),
                    None,
                )

                assert columna is not None, (
                    f"Falta tasa_impuesto en {tabla}."
                )

                assert columna["nullable"] is True, (
                    f"Nullable incorrecto en {tabla}."
                )

                assert (
                    columna["type"].precision == 7
                    and columna["type"].scale == 4
                ), f"Tipo numerico incorrecto en {tabla}."

                restricciones = inspector.get_check_constraints(
                    tabla,
                    schema="public",
                )

                nombre_esperado = (
                    "ck_pedido_detalle_tasa_impuesto"
                    if tabla == "pedido_detalles"
                    else "ck_venta_detalle_tasa_impuesto"
                )

                assert any(
                    item["name"] == nombre_esperado
                    for item in restricciones
                ), (
                    f"Falta la restriccion {nombre_esperado}."
                )

                print(
                    f"{tabla}: "
                    "tasa_impuesto NUMERIC(7,4) NULL - OK"
                )

                print(
                    f"{tabla}: "
                    f"{nombre_esperado} - OK"
                )

        print()
        print("MIGRACION 007: VERIFICACION COMPLETA")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
