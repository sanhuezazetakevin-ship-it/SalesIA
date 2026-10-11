# SalesIA Enterprise — Perfil HTTP real por módulo (Railway)

## Propósito
Los tres perfiles previos medían SQL dentro del cuerpo de tests, mezclando preparación de fixtures con ejecución de endpoints. El dashboard obtuvo 0 SQL porque sus casos emplean mocks. Esta entrega NO afirma que eso signifique 0 consultas reales.

## Cambios
- `tests/test_railway_perfil_http_real.py`: usa JWT firmado, sesiones y RBAC reales. Genera dos empresas aisladas en la sesión de PostgreSQL de testing; únicamente reemplaza `get_db` para usar la fixture segura `db_testing`, con rollback.
- `scripts/perf_http_real_testing.py`: verifica que las URLs de testing y principal no coinciden antes de comenzar.
- Mide SQL por petición HTTP (`client.get()`) para dashboard comercial, series temporales, resumen Analytics y notificaciones, para cada una de las dos empresas.
- Guarda solo número/duración de SQL y tiempo HTTP, nunca consultas, parámetros, hashes, tokens ni secretos.

## Ejecución
Desde la raíz del backend:

```cmd
python -m scripts.perf_http_real_testing
```

Resultado JSON: `reports/perf_http_real_testing.json`. Si el comando falla, envía el traceback; NO uses los valores del reporte anterior como nueva medición ni copies credenciales.

## Precauciones
1. Confirma `TEST_DATABASE_URL` separado de `DATABASE_URL`; la fixture verifica aislamiento Supabase y revierte los datos.
2. El reporte registra escenario sin ventas, por lo que no representa el coste de grandes volúmenes de datos; repetir sobre datos de prueba de tamaño controlado antes de ajustar índices.
3. Los tiempos provienen de `TestClient` local y Supabase de testing, no de Railway ni de usuarios concurrentes.
4. La medición requiere que los tests devuelvan HTTP 200. Si algo devuelve 403/422/500, primero corregir permisos o contratos; no reportar tiempos como exitosos.
5. Las rutas no escriben producción; la única conexión utilizada para los tests autorizados es la fixture `db_testing`.
6. No ejecutar regresión integral hasta analizar este informe.
