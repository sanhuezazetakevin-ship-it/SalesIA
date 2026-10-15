# SalesIA — Railway demo con Supabase TESTING

## Alcance de esta entrega

Se preserva el backend multiempresa de la version final y su frontend **como referencia**, sin reemplazar el frontend que el companero esta disenando. No se incluyen seeds masivos, credenciales, ni artefactos de reportes.

## Configuracion Railway

- Root directory: `/backend`.
- Mantener `railway.toml` con 1 worker y healthcheck ligero `/health`.
- `DATABASE_URL`: la cadena exacta de Supabase TESTING (obtener de gestor seguro, nunca subir `.env`).
- `DEMO_EXPECTED_SUPABASE_REF=dotqtobseniupdycsohb`: aborta el arranque si DATABASE_URL apunta a otro proyecto de Supabase.
- `ENVIRONMENT=production`: valida HTTPS en CORS; la base de datos sigue siendo TESTING.
- `JWT_SECRET_KEY`: secreto de al menos 32 caracteres distinto al usado en desarrollo.
- `SALESIA_PLATFORM_ADMIN_EMAILS`: el correo de operador existente en TESTING.
- `CORS_ORIGINS=https://NOMBRE.vercel.app` (separar varios origenes con comas, sin barras finales).
- `DB_POOL_SIZE=2`, `DB_MAX_OVERFLOW=1`, `DB_POOL_TIMEOUT=30` como valores iniciales conservadores.
- No ejecutar scripts de seed ni `alembic upgrade` automaticamente desde Railway.

## Frontend Vercel

- `VITE_API_BASE_URL=https://NOMBRE.up.railway.app` (sin barra final, NO localhost).
- Hacer build/redeploy tras cambiar variables Vite. Nunca usar HTTP desde frontend HTTPS.
- El frontend del companero requiere comparar contratos API y unir cambios de UX antes del deploy final.

## Diagnostico

- GET `/health`: proceso FastAPI arriba, sin depender de DB.
- GET `/ready`: realiza `SELECT 1` en PostgreSQL; devuelve 503 si falla la conexion.
- GET `/openapi.json`: la aplicacion publica rutas; puede cerrarse para produccion posteriormente.
- Verificar OPTIONS preflight con origen Vercel y encabezado Authorization.
- Revisar 401/403/404 distinguiendolos de 500/CORS; los 403/404 para recursos ajenos son esperados.

## Verificaciones antes de la exposicion

1. Ejecutar tests focalizados con DATABASE_URL principal y TEST_DATABASE_URL testing **distintos** en consola exclusiva.
2. Desplegar servicio Railway desde branch estable; confirmar `/health` y `/ready` en 200.
3. Iniciar sesion para cada empresa, consultar dashboard y probar JWT cruzado; 403/404.
4. Suspender/reactivar una empresa y verificar 401/403 en requests protegidas.
5. Medir latencias reales en Railway y observar CPU/memoria/tiempos SQL. No afirmar optimizacion de velocidad sin medidas antes/despues.

## Observaciones de auditoria

- No se realizo benchmark contra Supabase externo ni build completo de Vite en este entorno.
- Los paquetes pesados `scipy`, `openpyxl`, `reportlab` siguen en requirements por compatibilidad. Optimizar su instalacion exige ensayos de endpoints afectados.
- Tokens en localStorage implican riesgo ante XSS: evitar HTML no confiable y revisar CSP antes de abrir a clientes reales.
- La migracion automatica a la base principal permanece bloqueada en Alembic por diseno.
