
from sqlalchemy import text

from app.database.connection import engine


def test_connection():

    try:
        with engine.connect() as connection:

            result = connection.execute(
                text("SELECT 1")
            )

            print("================================")
            print("SALESIA ENTERPRISE")
            print("FASE 04 - POSTGRESQL")
            print("================================")

            print("Conexion PostgreSQL: OK")
            print("Resultado SELECT 1:", result.scalar())

    except Exception as error:

        print("Conexion PostgreSQL: ERROR")
        print("Detalle:", error)


if __name__ == "__main__":
    test_connection()
