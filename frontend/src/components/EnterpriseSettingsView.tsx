import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Settings,
  Building2,
  User,
  ShieldCheck,
  Percent,
  Save,
  Shield,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  Play,
  RefreshCw,
  AlertCircle,
  Activity,
  Layers,
  Info,
} from 'lucide-react';
import { api, ApiError } from '../services/api';
import type { User as UserType, RolEmpresa, RolPermisos } from '../types/api';
import { RolePermissionsSummary } from './RolePermissionsSummary';

type Igv = {
  id: number;
  codigo: string;
  nombre: string;
  tasa: string;
  activo: boolean;
  incluido_en_precio: boolean;
};

export const EnterpriseSettingsView: React.FC<{ user: UserType }> = ({ user }) => {
  const [igv, setIgv] = useState<Igv | null>(null);
  const [tasa, setTasa] = useState('');
  const [roles, setRoles] = useState<RolEmpresa[]>([]);
  const [expandedRoleId, setExpandedRoleId] = useState<number | null>(null);
  const [rolePermisosMap, setRolePermisosMap] = useState<Record<number, RolPermisos>>({});
  const [loadingRolePerms, setLoadingRolePerms] = useState<number | null>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [igvForbidden, setIgvForbidden] = useState(false);
  const [rolesForbidden, setRolesForbidden] = useState(false);

  const [testStatus, setTestStatus] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle');
  const [testResults, setTestResults] = useState<{ name: string; success: boolean; detail?: string }[]>([]);

  useEffect(() => {
    let active = true;
    const cargar = async () => {
      setLoading(true);
      const [rIgv, rRoles] = await Promise.allSettled([api.consultarIgv(), api.listarRoles()]);
      if (!active) return;

      if (rIgv.status === 'fulfilled') {
        setIgv(rIgv.value);
        setTasa(rIgv.value?.tasa ?? '');
        setIgvForbidden(false);
      } else {
        setIgvForbidden(rIgv.reason instanceof ApiError && rIgv.reason.status === 403);
        setError('No se pudo consultar la configuración tributaria.');
      }

      if (rRoles.status === 'fulfilled') {
        setRoles(rRoles.value);
        setRolesForbidden(false);
      } else {
        setRolesForbidden(rRoles.reason instanceof ApiError && rRoles.reason.status === 403);
      }
      setLoading(false);
    };

    void cargar();
    return () => {
      active = false;
    };
  }, []);

  const guardar = async () => {
    setNotice('');
    setError('');
    const n = Number(tasa);
    if (!/^\d+(\.\d{1,4})?$/.test(tasa.trim()) || !Number.isFinite(n) || n < 0 || n > 100) {
      setError('Introduce una tasa entre 0 y 100, con hasta cuatro decimales.');
      return;
    }
    if (!window.confirm(`¿Confirmas cambiar el IGV a ${tasa}%? Este cambio afectará la configuración de la empresa.`))
      return;

    setSaving(true);
    try {
      const actual = await api.actualizarIgv(tasa);
      setIgv((prev) => ({
        ...prev,
        id: actual.id,
        tasa: actual.tasa,
        codigo: prev?.codigo ?? 'IGV',
        nombre: prev?.nombre ?? 'Impuesto General a las Ventas',
        activo: true,
        incluido_en_precio: true,
      }));
      setNotice('Configuración tributaria guardada. El backend registró la operación para auditoría.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No fue posible guardar el IGV.');
    } finally {
      setSaving(false);
    }
  };

  const toggleRol = async (id: number) => {
    if (expandedRoleId === id) {
      setExpandedRoleId(null);
      return;
    }

    setExpandedRoleId(id);
    if (!rolePermisosMap[id]) {
      setLoadingRolePerms(id);
      try {
        const perms = await api.listarPermisosRol(id);
        setRolePermisosMap((prev) => ({ ...prev, [id]: perms }));
      } catch (e) {
        setError(e instanceof Error ? e.message : 'No fue posible consultar los permisos del rol.');
      } finally {
        setLoadingRolePerms(null);
      }
    }
  };

  const comprobar = async () => {
    setTestStatus('loading');
    setTestResults([]);

    const tests: [string, () => Promise<unknown>][] = [
      ['Sesión autenticada (Auth / Me)', () => api.getMe()],
      [
        'Dashboard comercial (KPIs y Analítica)',
        () => {
          const hoy = new Date();
          const desde = new Date(hoy.getTime() - 30 * 86400000);
          const fmt = (d: Date) =>
            `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
              d.getDate()
            ).padStart(2, '0')}`;
          return api.getDashboardComercial(fmt(desde), fmt(hoy), 5);
        },
      ],
      ['Listado de catálogo de productos', () => api.getProductos(1, 5)],
      ['Listado de cartera de clientes', () => api.getClientes(1, 5)],
      ['Listado de directorio de proveedores', () => api.getProveedores(1, 5)],
    ];

    const result = await Promise.allSettled(tests.map(([, fn]) => fn()));

    const formatted = result.map((r, i) => {
      const isOk = r.status === 'fulfilled';
      let detail: string | undefined = undefined;
      if (!isOk && r.reason instanceof ApiError) {
        detail = `HTTP ${r.reason.status} - ${r.reason.message}`;
      } else if (!isOk && r.reason instanceof Error) {
        detail = r.reason.message;
      }
      return {
        name: tests[i][0],
        success: isOk,
        detail,
      };
    });

    setTestResults(formatted);
    setTestStatus(result.every((r) => r.status === 'fulfilled') ? 'ok' : 'error');
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
            <Settings className="h-7 w-7 text-[#D97843] dark:text-[#FFA675]" />
            Configuración e Integración Empresarial
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 font-medium mt-1">
            Consulta y parametriza los aspectos fiscales de la empresa, revisa permisos y valida la conectividad con la API.
          </p>
        </div>
      </div>

      {/* Row of User & Organization Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass p-5 space-y-2">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Empresa Activa</span>
            <Building2 className="h-5 w-5 text-cyan-500" />
          </div>
          <div className="text-2xl font-bold text-slate-900 dark:text-white">
            ID #{user.empresa_id}
          </div>
          <p className="text-xs text-gray-400">
            Identificada desde tu token de sesión, sin requerir selección manual.
          </p>
        </div>

        <div className="glass p-5 space-y-2">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Usuario en Sesión</span>
            <User className="h-5 w-5 text-blue-500" />
          </div>
          <div className="text-lg font-bold text-slate-900 dark:text-white truncate">
            {user.nombre}
          </div>
          <p className="text-xs text-gray-400 truncate">{user.email}</p>
        </div>

        <div className="glass p-5 space-y-2">
          <div className="flex items-center justify-between text-gray-500 dark:text-gray-400">
            <span className="text-xs font-semibold uppercase tracking-wider">Estado de Sesión</span>
            <ShieldCheck className="h-5 w-5 text-emerald-500" />
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xl font-bold text-emerald-600 dark:text-emerald-400">
              Activa
            </span>
          </div>
          <p className="text-xs text-gray-400">Autenticación JWT validada contra el servidor.</p>
        </div>
      </div>

      {/* Alerts */}
      <AnimatePresence>
        {loading && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-info"
            role="status"
          >
            <RefreshCw className="h-4 w-4 animate-spin text-blue-500" />
            <span>Consultando configuración tributaria y catálogo de roles...</span>
          </motion.div>
        )}

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

        {notice && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-success"
            role="status"
          >
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
            <div className="flex-1 text-sm font-medium">{notice}</div>
            <button
              type="button"
              onClick={() => setNotice('')}
              className="text-emerald-400 hover:text-emerald-600 dark:hover:text-emerald-300"
            >
              <XCircle className="h-4 w-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Configuration Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* IGV Configuration Section */}
        <div className="lg:col-span-5 glass p-6 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-white/5">
            <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Percent className="h-5 w-5 text-cyan-500" />
              Impuesto sobre Ventas (IGV)
            </h3>
            {igv && (
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 font-semibold">
                Activo ({igv.tasa}%)
              </span>
            )}
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            Tasa impositiva aplicada a los cálculos comerciales de la empresa. Requiere el rol{' '}
            <code className="text-cyan-600 dark:text-cyan-400">ADMIN_EMPRESA</code> para su modificación.
          </p>

          {igvForbidden ? (
            <div className="alert-card alert-warning">
              <Info className="h-4 w-4 text-amber-500 shrink-0" />
              <span className="text-xs">
                La configuración de impuestos requiere el permiso tributario de administración de empresa.
              </span>
            </div>
          ) : (
            <div className="space-y-4 pt-2">
              <div>
                <label htmlFor="settings-igv" className="input-label">
                  Tasa porcentual del IGV (%) *
                </label>
                <div className="relative">
                  <input
                    id="settings-igv"
                    type="number"
                    min="0"
                    max="100"
                    step="0.0001"
                    className="input-field pr-12 text-base font-semibold"
                    value={tasa}
                    onChange={(e) => setTasa(e.target.value)}
                    placeholder="Ej. 18.00"
                  />
                  <span className="absolute right-3.5 top-2.5 text-sm font-bold text-gray-400">
                    %
                  </span>
                </div>
              </div>

              <div className="p-3.5 rounded-lg bg-gray-50 dark:bg-white/[0.02] border border-gray-200 dark:border-white/10 space-y-1 text-xs">
                <div className="flex justify-between text-gray-600 dark:text-gray-300">
                  <span>Código de impuesto:</span>
                  <span className="font-mono font-semibold">{igv?.codigo || 'IGV'}</span>
                </div>
                <div className="flex justify-between text-gray-600 dark:text-gray-300">
                  <span>Incluido en precio de venta:</span>
                  <span className="font-semibold">{igv?.incluido_en_precio ? 'Sí' : 'No'}</span>
                </div>
              </div>

              <button
                type="button"
                onClick={guardar}
                disabled={saving || loading || !tasa.trim()}
                className="w-full inline-flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Save className="h-4 w-4" />
                {saving ? 'Guardando cambios...' : 'Guardar configuración de IGV'}
              </button>
            </div>
          )}
        </div>

        {/* Roles and Permissions Section */}
        <div className="lg:col-span-7 glass p-6 space-y-4">
          <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-white/5">
            <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Shield className="h-5 w-5 text-cyan-500" />
              Roles y Permisos de la Empresa
            </h3>
            <span className="text-xs text-gray-400">{roles.length} roles</span>
          </div>

          <p className="text-xs text-gray-500 dark:text-gray-400">
            Haz clic en cualquier rol para inspeccionar los privilegios y accesos habilitados en el sistema.
          </p>

          {rolesForbidden ? (
            <div className="alert-card alert-warning">
              <Info className="h-4 w-4 text-amber-500 shrink-0" />
              <span className="text-xs">Tu cuenta no dispone de permisos para listar roles corporativos.</span>
            </div>
          ) : roles.length === 0 && !loading ? (
            <div className="py-8 text-center text-sm text-gray-400">
              No se encontraron roles accesibles en la empresa.
            </div>
          ) : (
            <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
              {roles.map((r) => {
                const isExpanded = expandedRoleId === r.rol_id;
                const permissionsData = rolePermisosMap[r.rol_id];
                const isLoadingThis = loadingRolePerms === r.rol_id;

                return (
                  <div
                    key={r.rol_id}
                    className="rounded-lg border border-gray-200 dark:border-white/10 overflow-hidden transition-all bg-white dark:bg-white/[0.02]"
                  >
                    <button
                      type="button"
                      onClick={() => toggleRol(r.rol_id)}
                      className="w-full flex items-center justify-between p-3.5 text-left hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                    >
                      <div className="flex items-center gap-2.5">
                        {isExpanded ? (
                          <ChevronDown className="h-4 w-4 text-cyan-500" />
                        ) : (
                          <ChevronRight className="h-4 w-4 text-gray-400" />
                        )}
                        <div>
                          <div className="text-sm font-semibold text-slate-900 dark:text-white">
                            {r.nombre}
                          </div>
                          <div className="text-xs text-gray-400 truncate max-w-sm">
                            {r.descripcion || 'Sin descripción'}
                          </div>
                        </div>
                      </div>
                      <span className="text-xs font-mono px-2 py-0.5 rounded bg-gray-100 dark:bg-white/5 text-gray-500 dark:text-gray-400">
                        ID #{r.rol_id}
                      </span>
                    </button>

                    {isExpanded && (
                      <div className="p-3 bg-gray-50/70 dark:bg-white/[0.03] border-t border-gray-100 dark:border-white/5">
                        {isLoadingThis ? (
                          <div className="py-6 flex items-center justify-center gap-2 text-xs text-cyan-500 font-medium">
                            <RefreshCw className="h-4 w-4 animate-spin" /> Consultando permisos del rol...
                          </div>
                        ) : permissionsData ? (
                          <RolePermissionsSummary
                            rolNombre={permissionsData.nombre}
                            rolDescripcion={permissionsData.descripcion}
                            permisos={permissionsData.permisos}
                          />
                        ) : (
                          <div className="py-4 text-center text-xs text-gray-400">
                            No fue posible obtener los permisos de este rol.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Integration Testing Section */}
      <div className="glass p-6 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-gray-100 dark:border-white/5">
          <div>
            <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Activity className="h-5 w-5 text-cyan-500" />
              Comprobación de Integración de Servicios
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              Ejecuta pruebas en paralelo de lectura directa hacia los módulos troncales del backend.
            </p>
          </div>

          <button
            type="button"
            onClick={comprobar}
            disabled={testStatus === 'loading'}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-sm transition-all duration-200 disabled:opacity-50 self-start sm:self-auto"
          >
            {testStatus === 'loading' ? (
              <RefreshCw className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {testStatus === 'loading' ? 'Verificando servicios...' : 'Comprobar integración'}
          </button>
        </div>

        {testResults.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
            {testResults.map((t, idx) => (
              <div
                key={idx}
                className={`p-3.5 rounded-xl border text-xs flex items-start gap-3 transition-all ${
                  t.success
                    ? 'bg-emerald-500/5 dark:bg-emerald-950/20 border-emerald-500/20'
                    : 'bg-rose-500/5 dark:bg-rose-950/20 border-rose-500/20'
                }`}
              >
                {t.success ? (
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="h-4 w-4 text-rose-500 shrink-0 mt-0.5" />
                )}
                <div className="space-y-0.5">
                  <div className="font-semibold text-slate-900 dark:text-white">
                    {t.name}
                  </div>
                  <div
                    className={
                      t.success
                        ? 'text-emerald-600 dark:text-emerald-400'
                        : 'text-rose-600 dark:text-rose-400 font-mono text-[11px]'
                    }
                  >
                    {t.success ? 'Conexión verificada OK' : t.detail || 'Fallo de conexión'}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
};
