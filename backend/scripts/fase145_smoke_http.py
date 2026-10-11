"""Medición de rutas públicas y denegación de rutas privadas sin credenciales.
No requiere conexiones a PostgreSQL; NO representa una prueba de carga.
"""
from time import perf_counter
from statistics import median
from fastapi.testclient import TestClient
from app.main import app

RUTAS_PROTEGIDAS = (
    '/api/mejoras/notificaciones-persistentes',
    '/api/mejoras/dashboard?fecha_inicio=2026-01-01&fecha_fin=2026-01-31',
    '/api/analytics/semana08?fecha_inicio=2026-01-01&fecha_fin=2026-01-31',
)

def ejecutar(n=20):
    with TestClient(app) as client:
        for ruta in RUTAS_PROTEGIDAS:
            tiempos=[]; estados=set()
            for _ in range(n):
                comienzo=perf_counter(); r=client.get(ruta); tiempos.append((perf_counter()-comienzo)*1000);estados.add(r.status_code)
            print(f'{ruta}: estados={sorted(estados)}, mediana_ms={median(tiempos):.2f}, max_ms={max(tiempos):.2f}')
            if any(s not in (401,403) for s in estados):
                raise RuntimeError(f'Una ruta privada respondió sin rechazar credenciales: {ruta}')

if __name__=='__main__': ejecutar()
