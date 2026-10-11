# SalesIA Enterprise — FASE 14.5 consolidada (validación previa al cierre)

Este paquete contiene el backend de la entrega de Semana 08, más los tests de contratos corregidos, el test de PostgreSQL de testing previamente aprobado y pruebas adicionales JWT.

## Evidencia existente (facilitada por el usuario)
- 607 pruebas de FASE 14 aprobadas anteriormente.
- 22 pruebas específicas de FASE 14.5/Semana 08 aprobadas.
- 4 pruebas PostgreSQL de testing aprobadas.
- Alembic testing en `9a1450000009 (head)`.

**Estos resultados son históricos; no constituyen una ejecución nueva de este paquete consolidado.**

## Ejecución recomendada (CMD Windows)

```cmd
python -m pytest tests/test_fase145_jwt_contratos.py tests/test_fase145_integracion_pg.py tests/test_fase145_calculos.py tests/test_fase145_rfm.py tests/test_semana08_calculos.py tests/test_fase145_contratos.py tests/test_fase145_extendida_contratos.py -q --tb=short -rs
python scripts/fase145_smoke_http.py
python -m pytest tests/ -q --tb=short
```

## Alcance y restricciones
- Los escenarios autorizados de la integración PostgreSQL sustituyen la identidad; falta una prueba completa de login real → JWT → RBAC → tenant contra PostgreSQL.
- La prueba nueva de JWT valida firma/tipo y comprobación de sesión con un DB simulado; no sustituye la integración completa.
- El smoke HTTP mide latencia local de rechazo; no prueba concurrencia ni capacidad de producción.
- Las proyecciones de inventario son promedios orientativos, no modelos ML entrenados/validados.
- No se incorpora Redis, tareas asíncronas persistentes ni rate limiting distribuido en esta entrega. Son requisitos separados de infraestructura.
- El frontend debe representar los gráficos; el backend devuelve contratos de datos y textos explicativos, no gráficos ya renderizados.

## Seguridad
- Conservar `.env` local, no copiar credenciales en ZIP.
- Nunca ejecutar migraciones con la base principal; solo `alembic -x db=testing ...`.
- No declarar completa esta fase hasta cubrir rendimiento en carga, JWT + RBAC reales, UI y regresión total.
