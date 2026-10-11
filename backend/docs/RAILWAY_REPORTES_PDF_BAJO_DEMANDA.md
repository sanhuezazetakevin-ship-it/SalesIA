# SalesIA — PDF visual bajo demanda (Railway)

Ruta nueva: `GET /api/reportes/pdf-directo?tipo=VENTAS&fecha_inicio=2026-01-01&fecha_fin=2026-01-31`.

Tipos: `VENTAS`, `ESTADISTICO`, `INVENTARIO` (productos vendidos), `CLIENTES`, `RENDIMIENTO`.

- JWT y permiso `reportes.generar` obligatorios. El servidor deriva el tenant del usuario, nunca de un parámetro externo.
- Devuelve bytes PDF (`application/pdf`, `Content-Disposition: attachment`). El frontend puede abrir el Blob o activar descarga.
- Se genera en memoria con ReportLab; no hay escritura al disco de Railway ni se crea un registro de archivo en `reportes_generados`.
- Incluye resumen de ventas confirmadas, gráfico vectorial de barras y explicación sencilla, con datos vacíos tratados explícitamente.
- Limita el rango a 367 días mediante la misma validación de reportes, y los grupos graficados a 8 (13 meses como máximo).
- Conserva rutas previas de FASE 12 para no romper el frontend. **Estas rutas anteriores siguen almacenando archivos en disco** y no son aptas para descarga persistente sin almacenamiento adicional. Migrar el botón del frontend a `pdf-directo`.
- En el navegador, petición autorizada -> `const blob = await response.blob(); const url = URL.createObjectURL(blob); ... URL.revokeObjectURL(url)`.
- No se realizan predicciones; el gráfico de inventario representa *unidades vendidas*, no existencias actuales.
- Para Railway: habilitar CORS únicamente para el origen Vercel autorizado, configurar Supabase y limitar generación concurrente/intervalos según carga.

## Pruebas

`python -m pytest tests/test_reportes_pdf_directo.py tests/test_reportes_fase12.py -q --tb=short`

`python -m pytest tests/test_fase145_http_jwt_pg_real.py tests/test_fase145_integracion_pg.py -q --tb=short`

Regresión integral antes del despliegue: `python -m pytest tests/ -q --tb=short`.

## Limitaciones

Reporte ejecutivo resumido; no sustituye exportaciones exhaustivas CSV/XLSX. Se deben validar las métricas con datos reales representativos en PostgreSQL testing y comprobar carga de PDF concurrente. El contenido depende de las transacciones confirmadas y no se conserva para re-descarga idéntica.
