"""FASE 09-D.4-C: auditoria RBAC solo lectura en Supabase Testing."""
from sqlalchemy import create_engine, text
from app.core.config import settings
from scripts.verificar_aislamiento_real import obtener_referencia_supabase

REQUERIDOS = {"pagos_proveedores.ver", "pagos_proveedores.registrar", "pagos_proveedores.anular"}
ROLES_ESPERADOS = {
    "ADMIN_EMPRESA": REQUERIDOS,
    "GERENTE": REQUERIDOS,
    "VENDEDOR": {"pagos_proveedores.ver"},
    "ALMACENERO": {"pagos_proveedores.ver"},
    "ANALISTA": {"pagos_proveedores.ver"},
}

def main():
    principal = obtener_referencia_supabase(settings.DATABASE_URL) if settings.DATABASE_URL else None
    testing = obtener_referencia_supabase(settings.TEST_DATABASE_URL) if settings.TEST_DATABASE_URL else None
    if not principal or not testing or principal == testing:
        raise RuntimeError("SEGURIDAD: aislamiento de Testing no verificado")
    print("Aislamiento Supabase: OK | Base principal: BLOQUEADA")
    engine = create_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text("SET TRANSACTION READ ONLY"))
            permisos = set(conn.execute(text("SELECT codigo FROM permisos WHERE codigo LIKE :pref"), {"pref": "pagos_proveedores.%"}).scalars())
            print("Permisos presentes:", sorted(permisos))
            empresa_id = conn.execute(text("SELECT id FROM empresas WHERE ruc=:ruc"), {"ruc": "20999999999"}).scalar_one_or_none()
            if empresa_id is None:
                raise RuntimeError("Empresa SalesIA Testing no encontrada")
            filas = conn.execute(text("""
                SELECT r.nombre, p.codigo FROM roles r
                JOIN roles_permisos rp ON rp.rol_id = r.id
                JOIN permisos p ON p.id = rp.permiso_id
                WHERE r.empresa_id = :empresa AND p.codigo LIKE :pref
            """), {"empresa": empresa_id, "pref": "pagos_proveedores.%"}).all()
            asignaciones = {}
            for nombre, codigo in filas:
                asignaciones.setdefault(nombre, set()).add(codigo)
            errores = []
            if permisos != REQUERIDOS:
                errores.append(f"Catalogo esperado {sorted(REQUERIDOS)}; real {sorted(permisos)}")
            for rol, esperado in ROLES_ESPERADOS.items():
                recibido = asignaciones.get(rol, set())
                print(f"{rol}: {sorted(recibido)}")
                if recibido != esperado:
                    errores.append(f"{rol}: esperado={sorted(esperado)}, real={sorted(recibido)}")
            total = conn.execute(text("SELECT COUNT(*) FROM permisos")).scalar_one()
            print("Permisos totales:", total)
            if total != 50:
                errores.append(f"Se esperaban 50 permisos, existen {total}")
            if errores:
                raise RuntimeError("VERIFICACION RBAC: REQUIERE REVISION\n" + "\n".join(errores))
            print("VERIFICACION RBAC PAGOS PROVEEDORES: APROBADA")
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()
