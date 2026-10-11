# SalesIA Enterprise — FASE 13 Seguridad y Auditoría

## Alcance de la entrega

Se conservan los sistemas existentes de autenticación con Argon2, JWT firmado, sesiones persistidas revocables, RBAC y auditoría de operaciones de negocio. No se cambian tablas ni migraciones.

Cambios introducidos:
- GET `/api/auditoria`: listado paginado (máximo 100 por solicitud), filtros por `accion`, `entidad`, `desde`, `hasta`. Las fechas deben incluir zona horaria y seguir un orden válido.
- Consulta restringida por `auditoria.ver`, usuario y empresa activos, y filtro `auditoria.empresa_id` impuesto en el servidor. No se acepta empresa_id desde la solicitud.
- La respuesta omite `datos_anteriores`, `datos_nuevos` y la dirección IP para reducir exposición accidental de datos sensibles.
- Restricción de `JWT_ALGORITHM` a `HS256` y verificación explícita del esquema Bearer en dependencias.
- Cabeceras `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy` y `Cache-Control`. HSTS en producción cuando FastAPI identifica HTTPS (configurar también HSTS en proxy de borde).

## Integración frontend

```
GET /api/auditoria?limite=25&desplazamiento=0&accion=CREAR
Authorization: Bearer <access_token>
```

Respuesta:
```
{"total":1,"limite":25,"desplazamiento":0,"items":[{"id":1,"usuario_id":5,"accion":"CREAR","entidad":"productos","entidad_id":17,"descripcion":"Registro","origen":"API","created_at":"2026-10-10T12:00:00Z"}]}
```

Usar paginación, mostrar 401 (reautenticación), 403 (sin permiso), 422 (filtros inválidos). No almacenar JWT en repositorios ni registrar Authorization en logs. No mostrar contenido sensible de auditoría al rol VENDEDOR sin permiso.

## Instalación y verificación

1. Respaldar backend y mantener intactos `.env`, credenciales y base de datos.
2. Asegurar dependencias habituales del proyecto, incluyendo `psycopg[binary]` para PostgreSQL.
3. Ejecutar `python -m pytest tests/test_fase13_seguridad.py -q --tb=short`.
4. Ejecutar `python -m pytest tests/ -q --tb=short`.
5. Verificar en `/docs` el listado de `/api/auditoria`; probar con y sin `auditoria.ver` y con registros de dos empresas de prueba.

## Precauciones y trabajo de aceptación

No se han ejecutado pruebas de integración real contra Supabase en esta entrega. Revisar CORS real y esquema HTTPS detrás del proxy antes de producción. Realizar evaluación de tasa de intentos de login, política de contraseñas, rotación de secretos, cobertura de todas las acciones críticas, retención y acceso a auditorías y copias cifradas. No afirmar que existe cumplimiento completo de seguridad solo por la regresión de pytest.
