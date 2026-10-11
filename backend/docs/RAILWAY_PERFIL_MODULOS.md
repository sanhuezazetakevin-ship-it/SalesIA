# SalesIA — Perfil por módulos (FASE 14.5, Railway)

## Objetivo
Medir el costo SQL *de las pruebas de integración existentes* antes de cambiar consultas. No se modifica la lógica de negocio ni se requiere migración.

## Seguridad
Compruebe que `TEST_DATABASE_URL` es una base de pruebas distinta de `DATABASE_URL`. El script se niega a ejecutarse si ambas coinciden en su destino conocido. **No desactive el bloqueo de Alembic** y no ejecute esto con una base productiva.

## Uso desde `backend/`

```
python -m scripts.perf_modulos_testing --modulo analytics
python -m scripts.perf_modulos_testing --modulo dashboard
python -m scripts.perf_modulos_testing --modulo notificaciones
```

Los resultados se guardan en `reports/perf_<modulo>_testing.json`.

## Interpretación de resultados
- Las mediciones son del **cuerpo de cada test**: pueden incluir inserciones de datos de prueba, creación de sesiones o múltiples solicitudes HTTP.
- Algunas pruebas de dashboard usan dobles de prueba: **cero consultas no significa que la consulta de producción sea rápida**.
- Las pruebas elegidas no ejercitan todo inventario visual ni todos los reportes. Se necesitan fixtures de datos y solicitudes HTTP autenticadas específicas para obtener perfiles representativos de esos módulos.
- No comparar P95 de muestras pequeñas como si fueran estadísticas de producción.
- Medir el mismo escenario antes y después de cualquier optimización, comparar recuentos SQL y latencia HTTP. Considerar `EXPLAIN (ANALYZE, BUFFERS)` solo en TESTING y evitando consultas muy costosas.

## Próxima implementación
Revisar los resultados y optimizar exclusivamente las consultas identificadas como repetitivas o costosas. Mantener verificaciones de empresa, sesión revocada y permisos en cada solicitud.
