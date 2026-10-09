# MVP-01-F.2 — Verificación real de persistencia

## Seguridad

- Requiere `TEST_DATABASE_URL` y la fixture `db_testing` existente.
- No ejecuta migraciones, no usa `create_all`, no usa `TRUNCATE` y no toca `DATABASE_URL`.
- La fixture debe verificar que los proyectos Supabase principal y Testing son diferentes.
- Las pruebas usan transacción externa y SAVEPOINT, que se revierten al finalizar.
- No instalar el servicio de historial desde este ZIP: ya fue instalado en MVP-01-F.1.

## Instalación

Copiar únicamente `tests/test_analytics_historial_postgres.py` dentro de `backend/tests/`.

## Ejecución

```cmd
python -m pytest tests/test_analytics_historial_postgres.py -v --tb=short
```

Si aprueban las 8 pruebas, ejecutar la regresión completa de Analytics:

```cmd
python -m pytest tests/test_analytics_calculos.py tests/test_analytics_resumen_integracion.py tests/test_analytics_distribuciones_calculos.py tests/test_analytics_distribuciones_integracion.py tests/test_analytics_probabilidades_calculos.py tests/test_analytics_probabilidades_integracion.py tests/test_analytics_historial_validaciones.py tests/test_analytics_historial_postgres.py -q --tb=short
```

Resultado esperado: **92 passed** si los 84 anteriores se mantienen.

## Límite funcional

El servicio interno de MVP-01-F.1 sigue autorizando `guardar_*` con `ventas.ver`.
**No exponer escritura mediante HTTP ni reutilizar esas funciones desde un router** hasta definir y aplicar un permiso de escritura específico, con seed y pruebas RBAC.
Trazabilidad de usuario se guarda dentro de JSON; no existe columna `usuario_id` dedicada.

## Siguiente bloque

MVP-01-F.3: API REST de lectura del historial; escritura condicionada a permisos adecuados.
