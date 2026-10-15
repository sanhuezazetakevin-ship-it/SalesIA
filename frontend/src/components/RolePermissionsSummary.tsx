import React, { useState } from 'react';
import {
  Shield,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  ShoppingCart,
  CreditCard,
  Package,
  Truck,
  BarChart3,
  Settings,
  Code2,
  ListFilter,
  Check,
  Sparkles,
} from 'lucide-react';

export interface RolePermissionsSummaryProps {
  rolNombre: string;
  rolDescripcion?: string | null;
  permisos: string[];
  onClose?: () => void;
}

interface ModuloInfo {
  id: string;
  nombre: string;
  icono: React.ElementType;
  colorBorder: string;
  colorBg: string;
  colorText: string;
  descripcionModulo: string;
  capacidades: {
    permiso: string | string[];
    descripcion: string;
    esencial?: boolean;
  }[];
}

const MODULOS_SISTEMA: ModuloInfo[] = [
  {
    id: 'ventas',
    nombre: 'Ventas y Clientes',
    icono: ShoppingCart,
    colorBorder: 'border-cyan-500/30',
    colorBg: 'bg-cyan-500/10 dark:bg-cyan-950/20',
    colorText: 'text-cyan-600 dark:text-cyan-400',
    descripcionModulo: 'Operaciones comerciales del día a día',
    capacidades: [
      {
        permiso: ['pedidos.crear', 'ventas.crear'],
        descripcion: 'Registrar nuevos pedidos y emitir ventas',
      },
      {
        permiso: ['pedidos.confirmar', 'ventas.confirmar'],
        descripcion: 'Confirmar pedidos y convertirlos en ventas formales',
      },
      {
        permiso: 'pedidos.cancelar',
        descripcion: 'Cancelar pedidos de clientes',
      },
      {
        permiso: ['clientes.crear', 'clientes.editar'],
        descripcion: 'Crear y actualizar la información de clientes',
      },
      {
        permiso: ['clientes.ver', 'pedidos.ver', 'ventas.ver'],
        descripcion: 'Consultar el catálogo de clientes y ventas registradas',
      },
    ],
  },
  {
    id: 'caja',
    nombre: 'Caja y Cobranzas',
    icono: CreditCard,
    colorBorder: 'border-emerald-500/30',
    colorBg: 'bg-emerald-500/10 dark:bg-emerald-950/20',
    colorText: 'text-emerald-600 dark:text-emerald-400',
    descripcionModulo: 'Cobro de ventas y flujo de dinero',
    capacidades: [
      {
        permiso: 'pagos.registrar',
        descripcion: 'Registrar cobros a clientes (efectivo, transferencias, tarjetas, apps)',
      },
      {
        permiso: 'pagos.anular',
        descripcion: 'Anular pagos registrados por motivos autorizados',
      },
      {
        permiso: 'pagos.ver',
        descripcion: 'Consultar historial de pagos y saldos pendientes',
      },
    ],
  },
  {
    id: 'almacen',
    nombre: 'Almacén e Inventario',
    icono: Package,
    colorBorder: 'border-amber-500/30',
    colorBg: 'bg-amber-500/10 dark:bg-amber-950/20',
    colorText: 'text-amber-600 dark:text-amber-400',
    descripcionModulo: 'Control físico de mercancía y entregas',
    capacidades: [
      {
        permiso: 'inventario.ver',
        descripcion: 'Consultar existencias de stock disponible en tiempo real',
      },
      {
        permiso: 'inventario.ajustar',
        descripcion: 'Realizar ajustes manuales de stock (ingresos/egresos justificados)',
      },
      {
        permiso: 'entregas.confirmar',
        descripcion: 'Confirmar despacho físico y entrega de pedidos a clientes',
      },
      {
        permiso: ['productos.crear', 'productos.editar'],
        descripcion: 'Crear y editar productos, precios y costos de referencia',
      },
      {
        permiso: ['categorias.crear', 'categorias.editar'],
        descripcion: 'Organizar y categorizar el catálogo de productos',
      },
    ],
  },
  {
    id: 'compras',
    nombre: 'Compras y Proveedores',
    icono: Truck,
    colorBorder: 'border-blue-500/30',
    colorBg: 'bg-blue-500/10 dark:bg-blue-950/20',
    colorText: 'text-blue-600 dark:text-blue-400',
    descripcionModulo: 'Abastecimiento de mercadería con proveedores',
    capacidades: [
      {
        permiso: ['compras.crear', 'compras.confirmar'],
        descripcion: 'Emitir y confirmar órdenes de compra a proveedores',
      },
      {
        permiso: 'recepciones.crear',
        descripcion: 'Registrar la recepción física de mercancía en almacén',
      },
      {
        permiso: 'pagos_proveedores.registrar',
        descripcion: 'Registrar pagos emitidos a proveedores por facturas',
      },
      {
        permiso: 'pagos_proveedores.anular',
        descripcion: 'Anular pagos a proveedores',
      },
      {
        permiso: ['proveedores.crear', 'proveedores.editar'],
        descripcion: 'Crear y actualizar datos de empresas proveedoras',
      },
    ],
  },
  {
    id: 'reportes',
    nombre: 'Reportes y Analítica',
    icono: BarChart3,
    colorBorder: 'border-purple-500/30',
    colorBg: 'bg-purple-500/10 dark:bg-purple-950/20',
    colorText: 'text-purple-600 dark:text-purple-400',
    descripcionModulo: 'Inteligencia de negocio y toma de decisiones',
    capacidades: [
      {
        permiso: ['reportes.generar', 'reportes.descargar'],
        descripcion: 'Generar y descargar reportes oficiales en PDF y Excel',
      },
      {
        permiso: 'analitica.ejecutar',
        descripcion: 'Ejecutar análisis predictivos, probabilidades y estadísticas',
      },
      {
        permiso: ['reportes.ver', 'analitica.ver'],
        descripcion: 'Visualizar tableros de métricas KPI e indicadores comerciales',
      },
    ],
  },
  {
    id: 'seguridad',
    nombre: 'Administración y Seguridad',
    icono: Settings,
    colorBorder: 'border-rose-500/30',
    colorBg: 'bg-rose-500/10 dark:bg-rose-950/20',
    colorText: 'text-rose-600 dark:text-rose-400',
    descripcionModulo: 'Control de accesos y configuración empresarial',
    capacidades: [
      {
        permiso: ['usuarios.crear', 'usuarios.autorizar'],
        descripcion: 'Invitar y aprobar el acceso a nuevos colaboradores',
      },
      {
        permiso: ['roles.asignar', 'roles.revocar'],
        descripcion: 'Asignar o retirar roles y permisos a los usuarios',
      },
      {
        permiso: 'configuracion.editar',
        descripcion: 'Modificar configuración tributaria e impuestos (IGV)',
      },
      {
        permiso: 'auditoria.ver',
        descripcion: 'Auditar el registro de seguridad de quién realizó cada acción',
      },
    ],
  },
];

export const RolePermissionsSummary: React.FC<RolePermissionsSummaryProps> = ({
  rolNombre,
  rolDescripcion,
  permisos,
  onClose,
}) => {
  const [modoTecnico, setModoTecnico] = useState(false);

  // Determinar permisos activos para cada módulo
  const setPermisos = new Set(permisos);

  const modulosEvaluados = MODULOS_SISTEMA.map((mod) => {
    const capacidadesHabilitadas = mod.capacidades.filter((cap) => {
      if (Array.isArray(cap.permiso)) {
        return cap.permiso.some((p) => setPermisos.has(p));
      }
      return setPermisos.has(cap.permiso);
    });

    const tieneAcceso = capacidadesHabilitadas.length > 0;
    const esAccesoTotal = capacidadesHabilitadas.length === mod.capacidades.length;

    return {
      ...mod,
      tieneAcceso,
      esAccesoTotal,
      capacidadesHabilitadas,
    };
  });

  const totalModulosConAcceso = modulosEvaluados.filter((m) => m.tieneAcceso).length;
  const esSuperAdmin = totalModulosConAcceso === MODULOS_SISTEMA.length && permisos.length > 35;

  return (
    <div className="mt-4 p-5 rounded-2xl border border-cyan-500/30 bg-white/95 dark:bg-[#0E131F]/90 backdrop-blur-xl shadow-xl space-y-4">
      {/* Encabezado */}
      <div className="flex items-start justify-between gap-3 pb-3 border-b border-gray-100 dark:border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-500 shadow-sm">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h4 className="text-base font-black text-slate-950 dark:text-white">
                ¿Qué puede hacer el rol <span className="text-[#D97843] dark:text-[#FFA675] underline decoration-[#D97843]/30">{rolNombre}</span>?
              </h4>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-[#D97843]/15 text-[#B35D2F] dark:text-[#FFA675] border border-[#D97843]/30">
                {permisos.length} funciones
              </span>
            </div>
            <p className="text-xs text-slate-700 dark:text-slate-200 mt-0.5 font-medium">
              {rolDescripcion || 'Perfil de permisos configurado en la empresa'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Alternar modo intuitivo vs técnico */}
          <button
            type="button"
            onClick={() => setModoTecnico((prev) => !prev)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-white/5 hover:bg-gray-200 dark:hover:bg-white/10 transition-colors"
            title="Alternar vista simplificada o técnica"
          >
            {modoTecnico ? (
              <>
                <ListFilter className="h-3.5 w-3.5 text-cyan-500" />
                <span>Ver lista resumida</span>
              </>
            ) : (
              <>
                <Code2 className="h-3.5 w-3.5 text-gray-400" />
                <span>Ver códigos técnicos</span>
              </>
            )}
          </button>

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-white/10 transition-colors"
              title="Cerrar detalle"
            >
              <XCircle className="h-5 w-5" />
            </button>
          )}
        </div>
      </div>

      {/* Banner resumen general intuitivo */}
      {!modoTecnico && (
        <div
          className={`p-3.5 rounded-xl border flex items-start gap-3 ${
            esSuperAdmin
              ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-800 dark:text-emerald-200'
              : 'bg-cyan-500/10 border-cyan-500/25 text-cyan-800 dark:text-cyan-200'
          }`}
        >
          <Sparkles className="h-5 w-5 shrink-0 mt-0.5 text-cyan-500" />
          <div className="text-xs leading-relaxed">
            {esSuperAdmin ? (
              <>
                <strong className="font-semibold block text-sm">Control Total de la Empresa (Superadministrador)</strong>
                Este rol tiene acceso completo a todas las áreas: puede vender, gestionar cobros, alterar stock, realizar compras, emitir reportes y administrar a otros empleados.
              </>
            ) : (
              <>
                <strong className="font-semibold block text-sm">Perfil con Acceso Focalizado</strong>
                Este rol tiene habilitadas{' '}
                <span className="font-bold underline">{totalModulosConAcceso} de 6 áreas operativas</span>. A continuación se listan claramente las actividades permitidas:
              </>
            )}
          </div>
        </div>
      )}

      {/* VISTA RESUMIDA E INTUITIVA */}
      {!modoTecnico ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 pt-1">
          {modulosEvaluados.map((mod) => {
            const Icono = mod.icono;

            return (
              <div
                key={mod.id}
                className={`p-3.5 rounded-xl border transition-all ${
                  mod.tieneAcceso
                    ? `${mod.colorBorder} ${mod.colorBg} shadow-xs`
                    : 'border-gray-200/50 dark:border-white/5 bg-gray-50/50 dark:bg-white/[0.02] opacity-50'
                }`}
              >
                {/* Cabecera del módulo */}
                <div className="flex items-center justify-between pb-2 border-b border-gray-100/50 dark:border-white/5 mb-2">
                  <div className="flex items-center gap-2">
                    <Icono className={`h-4 w-4 ${mod.tieneAcceso ? mod.colorText : 'text-gray-400'}`} />
                    <span className="text-xs font-bold text-gray-900 dark:text-white">
                      {mod.nombre}
                    </span>
                  </div>
                  {mod.tieneAcceso ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">
                      <Check className="h-3 w-3" />
                      {mod.esAccesoTotal ? 'Total' : 'Operativo'}
                    </span>
                  ) : (
                    <span className="px-2 py-0.5 rounded-full text-[10px] font-medium text-gray-400 bg-gray-100 dark:bg-white/5">
                      Sin acceso
                    </span>
                  )}
                </div>

                {/* Lista concisa de lo que puede hacer */}
                {mod.tieneAcceso ? (
                  <ul className="space-y-1.5">
                    {mod.capacidadesHabilitadas.map((cap, idx) => (
                      <li key={idx} className="flex items-start gap-2 text-xs text-gray-700 dark:text-gray-300">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0 mt-0.5" />
                        <span className="leading-tight">{cap.descripcion}</span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[11px] text-gray-400 italic">
                    Este rol no puede realizar operaciones de este módulo.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        /* VISTA TÉCNICA DETALLADA (CÓDIGOS RBAC) */
        <div className="space-y-2 pt-1">
          <p className="text-xs text-gray-400">
            Identificadores técnicos de permisos validados en el backend (FastAPI / PostgreSQL):
          </p>
          <div className="flex flex-wrap gap-1.5 max-h-60 overflow-y-auto p-3 rounded-xl bg-gray-50 dark:bg-white/5 border border-gray-200 dark:border-white/10">
            {permisos.map((p) => (
              <span
                key={p}
                className="px-2 py-0.5 rounded text-[11px] font-mono bg-white dark:bg-white/10 text-cyan-700 dark:text-cyan-300 border border-cyan-500/20 shadow-2xs"
              >
                {p}
              </span>
            ))}
            {permisos.length === 0 && (
              <span className="text-xs text-gray-400">Este rol no cuenta con permisos registrados.</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default RolePermissionsSummary;
