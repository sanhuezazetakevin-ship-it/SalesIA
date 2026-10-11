# SalesIA Enterprise — Optimización de Dashboard comercial

## Alcance
En `app/services/dashboard_comercial_service.py`, se sustituyeron las dos agregaciones separadas de KPIs del período actual y anterior por `_agregados_periodos`, que hace **una consulta PostgreSQL** con agregados `FILTER (WHERE ...)`.

No se cambiaron las rutas, respuestas, permisos, el modelo multiempresa ni la revocación de sesiones. Los rankings de productos, clientes y vendedores y los estados de pedidos siguen siendo consultas separadas. No se crearon migraciones.

## Baseline recibida
El informe `perf_http_real_testing.json` proporcionado midió `dashboard_comercial` con 11 SQL y 1455.561 ms (empresa A), y `dashboard_comercial_empresa_b` con 11 SQL y 1124.845 ms (empresa B). Son mediciones únicas con conjuntos vacíos en Supabase TESTING: **no son benchmarks de producción**.

La nueva versión está diseñada para reducir **una operación SQL por solicitud** del dashboard comercial, pero el ahorro debe comprobarse con el mismo perfilador.

## Validación en Windows
1. Respaldar backend y conservar `.env` y `TEST_DATABASE_URL` separado de la base principal.
2. Ejecutar: `python -m pytest tests/test_railway_opt_dashboard_periodos.py tests/test_dashboard_comercial_calculos.py tests/test_dashboard_comercial_http.py -q --tb=short`
3. Ejecutar las pruebas JWT/multiempresa: `python -m pytest tests/test_fase145_http_jwt_pg_real.py tests/test_fase145_integracion_pg.py -q --tb=short`
4. Ejecutar: `python -m scripts.perf_http_real_testing`
5. Comparar `reports/perf_http_real_testing.json` con la línea base de 11 operaciones SQL para Dashboard comercial. Si cambia cualquier KPI entre versiones para los mismos datos, no desplegar.
6. Antes de Railway producción, ejecutar la regresión integral y validar las migraciones/almacenamiento de reportes.

## Limitaciones
Las pruebas unitarias locales no conectan a Supabase. Se aprobaron 8 pruebas del nuevo cálculo y las funciones de cálculo existentes con variables de entorno de prueba ficticias. El endpoint completo, la equivalencia con ventas reales y la latencia siguen pendientes de validación en la instalación Windows.
