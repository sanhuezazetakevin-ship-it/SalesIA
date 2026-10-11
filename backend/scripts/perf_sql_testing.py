"""Perfil SQL de pruebas controladas con PostgreSQL TESTING.

Uso: python -m scripts.perf_sql_testing
No genera consultas nuevas y NO imprime SQL ni parámetros.
"""
from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from statistics import median
from time import perf_counter

DEFAULT_TESTS = (
    'tests/test_fase145_http_jwt_pg_real.py',
    'tests/test_fase145_integracion_pg.py',
)


def _percentile_95(values):
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[max(0, (95 * len(ordered) + 99) // 100 - 1)], 3)


class SQLProfiler:
    def __init__(self):
        self.active_test = None
        self.timings = defaultdict(list)
        self.test_times = {}
        self.errors = []
        self._test_start = None

    def pytest_runtest_call(self, item):
        self.active_test = item.nodeid
        self._test_start = perf_counter()

    def pytest_runtest_teardown(self, item, nextitem):
        self.active_test = None
        self._test_start = None

    def pytest_runtest_logreport(self, report):
        if report.when == 'call':
            self.test_times[report.nodeid] = round(report.duration * 1000, 3)
            if report.failed:
                self.errors.append(report.nodeid)

    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        context._salesia_profile_started = perf_counter()
        context._salesia_profile_test = self.active_test

    def after_cursor_execute(self, conn, cursor, statement, parameters, context, executemany):
        started = getattr(context, '_salesia_profile_started', None)
        test_id = getattr(context, '_salesia_profile_test', None)
        if started is None or test_id is None:
            return
        # Never retain SQL, bind parameters, tokens or user data.
        self.timings[test_id].append(round((perf_counter() - started) * 1000, 3))

    def handle_error(self, exception_context):
        context = exception_context.execution_context
        if context is None:
            return
        started = getattr(context, '_salesia_profile_started', None)
        test_id = getattr(context, '_salesia_profile_test', None)
        if started is not None and test_id is not None:
            self.timings[test_id].append(round((perf_counter() - started) * 1000, 3))

    def report(self):
        rows = []
        for name, duration in sorted(self.test_times.items()):
            measurements = self.timings[name]
            rows.append({
                'prueba': name,
                'duracion_test_ms': duration,
                'consultas_sql_durante_test': len(measurements),
                'sql_total_ms': round(sum(measurements), 3),
                'sql_mediana_ms': round(median(measurements), 3) if measurements else 0,
                'sql_p95_ms': _percentile_95(measurements),
                'sql_max_ms': round(max(measurements), 3) if measurements else 0,
            })
        return {'nota': 'Mediciones del cuerpo de cada test; no son latencias de produccion ni incluyen preparacion de fixtures.', 'resultados': rows, 'fallos': self.errors}


def main():
    # Validate environment separation before running any database-accessing tests.
    from app.core.config import settings
    from sqlalchemy.engine import make_url
    primary = getattr(settings, 'DATABASE_URL', None)
    testing = os.environ.get('TEST_DATABASE_URL') or getattr(settings, 'TEST_DATABASE_URL', None)
    if not primary or not testing:
        raise SystemExit('SEGURIDAD: configure DATABASE_URL y TEST_DATABASE_URL de testing.')
    a, b = make_url(str(primary)), make_url(str(testing))
    if not b.get_backend_name().startswith('postgresql'):
        raise SystemExit('SEGURIDAD: se requiere PostgreSQL de testing.')
    # URL rendering includes host/DB/username and password; compare raw normalized strings without logging.
    if a.render_as_string(hide_password=False) == b.render_as_string(hide_password=False):
        raise SystemExit('SEGURIDAD: DATABASE_URL y TEST_DATABASE_URL coinciden.')
    if (a.host, a.port, a.database, a.username) == (b.host, b.port, b.database, b.username):
        raise SystemExit('SEGURIDAD: destino principal y testing parecen el mismo. Compruebe el aislamiento.')
    import pytest
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    profiler = SQLProfiler()
    event.listen(Engine, 'before_cursor_execute', profiler.before_cursor_execute)
    event.listen(Engine, 'after_cursor_execute', profiler.after_cursor_execute)
    event.listen(Engine, 'handle_error', profiler.handle_error)
    try:
        rc = pytest.main([*DEFAULT_TESTS, '-q', '--tb=short'], plugins=[profiler])
    finally:
        event.remove(Engine, 'before_cursor_execute', profiler.before_cursor_execute)
        event.remove(Engine, 'after_cursor_execute', profiler.after_cursor_execute)
        event.remove(Engine, 'handle_error', profiler.handle_error)
    result = profiler.report()
    dest = Path('reports') / 'perf_sql_testing.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print('\nFASE14.5: perfil SQL por prueba (sin sentencias ni parametros)')
    for row in result['resultados']:
        print(f"{row['prueba']}: {row['consultas_sql_durante_test']} SQL, total={row['sql_total_ms']} ms, p95={row['sql_p95_ms']} ms")
    print(f'Informe: {dest}')
    return int(rc)


if __name__ == '__main__':
    raise SystemExit(main())
