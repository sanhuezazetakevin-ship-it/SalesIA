"""Medición HTTP real, estrictamente sobre PostgreSQL TESTING.

Los datos temporales usan db_testing y rollback; las métricas solo miden el
intervalo client.get(), sin incluir preparación de empresas, usuario o JWT.
"""
from __future__ import annotations

import json
from pathlib import Path
from statistics import median
from time import perf_counter

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine

from app.api.routes.analytics import router as analytics_router
from app.api.routes.dashboard import router as dashboard_router
from app.api.routes.notificaciones145 import router as notificaciones_router
from app.database.connection import get_db
from tests.test_fase145_http_jwt_pg_real import _empresa, _identidad, _headers


def _capturar_peticion(client, url, headers):
    medidas = []
    def before(conn, cursor, statement, parameters, context, executemany):
        context._fase145_inicio = perf_counter()
    def after(conn, cursor, statement, parameters, context, executemany):
        start = getattr(context, '_fase145_inicio', None)
        if start is not None:
            medidas.append((perf_counter() - start) * 1000)
    event.listen(Engine, 'before_cursor_execute', before)
    event.listen(Engine, 'after_cursor_execute', after)
    try:
        inicio = perf_counter()
        respuesta = client.get(url, headers=headers)
        duracion = (perf_counter() - inicio) * 1000
    finally:
        event.remove(Engine, 'before_cursor_execute', before)
        event.remove(Engine, 'after_cursor_execute', after)
    assert respuesta.status_code == 200, f'{url}: HTTP {respuesta.status_code}: {respuesta.text[:400]}'
    return {
        'http_estado': respuesta.status_code,
        'http_ms': round(duracion, 3),
        'sql_cantidad': len(medidas),
        'sql_total_ms': round(sum(medidas), 3),
        'sql_mediana_ms': round(median(medidas), 3) if medidas else 0,
        'sql_max_ms': round(max(medidas), 3) if medidas else 0,
    }


def test_perfil_http_real_multiempresa(db_testing):
    """JWT/RBAC auténticos; solo se sustituye get_db con la sesión testing."""
    empresa_a = _empresa(db_testing)
    empresa_b = _empresa(db_testing)
    _, _, token_a = _identidad(db_testing, empresa_a.id, True)
    _, _, token_b = _identidad(db_testing, empresa_b.id, True)
    app = FastAPI()
    for router in (dashboard_router, analytics_router, notificaciones_router):
        app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db_testing
    rutas = {
        'dashboard_comercial': '/api/dashboard/comercial?fecha_inicio=2026-01-01&fecha_fin=2026-01-31',
        'dashboard_serie': '/api/dashboard/ventas/serie?fecha_inicio=2026-01-01&fecha_fin=2026-01-31',
        'analytics_resumen': '/api/analytics/resumen?fecha_inicio=2026-01-01&fecha_fin=2026-01-31',
        'notificaciones': '/api/mejoras/notificaciones-persistentes?limite=20',
    }
    medidas = {}
    try:
        with TestClient(app) as client:
            for nombre, url in rutas.items():
                medidas[nombre] = _capturar_peticion(client, url, _headers(token_a))
            # Garantizar que las mismas rutas se ejecutan con la identidad B.
            # No se compara contenido monetario inventado; ambas empresas de
            # prueba carecen de ventas y no deben compartir notificaciones.
            for nombre, url in rutas.items():
                medidas[nombre + '_empresa_b'] = _capturar_peticion(client, url, _headers(token_b))
            sin_credenciales = client.get(rutas['notificaciones'])
            assert sin_credenciales.status_code == 401
    finally:
        app.dependency_overrides.clear()
    resultado = {
        'descripcion': 'Solicitudes reales TestClient + JWT + RBAC + PostgreSQL TESTING, con datos vacíos por empresa',
        'advertencia': 'No es una prueba de carga ni mide datos comerciales voluminosos o Railway en producción',
        'mediciones': medidas,
    }
    destino = Path('reports/perf_http_real_testing.json')
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\nPERFIL HTTP REAL TESTING (SQL por petición, sin SQL/credenciales):')
    for nombre, valor in medidas.items():
        print(f"{nombre}: HTTP={valor['http_estado']}, sql={valor['sql_cantidad']}, sql_ms={valor['sql_total_ms']}, http_ms={valor['http_ms']}")
    print('Informe:', destino)
