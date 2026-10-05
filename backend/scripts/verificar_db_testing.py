
"""
SalesIA Enterprise
FASE 05-A.4-C

Verificación de aislamiento entre PostgreSQL
principal y PostgreSQL de pruebas.

No modifica datos ni crea tablas.
"""

from sqlalchemy.engine import make_url

from app.core.config import settings


def identificar_destino(url: str) -> tuple:
    conexion = make_url(url)

    return (
        conexion.host,
        conexion.port or 5432,
        conexion.database,
        conexion.username,
    )


def main():
    print("=== SalesIA: Auditoría de aislamiento ===")

    if not settings.TEST_DATABASE_URL:
        raise SystemExit(
            "ERROR: TEST_DATABASE_URL no está configurada."
        )

    principal = make_url(settings.DATABASE_URL)
    testing = make_url(settings.TEST_DATABASE_URL)

    if (
        principal.get_backend_name() != "postgresql"
        or testing.get_backend_name() != "postgresql"
    ):
        raise SystemExit(
            "ERROR: Ambas conexiones deben utilizar PostgreSQL."
        )

    if identificar_destino(
        settings.DATABASE_URL
    ) == identificar_destino(
        settings.TEST_DATABASE_URL
    ):
        raise SystemExit(
            "ERROR: Las conexiones apuntan al mismo destino."
        )

    print("Motor principal: PostgreSQL")
    print("Motor testing: PostgreSQL")
    print("Comparación inicial de destinos: DIFERENTES")
    print("Verificación estática: OK")
    print(
        "Pendiente: comprobar la identidad real de ambos "
        "servidores antes de permitir escrituras."
    )


if __name__ == "__main__":
    main()
