"""Validación del catálogo de proveedores: solo lectura en Supabase TESTING."""
from sqlalchemy import create_engine, text
from app.core.config import settings
from scripts.verificar_aislamiento_real import obtener_referencia_supabase

REQUERIDOS = {'proveedores.ver', 'proveedores.crear', 'proveedores.editar'}
ROLES_ESPERADOS = {
    'ADMIN_EMPRESA': REQUERIDOS,
    'GERENTE': REQUERIDOS,
    'VENDEDOR': {'proveedores.ver'},
    'ALMACENERO': {'proveedores.ver'},
    'ANALISTA': {'proveedores.ver'},
}

def main():
    p = obtener_referencia_supabase(settings.DATABASE_URL) if settings.DATABASE_URL else None
    t = obtener_referencia_supabase(settings.TEST_DATABASE_URL) if settings.TEST_DATABASE_URL else None
    if not p or not t or p == t:
        raise RuntimeError('SEGURIDAD: aislamiento de Testing no verificado')
    print('Aislamiento Supabase: OK | Base principal: BLOQUEADA')
    engine = create_engine(settings.TEST_DATABASE_URL, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            conn.execute(text('SET TRANSACTION READ ONLY'))
            permisos = set(conn.execute(text('SELECT codigo FROM permisos WHERE codigo LIKE :pref'), {'pref': 'proveedores.%'}).scalars())
            print('Permisos presentes:', sorted(permisos))
            faltantes = REQUERIDOS - permisos
            empresa = conn.execute(text('SELECT id FROM empresas WHERE ruc=:ruc'), {'ruc': '20999999999'}).scalar_one_or_none()
            if empresa is None:
                raise RuntimeError('Empresa SalesIA Testing no encontrada (RUC 20999999999)')
            rows = conn.execute(text("SELECT r.nombre, p.codigo FROM roles r JOIN roles_permisos rp ON rp.rol_id = r.id JOIN permisos p ON p.id = rp.permiso_id WHERE r.empresa_id = :empresa AND p.codigo LIKE :pref"),
                {'empresa': empresa, 'pref': 'proveedores.%'}).all()
            asignaciones = {}
            for rol,permiso in rows:
                asignaciones.setdefault(rol,set()).add(permiso)
            errores = []
            for rol, esperado in ROLES_ESPERADOS.items():
                recibido = asignaciones.get(rol,set())
                print(f'{rol}: {sorted(recibido)}')
                if recibido != esperado:
                    errores.append(f'{rol}: esperado={sorted(esperado)}, real={sorted(recibido)}')
            if faltantes or errores:
                print('Faltantes:',sorted(faltantes),'Errores:',errores)
                raise SystemExit('VERIFICACION RBAC: REQUIERE REVISION')
            print('VERIFICACION RBAC: APROBADA')
    finally:
        engine.dispose()
if __name__ == '__main__':
    main()
