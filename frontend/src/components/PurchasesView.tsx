import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Truck,
  FileText,
  PackageCheck,
  CreditCard,
  BarChart3,
  Search,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  RefreshCw,
  Edit2,
  Ban,
  ChevronLeft,
  ChevronRight,
  Boxes,
  Building2,
  DollarSign,
  TrendingUp,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';
import { api } from '../services/api';

export type Proveedor = {
  id: number;
  razon_social: string;
  numero_documento: string | null;
  tipo_documento: string | null;
  email: string | null;
  telefono: string | null;
  activo: boolean;
};

type Linea = {
  id: number;
  producto_id: number;
  cantidad_solicitada: string;
  precio_unitario: string;
  total: string;
};

export type Orden = {
  id: number;
  codigo: string;
  proveedor_id: number;
  estado: string;
  estado_pago: string;
  total: string;
  moneda: string;
  detalles: Linea[];
};

export type Recepcion = {
  id: number;
  codigo: string;
  orden_id: number;
  estado: string;
  detalles: {
    id: number;
    orden_detalle_id: number;
    cantidad_recibida: string;
  }[];
};

export type Pago = {
  id: number;
  codigo: string;
  orden_id: number;
  monto: string;
  estado: string;
  medio_pago: string;
};

type Producto = {
  id: number;
  nombre: string;
  sku: string;
};

const currency = (v: string | number) =>
  new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(Number(v) || 0);

const errorText = (e: unknown) =>
  e instanceof Error ? e.message : 'No fue posible completar la operación.';

const initialSupplier = {
  razon_social: '',
  tipo_documento: 'RUC',
  numero_documento: '',
  email: '',
  telefono: '',
};

const getStatusBadgeClass = (estado: string) => {
  switch (estado.toUpperCase()) {
    case 'CONFIRMADA':
    case 'REGISTRADO':
    case 'COMPLETA':
    case 'PAGADO':
      return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20';
    case 'BORRADOR':
    case 'PARCIALMENTE_RECIBIDA':
    case 'PENDIENTE':
      return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20';
    case 'CANCELADA':
    case 'ANULADO':
    case 'RECHAZADA':
      return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20';
    default:
      return 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20';
  }
};

const CHART_COLORS = ['#06b6d4', '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export const PurchasesView: React.FC = () => {
  const [tab, setTab] = useState<'proveedores' | 'ordenes' | 'recepciones' | 'pagos' | 'analisis'>('proveedores');

  const [proveedores, setProveedores] = useState<Proveedor[]>([]);
  const [ordenes, setOrdenes] = useState<Orden[]>([]);
  const [recepciones, setRecepciones] = useState<Recepcion[]>([]);
  const [pagos, setPagos] = useState<Pago[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);

  const [supplier, setSupplier] = useState(initialSupplier);
  const [editId, setEditId] = useState<number | null>(null);

  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // Form states for Orders
  const [proveedorId, setProveedorId] = useState('');
  const [productoId, setProductoId] = useState('');
  const [cantidad, setCantidad] = useState('1');
  const [precio, setPrecio] = useState('');
  const [lineas, setLineas] = useState<
    { producto_id: number; cantidad: string; precio_unitario: string; impuesto: string }[]
  >([]);

  // Form states for Receptions
  const [ordenId, setOrdenId] = useState('');
  const [detailId, setDetailId] = useState('');
  const [recibido, setRecibido] = useState('1');

  // Form states for Payments
  const [pagoOrdenId, setPagoOrdenId] = useState('');
  const [monto, setMonto] = useState('');
  const [medio, setMedio] = useState('TRANSFERENCIA');

  // Pagination states
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 20;

  const [orderPage, setOrderPage] = useState(1);
  const [orderLimit, setOrderLimit] = useState(10);

  const [recepPage, setRecepPage] = useState(1);
  const [recepLimit, setRecepLimit] = useState(10);

  const [pagoPage, setPagoPage] = useState(1);
  const [pagoLimit, setPagoLimit] = useState(10);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [sp, or, re, pa, pr] = await Promise.allSettled([
        api.getProveedores(page, limit, search),
        api.getOrdenesCompra(1, 100),
        api.getRecepcionesCompra(1, 100),
        api.getPagosProveedor(1, 100),
        api.getProductos(1, 100),
      ]);

      const errors: string[] = [];
      if (sp.status === 'fulfilled') {
        setProveedores(sp.value.items);
        setTotal(sp.value.total);
      } else errors.push('proveedores');

      if (or.status === 'fulfilled') setOrdenes(or.value.items);
      else errors.push('órdenes');

      if (re.status === 'fulfilled') setRecepciones(re.value.items);
      else errors.push('recepciones');

      if (pa.status === 'fulfilled') setPagos(pa.value.items);
      else errors.push('pagos');

      if (pr.status === 'fulfilled') setProductos(pr.value.productos);
      else errors.push('productos');

      if (errors.length) {
        setError('No fue posible consultar: ' + errors.join(', ') + '. Revisa los permisos y la consola del backend.');
      }
    } catch (e) {
      setError(errorText(e));
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const supplierName = (id: number) =>
    proveedores.find((p) => p.id === id)?.razon_social || `Proveedor #${id}`;
  const productName = (id: number) =>
    productos.find((p) => p.id === id)?.nombre || `Producto #${id}`;
  const selectedOrder = ordenes.find((o) => String(o.id) === ordenId);

  const totalPurchase = lineas.reduce(
    (s, l) => s + Number(l.cantidad) * Number(l.precio_unitario) + Number(l.impuesto),
    0
  );
  const orderedTotal = ordenes.reduce((a, o) => a + Number(o.total || 0), 0);
  const paidTotal = pagos
    .filter((p) => p.estado === 'REGISTRADO')
    .reduce((a, p) => a + Number(p.monto || 0), 0);

  const porEstado = useMemo(
    () =>
      ordenes.reduce<Record<string, number>>((acc, o) => {
        acc[o.estado] = (acc[o.estado] || 0) + 1;
        return acc;
      }, {}),
    [ordenes]
  );

  const chartData = useMemo(() => {
    return Object.entries(porEstado).map(([estado, cantidad]) => ({
      estado,
      cantidad,
    }));
  }, [porEstado]);

  const guarded = async (action: () => Promise<unknown>, success: string) => {
    setSaving(true);
    setError('');
    setMessage('');
    try {
      await action();
      setMessage(success);
      await refresh();
    } catch (e) {
      setError(errorText(e));
    } finally {
      setSaving(false);
    }
  };

  const saveSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!supplier.razon_social.trim()) {
      setError('Ingresa la razón social.');
      return;
    }
    const payload = Object.fromEntries(
      Object.entries(supplier).map(([k, v]) => [k, v.trim() || null])
    );
    payload.razon_social = supplier.razon_social.trim();

    await guarded(
      () => (editId ? api.editarProveedor(editId, payload) : api.crearProveedor(payload)),
      editId ? 'Proveedor actualizado con éxito.' : 'Proveedor registrado con éxito.'
    );
    setSupplier(initialSupplier);
    setEditId(null);
  };

  const createOrder = () => {
    if (!proveedorId || lineas.length === 0) {
      setError('Selecciona un proveedor y añade al menos un producto.');
      return;
    }
    if (!window.confirm('¿Registrar esta orden de compra? Revisa productos, cantidades e importes antes de continuar.'))
      return;

    void guarded(
      () =>
        api.crearOrdenCompra({
          proveedor_id: Number(proveedorId),
          moneda: 'PEN',
          detalles: lineas,
        }),
      'Orden de compra registrada exitosamente.'
    );
    setProveedorId('');
    setLineas([]);
  };

  const addLine = () => {
    if (!productoId || Number(cantidad) <= 0 || Number(precio) <= 0) {
      setError('Selecciona un producto e introduce cantidad y precio válidos.');
      return;
    }
    setError('');
    setLineas((x) => [
      ...x,
      {
        producto_id: Number(productoId),
        cantidad,
        precio_unitario: precio,
        impuesto: '0',
      },
    ]);
    setProductoId('');
    setCantidad('1');
    setPrecio('');
  };

  const receive = () => {
    if (!ordenId || !detailId || Number(recibido) <= 0) {
      setError('Selecciona una orden, un producto y la cantidad recibida.');
      return;
    }
    if (!window.confirm('¿Confirmar recepción física de mercancía? Esta operación puede afectar al inventario.'))
      return;

    void guarded(
      () =>
        api.crearRecepcionCompra({
          orden_id: Number(ordenId),
          detalles: [{ orden_detalle_id: Number(detailId), cantidad_recibida: recibido }],
          idempotency_key: crypto.randomUUID(),
        }),
      'Recepción registrada con éxito.'
    );
    setDetailId('');
  };

  const pay = () => {
    if (!pagoOrdenId || Number(monto) <= 0) {
      setError('Selecciona una orden y un monto válido.');
      return;
    }
    if (!window.confirm(`¿Registrar pago de ${currency(monto)} al proveedor?`)) return;

    void guarded(
      () =>
        api.crearPagoProveedor({
          orden_id: Number(pagoOrdenId),
          monto,
          medio_pago: medio,
          idempotency_key: crypto.randomUUID(),
        }),
      'Pago registrado con éxito.'
    );
    setMonto('');
  };

  const tabsConfig = [
    { id: 'proveedores', label: 'Proveedores', icon: Building2 },
    { id: 'ordenes', label: 'Órdenes de Compra', icon: FileText },
    { id: 'recepciones', label: 'Recepciones', icon: PackageCheck },
    { id: 'pagos', label: 'Pagos', icon: CreditCard },
    { id: 'analisis', label: 'Indicadores', icon: BarChart3 },
  ] as const;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      {/* Header Section */}
      <div className="glass p-5 md:p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 border border-[#D97843]/20 dark:border-white/10 shadow-sm">
        <div>
          <h2 className="text-2xl md:text-3xl font-black tracking-tight text-slate-950 dark:text-white flex items-center gap-2.5 drop-shadow-sm">
            <Truck className="h-7 w-7 text-[#D97843] dark:text-[#FFA675]" />
            Compras y Proveedores
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 mt-1 font-medium">
            Gestión completa de abastecimiento: órdenes de compra, control de recepciones, pagos e indicadores comerciales.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void refresh()}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 hover:bg-gray-100 dark:hover:bg-white/10 text-gray-700 dark:text-gray-300 transition-colors shadow-sm self-start md:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-cyan-500' : ''}`} />
          {loading ? 'Sincronizando...' : 'Actualizar'}
        </button>
      </div>

      {/* Tabs Bar */}
      <div className="tab-bar overflow-x-auto p-1.5 glass">
        {tabsConfig.map(({ id, label, icon: Icon }) => {
          const isActive = tab === id;
          return (
            <button
              key={id}
              type="button"
              className={`tab-item flex items-center gap-2 whitespace-nowrap ${isActive ? 'active' : ''}`}
              onClick={() => {
                setTab(id);
                setError('');
                setMessage('');
              }}
            >
              <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-500' : 'text-gray-400'}`} />
              <span>{label}</span>
            </button>
          );
        })}
      </div>

      {/* Alerts */}
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

      {/* TAB 1: PROVEEDORES */}
      {tab === 'proveedores' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Supplier Form */}
          <div className="lg:col-span-5">
            <div className="glass p-6 space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-white/5">
                <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Building2 className="h-4 w-4 text-cyan-500" />
                  {editId ? 'Editar proveedor' : 'Nuevo proveedor'}
                </h3>
                {editId && (
                  <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
                    Modo edición
                  </span>
                )}
              </div>

              <form onSubmit={saveSupplier} className="space-y-3.5">
                <div>
                  <label className="input-label">Razón Social *</label>
                  <input
                    required
                    maxLength={200}
                    className="input-field"
                    value={supplier.razon_social}
                    onChange={(e) => setSupplier({ ...supplier, razon_social: e.target.value })}
                    placeholder="Ej. Distribuidora Andina S.A.C."
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="input-label">Tipo Doc.</label>
                    <select
                      className="input-field cursor-pointer"
                      value={supplier.tipo_documento}
                      onChange={(e) => setSupplier({ ...supplier, tipo_documento: e.target.value })}
                    >
                      <option value="RUC">RUC</option>
                      <option value="DNI">DNI</option>
                      <option value="CE">CE</option>
                      <option value="">Sin especificar</option>
                    </select>
                  </div>
                  <div>
                    <label className="input-label">Número Doc.</label>
                    <input
                      className="input-field"
                      value={supplier.numero_documento}
                      onChange={(e) => setSupplier({ ...supplier, numero_documento: e.target.value })}
                      placeholder="20100088899"
                    />
                  </div>
                </div>

                <div>
                  <label className="input-label">Correo Electrónico (opcional)</label>
                  <input
                    type="email"
                    className="input-field"
                    value={supplier.email}
                    onChange={(e) => setSupplier({ ...supplier, email: e.target.value })}
                    placeholder="contacto@proveedor.pe"
                  />
                </div>

                <div>
                  <label className="input-label">Teléfono (opcional)</label>
                  <input
                    className="input-field"
                    value={supplier.telefono}
                    onChange={(e) => setSupplier({ ...supplier, telefono: e.target.value })}
                    placeholder="+51 987 654 321"
                  />
                </div>

                <div className="pt-2 flex items-center gap-3">
                  <button
                    type="submit"
                    disabled={saving}
                    className="flex-1 px-4 py-2.5 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {saving ? 'Guardando...' : editId ? 'Guardar cambios' : 'Registrar proveedor'}
                  </button>
                  {editId && (
                    <button
                      type="button"
                      onClick={() => {
                        setSupplier(initialSupplier);
                        setEditId(null);
                      }}
                      className="px-3.5 py-2.5 rounded-lg text-sm font-medium border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/5 text-gray-700 dark:text-gray-300 transition-colors"
                    >
                      Cancelar
                    </button>
                  )}
                </div>
              </form>
            </div>
          </div>

          {/* Supplier Directory List */}
          <div className="lg:col-span-7">
            <div className="glass p-6 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                  Directorio de proveedores
                </h3>
                <div className="relative min-w-[220px]">
                  <Search className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                  <input
                    value={search}
                    onChange={(e) => {
                      setPage(1);
                      setSearch(e.target.value);
                    }}
                    placeholder="Buscar razón o RUC..."
                    className="input-field pl-9 py-1.5 text-xs"
                  />
                </div>
              </div>

              <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-white/10">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Proveedor</th>
                      <th>Documento</th>
                      <th>Contacto</th>
                      <th>Estado</th>
                      <th className="text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {proveedores.map((p) => (
                      <tr key={p.id}>
                        <td className="font-medium text-slate-900 dark:text-white">
                          {p.razon_social}
                        </td>
                        <td>
                          <span className="text-xs font-mono bg-gray-100 dark:bg-white/5 px-2 py-0.5 rounded">
                            {p.tipo_documento ? `${p.tipo_documento}: ` : ''}
                            {p.numero_documento || 'Sin doc.'}
                          </span>
                        </td>
                        <td className="text-xs">
                          {p.email && <div>{p.email}</div>}
                          {p.telefono && <div className="text-gray-400">{p.telefono}</div>}
                          {!p.email && !p.telefono && <span className="text-gray-400">—</span>}
                        </td>
                        <td>
                          <span
                            className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                              p.activo
                                ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                                : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                            }`}
                          >
                            {p.activo ? 'Activo' : 'Inactivo'}
                          </span>
                        </td>
                        <td className="text-right whitespace-nowrap">
                          <div className="inline-flex items-center gap-1.5 justify-end">
                            <button
                              type="button"
                              onClick={() => {
                                setEditId(p.id);
                                setSupplier({
                                  razon_social: p.razon_social,
                                  tipo_documento: p.tipo_documento || 'RUC',
                                  numero_documento: p.numero_documento || '',
                                  email: p.email || '',
                                  telefono: p.telefono || '',
                                });
                              }}
                              className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-white/10 text-cyan-600 dark:text-cyan-400 transition-colors"
                              title="Editar proveedor"
                            >
                              <Edit2 className="h-3.5 w-3.5" />
                            </button>
                            {p.activo && (
                              <button
                                type="button"
                                disabled={saving}
                                onClick={() => {
                                  if (window.confirm(`¿Desactivar al proveedor ${p.razon_social}?`)) {
                                    void guarded(
                                      () => api.desactivarProveedor(p.id),
                                      'Proveedor desactivado con éxito.'
                                    );
                                  }
                                }}
                                className="p-1.5 rounded-md hover:bg-rose-50 dark:hover:bg-rose-500/10 text-rose-600 dark:text-rose-400 transition-colors disabled:opacity-40"
                                title="Desactivar proveedor"
                              >
                                <Ban className="h-3.5 w-3.5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                    {!proveedores.length && (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-gray-400 text-sm">
                          No hay proveedores para mostrar en esta página o criterio.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="pagination-bar">
                <span>
                  Página {page} de {Math.max(1, Math.ceil(total / limit))} · {total} proveedores
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={page <= 1}
                    onClick={() => setPage((v) => v - 1)}
                    className="pagination-btn flex items-center gap-1"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                  </button>
                  <button
                    type="button"
                    disabled={page * limit >= total}
                    onClick={() => setPage((v) => v + 1)}
                    className="pagination-btn flex items-center gap-1"
                  >
                    Siguiente <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: ORDENES DE COMPRA */}
      {tab === 'ordenes' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Create Order Form */}
          <div className="lg:col-span-5">
            <div className="glass p-6 space-y-4">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-white/5">
                <FileText className="h-4 w-4 text-cyan-500" />
                Nueva orden de compra
              </h3>

              <div className="space-y-3.5">
                <div>
                  <label className="input-label">Proveedor Seleccionado *</label>
                  <select
                    className="input-field cursor-pointer"
                    value={proveedorId}
                    onChange={(e) => setProveedorId(e.target.value)}
                  >
                    <option value="">Selecciona un proveedor activo</option>
                    {proveedores
                      .filter((p) => p.activo)
                      .map((p) => (
                        <option value={p.id} key={p.id}>
                          {p.razon_social}
                        </option>
                      ))}
                  </select>
                </div>

                <div className="p-3.5 rounded-lg border border-dashed border-gray-200 dark:border-white/10 bg-gray-50/50 dark:bg-white/[0.02] space-y-3">
                  <span className="text-xs font-semibold uppercase tracking-wider text-cyan-600 dark:text-cyan-400">
                    Agregar producto a la orden
                  </span>
                  <div>
                    <label className="input-label">Producto</label>
                    <select
                      className="input-field cursor-pointer text-xs"
                      value={productoId}
                      onChange={(e) => setProductoId(e.target.value)}
                    >
                      <option value="">Selecciona un producto</option>
                      {productos.map((p) => (
                        <option value={p.id} key={p.id}>
                          {p.nombre} ({p.sku})
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="input-label">Cantidad</label>
                      <input
                        type="number"
                        min="0.001"
                        step="0.001"
                        className="input-field text-xs"
                        value={cantidad}
                        onChange={(e) => setCantidad(e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="input-label">Precio Unit. (S/)</label>
                      <input
                        type="number"
                        min="0.01"
                        step="0.01"
                        className="input-field text-xs"
                        value={precio}
                        onChange={(e) => setPrecio(e.target.value)}
                        placeholder="0.00"
                      />
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={addLine}
                    className="w-full inline-flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-medium border border-cyan-500/30 text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20 transition-colors"
                  >
                    <Plus className="h-3.5 w-3.5" /> Añadir a la lista
                  </button>
                </div>

                {/* Added items list */}
                {lineas.length > 0 && (
                  <div className="space-y-2">
                    <span className="text-xs font-medium text-gray-500">Líneas en preparación:</span>
                    <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                      {lineas.map((l, i) => (
                        <div
                          key={i}
                          className="flex items-center justify-between p-2 rounded-lg bg-white dark:bg-white/5 border border-gray-100 dark:border-white/5 text-xs"
                        >
                          <div className="truncate pr-2">
                            <span className="font-medium text-slate-800 dark:text-gray-200">
                              {productName(l.producto_id)}
                            </span>
                            <div className="text-gray-400">
                              {l.cantidad} un. × {currency(l.precio_unitario)}
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() => setLineas((ls) => ls.filter((_, j) => i !== j))}
                            className="p-1 rounded text-rose-500 hover:bg-rose-500/10"
                            title="Quitar ítem"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="p-3 rounded-lg bg-cyan-500/5 dark:bg-cyan-950/20 border border-cyan-500/20 flex items-center justify-between">
                  <span className="text-xs text-cyan-800 dark:text-cyan-300 font-medium">Total estimado:</span>
                  <span className="text-base font-bold text-cyan-600 dark:text-cyan-400">
                    {currency(totalPurchase)}
                  </span>
                </div>

                <p className="text-[11px] text-gray-400 leading-tight">
                  La orden se registra con impuesto S/ 0 por línea; verifica las tasas aplicables antes de confirmarla.
                </p>

                <button
                  type="button"
                  disabled={saving || !lineas.length || !proveedorId}
                  onClick={createOrder}
                  className="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Registrando orden...' : 'Registrar orden de compra'}
                </button>
              </div>
            </div>
          </div>

          {/* Orders History List */}
          <div className="lg:col-span-7">
            <div className="glass p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                  Órdenes registradas
                </h3>
                <span className="text-xs text-gray-400">Total: {ordenes.length}</span>
              </div>

              <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-white/10">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th>Proveedor</th>
                      <th>Estado</th>
                      <th>Total</th>
                      <th className="text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {ordenes
                      .slice((orderPage - 1) * orderLimit, orderPage * orderLimit)
                      .map((o) => (
                        <tr key={o.id}>
                          <td className="font-mono font-semibold text-slate-900 dark:text-white">
                            {o.codigo}
                          </td>
                          <td className="text-xs max-w-[160px] truncate">
                            {supplierName(o.proveedor_id)}
                          </td>
                          <td>
                            <span
                              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(
                                o.estado
                              )}`}
                            >
                              {o.estado}
                            </span>
                          </td>
                          <td className="font-semibold text-slate-900 dark:text-white">
                            {currency(o.total)}
                          </td>
                          <td className="text-right whitespace-nowrap">
                            {o.estado === 'BORRADOR' && (
                              <div className="inline-flex items-center gap-1.5 justify-end">
                                <button
                                  type="button"
                                  disabled={saving}
                                  onClick={() => {
                                    if (window.confirm(`¿Confirmar la orden ${o.codigo}?`)) {
                                      void guarded(
                                        () => api.confirmarOrdenCompra(o.id),
                                        'Orden confirmada con éxito.'
                                      );
                                    }
                                  }}
                                  className="px-2.5 py-1 rounded text-xs font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 hover:bg-emerald-500/20 transition-colors"
                                >
                                  Confirmar
                                </button>
                                <button
                                  type="button"
                                  disabled={saving}
                                  onClick={() => {
                                    if (window.confirm(`¿Cancelar la orden ${o.codigo}?`)) {
                                      void guarded(
                                        () => api.cancelarOrdenCompra(o.id),
                                        'Orden cancelada con éxito.'
                                      );
                                    }
                                  }}
                                  className="px-2.5 py-1 rounded text-xs font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors"
                                >
                                  Cancelar
                                </button>
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    {!ordenes.length && (
                      <tr>
                        <td colSpan={5} className="py-8 text-center text-gray-400 text-sm">
                          No hay órdenes de compra registradas.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Order pagination */}
              <div className="pagination-bar">
                <div className="flex items-center gap-3">
                  <span>
                    Mostrando {Math.min(ordenes.length, orderLimit * (orderPage - 1) + 1)}–
                    {Math.min(ordenes.length, orderLimit * orderPage)} de {ordenes.length}
                  </span>
                  <label className="flex items-center gap-1 text-xs">
                    Por pág.:
                    <select
                      className="bg-transparent border border-gray-200 dark:border-white/10 rounded px-1.5 py-0.5"
                      value={orderLimit}
                      onChange={(e) => {
                        setOrderLimit(Number(e.target.value));
                        setOrderPage(1);
                      }}
                    >
                      <option value={5}>5</option>
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                    </select>
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={orderPage <= 1}
                    onClick={() => setOrderPage((v) => v - 1)}
                    className="pagination-btn flex items-center gap-1"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                  </button>
                  <button
                    type="button"
                    disabled={orderPage * orderLimit >= ordenes.length}
                    onClick={() => setOrderPage((v) => v + 1)}
                    className="pagination-btn flex items-center gap-1"
                  >
                    Siguiente <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: RECEPCIONES */}
      {tab === 'recepciones' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Receive Form */}
          <div className="lg:col-span-5">
            <div className="glass p-6 space-y-4">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-white/5">
                <PackageCheck className="h-4 w-4 text-cyan-500" />
                Registrar recepción física
              </h3>
              <p className="text-xs text-gray-400">
                Selecciona la orden confirmada y la línea de producto que ingresó físicamente al almacén.
              </p>

              <div className="space-y-3.5">
                <div>
                  <label className="input-label">Orden de Compra Confirmada *</label>
                  <select
                    className="input-field cursor-pointer"
                    value={ordenId}
                    onChange={(e) => {
                      setOrdenId(e.target.value);
                      setDetailId('');
                    }}
                  >
                    <option value="">Selecciona una orden</option>
                    {ordenes
                      .filter((o) => o.estado === 'CONFIRMADA' || o.estado === 'PARCIALMENTE_RECIBIDA')
                      .map((o) => (
                        <option key={o.id} value={o.id}>
                          {o.codigo} · {supplierName(o.proveedor_id)}
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <label className="input-label">Producto / Línea de la Orden *</label>
                  <select
                    className="input-field cursor-pointer text-xs"
                    value={detailId}
                    onChange={(e) => setDetailId(e.target.value)}
                    disabled={!selectedOrder}
                  >
                    <option value="">
                      {selectedOrder ? 'Selecciona una línea' : 'Primero selecciona una orden'}
                    </option>
                    {selectedOrder?.detalles.map((d) => (
                      <option key={d.id} value={d.id}>
                        {productName(d.producto_id)} · Solicitado: {d.cantidad_solicitada}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="input-label">Cantidad Recibida *</label>
                  <input
                    type="number"
                    min="0.001"
                    step="0.001"
                    className="input-field"
                    value={recibido}
                    onChange={(e) => setRecibido(e.target.value)}
                  />
                </div>

                <button
                  type="button"
                  disabled={saving || !ordenId || !detailId || Number(recibido) <= 0}
                  onClick={receive}
                  className="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Registrando recepción...' : 'Confirmar recepción física'}
                </button>
              </div>
            </div>
          </div>

          {/* Receptions History */}
          <div className="lg:col-span-7">
            <div className="glass p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                  Historial de recepciones
                </h3>
                <span className="text-xs text-gray-400">Total: {recepciones.length}</span>
              </div>

              <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-white/10">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th>Orden ID</th>
                      <th>Estado</th>
                      <th>Líneas Recibidas</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recepciones
                      .slice((recepPage - 1) * recepLimit, recepPage * recepLimit)
                      .map((r) => (
                        <tr key={r.id}>
                          <td className="font-mono font-semibold text-slate-900 dark:text-white">
                            {r.codigo}
                          </td>
                          <td className="text-xs">
                            <span className="font-mono px-2 py-0.5 rounded bg-gray-100 dark:bg-white/5">
                              #{r.orden_id}
                            </span>
                          </td>
                          <td>
                            <span
                              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(
                                r.estado
                              )}`}
                            >
                              {r.estado}
                            </span>
                          </td>
                          <td className="text-xs text-gray-400">
                            {r.detalles?.length || 0} artículo(s)
                          </td>
                        </tr>
                      ))}
                    {!recepciones.length && (
                      <tr>
                        <td colSpan={4} className="py-8 text-center text-gray-400 text-sm">
                          No hay recepciones registradas en el sistema.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="pagination-bar">
                <div className="flex items-center gap-3">
                  <span>
                    Mostrando {Math.min(recepciones.length, recepLimit * (recepPage - 1) + 1)}–
                    {Math.min(recepciones.length, recepLimit * recepPage)} de {recepciones.length}
                  </span>
                  <label className="flex items-center gap-1 text-xs">
                    Por pág.:
                    <select
                      className="bg-transparent border border-gray-200 dark:border-white/10 rounded px-1.5 py-0.5"
                      value={recepLimit}
                      onChange={(e) => {
                        setRecepLimit(Number(e.target.value));
                        setRecepPage(1);
                      }}
                    >
                      <option value={5}>5</option>
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                    </select>
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={recepPage <= 1}
                    onClick={() => setRecepPage((v) => v - 1)}
                    className="pagination-btn flex items-center gap-1"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                  </button>
                  <button
                    type="button"
                    disabled={recepPage * recepLimit >= recepciones.length}
                    onClick={() => setRecepPage((v) => v + 1)}
                    className="pagination-btn flex items-center gap-1"
                  >
                    Siguiente <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: PAGOS */}
      {tab === 'pagos' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Payment Form */}
          <div className="lg:col-span-5">
            <div className="glass p-6 space-y-4">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-white/5">
                <CreditCard className="h-4 w-4 text-cyan-500" />
                Registrar pago a proveedor
              </h3>

              <div className="space-y-3.5">
                <div>
                  <label className="input-label">Orden a pagar *</label>
                  <select
                    className="input-field cursor-pointer"
                    value={pagoOrdenId}
                    onChange={(e) => setPagoOrdenId(e.target.value)}
                  >
                    <option value="">Selecciona una orden activa</option>
                    {ordenes
                      .filter((o) => o.estado !== 'CANCELADA' && o.estado !== 'BORRADOR')
                      .map((o) => (
                        <option value={o.id} key={o.id}>
                          {o.codigo} · {supplierName(o.proveedor_id)} ({currency(o.total)})
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <label className="input-label">Monto a pagar (S/) *</label>
                  <input
                    type="number"
                    min="0.01"
                    step="0.01"
                    className="input-field"
                    value={monto}
                    onChange={(e) => setMonto(e.target.value)}
                    placeholder="0.00"
                  />
                </div>

                <div>
                  <label className="input-label">Medio de Pago *</label>
                  <select
                    className="input-field cursor-pointer"
                    value={medio}
                    onChange={(e) => setMedio(e.target.value)}
                  >
                    <option value="TRANSFERENCIA">Transferencia Bancaria</option>
                    <option value="EFECTIVO">Efectivo</option>
                    <option value="TARJETA">Tarjeta</option>
                    <option value="YAPE">Yape</option>
                    <option value="PLIN">Plin</option>
                  </select>
                </div>

                <button
                  type="button"
                  disabled={saving || !pagoOrdenId || Number(monto) <= 0}
                  onClick={pay}
                  className="w-full py-2.5 px-4 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? 'Registrando pago...' : 'Registrar pago'}
                </button>
              </div>
            </div>
          </div>

          {/* Payments History */}
          <div className="lg:col-span-7">
            <div className="glass p-6 space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                  Historial de pagos
                </h3>
                <span className="text-xs text-gray-400">Total: {pagos.length}</span>
              </div>

              <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-white/10">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th>Orden ID</th>
                      <th>Monto</th>
                      <th>Medio</th>
                      <th>Estado</th>
                      <th className="text-right">Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {pagos
                      .slice((pagoPage - 1) * pagoLimit, pagoPage * pagoLimit)
                      .map((p) => (
                        <tr key={p.id}>
                          <td className="font-mono font-semibold text-slate-900 dark:text-white">
                            {p.codigo}
                          </td>
                          <td className="text-xs font-mono">#{p.orden_id}</td>
                          <td className="font-semibold text-slate-900 dark:text-white">
                            {currency(p.monto)}
                          </td>
                          <td className="text-xs">{p.medio_pago}</td>
                          <td>
                            <span
                              className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${getStatusBadgeClass(
                                p.estado
                              )}`}
                            >
                              {p.estado}
                            </span>
                          </td>
                          <td className="text-right whitespace-nowrap">
                            {p.estado === 'REGISTRADO' && (
                              <button
                                type="button"
                                disabled={saving}
                                onClick={() => {
                                  if (window.confirm(`¿Anular el pago ${p.codigo}?`)) {
                                    void guarded(
                                      () => api.anularPagoProveedor(p.id),
                                      'Pago anulado con éxito.'
                                    );
                                  }
                                }}
                                className="px-2.5 py-1 rounded text-xs font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20 hover:bg-rose-500/20 transition-colors"
                              >
                                Anular
                              </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    {!pagos.length && (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-gray-400 text-sm">
                          No hay pagos registrados.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="pagination-bar">
                <div className="flex items-center gap-3">
                  <span>
                    Mostrando {Math.min(pagos.length, pagoLimit * (pagoPage - 1) + 1)}–
                    {Math.min(pagos.length, pagoLimit * pagoPage)} de {pagos.length}
                  </span>
                  <label className="flex items-center gap-1 text-xs">
                    Por pág.:
                    <select
                      className="bg-transparent border border-gray-200 dark:border-white/10 rounded px-1.5 py-0.5"
                      value={pagoLimit}
                      onChange={(e) => {
                        setPagoLimit(Number(e.target.value));
                        setPagoPage(1);
                      }}
                    >
                      <option value={5}>5</option>
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                    </select>
                  </label>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={pagoPage <= 1}
                    onClick={() => setPagoPage((v) => v - 1)}
                    className="pagination-btn flex items-center gap-1"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                  </button>
                  <button
                    type="button"
                    disabled={pagoPage * pagoLimit >= pagos.length}
                    onClick={() => setPagoPage((v) => v + 1)}
                    className="pagination-btn flex items-center gap-1"
                  >
                    Siguiente <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: ANALISIS */}
      {tab === 'analisis' && (
        <div className="space-y-6">
          {/* KPI Cards Row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="glass p-5 space-y-2">
              <div className="flex items-center justify-between text-gray-500 dark:text-gray-400">
                <span className="text-xs font-semibold uppercase tracking-wider">Órdenes</span>
                <FileText className="h-4 w-4 text-cyan-500" />
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-white">
                {ordenes.length}
              </div>
              <p className="text-xs text-gray-400">Consultadas en la muestra</p>
            </div>

            <div className="glass p-5 space-y-2">
              <div className="flex items-center justify-between text-gray-500 dark:text-gray-400">
                <span className="text-xs font-semibold uppercase tracking-wider">Total Órdenes</span>
                <DollarSign className="h-4 w-4 text-emerald-500" />
              </div>
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">
                {currency(orderedTotal)}
              </div>
              <p className="text-xs text-gray-400">Monto total comprometido</p>
            </div>

            <div className="glass p-5 space-y-2">
              <div className="flex items-center justify-between text-gray-500 dark:text-gray-400">
                <span className="text-xs font-semibold uppercase tracking-wider">Pagos Reg.</span>
                <CreditCard className="h-4 w-4 text-blue-500" />
              </div>
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                {currency(paidTotal)}
              </div>
              <p className="text-xs text-gray-400">Pagos en estado registrado</p>
            </div>

            <div className="glass p-5 space-y-2">
              <div className="flex items-center justify-between text-gray-500 dark:text-gray-400">
                <span className="text-xs font-semibold uppercase tracking-wider">Recepciones</span>
                <Boxes className="h-4 w-4 text-amber-500" />
              </div>
              <div className="text-2xl font-bold text-slate-900 dark:text-white">
                {recepciones.length}
              </div>
              <p className="text-xs text-gray-400">Ingresos físicos procesados</p>
            </div>
          </div>

          {/* Bar Chart & Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            <div className="lg:col-span-8 glass p-6 space-y-4">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-cyan-500" />
                Distribución de órdenes por estado
              </h3>

              {chartData.length > 0 ? (
                <div className="h-72 w-full pt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" opacity={0.15} />
                      <XAxis
                        dataKey="estado"
                        tick={{ fontSize: 11, fill: '#888' }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <YAxis
                        allowDecimals={false}
                        tick={{ fontSize: 11, fill: '#888' }}
                        tickLine={false}
                        axisLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: 'rgba(18, 18, 26, 0.95)',
                          borderRadius: '8px',
                          border: '1px solid rgba(255,255,255,0.1)',
                          color: '#fff',
                          fontSize: '12px',
                        }}
                      />
                      <Bar dataKey="cantidad" radius={[6, 6, 0, 0]}>
                        {chartData.map((_, index) => (
                          <Cell
                            key={`cell-${index}`}
                            fill={CHART_COLORS[index % CHART_COLORS.length]}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="py-12 text-center text-sm text-gray-400">
                  Registra órdenes para visualizar el gráfico de distribución.
                </div>
              )}
            </div>

            <div className="lg:col-span-4 glass p-6 space-y-4">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                Resumen por Estado
              </h3>
              <div className="space-y-3">
                {Object.entries(porEstado).map(([state, count], idx) => {
                  const pct = ordenes.length ? Math.round((count / ordenes.length) * 100) : 0;
                  return (
                    <div key={state} className="space-y-1">
                      <div className="flex items-center justify-between text-xs">
                        <span className="font-medium text-slate-800 dark:text-gray-300">{state}</span>
                        <span className="text-gray-400">
                          {count} ({pct}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-100 dark:bg-white/5 h-2 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all duration-500"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: CHART_COLORS[idx % CHART_COLORS.length],
                          }}
                        />
                      </div>
                    </div>
                  );
                })}
                {!ordenes.length && (
                  <p className="text-xs text-gray-400 py-4 text-center">
                    No hay datos suficientes para el desglose.
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </motion.div>
  );
};
