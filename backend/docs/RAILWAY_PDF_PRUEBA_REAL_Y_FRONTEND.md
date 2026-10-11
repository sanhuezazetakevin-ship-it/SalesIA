# SalesIA Enterprise — Prueba PDF real y conexión React/Railway

## Pruebas previas (usar únicamente la base de TESTING)

El archivo `tests/test_railway_pdf_http_pg_real.py` ejecuta dos pruebas integradas:
- JWT firmado y sesión reales, permisos RBAC y empresa derivada del usuario.
- Genera ventas confirmadas y canceladas de dos empresas y descarga el PDF de cada una.
- Comprueba total correcto, contenido PDF, descarga privada, falta de JWT, rango inválido, ausencia de permiso, separación de empresas y que no se creen registros en `reportes_generados`.
- Usa `db_testing`, que exige `TEST_DATABASE_URL` distinto de `DATABASE_URL`, y rollback al finalizar.
- Si está instalado `pypdf`, comprueba también texto extraído del documento. No es obligatorio para el backend.

```
python -m pytest tests/test_railway_pdf_http_pg_real.py -q --tb=short -rs
python -m scripts.railway_pdf_release_check
python -m scripts.railway_preflight
```

Tras superarlas, realizar prueba real en Railway *staging* antes de habilitar producción; no reutilizar credenciales de producción en pruebas. La regresión integral de 664 pruebas fue comunicada para la versión previa; repetirla si se cambia código de negocio.

## Contrato React (fetch)

`GET /api/reportes/pdf-directo?tipo=VENTAS&fecha_inicio=2026-10-01&fecha_fin=2026-10-31`

`tipo`: `VENTAS`, `ESTADISTICO`, `INVENTARIO` (productos vendidos, no existencias actuales), `CLIENTES`, `RENDIMIENTO`.

- Header: `Authorization: Bearer <access_token>`.
- 200: `application/pdf` + `Content-Disposition: attachment` + `Cache-Control: private, no-store`.
- 401: token ausente/inválido. 403: permiso insuficiente. 422: fechas inválidas (también rangos superiores a 367 días).
- No enviar `empresa_id`; el backend lo deriva del JWT y PostgreSQL.

```ts
export async function descargarReportePdf(
  apiBaseUrl: string,
  accessToken: string,
  tipo: 'VENTAS' | 'ESTADISTICO' | 'INVENTARIO' | 'CLIENTES' | 'RENDIMIENTO',
  fechaInicio: string,
  fechaFin: string,
): Promise<void> {
  const params = new URLSearchParams({ tipo, fecha_inicio: fechaInicio, fecha_fin: fechaFin });
  const response = await fetch(`${apiBaseUrl.replace(/\/$/, '')}/api/reportes/pdf-directo?${params}`, {
    method: 'GET',
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: 'no-store',
  });
  if (!response.ok) {
    throw new Error(`No se pudo generar el reporte. HTTP ${response.status}`);
  }
  const contentType = response.headers.get('content-type') || '';
  if (!contentType.includes('application/pdf')) throw new Error('El servidor no devolvió un PDF');
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = `SalesIA_${tipo}_${fechaInicio}_${fechaFin}.pdf`;
    document.body.appendChild(link);
    link.click();
    link.remove();
  } finally {
    setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
  }
}
```

En el botón React, bloquear doble clic mientras carga, mostrar error legible y usar el token de la sesión ya autenticada; no guardarlo en URL ni imprimirlo. El endpoint no guarda PDF para descarga posterior idéntica.

## Railway — criterios operativos

- Configurar origen HTTPS exacto de Vercel en `CORS_ORIGINS`; no usar `*` en producción.
- `DATABASE_URL` Supabase y `JWT_SECRET_KEY` como secretos en Railway. No subir `.env` al repositorio/ZIP.
- `ENVIRONMENT=production` y `PORT` proporcionado por Railway; inicio con `uvicorn app.main:app` y endpoint `/health`.
- Migraciones Alembic: revisión y ejecución explícitas, nunca automáticas al iniciar el contenedor.
- No programar generación masiva/concurrente sin límites; medir RAM y tiempo con PDFs de períodos máximos.
- Endpoints antiguos de FASE 12 mantienen almacenamiento en disco. El frontend debe usar `/pdf-directo` para evitarlo.
- El preflight es estático: no prueba conexión a Supabase, infraestructura Railway, ni volumen de ventas alto.
