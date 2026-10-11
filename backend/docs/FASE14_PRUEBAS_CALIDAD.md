# SalesIA Enterprise — FASE 14: pruebas y calidad

## Alcance

Esta fase incorpora una puerta de calidad repetible sin modificar la lógica empresarial ni el esquema SQL. Incluye auditoría sintáctica de los archivos Python y pruebas adicionales de contratos FastAPI, rutas duplicadas, dependencia de autenticación, documentación OpenAPI, cabeceras de seguridad y límites de parámetros.

## Orden de ejecución (Windows CMD, desde `backend`, con `.venv` activo)

```cmd
python scripts/fase14_auditoria_estatica.py
python -m pytest tests/test_fase14_contratos.py -q --tb=short
python -m pytest tests/test_fase13_seguridad.py tests/test_security.py tests/test_session_service.py -q --tb=short
python -m pytest tests/ -q --tb=short -k "auth or security or session or permiso or auditoria"
python -m pytest tests/ -q --tb=short
```

**Importante:** solo el último comando valida la regresión integral. Las pruebas filtradas no prueban la totalidad de los servicios y las pruebas automatizadas no reemplazan pruebas manuales, de carga o un pentest autorizado.

## Criterios de aceptación

1. Auditoría estática sin errores.
2. Contratos API sin fallos, duplicaciones ni pérdida de seguridad.
3. Tests específicos y selección de seguridad aprobados.
4. Regresión completa aprobada sin fallos.
5. Verificación manual de flujos críticos con usuarios de dos empresas aisladas, roles distintos y sesiones revocadas.
6. En un entorno de staging independiente, realizar pruebas de carga y registrar latencias, errores, consumo de memoria y límites de infraestructura; no se presupone un SLA no medido.
7. Verificar que TEST_DATABASE_URL es una base de pruebas diferente de producción **antes** de ejecutar pruebas de integración.

## Evidencia

Guardar los comandos utilizados, versión de Python, número de tests, duración y resultados en un acta. Si existe un fallo de calidad no dar por cerrada FASE 14. No compartir `.env`, credenciales, volcado SQL ni tokens con terceros.

## Historial

Al iniciar FASE 14, el último resultado documentado del usuario es 17 pruebas específicas de seguridad aprobadas y 106 pruebas filtradas aprobadas; 495 casos quedaron sin ejecutar en ese filtro. El último resultado integral (FASE 12) fue 597 aprobadas. No existe aún resultado integral de FASE 14.
