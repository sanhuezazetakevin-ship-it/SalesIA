# SalesIA — optimización focalizada para demo Railway

## Cambios
- Pool PostgreSQL por defecto: 2 conexiones permanentes, 1 overflow; configurable con DB_POOL_SIZE y DB_MAX_OVERFLOW. Pool pre-ping y reciclaje se mantienen.
- GZip sobre respuestas mayores o iguales a 1200 bytes cuando el cliente anuncia soporte. Puede mejorar transferencia de listados y JSON de analítica; añade costo CPU. Medir en Railway antes de afirmar una mejora.
- Benchmark HTTP en `scripts/benchmark_http_demo.py`. Solo GET, no modifica datos ni imprime el token.
- Se conservaron JWT, RBAC, rutas, modelos, consultas de negocio y protecciones de Alembic.

## Despliegue demo
- Railway Root Directory: `/backend` si está en monorepo.
- Railway variables: DATABASE_URL (Supabase TESTING), DEMO_EXPECTED_SUPABASE_REF=dotqtobseniupdycsohb, JWT_SECRET_KEY (privada), CORS_ORIGINS=https://TU-FRONT.vercel.app, ENVIRONMENT=production.
- No copies TEST_DATABASE_URL ni `.env` al servicio.
- Railway `railway.toml` usa `/health` (liveness). Comprobar `GET /ready` aparte para test de base, no cambiar automáticamente a readiness: fallos transitorios de DB podrían causar reinicios.
- HTTPS gestionado por plataformas. `VITE_API_BASE_URL` debe ser `https://...` en Vercel para evitar mixed content.
- La base de testing es solo para demostración; usar después base separada para producción.

## Benchmark
```
python -m scripts.benchmark_http_demo --base-url http://127.0.0.1:8000 --path /health --path /ready
```
En Railway, para rutas que requieren sesión: establecer `SALESIA_BENCH_TOKEN` solamente en la terminal local, y usar `--path /api/...` con una ruta GET real. No subir tokens a Git ni compartirlos. Comparar latencias p50/p95 en las mismas condiciones y sin `--reload`.

## Limitaciones
No se dispone de acceso a la BD privada ni a Railway en este entorno; las medidas SQL que suministró el usuario son la línea base, no una prueba de mejora. Ejecutar suites HTTP/JWT y multiempresa contra TESTING antes de despliegue.
