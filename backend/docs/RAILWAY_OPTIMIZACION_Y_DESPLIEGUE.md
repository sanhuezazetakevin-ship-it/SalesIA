# SalesIA Enterprise — Railway: paquete conservador de preparación

## Modificaciones realizadas
- Dependencias añadidas: SciPy (Semana 08), openpyxl (Excel) y ReportLab (PDF).
- Python 3.13 fijado en `.python-version` (coincide con el entorno de pruebas informado).
- `railway.toml`: un worker Uvicorn, puerto dinámico `PORT`, health check `/health`.
- Pool SQLAlchemy limitado y configurable: `DB_POOL_SIZE=5`, `DB_MAX_OVERFLOW=5`, `DB_POOL_TIMEOUT=30`, `pool_use_lifo`.
- `.env.example`, exclusiones de secretos en Git y archivos generados; script de preflight.
- Mantiene intactos los endpoints, permisos y la selección de DB en Alembic.

## Validación en Windows
```
python -m scripts.railway_preflight
python -m pytest tests/test_railway_packaging.py -q
python -m pytest tests/test_fase145_http_jwt_pg_real.py tests/test_fase145_integracion_pg.py -q --tb=short
python -m pytest tests/ -q --tb=short
```

## Variables de Railway
Configurar `DATABASE_URL`, `JWT_SECRET_KEY` (aleatoria >=32 caracteres), `ENVIRONMENT=production`, `CORS_ORIGINS` (URL HTTPS de Vercel), `JWT_ALGORITHM=HS256`; opcional `DB_POOL_SIZE`, `DB_MAX_OVERFLOW`, `DB_POOL_TIMEOUT`.
No copiar `.env` a Git ni a ZIP públicos. Evitar incluir `TEST_DATABASE_URL` en el servicio de producción.

## Riesgos bloqueantes del despliegue
1. **Migraciones**: `alembic/env.py` bloquea la DB principal (correcto para seguridad). `alembic upgrade head` NO es procedimiento de producción: diseñar y probar proceso de migración de producción con aprobación explícita y copia de seguridad. No modificar esta salvaguarda automáticamente.
2. **Reportes**: `app/services/reportes_service.py` escribe en `reports/generated` por defecto. El disco efímero de Railway puede perder archivos en reinicios/despliegues. Migrar a almacenamiento privado persistente (p. ej. objeto externo) y URLs firmadas con comprobación de empresa antes del despliegue real. No usar bucket público.
3. **Health check**: `/health` sólo confirma proceso HTTP vivo; NO prueba PostgreSQL ni integridad de migraciones.
4. **Capacidad**: una instancia con un worker reduce consumo base; pruebas de carga real determinarán `workers`, pool y escalado. Nunca extrapolar desde respuestas HTTP 401.
5. **Protección**: rate limiting distribuido/Redis, workers en segundo plano y ML entrenado no están completados; no describirlos como operativos.
6. **Verificación**: comprobar variables y conectividad de Supabase, conexión SSL/pooler, CORS HTTPS, métricas y alertas en staging antes de exponer producción.

## Comandos de Railway
Railway detecta `railway.toml`. Verificar la instalación de requisitos y `/health`, después probar autenticación desde la URL HTTPS de Vercel. NO colocar credenciales en los logs ni la URL del repositorio.
