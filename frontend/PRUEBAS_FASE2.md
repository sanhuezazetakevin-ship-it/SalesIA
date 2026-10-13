# SalesIA Enterprise — Fase 2: consola de pruebas

**Propósito:** validación funcional en Supabase Testing. **No es una propuesta de rediseño UI.** Se preserva el CSS y estructura monocromática original. No se incluyen ni modifican archivos del backend.

## Integración en Git

Trabajar sobre `feat/frontend-user-management`. Respaldar los archivos locales y comparar con `git diff` antes de sustituir el frontend. El ZIP no contiene `.env`, `node_modules`, `dist` ni datos de Supabase. Tras extraer en la raíz del repositorio, ejecutar en `frontend`:

```bat
npm ci
npm run build
npm run dev
```

Comprobar que `VITE_API_BASE_URL` corresponde al backend local y que el backend usa **DATABASE_URL de testing** (no producción). No ejecutar suites de pruebas de BD que eliminen registros mientras se usa el entorno de integración.

## Pruebas manuales

1. **Administrador:** iniciar sesión en «1. Autenticación» y abrir «6. Usuarios y Roles (Pruebas)».
2. **Pendientes (GET /api/usuarios/pendientes):** pulsar «Actualizar pendientes». Sin invitados registrados, lista vacía es correcta; un 403 indica falta de permisos.
3. **Roles (GET /api/roles):** listar los roles; pulsar «Ver permisos» para GET /api/roles/{id}/permisos.
4. **Invitación (POST /api/invitaciones):** generar invitación para un correo de prueba distinto al del administrador. El token se muestra una única vez; copiarlo por un canal seguro. Caduca a las 48 horas. No guardar el token en Git, logs públicos ni capturas.
5. **Registro (POST /api/auth/register-invitation):** cerrar la sesión administrativa, abrir «Registro por Invitación», usar token, correo exacto del invitado, nombre y contraseña nueva. El registro queda inactivo hasta aprobación.
6. **Aprobación (GET pendientes / POST aprobación):** volver a iniciar sesión como administrador, actualizar pendientes y aprobar al invitado, previa confirmación.
7. **Roles (POST/DELETE /api/roles/asignaciones):** introducir el ID del usuario aprobado (activo) y seleccionar un rol para asignarlo. Verificar respuesta; probar revocación solo en un usuario de testing. **No revocar el único administrador.**
8. **Login del invitado:** cerrar sesión de administrador, iniciar sesión con la cuenta aprobada. Según permisos, algunos módulos pueden responder 403 (comportamiento previsto).

## Limitaciones del alcance

- No existe GET /api/usuarios general en los contratos revisados, por eso la consola muestra solo pendientes y requiere ID explícito para asignaciones.
- Los permisos se hacen cumplir en FastAPI, no en los botones; 403 es una respuesta válida de autorización.
- La pantalla de registro es una pestaña local pública, no un enlace de invitación enviado por correo.
- El token de invitación puede exponerse en la pantalla mientras está visible; solo usar cuentas de testing y compartir de forma privada.
- No se incorporan pruebas automáticas E2E nuevas. Verificar la compilación en Windows.
- Si aparecen errores HTTP, consultar la pestaña Network sin compartir JWT, contraseña ni token de invitación.

## Archivos de Fase 2

- `src/components/UsersManagementView.tsx` (nuevo)
- `src/components/InvitationRegistrationView.tsx` (nuevo)
- `src/types/api.ts` (contratos añadidos)
- `src/services/api.ts` (métodos REST añadidos)
- `src/App.tsx` y `src/components/Header.tsx` (pestañas añadidas)
