# SalesIA MVP-01-E.2 — Probabilidades HTTP

## Instalación
Copiar el contenido de `app/` y `tests/` en el backend, preservando las rutas. No reemplazar `analytics_probabilidades_calculos.py` (MVP-01-E.1).

En `app/main.py`, incorporar UNA sola vez:

```python
from app.api.routes.analytics_probabilidades import router as analytics_probabilidades_router
```

Y, después de crear `app = FastAPI(...)`, registrar UNA sola vez:

```python
app.include_router(analytics_probabilidades_router)
```

## Contrato HTTP
`GET /api/analytics/probabilidades?fecha_inicio=2026-10-01&fecha_fin=2026-10-31&umbral_importe=100.00`

JWT requerido; RBAC `ventas.ver`; empresa obtenida del usuario autenticado; incluye solo ventas `CONFIRMADA` creadas en rango inclusivo de días UTC; `umbral_importe` inclusivo; límite 367 días y 50000 ventas.

`null` en probabilidades con denominador cero; cadenas con cuatro decimales cuando están definidas. Clasifica estados de pago `PENDIENTE`, `PARCIAL`, `PAGADO`. Probabilidades descriptivas observadas (no predicciones ni garantía de pagos futuros). Sin escritura de BD y sin migraciones.

## Pruebas — solo Testing
```cmd
python -m pytest tests/test_analytics_probabilidades_integracion.py -v --tb=short
```
Para ejecutar las 63 de Analytics (54 anteriores + 9 nuevas):
```cmd
python -m pytest tests/test_analytics_calculos.py tests/test_analytics_resumen_integracion.py tests/test_analytics_distribuciones_calculos.py tests/test_analytics_distribuciones_integracion.py tests/test_analytics_probabilidades_calculos.py tests/test_analytics_probabilidades_integracion.py -q --tb=short
```

Las pruebas requieren `TEST_DATABASE_URL` configurada hacia Supabase Testing. `tests/conftest.py` debe conservar la fixture `db_testing` con rollback. No ejecutar los tests con la base principal. No compartir `.env` ni claves.
