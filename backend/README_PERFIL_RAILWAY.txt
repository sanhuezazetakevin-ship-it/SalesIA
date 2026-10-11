SalesIA Enterprise - Perfil HTTP real con PostgreSQL Testing

Esta entrega preserva el backend aportado por el usuario y agrega:
 tests/test_railway_perfil_http_real.py
 scripts/perf_http_real_testing.py
 docs/RAILWAY_PERFIL_HTTP_REAL_TESTING.md
 referencias/perf_{analytics,dashboard,notificaciones}_testing.json

Ejecutar desde el directorio backend:
  python -m scripts.perf_http_real_testing

Enviar el resultado del comando y, si se crea, reports/perf_http_real_testing.json.
No subir .env, tokens o credenciales. No contiene optimizaciones SQL de producción aún.
