import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  UserPlus,
  UserCheck,
  UserMinus,
  Mail,
  Key,
  Shield,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Copy,
  Check,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Clock,
  Layers,
  Info,
} from 'lucide-react';
import { api } from '../services/api';
import { InvitacionCreada, RolEmpresa, RolPermisos, UsuarioPendiente } from '../types/api';
import { RolePermissionsSummary } from './RolePermissionsSummary';

const errorText = (e: unknown) => (e instanceof Error ? e.message : 'Error desconocido');

export const UsersManagementView: React.FC = () => {
  const [paginaPendientes, setPaginaPendientes] = useState(1);
  const [paginaRoles, setPaginaRoles] = useState(1);
  const limiteLista = 10;

  const [pendientes, setPendientes] = useState<UsuarioPendiente[]>([]);
  const [roles, setRoles] = useState<RolEmpresa[]>([]);
  const [email, setEmail] = useState('');
  const [invitacion, setInvitacion] = useState<InvitacionCreada | null>(null);
  const [permisos, setPermisos] = useState<RolPermisos | null>(null);
  const [usuarioId, setUsuarioId] = useState('');
  const [rolId, setRolId] = useState('');

  const [busy, setBusy] = useState(false);
  const [pendingBusy, setPendingBusy] = useState(false);
  const [rolesBusy, setRolesBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [copiedToken, setCopiedToken] = useState(false);

  const cargarPendientes = async () => {
    setPendingBusy(true);
    try {
      setPendientes(await api.listarUsuariosPendientes());
      setError('');
    } catch (e) {
      setError(`Pendientes: ${errorText(e)}`);
    } finally {
      setPendingBusy(false);
    }
  };

  const cargarRoles = async () => {
    setRolesBusy(true);
    try {
      const rows = await api.listarRoles();
      setRoles(rows);
      setRolId((current) => current || String(rows[0]?.rol_id || ''));
      setError('');
    } catch (e) {
      setError(`Roles: ${errorText(e)}`);
    } finally {
      setRolesBusy(false);
    }
  };

  useEffect(() => {
    void cargarPendientes();
    void cargarRoles();
  }, []);

  const run = async (action: () => Promise<string>) => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      setMessage(await action());
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  };

  const validId = (v: string): number | null => {
    const number = Number(v);
    return /^\d+$/.test(v.trim()) && Number.isSafeInteger(number) && number > 0 ? number : null;
  };

  const cambiarRol = (operacion: 'asignar' | 'revocar') => {
    const usuario = validId(usuarioId);
    const rol = validId(rolId);
    if (!usuario || !rol) {
      setError('Introduce identificadores numéricos válidos para el usuario y el rol.');
      return;
    }
    const roleLabel = roles.find((r) => r.rol_id === rol)?.nombre || String(rol);
    if (
      !window.confirm(
        `¿${operacion === 'asignar' ? 'Asignar' : 'Revocar'} el rol "${roleLabel}" al usuario #${usuario}? Esta operación modificará los accesos inmediatamente.`
      )
    )
      return;

    void run(async () => {
      const response =
        operacion === 'asignar'
          ? await api.asignarRol(usuario, rol)
          : await api.revocarRol(usuario, rol);
      return `Rol ${response.rol_nombre}: ${response.estado}${
        response.sesiones_revocadas !== undefined
          ? `. Sesiones revocadas: ${response.sesiones_revocadas}`
          : ''
      }.`;
    });
  };

  const copiarAlPortapapeles = (texto: string) => {
    navigator.clipboard
      .writeText(texto)
      .then(() => {
        setCopiedToken(true);
        setTimeout(() => setCopiedToken(false), 3000);
        setMessage('Token copiado al portapapeles. Compártelo únicamente por un canal privado.');
      })
      .catch((e) => setError(errorText(e)));
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="glass p-5 md:p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 border border-[#D97843]/20 dark:border-white/10 shadow-sm">
        <div>
          <h2 className="text-2xl md:text-3xl font-black tracking-tight text-slate-950 dark:text-white flex items-center gap-2.5 drop-shadow-sm">
            <Users className="h-7 w-7 text-[#D97843] dark:text-[#FFA675]" />
            Gestión de Usuarios y Control de Acceso (RBAC)
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 font-medium mt-1">
            Administración de invitaciones seguras, aprobación de nuevas cuentas y asignación de roles y permisos corporativos.
          </p>
        </div>
      </div>

      {/* Global Alerts */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-error"
            role="alert"
          >
            <AlertCircle className="h-5 w-5 shrink-0 text-red-500" />
            <div className="flex-1 text-sm font-medium">{error}</div>
            <button
              type="button"
              onClick={() => setError('')}
              className="text-red-400 hover:text-red-600 dark:hover:text-red-300"
            >
              <XCircle className="h-4 w-4" />
            </button>
          </motion.div>
        )}

        {message && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-success"
            role="status"
          >
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
            <div className="flex-1 text-sm font-medium">{message}</div>
            <button
              type="button"
              onClick={() => setMessage('')}
              className="text-emerald-400 hover:text-emerald-600 dark:hover:text-emerald-300"
            >
              <XCircle className="h-4 w-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* SECTION 1: INVITAR USUARIO */}
        <div className="lg:col-span-6 space-y-6">
          <div className="glass p-6 space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-white/5">
              <UserPlus className="h-5 w-5 text-cyan-500" />
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                Invitar nuevo usuario
              </h3>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Genera una invitación segura por correo. El enlace y token generado permitirán al destinatario registrarse bajo tu empresa.
            </p>

            <form
              onSubmit={(e) => {
                e.preventDefault();
                setInvitacion(null);
                void run(async () => {
                  const response = await api.crearInvitacion(email.trim());
                  setInvitacion(response);
                  setEmail('');
                  return 'Invitación generada exitosamente. Comparte el token mediante un canal seguro.';
                });
              }}
              className="space-y-4"
            >
              <div>
                <label htmlFor="invite-email" className="input-label">
                  Correo electrónico corporativo *
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
                  <input
                    id="invite-email"
                    type="email"
                    required
                    className="input-field pl-10"
                    placeholder="nuevo.usuario@empresa.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={busy || !email.trim()}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <UserPlus className="h-4 w-4" />
                {busy ? 'Generando invitación...' : 'Enviar invitación'}
              </button>
            </form>

            {/* Generated Invitation Token Card */}
            {invitacion && (
              <motion.div
                initial={{ opacity: 0, scale: 0.98 }}
                animate={{ opacity: 1, scale: 1 }}
                className="mt-4 p-4 rounded-xl border border-cyan-500/30 bg-cyan-500/5 dark:bg-cyan-950/20 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold uppercase tracking-wider text-cyan-600 dark:text-cyan-400 flex items-center gap-1.5">
                    <Key className="h-3.5 w-3.5" /> Token de Invitación Generado
                  </span>
                  <span className="text-[11px] text-gray-400 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    Expira: {new Date(invitacion.fecha_expiracion).toLocaleDateString()}
                  </span>
                </div>

                <div className="text-xs text-gray-700 dark:text-gray-300">
                  Invitación para: <strong>{invitacion.email}</strong>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    aria-label="Token de invitación"
                    readOnly
                    value={invitacion.token}
                    className="input-field font-mono text-xs py-2 bg-white/70 dark:bg-black/30"
                  />
                  <button
                    type="button"
                    onClick={() => copiarAlPortapapeles(invitacion.token)}
                    className="p-2 rounded-lg border border-cyan-500/30 bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-600 dark:text-cyan-400 transition-colors shrink-0"
                    title="Copiar token"
                  >
                    {copiedToken ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                  </button>
                </div>

                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={() => setInvitacion(null)}
                    className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 underline"
                  >
                    Ocultar tarjeta de token
                  </button>
                </div>
              </motion.div>
            )}
          </div>

          {/* SECTION 4: ASIGNAR Y REVOCAR ROLES */}
          <div className="glass p-6 space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-white/5">
              <ShieldCheck className="h-5 w-5 text-cyan-500" />
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                Asignación de Roles
              </h3>
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Modifica los permisos de un usuario existente. La asignación o revocación surte efecto de inmediato.
            </p>

            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label htmlFor="target-user" className="input-label">
                    ID de Usuario *
                  </label>
                  <input
                    id="target-user"
                    type="number"
                    min="1"
                    step="1"
                    className="input-field"
                    placeholder="Ej. 12"
                    value={usuarioId}
                    onChange={(e) => setUsuarioId(e.target.value)}
                  />
                </div>

                <div>
                  <label htmlFor="target-role" className="input-label">
                    Rol a gestionar *
                  </label>
                  <select
                    id="target-role"
                    className="input-field cursor-pointer"
                    value={rolId}
                    onChange={(e) => setRolId(e.target.value)}
                  >
                    {roles.map((r) => (
                      <option key={r.rol_id} value={r.rol_id}>
                        {r.nombre} (ID #{r.rol_id})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-1">
                <button
                  type="button"
                  disabled={busy || !roles.length || !usuarioId}
                  onClick={() => cambiarRol('asignar')}
                  className="inline-flex items-center justify-center gap-2 py-2 px-3.5 rounded-lg text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-700 transition-colors shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <UserPlus className="h-4 w-4" />
                  Asignar Rol
                </button>
                <button
                  type="button"
                  disabled={busy || !roles.length || !usuarioId}
                  onClick={() => cambiarRol('revocar')}
                  className="inline-flex items-center justify-center gap-2 py-2 px-3.5 rounded-lg text-xs font-semibold text-rose-600 dark:text-rose-400 bg-rose-500/10 border border-rose-500/20 hover:bg-rose-500/20 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <UserMinus className="h-4 w-4" />
                  Revocar Rol
                </button>
              </div>

              <div className="flex items-start gap-2 pt-1 text-[11px] text-gray-400">
                <Info className="h-3.5 w-3.5 shrink-0 mt-0.5 text-cyan-500" />
                <span>
                  No está permitido revocar los permisos de tu propia cuenta administradora desde este panel.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* SECTION 2 & 3: USUARIOS PENDIENTES & ROLES TABLE */}
        <div className="lg:col-span-6 space-y-6">
          {/* Pending Users Table */}
          <div className="glass p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-white/5">
              <div className="flex items-center gap-2">
                <UserCheck className="h-5 w-5 text-cyan-500" />
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                  Usuarios pendientes de aprobación
                </h3>
              </div>
              <button
                type="button"
                onClick={() => void cargarPendientes()}
                disabled={pendingBusy}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 text-gray-500 dark:text-gray-400 transition-colors"
                title="Actualizar pendientes"
              >
                <RefreshCw className={`h-4 w-4 ${pendingBusy ? 'animate-spin text-cyan-500' : ''}`} />
              </button>
            </div>

            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-white/10">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Correo</th>
                    <th>Estado</th>
                    <th className="text-right">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {pendientes
                    .slice(
                      (paginaPendientes - 1) * limiteLista,
                      paginaPendientes * limiteLista
                    )
                    .map((u) => (
                      <tr key={u.usuario_id}>
                        <td className="font-mono text-xs">#{u.usuario_id}</td>
                        <td className="font-medium text-slate-900 dark:text-white">{u.nombre}</td>
                        <td className="text-xs">{u.email}</td>
                        <td>
                          <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                            Pendiente
                          </span>
                        </td>
                        <td className="text-right whitespace-nowrap">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => {
                              if (
                                !window.confirm(
                                  `¿Aprobar la cuenta de ${u.nombre}? Esta acción activará al usuario en la plataforma.`
                                )
                              )
                                return;
                              void run(async () => {
                                const result = await api.aprobarUsuario(u.usuario_id);
                                await cargarPendientes();
                                return `Usuario #${result.usuario_id} (${u.nombre}): ${result.estado}.`;
                              });
                            }}
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
                          >
                            <CheckCircle2 className="h-3.5 w-3.5" />
                            Aprobar
                          </button>
                        </td>
                      </tr>
                    ))}
                  {!pendingBusy && pendientes.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-gray-400 text-sm">
                        No hay usuarios pendientes de aprobación actualmente.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination-bar">
              <span>
                Página {paginaPendientes} de {Math.max(1, Math.ceil(pendientes.length / limiteLista))} ·{' '}
                {pendientes.length} pendientes
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={paginaPendientes <= 1}
                  onClick={() => setPaginaPendientes((p) => p - 1)}
                  className="pagination-btn flex items-center gap-1"
                >
                  <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                </button>
                <button
                  type="button"
                  disabled={paginaPendientes * limiteLista >= pendientes.length}
                  onClick={() => setPaginaPendientes((p) => p + 1)}
                  className="pagination-btn flex items-center gap-1"
                >
                  Siguiente <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Roles and Permissions Table */}
          <div className="glass p-6 space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-white/5">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-cyan-500" />
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                  Roles definidos en la empresa
                </h3>
              </div>
              <button
                type="button"
                onClick={() => void cargarRoles()}
                disabled={rolesBusy}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-white/10 text-gray-500 dark:text-gray-400 transition-colors"
                title="Actualizar roles"
              >
                <RefreshCw className={`h-4 w-4 ${rolesBusy ? 'animate-spin text-cyan-500' : ''}`} />
              </button>
            </div>

            <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-white/10">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Rol</th>
                    <th>Descripción</th>
                    <th className="text-right">Permisos</th>
                  </tr>
                </thead>
                <tbody>
                  {roles
                    .slice((paginaRoles - 1) * limiteLista, paginaRoles * limiteLista)
                    .map((r) => (
                      <tr key={r.rol_id}>
                        <td className="font-mono text-xs">#{r.rol_id}</td>
                        <td className="font-medium text-slate-900 dark:text-white">{r.nombre}</td>
                        <td className="text-xs text-gray-400 max-w-xs truncate">
                          {r.descripcion || '—'}
                        </td>
                        <td className="text-right whitespace-nowrap">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() =>
                              void run(async () => {
                                const result = await api.listarPermisosRol(r.rol_id);
                                setPermisos(result);
                                return `Permisos consultados: ${result.nombre}.`;
                              })
                            }
                            className="inline-flex items-center gap-1 px-2.5 py-1 rounded text-xs font-medium bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 transition-colors"
                          >
                            <Layers className="h-3.5 w-3.5" />
                            Ver
                          </button>
                        </td>
                      </tr>
                    ))}
                  {roles.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-gray-400 text-sm">
                        Sin roles registrados o sin permiso de lectura.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination-bar">
              <span>
                Página {paginaRoles} de {Math.max(1, Math.ceil(roles.length / limiteLista))} · {roles.length}{' '}
                roles
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={paginaRoles <= 1}
                  onClick={() => setPaginaRoles((p) => p - 1)}
                  className="pagination-btn flex items-center gap-1"
                >
                  <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                </button>
                <button
                  type="button"
                  disabled={paginaRoles * limiteLista >= roles.length}
                  onClick={() => setPaginaRoles((p) => p + 1)}
                  className="pagination-btn flex items-center gap-1"
                >
                  Siguiente <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>

            {/* Inspected Role Permissions Detail */}
            {permisos && (
              <RolePermissionsSummary
                rolNombre={permisos.nombre}
                rolDescripcion={permisos.descripcion}
                permisos={permisos.permisos}
                onClose={() => setPermisos(null)}
              />
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};
