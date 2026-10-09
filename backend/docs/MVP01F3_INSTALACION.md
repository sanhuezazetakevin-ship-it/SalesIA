# SalesIA MVP-01-F.3 — Historial HTTP

## Alcance
Cuatro operaciones nuevas: POST /api/analytics/historial/estadisticos,
POST /api/analytics/historial/probabilidades, GET /api/analytics/historial,
GET /api/analytics/historial/{tipo}/{analisis_id}.

Lectura: conserva `ventas.ver` por compatibilidad con `analytics_historial_service.py`.
Escritura: exige adicionalmente `analitica.ejecutar` (permiso existente en el seed).
Resultados recalculados en el servidor. El cuerpo POST solo admite nombres, fechas y umbral.

## Instalación
Copiar `app/` y `tests/` a la raíz backend, preservando archivos existentes.
No sustituir `analytics_historial_service.py` ni modelos.

Agregar en `app/main.py`:
```python
from app.api.routes.analytics_historial import router as analytics_historial_router
```
Luego de crear `app`:
```python
app.include_router(analytics_historial_router)
```

## Ejecutar por etapas
```cmd
python -m pytest tests/test_analytics_historial_http_contrato.py -q --tb=short
python -m pytest tests/test_analytics_historial_validaciones.py tests/test_analytics_historial_postgres.py tests/test_analytics_historial_http_contrato.py -q --tb=short
```
Objetivo 35 pruebas (21+8+6); todavía hace falta prueba HTTP real con JWT y Testing.

## Consideraciones
- `analitica.ejecutar` ya existe en CATALOGO, pero verificar asignaciones efectivas en Testing.
- No usar contra producción antes de ejecutar las pruebas HTTP reales de JWT/RBAC/multiempresa.
- El servicio interno aún usa `ventas.ver` para guardar. La frontera HTTP refuerza RBAC; antes de abrir otros canales de escritura, centralizar el control de `analitica.ejecutar` dentro del servicio sin romper pruebas antiguas.
- El usuario ejecutor se almacena dentro de JSON, no en columna FK propia.
- Los POST efectúan `commit`: en pruebas, depender de la fixture transaccional `db_testing` con rollback externo y overrides de FastAPI.
- La lista limita a 100 filas; aún no incorpora paginación cursor.
