
"""
SalesIA Enterprise
FASE 05-F.5D

Auditoria de solo lectura de permisos globales
en PostgreSQL Testing.
"""

from sqlalchemy import create_engine, select, func

from app.core.config import settings
from app.models.permiso import Permiso

from scripts.verificar_aislamiento_real import (
    obtener_referencia_supabase,
)


def main():
    if not settings.TEST_DATABASE_URL:
        raise RuntimeError(
            "SEGURIDAD: TEST_DATABASE_URL no configurada."
        )

    principal = obtener_referencia_supabase(
        settings.DATABASE_URL
    )

    testing = obtener_referencia_supabase(
        settings.TEST_DATABASE_URL
    )

    if not principal or not testing or principal == testing:
        raise RuntimeError(
            "SEGURIDAD: aislamiento de Testing no verificado."
        )

    engine = create_engine(
        settings.TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as conexion:
            cantidad = conexion.scalar(
                select(func.count(Permiso.id))
            )

            codigos = conexion.scalars(
                select(Permiso.codigo).order_by(Permiso.codigo)
            ).all()

            print("=== Auditoria de permisos TESTING ===")
            print("Permisos globales existentes:", cantidad)

            if codigos:
                print("Codigos existentes:")
                for codigo in codigos:
                    print("-", codigo)
            else:
                print("No existen permisos globales.")

            print("AUDITORIA DE SOLO LECTURA COMPLETADA.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
