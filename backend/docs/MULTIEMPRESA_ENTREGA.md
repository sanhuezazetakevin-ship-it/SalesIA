# SalesIA — Entrega integrada multiempresa

## Alcance

Incluye backend y frontend en este ZIP. No contiene credenciales ni archivos `.env`.
No modifica las rutas existentes de compras, ventas y pagos.

### Incorporado

- `POST /api/publico/solicitudes-empresa` se mantiene como registro de solicitud pendiente.
- `GET /api/plataforma/empresas/solicitudes`: consulta de solicitudes.
- `POST /api/plataforma/empresas/solicitudes/{id}/aprobar`: en una transacción PostgreSQL crea empresa, configuración, catálogo RBAC, administrador inicial y marca solicitud como aprobada.
- `POST /api/plataforma/empresas/solicitudes/{id}/rechazar`: rechazo de solicitudes pendientes.
- `GET /api/plataforma/empresas`: consulta de empresas.
- `PATCH /api/plataforma/empresas/{id}/estado?activo=false`: suspensión y reactivación.
- Pantalla **Administración de plataforma**, accesible solo cuando la API reconoce el operador.

### Configuración requerida

En `.env` del backend, agregar manualmente:

```dotenv
SALESIA_PLATFORM_ADMIN_EMAILS=correo-del-operador-ya-registrado@ejemplo.com
```

Debe ser un usuario **ya existente, activo y con sesión válida**; por seguridad no existe un operador predeterminado. Solo el propietario del despliegue debe configurar esta variable. **No añadas correos de administradores de clientes**. No uses datos reales para pruebas.

### Puesta en marcha (Windows)

1. Haz una copia de seguridad de PostgreSQL y de tu proyecto actual.
2. Aplica las migraciones actuales con `python -m alembic upgrade head` en el entorno correcto. La tabla `solicitudes_alta_empresas` fue definida en la migración 010 del proyecto original.
3. Configura la variable de operador y reinicia FastAPI.
4. Inicia frontend con `npm ci` y `npm run dev` después de extraer el ZIP.
5. Inicia sesión como el operador configurado; aparece **Administración de plataforma**.
6. Desde la página pública, crea una solicitud con RUC ficticio de 11 dígitos y correo de prueba. Desde el panel, aprueba usando correo no registrado y contraseña inicial de 12 caracteres o más.
7. Inicia sesión con el administrador nuevo; crea producto/cliente y verifica que no sean visibles desde la empresa original. Comprueba también accesos cruzados a IDs por HTTP.
8. Suspende la nueva empresa y confirma que su sesión deja de funcionar; actívala y verifica el acceso después de iniciar sesión nuevamente.

### Pruebas

```bat
python -m pytest tests/test_plataforma_empresas_contract.py -q
python -m pytest tests/test_tenant_dependencies.py tests/test_tenant_integration.py -q
```

Las pruebas multiempresa reales requieren `TEST_DATABASE_URL` correctamente aislada. No apuntes las pruebas a producción.

### Limitaciones y pendientes

- Esta entrega no certifica el aislamiento de todos los endpoints en una base de datos real; hay que ejecutar las pruebas de punta a punta con PostgreSQL y tokens de dos empresas.
- No se agregaron migraciones nuevas: se reutilizaron las tablas `empresas`, `usuarios`, `roles`, `permisos`, `configuraciones_empresa` y `solicitudes_alta_empresas`.
- La activación/desactivación conserva sesiones existentes; una empresa desactivada debe ser rechazada por la verificación activa de sesión en el backend.
- La contraseña inicial debe transmitirse exclusivamente por HTTPS en producción; se recomienda agregar cambio obligatorio de contraseña en primer acceso y un flujo de invitación para el administrador.
- La autorización de plataforma está basada en una allowlist de correos configurados en el servidor, además del JWT y sesión válidos, no en un rol de plataforma persistente. Para una operación comercial avanzada se recomienda un modelo de operadores separado, 2FA y auditoría persistente de acciones de plataforma.
- La pantalla es un módulo funcional inicial; falta evaluación de UX, paginación avanzada y registro persistente de los eventos administrativos.
