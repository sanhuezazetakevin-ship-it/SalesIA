# MVP-01-F.4 — Seguridad HTTP del historial de Analytics

## Requisitos

- Backend SalesIA actualizado hasta MVP-01-F.3.
- `TEST_DATABASE_URL` apuntando a la **base Supabase Testing**, distinta a la principal.
- Fixture `db_testing` reversible y helper `cliente_analytics` ya validados.
- Permisos `ventas.ver` y `analitica.ejecutar` disponibles en el catálogo RBAC del entorno Testing.

## Instalación

Copiar únicamente `tests/test_analytics_historial_http_seguridad.py` en `backend/tests/`.
No reemplazar modelos, rutas, servicios ni fixtures. No ejecutar migraciones.

## Ejecución

```cmd
python -m pytest tests/test_analytics_historial_http_seguridad.py -v --tb=short
```

Objetivo: 9 pruebas. Si alguna falla, compartir el traceback completo y detener el cierre de la fase.

Para regresión completa de Analytics:

```cmd
python -m pytest tests/test_analytics_*py -q --tb=short
```

**Precaución:** Las pruebas HTTP ejecutan `commit()` dentro de sesiones proporcionadas por `db_testing`. La seguridad de los datos depende de que la fixture mantenga la transacción externa reversible; verificarla antes de ejecutar. No usar DATABASE_URL principal.
