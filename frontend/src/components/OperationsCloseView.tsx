import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Warehouse,
  History,
  Users,
  Search,
  Sliders,
  CheckCircle2,
  AlertCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Info,
  ShieldCheck,
  Package,
  AlertTriangle,
  Boxes,
  ArrowRight,
  BarChart2,
  PieChart as PieChartIcon,
  Sparkles,
  ArrowUpRight,
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  CartesianGrid,
  Cell,
  PieChart,
  Pie,
  Legend,
} from 'recharts';
import { api } from '../services/api';

type Item = {
  inventario_id: number | null;
  producto_id: number;
  producto: string;
  sku: string;
  cantidad_disponible: string;
};

type Movimiento = {
  id: number;
  producto_id: number;
  tipo: string;
  cantidad_delta: string;
  motivo: string;
  referencia: string | null;
  fecha: string;
};

type Vendedor = {
  id: number;
  nombre: string;
  email: string;
  activo: boolean;
};

const PAGE = 15;
const UMBRAL_SEGURIDAD = 30; // Unidades objetivo para nivel de reposición seguro

// Tooltip estilizado para el gráfico de barras comparativo
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const ReposicionTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="p-3 rounded-xl bg-slate-900/95 text-white border border-white/10 shadow-2xl backdrop-blur-xl text-xs space-y-1.5 min-w-[210px]">
        <div className="font-semibold text-white border-b border-white/10 pb-1 flex items-center justify-between gap-2">
          <span className="truncate max-w-[140px]">{data.nombreCompleto || data.nombre}</span>
          <span className="font-mono text-[10px] text-cyan-400 bg-cyan-500/10 px-1.5 py-0.5 rounded shrink-0">
            {data.sku}
          </span>
        </div>
        <div className="flex items-center justify-between text-gray-300">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-cyan-400" /> Stock disponible actual:
          </span>
          <strong className="text-white font-mono">{data.stockActual} uds</strong>
        </div>
        <div className="flex items-center justify-between text-gray-300">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-amber-400" /> Unidades a rellenar:
          </span>
          <strong className="text-amber-400 font-mono">+{data.unidadesARellenar} uds</strong>
        </div>
        <div className="pt-1 text-[10px] text-gray-400 border-t border-white/5 flex items-center justify-between">
          <span>Meta seguridad empresa:</span>
          <span className="font-mono font-medium text-gray-300">{UMBRAL_SEGURIDAD} uds</span>
        </div>
      </div>
    );
  }
  return null;
};

// Tooltip para el gráfico de dona
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const DonutTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0];
    return (
      <div className="p-2.5 rounded-lg bg-slate-900/95 text-white border border-white/10 shadow-xl backdrop-blur-xl text-xs">
        <div className="font-medium text-gray-300">{data.name}</div>
        <div className="text-sm font-bold text-cyan-400 font-mono mt-0.5">
          {data.value} productos
        </div>
      </div>
    );
  }
  return null;
};

export const OperationsCloseView: React.FC = () => {
  const [tab, setTab] = useState<'stock' | 'movimientos' | 'vendedores'>('stock');
  const [pagina, setPagina] = useState(1);
  const [busqueda, setBusqueda] = useState('');
  const [filtroStock, setFiltroStock] = useState<'todos' | 'por_rellenar' | 'optimo'>('todos');
  const [vistaGrafica, setVistaGrafica] = useState<'deficit' | 'salud'>('deficit');

  const [items, setItems] = useState<Item[]>([]);
  const [allStock, setAllStock] = useState<Item[]>([]);
  const [movimientos, setMovimientos] = useState<Movimiento[]>([]);
  const [vendedores, setVendedores] = useState<Vendedor[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');

  // Form states for inventory adjustment
  const [producto, setProducto] = useState('');
  const [delta, setDelta] = useState('');
  const [motivo, setMotivo] = useState('');
  const [referencia, setReferencia] = useState('');
  const [guardando, setGuardando] = useState(false);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let vivo = true;
    setLoading(true);
    setError('');

    (async () => {
      try {
        if (tab === 'stock') {
          // Consultar página actual y catálogo completo para el gráfico de reposición
          const [resPaginada, resCompleta] = await Promise.all([
            api.listarInventarioOperativo(pagina, PAGE, busqueda),
            api.listarInventarioOperativo(1, 100, ''),
          ]);

          if (vivo) {
            setItems(resPaginada.items);
            setTotal(resPaginada.total);
            setAllStock(resCompleta.items);
          }
        } else if (tab === 'movimientos') {
          const r = await api.listarMovimientosOperativos(pagina, PAGE);
          if (vivo) {
            setMovimientos(r.items);
            setTotal(r.total);
          }
        } else {
          const r = await api.listarVendedoresOperativos(pagina, PAGE, busqueda);
          if (vivo) {
            setVendedores(r.items);
            setTotal(r.total);
          }
        }
      } catch (e) {
        if (vivo) setError(e instanceof Error ? e.message : 'No se pudo consultar el módulo.');
      } finally {
        if (vivo) setLoading(false);
      }
    })();

    return () => {
      vivo = false;
    };
  }, [tab, pagina, busqueda, version]);

  // Cálculos estadísticos para reposición y gráficas profesionales
  const statsReposicion = useMemo(() => {
    const fuente = allStock.length > 0 ? allStock : items;

    const sinStock = fuente.filter((p) => (Number(p.cantidad_disponible) || 0) <= 0);
    const stockBajo = fuente.filter((p) => {
      const q = Number(p.cantidad_disponible) || 0;
      return q > 0 && q <= 20;
    });
    const stockOptimo = fuente.filter((p) => (Number(p.cantidad_disponible) || 0) > 20);

    const totalPorRellenar = sinStock.length + stockBajo.length;
    const totalItems = fuente.length;
    const tasaSalud = totalItems > 0 ? Math.round((stockOptimo.length / totalItems) * 100) : 100;

    const unidadesTotalesARellenar = fuente.reduce((acc, p) => {
      const q = Number(p.cantidad_disponible) || 0;
      return acc + Math.max(0, UMBRAL_SEGURIDAD - q);
    }, 0);

    // Top productos con mayor urgencia de reabastecimiento
    const topParaRellenar = fuente
      .map((p) => {
        const q = Number(p.cantidad_disponible) || 0;
        const deficit = Math.max(0, UMBRAL_SEGURIDAD - q);
        return {
          productoId: p.producto_id,
          nombre: p.producto.length > 18 ? `${p.producto.slice(0, 16)}...` : p.producto,
          nombreCompleto: p.producto,
          sku: p.sku,
          stockActual: q,
          unidadesARellenar: deficit,
          urgencia: q <= 0 ? 2 : q <= 10 ? 1 : 0,
        };
      })
      .filter((p) => p.unidadesARellenar > 0)
      .sort((a, b) => b.unidadesARellenar - a.unidadesARellenar)
      .slice(0, 7);

    const pieData = [
      { name: 'Sin stock (Urgente)', value: sinStock.length, color: '#ef4444' },
      { name: 'Stock bajo (Por reponer)', value: stockBajo.length, color: '#f59e0b' },
      { name: 'Stock óptimo', value: stockOptimo.length, color: '#10b981' },
    ].filter((d) => d.value > 0);

    return {
      sinStock,
      stockBajo,
      stockOptimo,
      totalPorRellenar,
      totalItems,
      tasaSalud,
      unidadesTotalesARellenar,
      topParaRellenar,
      pieData,
    };
  }, [allStock, items]);

  // Filtrado local de la tabla por estado si se selecciona un chip
  const itemsMostrados = useMemo(() => {
    if (filtroStock === 'por_rellenar') {
      return items.filter((p) => (Number(p.cantidad_disponible) || 0) <= 20);
    }
    if (filtroStock === 'optimo') {
      return items.filter((p) => (Number(p.cantidad_disponible) || 0) > 20);
    }
    return items;
  }, [items, filtroStock]);

  const ajustar = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = Number(producto);
    const n = Number(delta);

    if (
      !Number.isInteger(id) ||
      id <= 0 ||
      !Number.isFinite(n) ||
      n === 0 ||
      motivo.trim().length < 8
    ) {
      setError(
        'Datos de ajuste inválidos: producto obligatorio, variación distinta de 0 y motivo con mínimo 8 caracteres.'
      );
      return;
    }

    setGuardando(true);
    setError('');
    setMensaje('');

    try {
      const resp = await api.ajustarInventario({
        producto_id: id,
        cantidad_delta: delta.trim(),
        motivo: motivo.trim(),
        referencia: referencia.trim() ? referencia.trim() : undefined,
      });

      setMensaje(
        `Ajuste registrado exitosamente para producto #${resp.producto_id}: Stock actualizado de ${resp.stock_anterior} a ${resp.stock_actual} (${resp.delta}).`
      );
      setProducto('');
      setDelta('');
      setMotivo('');
      setReferencia('');
      setVersion((v) => v + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al registrar el ajuste de inventario.');
    } finally {
      setGuardando(false);
    }
  };

  const seleccionarProductoParaAjuste = (id: number) => {
    setProducto(String(id));
    const formElem = document.getElementById('formulario-ajuste');
    if (formElem) {
      formElem.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const cambiar = (t: 'stock' | 'movimientos' | 'vendedores') => {
    setTab(t);
    setPagina(1);
    setBusqueda('');
    setFiltroStock('todos');
    setError('');
    setMensaje('');
  };

  const max = Math.max(1, Math.ceil(total / PAGE));

  const renderStockPill = (qtyStr: string) => {
    const qty = Number(qtyStr) || 0;
    if (qty > 20) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          Óptimo ({qty})
        </span>
      );
    } else if (qty > 0) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
          Bajo ({qty})
        </span>
      );
    } else {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
          <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
          Sin stock ({qty})
        </span>
      );
    }
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
          <h2 className="text-2xl md:text-3xl font-black tracking-tight text-slate-950 dark:text-white flex items-center gap-3 drop-shadow-sm">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#2E6F5C] via-[#3D8972] to-[#1E5041] flex items-center justify-center text-white shadow-md shadow-[#2E6F5C]/20">
              <Warehouse className="h-5 w-5" />
            </div>
            <span>Operación de Inventario y Almacén</span>
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 mt-1 font-medium pl-0.5">
            Monitoreo en tiempo real de existencias, necesidades de reposición y trazabilidad de movimientos.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setVersion((v) => v + 1)}
          disabled={loading}
          className="inline-flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium border border-gray-200 dark:border-white/10 bg-white dark:bg-white/5 hover:bg-gray-100 dark:hover:bg-white/10 text-gray-700 dark:text-gray-300 transition-colors shadow-sm self-start md:self-auto"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-cyan-500' : ''}`} />
          {loading ? 'Consultando...' : 'Recargar datos'}
        </button>
      </div>

      {/* Tabs Principales */}
      <div className="tab-bar overflow-x-auto p-1.5 glass">
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${tab === 'stock' ? 'active' : ''}`}
          onClick={() => cambiar('stock')}
        >
          <Warehouse className={`h-4 w-4 ${tab === 'stock' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>Existencias y reposición</span>
        </button>
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${tab === 'movimientos' ? 'active' : ''}`}
          onClick={() => cambiar('movimientos')}
        >
          <History className={`h-4 w-4 ${tab === 'movimientos' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>Historial de movimientos</span>
        </button>
        <button
          type="button"
          className={`tab-item flex items-center gap-2 ${tab === 'vendedores' ? 'active' : ''}`}
          onClick={() => cambiar('vendedores')}
        >
          <Users className={`h-4 w-4 ${tab === 'vendedores' ? 'text-cyan-500' : 'text-gray-400'}`} />
          <span>Directorio de vendedores</span>
        </button>
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

        {mensaje && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-success"
            role="status"
          >
            <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
            <div className="flex-1 text-sm font-medium">{mensaje}</div>
            <button
              type="button"
              onClick={() => setMensaje('')}
              className="text-emerald-400 hover:text-emerald-600 dark:hover:text-emerald-300"
            >
              <XCircle className="h-4 w-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ======================================================== */}
      {/* VISTA 1: EXISTENCIAS (DISTRIBUCIÓN EQUITATIVA 50% / 50%) */}
      {/* ======================================================== */}
      {tab === 'stock' && (
        <div className="space-y-6">
          {/* Tarjetas KPI Superiores Resumen de Reposición */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="glass p-4 rounded-xl border border-gray-200/50 dark:border-white/10 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  Por Rellenar
                </span>
                <div className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">
                  {statsReposicion.totalPorRellenar}
                  <span className="text-xs font-normal text-gray-400 ml-1">productos</span>
                </div>
                <span className="text-[10px] text-amber-500 font-medium">
                  {statsReposicion.sinStock.length} agotados · {statsReposicion.stockBajo.length} bajos
                </span>
              </div>
              <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-500">
                <AlertTriangle className="h-5 w-5" />
              </div>
            </div>

            <div className="glass p-4 rounded-xl border border-gray-200/50 dark:border-white/10 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  Déficit a Reponer
                </span>
                <div className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">
                  +{statsReposicion.unidadesTotalesARellenar}
                  <span className="text-xs font-normal text-gray-400 ml-1">unidades</span>
                </div>
                <span className="text-[10px] text-gray-400">Para meta de 30 uds por ítem</span>
              </div>
              <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-500">
                <Boxes className="h-5 w-5" />
              </div>
            </div>

            <div className="glass p-4 rounded-xl border border-gray-200/50 dark:border-white/10 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  Stock Óptimo
                </span>
                <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  {statsReposicion.stockOptimo.length}
                  <span className="text-xs font-normal text-gray-400 ml-1">productos</span>
                </div>
                <span className="text-[10px] text-emerald-500 font-medium">Mayor a 20 unidades</span>
              </div>
              <div className="w-10 h-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-500">
                <CheckCircle2 className="h-5 w-5" />
              </div>
            </div>

            <div className="glass p-4 rounded-xl border border-gray-200/50 dark:border-white/10 flex items-center justify-between">
              <div>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-gray-500 dark:text-gray-400">
                  Salud del Almacén
                </span>
                <div className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">
                  {statsReposicion.tasaSalud}%
                </div>
                <span className="text-[10px] text-gray-400">
                  {statsReposicion.totalItems} productos en catálogo
                </span>
              </div>
              <div className="w-10 h-10 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-500">
                <Sparkles className="h-5 w-5" />
              </div>
            </div>
          </div>

          {/* GRID EQUITATIVO 50% / 50% (GRÁFICA PROFESIONAL + LISTADO ACTUAL) */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
            {/* ======================================================== */}
            {/* COLUMNA 1 (50%): GRÁFICA PROFESIONAL DE PRODUCTOS A RELLENAR */}
            {/* ======================================================== */}
            <div className="glass p-6 rounded-2xl flex flex-col justify-between space-y-4">
              <div>
                {/* Cabecera del Gráfico con Toggle de Visualización */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-gray-100 dark:border-white/10 gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <BarChart2 className="h-5 w-5 text-cyan-500" />
                      Diagnóstico de Productos a Rellenar
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {vistaGrafica === 'deficit'
                        ? 'Comparativa entre existencias actuales y unidades faltantes por producto'
                        : 'Proporción general de salud y estado de abastecimiento en almacén'}
                    </p>
                  </div>

                  <div className="flex items-center gap-1 p-1 bg-gray-100 dark:bg-white/5 rounded-lg self-start sm:self-auto">
                    <button
                      type="button"
                      onClick={() => setVistaGrafica('deficit')}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                        vistaGrafica === 'deficit'
                          ? 'bg-cyan-500 text-white shadow-xs'
                          : 'text-gray-500 hover:text-gray-700 dark:hover:text-white'
                      }`}
                      title="Ver barras de déficit a reponer"
                    >
                      Déficit por Ítem
                    </button>
                    <button
                      type="button"
                      onClick={() => setVistaGrafica('salud')}
                      className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                        vistaGrafica === 'salud'
                          ? 'bg-cyan-500 text-white shadow-xs'
                          : 'text-gray-500 hover:text-gray-700 dark:hover:text-white'
                      }`}
                      title="Ver distribución porcentual"
                    >
                      Salud Almacén
                    </button>
                  </div>
                </div>

                {/* Área de la Gráfica */}
                <div className="pt-4">
                  {vistaGrafica === 'deficit' ? (
                    <div>
                      {statsReposicion.topParaRellenar.length > 0 ? (
                        <div>
                          <div className="flex items-center justify-between text-xs text-gray-400 mb-2 px-1">
                            <span>Top productos críticos (mayor déficit):</span>
                            <span className="text-[11px] text-cyan-500 font-medium">
                              Meta: {UMBRAL_SEGURIDAD} unidades
                            </span>
                          </div>

                          <div className="h-[300px] w-full">
                            <ResponsiveContainer width="100%" height="100%">
                              <BarChart
                                data={statsReposicion.topParaRellenar}
                                layout="vertical"
                                margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
                              >
                                <CartesianGrid
                                  strokeDasharray="3 3"
                                  stroke="rgba(255,255,255,0.06)"
                                  horizontal={false}
                                />
                                <XAxis
                                  type="number"
                                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                                  axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                                />
                                <YAxis
                                  type="category"
                                  dataKey="nombre"
                                  width={110}
                                  tick={{ fill: '#94a3b8', fontSize: 11 }}
                                  axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                                />
                                <RechartsTooltip content={<ReposicionTooltip />} />
                                <Legend
                                  wrapperStyle={{ paddingTop: '8px', fontSize: '11px' }}
                                />
                                <Bar
                                  dataKey="stockActual"
                                  name="Stock Actual"
                                  fill="#06b6d4"
                                  radius={[0, 4, 4, 0]}
                                  barSize={14}
                                />
                                <Bar
                                  dataKey="unidadesARellenar"
                                  name="Unidades a Rellenar"
                                  fill="#f59e0b"
                                  radius={[0, 4, 4, 0]}
                                  barSize={14}
                                />
                              </BarChart>
                            </ResponsiveContainer>
                          </div>
                        </div>
                      ) : (
                        <div className="h-[300px] flex flex-col items-center justify-center gap-3 text-center p-6 border border-dashed border-emerald-500/30 rounded-xl bg-emerald-500/5">
                          <CheckCircle2 className="h-10 w-10 text-emerald-500" />
                          <div>
                            <div className="text-sm font-semibold text-gray-900 dark:text-white">
                              ¡Inventario completamente abastecido!
                            </div>
                            <p className="text-xs text-gray-400 mt-1 max-w-xs">
                              Todos los productos controlados superan el umbral mínimo de seguridad ({UMBRAL_SEGURIDAD} uds).
                            </p>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Vista Distribución Donut */
                    <div className="h-[300px] w-full flex flex-col items-center justify-center relative">
                      <ResponsiveContainer width="100%" height={240}>
                        <PieChart>
                          <Pie
                            data={statsReposicion.pieData}
                            dataKey="value"
                            nameKey="name"
                            innerRadius={65}
                            outerRadius={95}
                            paddingAngle={5}
                          >
                            {statsReposicion.pieData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <RechartsTooltip content={<DonutTooltip />} />
                          <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '8px' }} />
                        </PieChart>
                      </ResponsiveContainer>

                      {/* Contador central del donut */}
                      <div className="absolute top-[38%] left-1/2 -translate-x-1/2 -translate-y-1/2 text-center pointer-events-none">
                        <span className="text-2xl font-bold text-slate-900 dark:text-white font-mono block">
                          {statsReposicion.totalPorRellenar}
                        </span>
                        <span className="text-[10px] uppercase font-semibold text-amber-500 tracking-wider">
                          Por Rellenar
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Pie informativo del gráfico */}
              <div className="p-3 rounded-xl bg-cyan-500/5 dark:bg-cyan-950/20 border border-cyan-500/20 flex items-center justify-between text-xs text-cyan-700 dark:text-cyan-300">
                <div className="flex items-center gap-2">
                  <Info className="h-4 w-4 shrink-0 text-cyan-500" />
                  <span>
                    Prioriza reposición de los productos marcados en color <strong>ámbar/rojo</strong>.
                  </span>
                </div>
                <span className="text-[11px] font-mono font-medium hidden sm:inline">
                  {statsReposicion.sinStock.length} sin existencias
                </span>
              </div>
            </div>

            {/* ======================================================== */}
            {/* COLUMNA 2 (50%): LISTADO ACTUAL DE EXISTENCIAS EN ALMACÉN */}
            {/* ======================================================== */}
            <div className="glass p-6 rounded-2xl flex flex-col justify-between space-y-4">
              <div>
                {/* Cabecera del Listado con Búsqueda Integrada */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-gray-100 dark:border-white/10 gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                      <Package className="h-5 w-5 text-cyan-500" />
                      Listado de Existencias
                    </h3>
                    <p className="text-xs text-gray-400 mt-0.5">
                      Catálogo con existencias físicas y acceso rápido a ajustes
                    </p>
                  </div>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-gray-100 dark:bg-white/5 text-gray-500 dark:text-gray-400 self-start sm:self-auto">
                    {total} registros
                  </span>
                </div>

                {/* Filtro de Búsqueda y Chips de Estado */}
                <div className="pt-3 space-y-2.5">
                  <div className="relative">
                    <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-gray-400" />
                    <input
                      id="buscar-inventario"
                      className="input-field pl-10 text-xs py-2"
                      placeholder="Buscar por nombre de producto o código SKU..."
                      value={busqueda}
                      onChange={(e) => {
                        setBusqueda(e.target.value);
                        setPagina(1);
                      }}
                    />
                    {busqueda && (
                      <button
                        type="button"
                        onClick={() => {
                          setBusqueda('');
                          setPagina(1);
                        }}
                        className="absolute right-3 top-2.5 text-xs text-gray-400 hover:text-gray-700 dark:hover:text-white"
                      >
                        ✕
                      </button>
                    )}
                  </div>

                  {/* Chips de filtro rápido */}
                  <div className="flex items-center gap-2 overflow-x-auto text-xs pt-0.5">
                    <span className="text-gray-400 text-[11px] font-medium shrink-0">Filtrar:</span>
                    <button
                      type="button"
                      onClick={() => setFiltroStock('todos')}
                      className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors shrink-0 ${
                        filtroStock === 'todos'
                          ? 'bg-cyan-500 text-white'
                          : 'bg-gray-100 dark:bg-white/5 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-white/10'
                      }`}
                    >
                      Todos ({items.length})
                    </button>
                    <button
                      type="button"
                      onClick={() => setFiltroStock('por_rellenar')}
                      className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors shrink-0 ${
                        filtroStock === 'por_rellenar'
                          ? 'bg-amber-500 text-white'
                          : 'bg-amber-500/10 text-amber-600 dark:text-amber-400 hover:bg-amber-500/20'
                      }`}
                    >
                      Por rellenar ({statsReposicion.totalPorRellenar})
                    </button>
                    <button
                      type="button"
                      onClick={() => setFiltroStock('optimo')}
                      className={`px-2.5 py-0.5 rounded-full text-xs font-medium transition-colors shrink-0 ${
                        filtroStock === 'optimo'
                          ? 'bg-emerald-500 text-white'
                          : 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20'
                      }`}
                    >
                      Óptimo ({statsReposicion.stockOptimo.length})
                    </button>
                  </div>
                </div>

                {/* Tabla de existencias compacta y profesional */}
                <div className="mt-3 overflow-x-auto rounded-xl border border-gray-200 dark:border-white/10 max-h-[290px] overflow-y-auto">
                  <table className="data-table">
                    <thead className="sticky top-0 bg-gray-50 dark:bg-[#0A0A0F] z-10">
                      <tr>
                        <th>Producto / SKU</th>
                        <th className="text-right">Stock</th>
                        <th>Estado</th>
                        <th className="text-center">Ajustar</th>
                      </tr>
                    </thead>
                    <tbody>
                      {itemsMostrados.map((p) => (
                        <tr key={p.producto_id} className="hover:bg-cyan-500/[0.03]">
                          <td>
                            <div className="font-semibold text-slate-900 dark:text-white text-xs truncate max-w-[150px]">
                              {p.producto}
                            </div>
                            <span className="font-mono text-[10px] text-gray-400">
                              {p.sku}
                            </span>
                          </td>
                          <td className="text-right font-mono font-bold text-slate-900 dark:text-white text-xs">
                            {p.cantidad_disponible}
                          </td>
                          <td>{renderStockPill(p.cantidad_disponible)}</td>
                          <td className="text-center">
                            <button
                              type="button"
                              onClick={() => seleccionarProductoParaAjuste(p.producto_id)}
                              className="p-1.5 rounded-lg text-cyan-600 dark:text-cyan-400 bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/20 transition-colors"
                              title="Cargar producto en formulario de ajuste manual"
                            >
                              <Sliders className="h-3.5 w-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                      {!itemsMostrados.length && !loading && (
                        <tr>
                          <td colSpan={4} className="py-8 text-center text-gray-400 text-xs">
                            No se encontraron productos para los criterios seleccionados.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Barra de Paginación Integrada en el Card */}
              <div className="pagination-bar pt-2 border-t border-gray-100 dark:border-white/5">
                <span className="text-xs text-gray-400">
                  Pág. {pagina} de {max} · {total} ítems
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    disabled={pagina <= 1 || loading}
                    onClick={() => setPagina((p) => p - 1)}
                    className="pagination-btn px-2.5 py-1 text-xs flex items-center gap-1"
                  >
                    <ChevronLeft className="h-3.5 w-3.5" /> Ant.
                  </button>
                  <button
                    type="button"
                    disabled={pagina >= max || loading}
                    onClick={() => setPagina((p) => p + 1)}
                    className="pagination-btn px-2.5 py-1 text-xs flex items-center gap-1"
                  >
                    Sig. <ChevronRight className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* ======================================================== */}
          {/* FORMULARIO DE AJUSTE MANUAL DE INVENTARIO (INFERIOR) */}
          {/* ======================================================== */}
          <div id="formulario-ajuste" className="glass p-6 rounded-2xl space-y-4">
            <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-white/5">
              <div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Sliders className="h-4 w-4 text-cyan-500" />
                  Ajuste manual de existencias
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Solo personal autorizado. Valores positivos suman unidades; valores negativos descuentan mercancía.
                </p>
              </div>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
                inventario.ajustar
              </span>
            </div>

            <form onSubmit={ajustar} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <label className="input-label">Producto a Ajustar *</label>
                  <select
                    className="input-field cursor-pointer text-xs"
                    value={producto}
                    onChange={(e) => setProducto(e.target.value)}
                    required
                  >
                    <option value="">Seleccionar producto</option>
                    {(allStock.length > 0 ? allStock : items).map((p) => (
                      <option key={p.producto_id} value={p.producto_id}>
                        {p.producto} ({p.sku}) - Stock: {p.cantidad_disponible}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="input-label">Variación de Stock (+ / -) *</label>
                  <input
                    type="number"
                    step="0.001"
                    required
                    className="input-field text-xs"
                    value={delta}
                    onChange={(e) => setDelta(e.target.value)}
                    placeholder="Ej. +10 o -3"
                  />
                </div>

                <div>
                  <label className="input-label">Referencia Externa (opcional)</label>
                  <input
                    maxLength={100}
                    className="input-field text-xs"
                    value={referencia}
                    onChange={(e) => setReferencia(e.target.value)}
                    placeholder="Ej. Guía Ingreso #0124"
                  />
                </div>

                <div>
                  <label className="input-label">Motivo (mínimo 8 caracteres) *</label>
                  <input
                    required
                    minLength={8}
                    maxLength={255}
                    className="input-field text-xs"
                    value={motivo}
                    onChange={(e) => setMotivo(e.target.value)}
                    placeholder="Ej. Reabastecimiento por compra local"
                  />
                </div>
              </div>

              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <ShieldCheck className="h-4 w-4 text-cyan-500 shrink-0" />
                  <span>
                    El movimiento se audita en la base de datos con la marca de tiempo y usuario logueado.
                  </span>
                </div>
                <button
                  type="submit"
                  disabled={guardando || loading}
                  className="px-5 py-2.5 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
                >
                  {guardando ? 'Registrando ajuste...' : 'Confirmar ajuste de stock'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* VISTA 2: HISTORIAL DE MOVIMIENTOS                        */}
      {/* ======================================================== */}
      {tab === 'movimientos' && (
        <div className="glass p-6 space-y-4 rounded-2xl">
          <div className="flex items-center justify-between pb-2 border-b border-gray-100 dark:border-white/10">
            <div>
              <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <History className="h-5 w-5 text-cyan-500" />
                Registro de Movimientos de Almacén
              </h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Auditoría histórica de entradas, salidas y correcciones de inventario
              </p>
            </div>
            <span className="text-xs text-gray-400">Total: {total} movimientos</span>
          </div>

          <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-white/10">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Fecha</th>
                  <th>Producto ID</th>
                  <th>Tipo</th>
                  <th>Variación (Delta)</th>
                  <th>Motivo</th>
                  <th>Referencia</th>
                </tr>
              </thead>
              <tbody>
                {movimientos.map((m) => {
                  const deltaNum = Number(m.cantidad_delta) || 0;
                  const isPositive = deltaNum > 0;
                  return (
                    <tr key={m.id}>
                      <td className="whitespace-nowrap text-xs text-gray-500 dark:text-gray-400">
                        {new Date(m.fecha).toLocaleString('es-PE')}
                      </td>
                      <td className="font-mono text-xs">#{m.producto_id}</td>
                      <td>
                        <span className="inline-flex px-2 py-0.5 rounded-full text-xs font-medium bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
                          {m.tipo}
                        </span>
                      </td>
                      <td className="font-mono font-semibold">
                        <span
                          className={`inline-flex items-center gap-1 ${
                            isPositive
                              ? 'text-emerald-600 dark:text-emerald-400'
                              : 'text-rose-600 dark:text-rose-400'
                          }`}
                        >
                          {isPositive ? (
                            <TrendingUp className="h-3.5 w-3.5" />
                          ) : (
                            <TrendingDown className="h-3.5 w-3.5" />
                          )}
                          {isPositive ? `+${m.cantidad_delta}` : m.cantidad_delta}
                        </span>
                      </td>
                      <td className="text-xs max-w-xs truncate" title={m.motivo}>
                        {m.motivo}
                      </td>
                      <td className="text-xs text-gray-400 font-mono">
                        {m.referencia || '—'}
                      </td>
                    </tr>
                  );
                })}
                {!movimientos.length && !loading && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-gray-400 text-sm">
                      No hay registros de movimientos en el historial operativo.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="pagination-bar">
            <span>
              Mostrando página {pagina} de {max} · {total} movimientos
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={pagina <= 1 || loading}
                onClick={() => setPagina((p) => p - 1)}
                className="pagination-btn flex items-center gap-1"
              >
                <ChevronLeft className="h-3.5 w-3.5" /> Anterior
              </button>
              <button
                type="button"
                disabled={pagina >= max || loading}
                onClick={() => setPagina((p) => p + 1)}
                className="pagination-btn flex items-center gap-1"
              >
                Siguiente <ChevronRight className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ======================================================== */}
      {/* VISTA 3: DIRECTORIO DE VENDEDORES                        */}
      {/* ======================================================== */}
      {tab === 'vendedores' && (
        <div className="space-y-4">
          <div className="glass p-6 space-y-4 rounded-2xl">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-2 border-b border-gray-100 dark:border-white/10 gap-3">
              <div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Users className="h-5 w-5 text-cyan-500" />
                  Equipo de Ventas Activo
                </h3>
                <p className="text-xs text-gray-400 mt-0.5">
                  Directorio de comerciales con permiso de emisión de pedidos y ventas
                </p>
              </div>
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-gray-400" />
                <input
                  className="input-field pl-10 text-xs py-2"
                  placeholder="Buscar vendedor..."
                  value={busqueda}
                  onChange={(e) => {
                    setBusqueda(e.target.value);
                    setPagina(1);
                  }}
                />
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-white/10">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Vendedor</th>
                    <th>Correo Institucional</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {vendedores.map((v) => (
                    <tr key={v.id}>
                      <td className="font-medium text-slate-900 dark:text-white">{v.nombre}</td>
                      <td className="text-xs">{v.email}</td>
                      <td>
                        <span
                          className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                            v.activo
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {v.activo ? 'Activo' : 'Inactivo'}
                        </span>
                      </td>
                    </tr>
                  ))}
                  {!vendedores.length && !loading && (
                    <tr>
                      <td colSpan={3} className="py-8 text-center text-gray-400 text-sm">
                        No se encontraron vendedores registrados.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="pagination-bar">
              <span>
                Mostrando página {pagina} de {max} · {total} vendedores
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={pagina <= 1 || loading}
                  onClick={() => setPagina((p) => p - 1)}
                  className="pagination-btn flex items-center gap-1"
                >
                  <ChevronLeft className="h-3.5 w-3.5" /> Anterior
                </button>
                <button
                  type="button"
                  disabled={pagina >= max || loading}
                  onClick={() => setPagina((p) => p + 1)}
                  className="pagination-btn flex items-center gap-1"
                >
                  Siguiente <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          </div>

          <div className="alert-card alert-info">
            <Info className="h-5 w-5 shrink-0 text-blue-500" />
            <p className="text-xs">
              Para añadir o retirar vendedores de esta lista, dirígete a la sección <strong>Usuarios</strong>{' '}
              para asignar o revocar el rol de vendedor. Todas las cuentas operan de forma centralizada sin duplicar registros.
            </p>
          </div>
        </div>
      )}
    </motion.div>
  );
};

export default OperationsCloseView;
