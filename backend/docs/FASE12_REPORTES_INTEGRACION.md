# SalesIA Enterprise — FASE 12: Reportes

## Contrato REST

Base: `/api/reportes`. Incluir `Authorization: Bearer <access_token>` en **todas** las peticiones.

- `GET /previsualizar?tipo=VENTAS&fecha_inicio=2026-01-01&fecha_fin=2026-01-31&limite=100`: respuesta JSON con columnas, filas y cantidad total.
- `POST /generar?tipo=VENTAS&formato=CSV&fecha_inicio=2026-01-01&fecha_fin=2026-01-31`: crea un registro en `reportes_generados` y un archivo privado, responde 201 con `id`.
- `GET /`: historial del tenant, paginado por límite (máximo 100).
- `GET /{reporte_id}`: detalle del registro, incluye parámetros de creación.
- `GET /{reporte_id}/descargar`: descarga binaria (usar `response.blob()` en frontend).
- `GET /imprimible?tipo=VENTAS&fecha_inicio=2026-01-01&fecha_fin=2026-01-31`: HTML para imprimir; debe solicitarse mediante `fetch` autenticado y mostrarse en contexto aislado. No usar iframe sin sanitizar ni inyectar HTML en la app.

**Tipos:** `VENTAS`, `ESTADISTICO`, `INVENTARIO` (productos vendidos, **NO** inventario físico), `CLIENTES`, `RENDIMIENTO` (vendedores identificados por `usuario_id`). **Formatos:** `CSV`, `XLSX`, `PDF`. Fechas inclusivas UTC. Solo ventas `CONFIRMADA`. Moneda PEN (conforme al módulo de dashboard ya existente).

## Seguridad

- `reportes.ver`: previsualizar, listar, detalle, imprimible.
- `reportes.generar`: generar CSV/XLSX/PDF.
- `reportes.descargar`: descargar.
- `empresa_id` siempre se deriva de JWT/sesión y no se acepta como parámetro.
- Se restringen períodos a un máximo de 367 días y resultados a 50 000 filas.
- Los archivos se guardan en `SALESIA_REPORT_DIR` (por defecto `reports/generated`). El directorio **debe** estar fuera del directorio público del servidor; persistirlo en un volumen privado para Railway/u otro proveedor; no subir reportes reales a Git.
- No es un sustituto de almacenamiento de objetos para producción multiinstancia. En producción con réplicas, integrar S3/Supabase Storage privado y descargas firmadas autorizadas.
- No se incluyen datos personales sensibles adicionales (p. ej. DNI/email) en el reporte de clientes.

## Verificaciones frontend

1. Usuario sin token: 401.
2. Usuario sin permisos: 403.
3. Rango inválido: 422; fechas válidas sin ventas: reporte con encabezados.
4. Confirmar que un usuario de empresa B no accede a un reporte generado por empresa A (404).
5. Generar/descargar cada uno de CSV, XLSX y PDF; comprobar contenido, extensión y MIME.
6. Comprobar vista imprimible sin ejecutar contenido malicioso proveniente de nombres de clientes/productos.
7. Probar descarga después de reiniciar el servidor, desde el volumen persistente.

## Comandos

```cmd
python -m pytest tests/test_reportes_fase12.py -q --tb=short
python -m pytest tests/ -q --tb=short
```

Para exportar XLSX, instalar `openpyxl`; para PDF, `reportlab`. Configurar `SALESIA_REPORT_DIR` en el entorno de ejecución. No reemplazar `.env` ni credenciales.
