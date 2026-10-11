"""Perfil SQL de suites existentes en PostgreSQL TESTING.

Ejecutar desde raíz: python -m scripts.perf_modulos_testing --modulo analytics
No recoge SQL, parámetros, credenciales ni datos personales.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from sqlalchemy.engine import make_url

from scripts.perf_sql_testing import SQLProfiler

SUITES = {
    'analytics': (
        'tests/test_analytics_resumen_integracion.py',
        'tests/test_analytics_distribuciones_integracion.py',
        'tests/test_analytics_probabilidades_integracion.py',
    ),
    'dashboard': (
        'tests/test_dashboard_comercial_http.py',
        'tests/test_dashboard_http_contrato.py',
        'tests/test_railway_opt_series.py',
    ),
    'notificaciones': (
        'tests/test_fase145_http_jwt_pg_real.py',
        'tests/test_fase145_integracion_pg.py',
    ),
}


def verificar_testing():
    from app.core.config import settings
    primary = getattr(settings, 'DATABASE_URL', None)
    testing = os.environ.get('TEST_DATABASE_URL') or getattr(settings, 'TEST_DATABASE_URL', None)
    if not primary or not testing:
        raise RuntimeError('Se requieren DATABASE_URL y TEST_DATABASE_URL independientes.')
    a, b = make_url(str(primary)), make_url(str(testing))
    if not b.get_backend_name().startswith('postgresql'):
        raise RuntimeError('La URL de testing debe ser PostgreSQL.')
    if a.render_as_string(hide_password=False) == b.render_as_string(hide_password=False):
        raise RuntimeError('Las URL principal y testing coinciden.')
    if (a.host, a.port, a.database, a.username) == (b.host, b.port, b.database, b.username):
        raise RuntimeError('Principal y testing parecen apuntar al mismo destino.')


def ejecutar(modulo):
    verificar_testing()
    import pytest
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    paths = SUITES[modulo]
    missing = [p for p in paths if not Path(p).is_file()]
    if missing:
        raise RuntimeError('Faltan tests: ' + ', '.join(missing))
    profiler = SQLProfiler()
    listeners = [
        ('before_cursor_execute', profiler.before_cursor_execute),
        ('after_cursor_execute', profiler.after_cursor_execute),
        ('handle_error', profiler.handle_error),
    ]
    for name, fn in listeners:
        event.listen(Engine, name, fn)
    try:
        rc = pytest.main([*paths, '-q', '--tb=short', '-rs'], plugins=[profiler])
    finally:
        for name, fn in listeners:
            event.remove(Engine, name, fn)

    output = profiler.report()
    output['modulo'] = modulo
    output['nota_adicional'] = ('Perfil del cuerpo de pruebas. Incluye SQL de preparación dentro del test; '
                                'algunos tests de dashboard usan mocks y no miden su consulta real. '
                                'No representa latencia de Railway en producción.')
    dest = Path('reports') / f'perf_{modulo}_testing.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nPERFIL {modulo}: {sum(r["consultas_sql_durante_test"] for r in output["resultados"])} operaciones SQL medidas')
    for row in output['resultados']:
        print(f'{row["prueba"]}: SQL={row["consultas_sql_durante_test"]}, '
              f'tiempo_sql_ms={row["sql_total_ms"]}, p95_ms={row["sql_p95_ms"]}')
    print(f'Informe: {dest}')
    return int(rc)


def main():
    parser = argparse.ArgumentParser(description='Perfilado SQL controlado de SalesIA.')
    parser.add_argument('--modulo', choices=sorted(SUITES), required=True)
    args = parser.parse_args()
    return ejecutar(args.modulo)


if __name__ == '__main__':
    raise SystemExit(main())
