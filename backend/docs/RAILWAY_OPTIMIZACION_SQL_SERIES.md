# SalesIA Enterprise — Optimización SQL segura para Railway

## Cambio aplicado

Servicio: `app/services/dashboard_series_service.py`.

Anteriormente, para `GET /api/dashboard/ventas/serie` se ejecutaban dos consultas: un COUNT de ventas y una transferencia de hasta 50 000 registros individuales de fecha e importe a Python.

Ahora se utiliza **una sola consulta PostgreSQL** agrupada por día/mes UTC (`timezone('UTC', created_at)` y `date_trunc`). La aplicación recibe una fila por período con COUNT y SUM, conserva los períodos sin ventas, precisión decimal, filtro obligatorio `empresa_id`, estado CONFIRMADA, RBAC existente y el límite de 50 000 ventas. La salida JSON de la API conserva su forma anterior.

La agregación del lado de la base de datos reduce filas transportadas, pero no implica necesariamente menor tiempo total cuando PostgreSQL está bajo alta carga: debe comprobarse con mediciones.

## Pruebas

```bat
python -m pytest tests/test_railway_opt_series.py tests/test_dashboard_series_calculos.py tests/test_dashboard_http_contrato.py -q --tb=short
python -m pytest tests/test_fase145_http_jwt_pg_real.py tests/test_fase145_integracion_pg.py -q --tb=short
```

Después ejecutar la regresión integral `python -m pytest tests/ -q --tb=short`.

Las pruebas de cálculo ejecutadas durante la preparación: 8 aprobadas. Las pruebas HTTP y las de PostgreSQL están pendientes en el entorno local del usuario.

## Validación real en Supabase TESTING

- Ejecutar el endpoint con un usuario autorizado real usando varios intervalos, incluido uno sin ventas y otro cruzando meses.
- Registrar latencia mediana y P95 antes y después en la misma base de datos y volumen de datos.
- Revisar `EXPLAIN (ANALYZE, BUFFERS)` únicamente con acceso autorizado a la base de testing, utilizando filtros por empresa y estado y un rango representativo de created_at.
- Si aparece secuencial scan costoso con muchas ventas, evaluar un índice compuesto sobre `(empresa_id, estado, created_at)` mediante migración revisada; no crear índices a ciegas.
- Verificar que el frontend mantenga el gráfico y los valores en PEN correctos.

## Riesgos ajenos a esta optimización

- El cuello de botella de ~811 ms corresponde a **otra ruta autenticada de notificaciones**; no se debe anunciar mejora de ese número con este parche.
- Migraciones de producción siguen deliberadamente bloqueadas por Alembic.
- Persistencia de reportes en disco local requiere almacenamiento externo antes de producción.
- Redis, ejecución distribuida y pruebas de carga concurrente no se implementan en este cambio.
