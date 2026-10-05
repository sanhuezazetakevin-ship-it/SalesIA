
"""
SalesIA Enterprise
FASE 05-A.4-C

Verificación de aislamiento real de dos proyectos Supabase.

Solo ejecuta consultas de lectura.
No modifica tablas, usuarios ni migraciones.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from app.core.config import settings


class ErrorAislamiento(Exception):
    pass


def obtener_referencia_supabase(url_original: str) -> str:
    """
    Admite conexiones oficiales habituales:

    Directa:
        db.PROJECT_REF.supabase.co

    Pooler:
        usuario postgres.PROJECT_REF

    Si no puede identificar el proyecto, falla por seguridad.
    """
    url = make_url(url_original)

    host = (url.host or "").lower()
    usuario = url.username or ""

    referencias = []

    if host.startswith("db.") and host.endswith(".supabase.co"):
        referencia = host[len("db."):-len(".supabase.co")]
        if referencia:
            referencias.append(referencia)

    if usuario.startswith("postgres."):
        referencia = usuario[len("postgres."):]
        if referencia:
            referencias.append(referencia.lower())

    if not referencias:
        raise ErrorAislamiento(
            "No se pudo identificar la referencia del proyecto "
            "Supabase. No se autoriza continuar automáticamente."
        )

    if len(set(referencias)) != 1:
        raise ErrorAislamiento(
            "La referencia del host no coincide con la del usuario."
        )

    return referencias[0]


def consultar_base(nombre: str, url_original: str) -> dict:
    url = make_url(url_original)

    if url.get_backend_name() != "postgresql":
        raise ErrorAislamiento(
            f"{nombre}: el motor configurado no es PostgreSQL."
        )

    engine = create_engine(
        url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )

    try:
        with engine.connect() as conexion:
            # Todas las operaciones siguientes son de lectura.
            conexion.execute(text("SET TRANSACTION READ ONLY"))

            resultado = conexion.execute(
                text(
                    """
                    SELECT
                        current_database() AS base,
                        current_user AS usuario,
                        current_setting('server_version') AS version
                    """
                )
            ).mappings().one()

            return dict(resultado)

    finally:
        engine.dispose()


def main():
    print("=== SalesIA: aislamiento PostgreSQL ===")

    if not settings.TEST_DATABASE_URL:
        raise ErrorAislamiento(
            "TEST_DATABASE_URL no está configurada."
        )

    referencia_principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    referencia_testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    if referencia_principal == referencia_testing:
        raise ErrorAislamiento(
            "Ambas conexiones pertenecen al mismo proyecto Supabase."
        )

    print("[OK] Referencias Supabase diferentes.")

    principal = consultar_base(
        "PRINCIPAL",
        settings.DATABASE_URL,
    )

    print("[OK] Conexión principal: disponible.")

    testing = consultar_base(
        "TESTING",
        settings.TEST_DATABASE_URL,
    )

    print("[OK] Conexión testing: disponible.")

    print()
    print("Motor: PostgreSQL")
    print("Base principal:", principal["base"])
    print("Base testing:", testing["base"])
    print("Versión principal:", principal["version"])
    print("Versión testing:", testing["version"])

    print()
    print("RESULTADO: AISLAMIENTO VERIFICADO")
    print("No se realizaron operaciones de escritura.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print()
        print("RESULTADO: VERIFICACIÓN NO APROBADA")
        print("Tipo de error:", type(exc).__name__)
        print(
            "Revisa las conexiones localmente. "
            "No compartas contraseñas ni cadenas de conexión."
        )
        raise SystemExit(1)
