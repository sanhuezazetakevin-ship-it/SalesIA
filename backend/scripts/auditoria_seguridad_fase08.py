"""SalesIA Enterprise - FASE 08-G.3: auditoria de seguridad de solo lectura.

Ejecutar: python -m scripts.auditoria_seguridad_fase08
No almacena, imprime ni expone credenciales, secretos o tokens.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.security import (
    TokenInvalidoError,
    create_access_token,
    create_refresh_token,
    decode_token,
)
from scripts.verificar_aislamiento_real import obtener_referencia_supabase


CONSULTAS = {
    "Roles asignados a usuarios de otra empresa": """
        SELECT COUNT(*) FROM usuarios_roles ur
        JOIN usuarios u ON u.id = ur.usuario_id
        JOIN roles r ON r.id = ur.rol_id
        WHERE ur.empresa_id <> u.empresa_id
           OR ur.empresa_id <> r.empresa_id
    """,
    "Sesiones asociadas a otra empresa": """
        SELECT COUNT(*) FROM sesiones s
        JOIN usuarios u ON u.id = s.usuario_id
        WHERE s.empresa_id <> u.empresa_id
    """,
    "Sesiones no revocadas de usuarios inactivos": """
        SELECT COUNT(*) FROM sesiones s
        JOIN usuarios u ON u.id = s.usuario_id
        WHERE s.revocada = FALSE
          AND s.fecha_expiracion > CURRENT_TIMESTAMP
          AND u.activo = FALSE
    """,
    "Sesiones no revocadas de empresas inactivas": """
        SELECT COUNT(*) FROM sesiones s
        JOIN empresas e ON e.id = s.empresa_id
        WHERE s.revocada = FALSE
          AND s.fecha_expiracion > CURRENT_TIMESTAMP
          AND e.activo = FALSE
    """,
    "Sesiones vigentes sin rol empresarial": """
        SELECT COUNT(*) FROM sesiones s
        JOIN usuarios u ON u.id = s.usuario_id
        JOIN empresas e ON e.id = s.empresa_id
        WHERE s.revocada = FALSE
          AND s.fecha_expiracion > CURRENT_TIMESTAMP
          AND u.activo = TRUE AND e.activo = TRUE
          AND NOT EXISTS (
              SELECT 1 FROM usuarios_roles ur
              JOIN roles r ON r.id = ur.rol_id
              WHERE ur.usuario_id = u.id
                AND ur.empresa_id = s.empresa_id
                AND r.empresa_id = s.empresa_id
          )
    """,
    "Hashes de refresh token con formato invalido": """
        SELECT COUNT(*) FROM sesiones
        WHERE token_hash IS NULL
           OR token_hash !~ '^[0-9a-f]{64}$'
    """,
    "Codigos de permisos empresariales inexistentes": """
        SELECT COUNT(*) FROM (VALUES
            ('pedidos.ver'), ('pedidos.crear'), ('pedidos.confirmar'),
            ('pedidos.cancelar'), ('ventas.ver'), ('ventas.crear'),
            ('pagos.ver'), ('pagos.registrar'), ('pagos.anular'),
            ('entregas.ver'), ('entregas.confirmar')
        ) AS requerido(codigo)
        WHERE NOT EXISTS (
            SELECT 1 FROM permisos p WHERE p.codigo = requerido.codigo
        )
    """,
    "Roles sin empresa valida": """
        SELECT COUNT(*) FROM roles r
        LEFT JOIN empresas e ON e.id = r.empresa_id
        WHERE e.id IS NULL
    """,
}


def _comprobar_jwt() -> tuple[int, int]:
    """Pruebas locales en memoria; no consultan ni escriben datos."""
    identificadores = dict(usuario_id=123456, empresa_id=123456, sesion_id=123456)
    access = create_access_token(**identificadores)
    refresh = create_refresh_token(**identificadores)
    checks = 0
    errores = 0

    def comprobar(nombre, operacion, deberia_fallar=False):
        nonlocal checks, errores
        checks += 1
        try:
            operacion()
            correcto = not deberia_fallar
        except TokenInvalidoError:
            correcto = deberia_fallar
        except Exception:
            correcto = False
        if not correcto:
            errores += 1
        print(f"JWT {nombre}: {'OK' if correcto else 'FALLO'}")

    comprobar("access valido", lambda: decode_token(access, expected_type="access"))
    comprobar("refresh valido", lambda: decode_token(refresh, expected_type="refresh"))
    comprobar("refresh como access rechazado", lambda: decode_token(refresh, expected_type="access"), True)
    comprobar("access como refresh rechazado", lambda: decode_token(access, expected_type="refresh"), True)
    segmentos = access.split(".")
    firma = segmentos[2]
    firma_alterada = ("A" if firma[0] != "A" else "B") + firma[1:]
    manipulado = ".".join((segmentos[0], segmentos[1], firma_alterada))
    comprobar("firma alterada rechazada", lambda: decode_token(manipulado, expected_type="access"), True)
    payload = {
        "sub": "123456", "empresa_id": 123456, "sid": 123456,
        "type": "access", "jti": str(uuid4()),
        "iat": datetime.now(timezone.utc) - timedelta(minutes=5),
        "nbf": datetime.now(timezone.utc) - timedelta(minutes=5),
        "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
    }
    expirado = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    comprobar("expirado rechazado", lambda: decode_token(expirado, expected_type="access"), True)
    return checks, errores


def main():
    print("=" * 58)
    print("SALESIA ENTERPRISE - FASE 08-G.3")
    print("AUDITORIA DE SEGURIDAD - SOLO LECTURA")
    print("=" * 58)
    principal = obtener_referencia_supabase(settings.DATABASE_URL)
    testing_url = settings.TEST_DATABASE_URL
    testing = obtener_referencia_supabase(testing_url) if testing_url else None
    if not principal or not testing or principal == testing:
        raise RuntimeError("SEGURIDAD: aislamiento Supabase no verificado. Auditoria bloqueada.")
    print("Aislamiento Supabase: OK")
    print("Base principal: BLOQUEADA")
    print("\nVALIDACIONES JWT")
    comprobaciones_jwt, errores_jwt = _comprobar_jwt()
    print("\nVERIFICACIONES POSTGRESQL TESTING")
    engine = create_engine(testing_url, pool_pre_ping=True)
    total = 0
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET TRANSACTION READ ONLY"))
                for nombre, consulta in CONSULTAS.items():
                    cantidad = connection.execute(text(consulta)).scalar_one()
                    print(f"{nombre}: {cantidad}")
                    total += cantidad
    finally:
        engine.dispose()
    print("-" * 58)
    print(f"Consultas SQL ejecutadas: {len(CONSULTAS)}")
    print(f"Comprobaciones JWT: {comprobaciones_jwt}")
    print(f"Hallazgos SQL: {total}")
    print(f"Fallos JWT: {errores_jwt}")
    if total or errores_jwt:
        print("AUDITORIA DE SEGURIDAD: REQUIERE REVISION")
        raise SystemExit(1)
    print("AUDITORIA AUTOMATICA DE SEGURIDAD: APROBADA")
    print("Nota: esto no sustituye pruebas HTTP de acceso no autorizado ni una revision manual.")


if __name__ == "__main__":
    main()
