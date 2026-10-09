"""Diagnostico de catalogo RBAC de SalesIA (exclusivamente TESTING, solo lectura).

Ejecutar desde backend: python -m scripts.diagnostico_permisos_fase08
"""
from sqlalchemy import create_engine, text

from app.core.config import settings
from scripts.verificar_aislamiento_real import obtener_referencia_supabase

REQUERIDOS = (
    'pedidos.ver', 'pedidos.crear', 'pedidos.confirmar', 'pedidos.cancelar',
    'ventas.ver', 'ventas.crear', 'pagos.ver', 'pagos.registrar',
    'pagos.anular', 'entregas.ver', 'entregas.confirmar',
)


def main():
    principal_url = settings.DATABASE_URL
    testing_url = settings.TEST_DATABASE_URL
    principal = obtener_referencia_supabase(principal_url) if principal_url else None
    testing = obtener_referencia_supabase(testing_url) if testing_url else None
    if not principal or not testing or principal == testing:
        raise RuntimeError('SEGURIDAD: no se verifico el aislamiento de Supabase; ejecucion bloqueada.')

    print('=' * 58)
    print('SALESIA - DIAGNOSTICO DE PERMISOS - SOLO TESTING')
    print('=' * 58)
    print('Aislamiento Supabase: OK')
    print('Base principal: BLOQUEADA')

    engine = create_engine(testing_url, pool_pre_ping=True)
    try:
        with engine.connect() as db:
            with db.begin():
                db.execute(text('SET TRANSACTION READ ONLY'))
                resumen = {
                    'Empresas': 'SELECT COUNT(*) FROM empresas',
                    'Usuarios': 'SELECT COUNT(*) FROM usuarios',
                    'Roles': 'SELECT COUNT(*) FROM roles',
                    'Permisos en catalogo': 'SELECT COUNT(*) FROM permisos',
                    'Asignaciones de roles a usuarios': 'SELECT COUNT(*) FROM usuarios_roles',
                    'Asignaciones de permisos a roles': 'SELECT COUNT(*) FROM roles_permisos',
                }
                print('\nRESUMEN')
                for etiqueta, sql in resumen.items():
                    print(f'{etiqueta}: {db.execute(text(sql)).scalar_one()}')

                codigos = set(db.execute(text('SELECT codigo FROM permisos')).scalars().all())
                print('\nPERMISOS REQUERIDOS POR LA AUDITORIA')
                for codigo in REQUERIDOS:
                    estado = 'EXISTE' if codigo in codigos else 'AUSENTE'
                    print(f'{codigo}: {estado}')

                print('\nCATALOGO EXISTENTE (CODIGOS)')
                if codigos:
                    for codigo in sorted(codigos):
                        print(f'- {codigo}')
                else:
                    print('(vacio)')

                ausentes = sum(c not in codigos for c in REQUERIDOS)
                print('\nTotal requeridos ausentes:', ausentes)
                print('No se realizaron cambios.')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
