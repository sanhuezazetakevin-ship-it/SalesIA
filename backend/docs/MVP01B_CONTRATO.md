# SalesIA Enterprise — MVP-01-B, contrato analítico v0.1

## Instalación
Copiar `app/services/analytics_resumen_service.py`, `app/schemas/analytics_resumen.py`,
`app/api/routes/analytics.py` y `tests/test_analytics_calculos.py` a las rutas indicadas.
En `app/main.py` agregar:

```python
from app.api.routes.analytics import router as analytics_router
app.include_router(analytics_router)
```

No cambiar otras líneas. Ejecutar desde `backend`:

```cmd
python -m pytest tests/test_analytics_calculos.py -q
python -m pytest tests/ -q --tb=short
```

## GET /api/analytics/resumen
Bearer JWT obligatorio. Permiso existente `ventas.ver` (temporal para MVP inicial).
Parámetros obligatorios `fecha_inicio` y `fecha_fin`, formato ISO `YYYY-MM-DD`.
Regla: fecha de `ventas.created_at` en **UTC**, inicio inclusivo y fin inclusivo por fecha,
implementado como límite superior exclusivo al día siguiente. Rango máximo 367 días.
Solo ventas con `estado='CONFIRMADA'`. Se incluye una venta aunque tenga pago pendiente:
`total_ventas` expresa **ventas**, NO cobros, ingresos de caja ni utilidades.
No se incluyen ventas REGISTRADA ni CANCELADA. Moneda PEN asumida para el MVP.
Aislamiento por `empresa_id` obtenido del usuario validado con JWT, nunca recibido del navegador.

Respuesta `200`:
```json
{"periodo":{"fecha_inicio":"2026-10-01","fecha_fin":"2026-10-31"},
 "moneda":"PEN","criterio_estado":"CONFIRMADA","zona_horaria":"UTC",
 "cantidad_ventas":3,"total_ventas":"120.00", "ticket_promedio":"40.00","mediana_ventas":"20.00"}
```
Sin ventas: cantidad=0, total='0.00', promedio y mediana `null`.
401 sin JWT / JWT inválido o sesión vencida; 403 sin permiso; 422 fechas inválidas o límite excedido.
Límite de seguridad de 50000 ventas por consulta: no se devuelve una media parcial.

## Pendientes para bloques siguientes
- Pruebas HTTP de auth/RBAC y consultas reales con `db_testing` + comparación multiempresa.
- Analizar impacto de timezone empresarial configurable y diferentes monedas.
- Agregación SQL paginada o percentile_cont para volúmenes superiores.
- Histórico en `analisis_estadisticos`, variables estadísticas y Teorema de Bayes.
- Acordar permiso específico `analytics.ver` y migración/seed si cambia matriz RBAC.
- No ejecutar migraciones ni scripts de escritura en base principal.
