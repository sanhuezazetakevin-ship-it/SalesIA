import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { motion } from 'framer-motion';
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Legend,
  BarChart,
} from 'recharts';
import {
  Calendar,
  DollarSign,
  TrendingUp,
  ShoppingCart,
  Activity,
  Download,
  RefreshCw,
  Package,
  Users,
  Award,
  AlertCircle,
  Info,
  Sparkles,
  BarChart3,
  PieChart as PieChartIcon,
  TrendingDown,
  Loader2,
  FileSpreadsheet,
  Sigma,
  HelpCircle,
  Layers,
  ArrowUpRight,
  ArrowDownRight,
} from 'lucide-react';
import { api } from '../services/api';
import {
  DashboardComercialResponse,
  SerieVentasResponse,
  RankingItem,
  AnalyticsResumenResponse,
  AnalyticsProbabilidadesResponse,
  AnalyticsDistribucionesResponse,
  Semana08Response,
} from '../types/api';
import { SalesFunnelChart } from './ui';

/* ===== HELPER UTILITIES ===== */

const fechaLocal = (date: Date): string => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const soles = (valor: string | number | null | undefined): string =>
  valor === null || valor === undefined || valor === '' || !Number.isFinite(Number(valor))
    ? 'N/D'
    : new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(Number(valor));

const numero = (valor: string | number | null | undefined): number => {
  const n = Number(valor);
  return Number.isFinite(n) ? n : 0;
};

const decimal = (valor: string | number | null | undefined, max = 2): string => {
  const n = Number(valor);
  return Number.isFinite(n) ? n.toFixed(max) : 'N/D';
};

const porcentajeTexto = (valor: string | number | null | undefined): string => {
  const n = Number(valor);
  return Number.isFinite(n) ? `${n >= 0 ? '+' : ''}${n.toFixed(2)}%` : 'N/D';
};

const capitalizar = (texto: string): string =>
  texto
    .toLowerCase()
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((parte) => parte.charAt(0).toUpperCase() + parte.slice(1))
    .join(' ');

const csvCelda = (valor: string | number): string => {
  const texto = String(valor);
  const seguro = /^[\s]*[=+@-]/.test(texto) ? `'${texto}` : texto;
  return `"${seguro.replace(/"/g, '""')}"`;
};

const ESTADO_COLORES: Record<string, string> = {
  CONFIRMADO: '#06b6d4',
  COMPLETADO: '#10b981',
  CANCELADO: '#ef4444',
  BORRADOR: '#f59e0b',
  PENDIENTE: '#6366f1',
};

/* ===== SPINNER COMPONENT ===== */

export const Spinner: React.FC<{ text?: string; className?: string }> = ({
  text = 'Consultando indicadores comerciales y estadísticos...',
  className = '',
}) => (
  <div className={`flex flex-col items-center justify-center p-8 space-y-3 ${className}`}>
    <div className="relative">
      <div className="w-10 h-10 rounded-full border-2 border-cyan-500/20 border-t-cyan-500 animate-spin" />
      <div className="absolute inset-0 flex items-center justify-center">
        <Loader2 className="w-5 h-5 text-cyan-400 animate-spin" />
      </div>
    </div>
    {text && <p className="text-sm text-gray-500 dark:text-gray-400 font-medium">{text}</p>}
  </div>
);

/* ===== MAIN DASHBOARD COMPONENT ===== */

export const DashboardView: React.FC = () => {
  const hoy = fechaLocal(new Date());
  const haceUnMes = fechaLocal(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000));

  const [fechaInicio, setFechaInicio] = useState(haceUnMes);
  const [fechaFin, setFechaFin] = useState(hoy);
  const [agrupacion, setAgrupacion] = useState<'dia' | 'mes'>('dia');
  const [limite, setLimite] = useState(10);

  const [loading, setLoading] = useState(false);
  const requestId = useRef(0);
  const [error, setError] = useState<string | null>(null);
  const [erroresComplementarios, setErroresComplementarios] = useState<string[]>([]);

  const [dataComercial, setDataComercial] = useState<DashboardComercialResponse | null>(null);
  const [dataSerie, setDataSerie] = useState<SerieVentasResponse | null>(null);
  const [analyticsResumen, setAnalyticsResumen] = useState<AnalyticsResumenResponse | null>(null);
  const [analyticsProbabilidades, setAnalyticsProbabilidades] = useState<AnalyticsProbabilidadesResponse | null>(null);
  const [analyticsDistribuciones, setAnalyticsDistribuciones] = useState<AnalyticsDistribucionesResponse | null>(null);
  const [analyticsSemana08, setAnalyticsSemana08] = useState<Semana08Response | null>(null);

  const rangoInvalido = !fechaInicio || !fechaFin || fechaInicio > fechaFin;

  const cargarDashboard = useCallback(async () => {
    const id = ++requestId.current;
    if (!fechaInicio || !fechaFin || fechaInicio > fechaFin) {
      setError('Selecciona un rango válido: la fecha inicial no puede ser posterior a la final.');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);
    setErroresComplementarios([]);

    try {
      const [comercial, serie] = await Promise.all([
        api.getDashboardComercial(fechaInicio, fechaFin, limite),
        api.getSerieVentas(fechaInicio, fechaFin, agrupacion),
      ]);

      if (id !== requestId.current) return;
      setDataComercial(comercial);
      setDataSerie(serie);

      const extras = await Promise.allSettled([
        api.getAnalyticsResumen(fechaInicio, fechaFin),
        api.getAnalyticsProbabilidades(fechaInicio, fechaFin, '100.00'),
        api.getAnalyticsDistribuciones(fechaInicio, fechaFin, 'estado_pago', 5),
        api.getSemana08(fechaInicio, fechaFin, undefined, 0.05),
      ]);

      if (id !== requestId.current) return;

      const mensajes: string[] = [];

      if (extras[0].status === 'fulfilled') setAnalyticsResumen(extras[0].value);
      else {
        setAnalyticsResumen(null);
        mensajes.push('No fue posible cargar el resumen estadístico.');
      }

      if (extras[1].status === 'fulfilled') setAnalyticsProbabilidades(extras[1].value);
      else {
        setAnalyticsProbabilidades(null);
        mensajes.push('No fue posible cargar el módulo de probabilidades.');
      }

      if (extras[2].status === 'fulfilled') setAnalyticsDistribuciones(extras[2].value);
      else {
        setAnalyticsDistribuciones(null);
        mensajes.push('No fue posible cargar la distribución de estados de pago.');
      }

      if (extras[3].status === 'fulfilled') setAnalyticsSemana08(extras[3].value);
      else {
        setAnalyticsSemana08(null);
        mensajes.push('No fue posible cargar el bloque de dispersión e hipótesis.');
      }

      setErroresComplementarios(mensajes);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al cargar el dashboard';
      if (id === requestId.current) {
        setError(msg);
        setDataComercial(null);
        setDataSerie(null);
      }
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [fechaInicio, fechaFin, limite, agrupacion]);

  useEffect(() => {
    cargarDashboard();
  }, [cargarDashboard]);

  const exportarCSV = () => {
    if (!dataSerie?.puntos?.length) return;
    const filas = [
      ['Fecha', 'Cantidad de ventas', 'Total de ventas (PEN)'],
      ...dataSerie.puntos.map((p) => [p.fecha, p.cantidad_ventas, p.total_ventas]),
    ];
    const contenido = '\uFEFF' + filas.map((f) => f.map(csvCelda).join(';')).join('\r\n');
    const url = URL.createObjectURL(new Blob([contenido], { type: 'text/csv;charset=utf-8;' }));
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = `salesia_ventas_${fechaInicio}_${fechaFin}_${agrupacion}.csv`;
    enlace.click();
    URL.revokeObjectURL(url);
  };

  const totalPedidos = dataComercial?.pedidos_por_estado
    ? Object.values(dataComercial.pedidos_por_estado).reduce((a, b) => a + b, 0)
    : null;

  const kpisEstadisticos = useMemo(() => {
    const cantidadVentas = dataComercial?.kpis.cantidad_ventas ?? analyticsResumen?.cantidad_ventas ?? 0;
    const totalVentas = numero(dataComercial?.kpis.total_ventas ?? analyticsResumen?.total_ventas ?? 0);
    const promedio = numero(dataComercial?.kpis.ticket_promedio ?? analyticsResumen?.ticket_promedio ?? 0);
    const mediana = numero(analyticsResumen?.mediana_ventas ?? analyticsSemana08?.resultados?.mediana ?? analyticsSemana08?.mediana ?? 0);
    const dispersion = analyticsSemana08?.resultados?.desviacion_muestral ?? analyticsSemana08?.desviacion_muestral;
    const periodoAnterior = numero(dataComercial?.kpis_periodo_anterior?.total_ventas ?? 0);
    const promedioDiario = dataSerie?.puntos?.length ? totalVentas / dataSerie.puntos.length : 0;

    return { cantidadVentas, totalVentas, promedio, mediana, dispersion, periodoAnterior, promedioDiario };
  }, [dataComercial, analyticsResumen, analyticsSemana08, dataSerie]);

  const estadoPedidoPrincipal = useMemo(() => {
    if (!dataComercial?.pedidos_por_estado) return null;
    const entries = Object.entries(dataComercial.pedidos_por_estado);
    if (!entries.length) return null;
    const [estado, cantidad] = entries.reduce((max, actual) => (actual[1] > max[1] ? actual : max));
    return { estado, cantidad };
  }, [dataComercial]);

  const insightsEjecutivos = useMemo(() => {
    const lista: string[] = [];

    if (dataComercial) {
      lista.push(
        `En el periodo seleccionado se registraron ${dataComercial.kpis.cantidad_ventas} ventas confirmadas por un total de ${soles(dataComercial.kpis.total_ventas)}.`
      );
    }

    if (analyticsResumen?.mediana_ventas) {
      const media = numero(dataComercial?.kpis.ticket_promedio ?? analyticsResumen.ticket_promedio);
      const mediana = numero(analyticsResumen.mediana_ventas);
      if (media > 0 && mediana > 0) {
        lista.push(
          media > mediana
            ? `La media (${soles(media)}) es superior a la mediana (${soles(mediana)}), lo que sugiere operaciones altas que empujan el promedio.`
            : `La media (${soles(media)}) y la mediana (${soles(mediana)}) se mantienen cercanas, lo que indica un comportamiento de ventas más equilibrado.`
        );
      }
    }

    if (estadoPedidoPrincipal) {
      lista.push(
        `El estado con mayor presencia en pedidos es ${capitalizar(estadoPedidoPrincipal.estado)} con ${estadoPedidoPrincipal.cantidad} registros.`
      );
    }

    if (analyticsProbabilidades?.probabilidad_pagado_dado_alto) {
      lista.push(
        `La probabilidad de que una venta de importe alto esté pagada es ${analyticsProbabilidades.probabilidad_pagado_dado_alto}.`
      );
    }

    if (dataComercial?.variacion_porcentual_ventas !== null && dataComercial?.variacion_porcentual_ventas !== undefined) {
      const varNum = Number(dataComercial.variacion_porcentual_ventas);
      if (Number.isFinite(varNum)) {
        lista.push(
          varNum >= 0
            ? `Las ventas crecieron ${varNum.toFixed(2)}% respecto al periodo anterior.`
            : `Las ventas disminuyeron ${Math.abs(varNum).toFixed(2)}% respecto al periodo anterior.`
        );
      }
    }

    if (!lista.length) {
      lista.push('Cuando existan ventas, comparativas y datos estadísticos, aquí se mostrará un resumen ejecutivo automático para la toma de decisiones.');
    }

    return lista.slice(0, 5);
  }, [dataComercial, analyticsResumen, analyticsProbabilidades, estadoPedidoPrincipal]);

  // Chart data: Pie Chart (Ventas por Estado)
  const pieData = useMemo(() => {
    if (!dataComercial?.pedidos_por_estado) return [];
    return Object.entries(dataComercial.pedidos_por_estado).map(([estado, cantidad]) => {
      const upper = estado.toUpperCase();
      return {
        name: capitalizar(estado),
        rawStatus: upper,
        value: cantidad,
        color: ESTADO_COLORES[upper] || '#8b5cf6',
      };
    });
  }, [dataComercial]);

  // Chart data: Composed Chart (Evolución de ventas)
  const serieChartData = useMemo(() => {
    if (!dataSerie?.puntos || dataSerie.puntos.length === 0) return [];
    return dataSerie.puntos.map((p) => ({
      fecha: p.fecha,
      labelFecha: agrupacion === 'dia' ? p.fecha.slice(5) : p.fecha,
      total_ventas: numero(p.total_ventas),
      cantidad_ventas: p.cantidad_ventas,
    }));
  }, [dataSerie, agrupacion]);

  // Distribution chart data
  const distribucionChartData = useMemo(() => {
    const items = analyticsDistribuciones?.distribucion ?? analyticsDistribuciones?.intervalos ?? [];
    if (!items.length) return [];
    return items.map((it) => ({
      etiqueta: it.categoria || it.etiqueta || (it.desde ? `${it.desde} - ${it.hasta}` : 'Rango'),
      frecuencia: it.frecuencia_absoluta ?? it.frecuencia ?? 0,
      porcentaje: it.frecuencia_relativa ?? it.porcentaje ?? '',
    }));
  }, [analyticsDistribuciones]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* ===== HEADER & TITLE (GLASS CONTAINER) ===== */}
      <div className="glass p-5 md:p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 border border-[#D97843]/20 dark:border-white/10 shadow-sm">
        <div>
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 text-xs font-extrabold uppercase tracking-wider rounded-md bg-emerald-600/15 text-emerald-800 border border-emerald-600/30 dark:bg-emerald-500/20 dark:text-emerald-300 dark:border-emerald-500/40">
              Panel Empresarial
            </span>
            <span className="text-xs text-slate-400">·</span>
            <span className="text-xs text-slate-600 dark:text-slate-300 font-semibold">FastAPI + PostgreSQL</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-black tracking-tight text-slate-950 dark:text-white mt-1.5 drop-shadow-sm">
            Dashboard Ejecutivo y Comercial
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 mt-1 font-medium">
            Monitoreo en tiempo real de ventas, rentabilidad, rendimiento del equipo e inferencia estadística.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="px-3.5 py-1.5 rounded-xl bg-white/80 dark:bg-white/10 border border-slate-200/80 dark:border-white/15 text-xs shadow-sm">
            <span className="text-slate-600 dark:text-slate-300 font-medium">Moneda:</span>{' '}
            <strong className="text-slate-950 dark:text-white font-bold">{dataComercial?.moneda || 'PEN'}</strong>
          </div>
          <div className="px-3.5 py-1.5 rounded-xl bg-white/80 dark:bg-white/10 border border-slate-200/80 dark:border-white/15 text-xs shadow-sm">
            <span className="text-slate-600 dark:text-slate-300 font-medium">Zona:</span>{' '}
            <strong className="text-slate-950 dark:text-white font-bold">{dataComercial?.zona_horaria || 'UTC-5'}</strong>
          </div>
          <div className="px-3.5 py-1.5 rounded-xl bg-white/80 dark:bg-white/10 border border-slate-200/80 dark:border-white/15 text-xs shadow-sm">
            <span className="text-slate-600 dark:text-slate-300 font-medium">Criterio:</span>{' '}
            <strong className="text-slate-950 dark:text-white font-bold">{dataComercial?.criterio_estado || 'Confirmadas'}</strong>
          </div>
        </div>
      </div>

      {/* ===== FILTER BAR (GLASS CARD) ===== */}
      <div className="glass p-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 items-end">
          {/* Fecha Inicio */}
          <div>
            <label htmlFor="dashboard-inicio" className="input-label flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-cyan-500" />
              Fecha Inicio
            </label>
            <input
              id="dashboard-inicio"
              type="date"
              value={fechaInicio}
              onChange={(e) => setFechaInicio(e.target.value)}
              className="input-field"
            />
          </div>

          {/* Fecha Fin */}
          <div>
            <label htmlFor="dashboard-fin" className="input-label flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-cyan-500" />
              Fecha Fin
            </label>
            <input
              id="dashboard-fin"
              type="date"
              value={fechaFin}
              onChange={(e) => setFechaFin(e.target.value)}
              className="input-field"
            />
          </div>

          {/* Agrupación */}
          <div>
            <label htmlFor="dashboard-agrupacion" className="input-label">Agrupación Gráfica</label>
            <select
              id="dashboard-agrupacion"
              value={agrupacion}
              onChange={(e) => setAgrupacion(e.target.value as 'dia' | 'mes')}
              className="input-field"
            >
              <option value="dia">Por Día</option>
              <option value="mes">Por Mes</option>
            </select>
          </div>

          {/* Límite Rankings */}
          <div>
            <label htmlFor="dashboard-limite" className="input-label">Límite Rankings</label>
            <select
              id="dashboard-limite"
              value={limite}
              onChange={(e) => setLimite(Number(e.target.value))}
              className="input-field"
            >
              <option value={5}>Top 5</option>
              <option value={10}>Top 10</option>
              <option value={20}>Top 20</option>
            </select>
          </div>

          {/* Action Buttons */}
          <div className="sm:col-span-2 md:col-span-4 lg:col-span-2 flex items-center gap-2">
            <button
              onClick={cargarDashboard}
              disabled={loading || rangoInvalido}
              className="flex-1 px-4 py-2.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-medium text-sm transition-all shadow-[0_0_15px_rgba(6,182,212,0.3)] hover:shadow-[0_0_20px_rgba(6,182,212,0.5)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Consultando...' : 'Consultar'}</span>
            </button>

            <button
              type="button"
              onClick={exportarCSV}
              disabled={!dataSerie?.puntos?.length || loading}
              title="Descargar serie temporal en CSV"
              className="px-3.5 py-2.5 rounded-lg border border-gray-200 dark:border-white/10 bg-white/50 dark:bg-white/5 hover:bg-gray-100 dark:hover:bg-white/10 text-gray-700 dark:text-gray-200 font-medium text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5 cursor-pointer"
            >
              <Download className="w-4 h-4 text-cyan-500" />
              <span className="hidden sm:inline">CSV</span>
            </button>
          </div>
        </div>
      </div>

      {/* ===== ALERTS & STATUS ===== */}
      {rangoInvalido && (
        <div className="alert-card alert-error">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-sm">Rango de fechas no válido</h4>
            <p className="text-xs opacity-90">La fecha inicial no puede ser posterior a la fecha final.</p>
          </div>
        </div>
      )}

      {error && (
        <div className="alert-card alert-error">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-sm">Error de comunicación</h4>
            <p className="text-xs opacity-90">{error}</p>
          </div>
        </div>
      )}

      {loading && <Spinner text="Consultando indicadores comerciales y estadísticos..." />}

      {!loading && erroresComplementarios.length > 0 && (
        <div className="alert-card alert-info">
          <Info className="w-5 h-5 text-blue-500 flex-shrink-0 mt-0.5" />
          <div>
            <h4 className="font-semibold text-sm">Información complementaria</h4>
            <p className="text-xs opacity-90">
              Algunos bloques complementarios aún no están disponibles para el período seleccionado. El tablero principal continúa 100% operativo.
            </p>
          </div>
        </div>
      )}

      {/* ===== KPI CARDS ROW (4 CARDS) ===== */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Card 1: Ventas Totales */}
        <div className="glass p-5 flex flex-col justify-between hover:shadow-[0_0_15px_rgba(6,182,212,0.15)] transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold">
              Ventas Totales
            </span>
            <div className="p-2.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-500">
              <DollarSign className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {soles(dataComercial?.kpis.total_ventas)}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
                {dataComercial?.moneda || 'PEN'}
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {dataComercial?.kpis_periodo_anterior
                  ? `Ant: ${soles(dataComercial.kpis_periodo_anterior.total_ventas)}`
                  : 'Total acumulado'}
              </span>
            </div>
          </div>
        </div>

        {/* Card 2: Ticket Promedio */}
        <div className="glass p-5 flex flex-col justify-between hover:shadow-[0_0_15px_rgba(59,130,246,0.15)] transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold">
              Ticket Promedio
            </span>
            <div className="p-2.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-500">
              <TrendingUp className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {soles(dataComercial?.kpis.ticket_promedio)}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
                Media
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {analyticsResumen?.mediana_ventas
                  ? `Mediana: ${soles(analyticsResumen.mediana_ventas)}`
                  : 'Por operación'}
              </span>
            </div>
          </div>
        </div>

        {/* Card 3: Cantidad Ventas */}
        <div className="glass p-5 flex flex-col justify-between hover:shadow-[0_0_15px_rgba(16,185,129,0.15)] transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold">
              Cantidad Ventas
            </span>
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-500">
              <ShoppingCart className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {dataComercial?.kpis.cantidad_ventas !== undefined
                ? dataComercial.kpis.cantidad_ventas.toLocaleString('es-PE')
                : '0'}
            </div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                Confirmadas
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {totalPedidos ? `${totalPedidos} pedidos totales` : 'Operaciones cerradas'}
              </span>
            </div>
          </div>
        </div>

        {/* Card 4: Variación Comercial */}
        <div className="glass p-5 flex flex-col justify-between hover:shadow-[0_0_15px_rgba(245,158,11,0.15)] transition-all">
          <div className="flex items-center justify-between">
            <span className="text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold">
              Variación
            </span>
            <div className="p-2.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-500">
              <Activity className="w-5 h-5" />
            </div>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold text-gray-900 dark:text-white">
              {porcentajeTexto(dataComercial?.variacion_porcentual_ventas)}
            </div>
            <div className="flex items-center gap-2 mt-2">
              {dataComercial?.variacion_porcentual_ventas != null ? (
                Number(dataComercial.variacion_porcentual_ventas) >= 0 ? (
                  <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                    <ArrowUpRight className="w-3.5 h-3.5" />
                    Crecimiento
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
                    <ArrowDownRight className="w-3.5 h-3.5" />
                    Disminución
                  </span>
                )
              ) : (
                <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-gray-500/10 text-gray-400 border border-gray-500/20">
                  Sin comparativa
                </span>
              )}
              <span className="text-xs text-gray-500 dark:text-gray-400 truncate">
                vs periodo anterior
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ===== EXECUTIVE INSIGHTS SECTION ===== */}
      <div className="glass p-5 rounded-xl border-l-4 border-l-cyan-500">
        <div className="flex items-center gap-2.5 mb-3">
          <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-gray-900 dark:text-white">
            Resumen Ejecutivo & Lectura Guiada
          </h3>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {insightsEjecutivos.map((texto, idx) => (
            <div
              key={idx}
              className="p-3 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5 flex items-start gap-2.5"
            >
              <span className="w-5 h-5 rounded-full flex-shrink-0 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 font-bold text-xs flex items-center justify-center border border-cyan-500/20">
                {idx + 1}
              </span>
              <p className="text-xs text-gray-700 dark:text-gray-300 leading-relaxed">{texto}</p>
            </div>
          ))}
        </div>
      </div>

      {/* ===== PIPELINE / SALES FUNNEL ===== */}
      <SalesFunnelChart
        pedidosPorEstado={dataComercial?.pedidos_por_estado}
        totalVentasMonto={Number(dataComercial?.kpis.total_ventas || 0)}
        cantidadVentas={Number(dataComercial?.kpis.cantidad_ventas || 0)}
      />

      {/* ===== CHARTS SECTION (2 COLUMNS) ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: PieChart (Ventas por Estado de Pedido) */}
        <div className="glass p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-white/5">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-500">
                <PieChartIcon className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white text-base">
                  Ventas por Estado de Pedido
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Total auditado: {totalPedidos ?? 0} pedidos
                </p>
              </div>
            </div>
          </div>

          {pieData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
              No hay pedidos registrados en el intervalo seleccionado.
            </div>
          ) : (
            <div className="space-y-4">
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1a2e',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderRadius: '0.75rem',
                        boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)',
                        color: '#f3f4f6',
                      }}
                      formatter={(val: any) => [
                        `${val} pedidos (${totalPedidos ? ((Number(val) / totalPedidos) * 100).toFixed(1) : 0}%)`,
                        'Cantidad',
                      ]}
                    />
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={55}
                      outerRadius={88}
                      paddingAngle={4}
                    >
                      {pieData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={entry.color}
                          stroke="rgba(0,0,0,0.2)"
                          strokeWidth={1}
                        />
                      ))}
                    </Pie>
                    <Legend wrapperStyle={{ fontSize: '12px', color: '#9ca3af' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Status pills breakdown */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 pt-2 border-t border-gray-100 dark:border-white/5">
                {pieData.map((item) => {
                  const pct = totalPedidos ? ((item.value / totalPedidos) * 100).toFixed(1) : '0';
                  return (
                    <div
                      key={item.rawStatus}
                      className="p-2 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5 flex items-center justify-between"
                    >
                      <div className="flex items-center gap-1.5 truncate">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{ backgroundColor: item.color }}
                        />
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300 truncate">
                          {item.name}
                        </span>
                      </div>
                      <div className="text-right pl-2">
                        <span className="text-xs font-bold text-gray-900 dark:text-white">
                          {item.value}
                        </span>
                        <span className="text-[10px] text-gray-400 block">{pct}%</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>

        {/* Right: ComposedChart (Evolución de Ventas) */}
        <div className="glass p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-white/5">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-500">
                <BarChart3 className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white text-base">
                  Evolución de Ventas
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {agrupacion === 'dia' ? 'Serie Diaria' : 'Serie Mensual'} · {dataSerie?.moneda || 'PEN'}
                </p>
              </div>
            </div>
            <span className="text-xs px-2.5 py-1 rounded-full bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 font-medium">
              {dataSerie?.criterio_estado || 'Confirmadas'}
            </span>
          </div>

          {!dataSerie?.puntos || dataSerie.puntos.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-sm text-gray-500 dark:text-gray-400">
              No hay ventas confirmadas en este intervalo de fechas ({fechaInicio} al {fechaFin}).
            </div>
          ) : (
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={serieChartData}
                  margin={{ top: 10, right: 10, left: 0, bottom: 20 }}
                >
                  <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" vertical={false} />
                  <XAxis
                    dataKey="labelFecha"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                    tickLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    yAxisId="left"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                    tickLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                    tickFormatter={(v) => `S/ ${v >= 1000 ? `${(v / 1000).toFixed(0)}k` : v}`}
                  />
                  <YAxis
                    yAxisId="right"
                    orientation="right"
                    tick={{ fill: '#9ca3af', fontSize: 11 }}
                    axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                    tickLine={{ stroke: 'rgba(255,255,255,0.1)' }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1a1a2e',
                      borderColor: 'rgba(255,255,255,0.1)',
                      borderRadius: '0.75rem',
                      boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)',
                      color: '#f3f4f6',
                    }}
                    formatter={(value: any, name: any) => {
                      if (name === 'Total Ventas (PEN)') return [soles(value), name];
                      return [`${value} ventas`, name];
                    }}
                    labelFormatter={(label, payload) => {
                      const item = payload?.[0]?.payload;
                      return item ? `Fecha: ${item.fecha}` : String(label);
                    }}
                  />
                  <Legend wrapperStyle={{ paddingTop: '10px', fontSize: '12px', color: '#9ca3af' }} />
                  <Bar
                    yAxisId="left"
                    dataKey="total_ventas"
                    name="Total Ventas (PEN)"
                    fill="#06b6d4"
                    radius={[4, 4, 0, 0]}
                    maxBarSize={36}
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="cantidad_ventas"
                    name="Cantidad Ventas"
                    stroke="#10b981"
                    strokeWidth={2.5}
                    dot={{ r: 3, fill: '#10b981' }}
                    activeDot={{ r: 5 }}
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* ===== RANKINGS SECTION (3 COLUMNS) ===== */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Award className="w-5 h-5 text-cyan-500" />
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            Rankings Comerciales
          </h3>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            (Top {limite} en el período)
          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 1. Top Productos */}
          <div className="glass p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-white/5 mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-500 border border-cyan-500/20">
                    <Package className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
                      Top Productos
                    </h4>
                    <span className="text-[11px] text-gray-400">Por facturación total</span>
                  </div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 font-medium">
                  {dataComercial?.productos_destacados?.length ?? 0}
                </span>
              </div>

              {!dataComercial?.productos_destacados?.length ? (
                <p className="text-xs text-gray-500 dark:text-gray-400 p-6 text-center">
                  Sin productos registrados en este período.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th className="w-8 text-center">#</th>
                        <th>Producto</th>
                        <th className="text-right">Ops</th>
                        <th className="text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dataComercial.productos_destacados.map((item, idx) => (
                        <tr key={`${item.id}-${idx}`}>
                          <td className="text-center">
                            {idx === 0 ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500/20 text-amber-500 font-bold text-xs border border-amber-500/30">
                                1
                              </span>
                            ) : idx === 1 ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-400/20 text-slate-400 font-bold text-xs border border-slate-400/30">
                                2
                              </span>
                            ) : idx === 2 ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-700/20 text-amber-600 font-bold text-xs border border-amber-700/30">
                                3
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400">{idx + 1}</span>
                            )}
                          </td>
                          <td className="font-medium text-gray-900 dark:text-gray-200 text-xs truncate max-w-[120px]" title={item.nombre}>
                            {item.nombre}
                          </td>
                          <td className="text-right text-xs text-gray-500 dark:text-gray-400">
                            {item.cantidad}
                          </td>
                          <td className="text-right text-xs font-semibold text-gray-900 dark:text-cyan-400 whitespace-nowrap">
                            {soles(item.total)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* 2. Top Clientes */}
          <div className="glass p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-white/5 mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500 border border-blue-500/20">
                    <Users className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
                      Top Clientes
                    </h4>
                    <span className="text-[11px] text-gray-400">Por volumen de compra</span>
                  </div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 font-medium">
                  {dataComercial?.clientes_destacados?.length ?? 0}
                </span>
              </div>

              {!dataComercial?.clientes_destacados?.length ? (
                <p className="text-xs text-gray-500 dark:text-gray-400 p-6 text-center">
                  Sin clientes registrados en este período.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th className="w-8 text-center">#</th>
                        <th>Cliente</th>
                        <th className="text-right">Ops</th>
                        <th className="text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dataComercial.clientes_destacados.map((item, idx) => (
                        <tr key={`${item.id}-${idx}`}>
                          <td className="text-center">
                            {idx === 0 ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500/20 text-amber-500 font-bold text-xs border border-amber-500/30">
                                1
                              </span>
                            ) : idx === 1 ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-400/20 text-slate-400 font-bold text-xs border border-slate-400/30">
                                2
                              </span>
                            ) : idx === 2 ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-700/20 text-amber-600 font-bold text-xs border border-amber-700/30">
                                3
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400">{idx + 1}</span>
                            )}
                          </td>
                          <td className="font-medium text-gray-900 dark:text-gray-200 text-xs truncate max-w-[120px]" title={item.nombre}>
                            {item.nombre}
                          </td>
                          <td className="text-right text-xs text-gray-500 dark:text-gray-400">
                            {item.cantidad}
                          </td>
                          <td className="text-right text-xs font-semibold text-gray-900 dark:text-cyan-400 whitespace-nowrap">
                            {soles(item.total)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* 3. Top Vendedores */}
          <div className="glass p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between pb-3 border-b border-gray-100 dark:border-white/5 mb-3">
                <div className="flex items-center gap-2">
                  <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                    <Award className="w-4 h-4" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900 dark:text-white text-sm">
                      Top Vendedores
                    </h4>
                    <span className="text-[11px] text-gray-400">Por cierre comercial</span>
                  </div>
                </div>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-medium">
                  {dataComercial?.vendedores_destacados?.length ?? 0}
                </span>
              </div>

              {!dataComercial?.vendedores_destacados?.length ? (
                <p className="text-xs text-gray-500 dark:text-gray-400 p-6 text-center">
                  Sin vendedores registrados en este período.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th className="w-8 text-center">#</th>
                        <th>Vendedor</th>
                        <th className="text-right">Ops</th>
                        <th className="text-right">Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dataComercial.vendedores_destacados.map((item, idx) => (
                        <tr key={`${item.id}-${idx}`}>
                          <td className="text-center">
                            {idx === 0 ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500/20 text-amber-500 font-bold text-xs border border-amber-500/30">
                                1
                              </span>
                            ) : idx === 1 ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-slate-400/20 text-slate-400 font-bold text-xs border border-slate-400/30">
                                2
                              </span>
                            ) : idx === 2 ? (
                              <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-700/20 text-amber-600 font-bold text-xs border border-amber-700/30">
                                3
                              </span>
                            ) : (
                              <span className="text-xs text-gray-400">{idx + 1}</span>
                            )}
                          </td>
                          <td className="font-medium text-gray-900 dark:text-gray-200 text-xs truncate max-w-[120px]" title={item.nombre}>
                            {item.nombre}
                          </td>
                          <td className="text-right text-xs text-gray-500 dark:text-gray-400">
                            {item.cantidad}
                          </td>
                          <td className="text-right text-xs font-semibold text-gray-900 dark:text-cyan-400 whitespace-nowrap">
                            {soles(item.total)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* ===== ANALYTICS SECTION ===== */}
      <div className="space-y-4 pt-4 border-t border-gray-200 dark:border-white/10">
        <div className="flex items-center gap-2">
          <Sigma className="w-5 h-5 text-cyan-500" />
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            Analítica Avanzada & Estadística Inferencial
          </h3>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Card 1: Resumen Estadístico & Probabilidades */}
          <div className="glass p-5 space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-white/5">
              <div className="p-1.5 rounded-lg bg-cyan-500/10 text-cyan-400">
                <BarChart3 className="w-4 h-4" />
              </div>
              <h4 className="font-semibold text-sm text-gray-900 dark:text-white">
                Resumen Estadístico
              </h4>
            </div>

            {analyticsResumen ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-3 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5">
                    <span className="text-[11px] text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                      Mediana
                    </span>
                    <strong className="text-base font-bold text-gray-900 dark:text-cyan-400">
                      {soles(analyticsResumen.mediana_ventas)}
                    </strong>
                    <span className="text-[10px] text-gray-400 block mt-0.5">Valor central</span>
                  </div>

                  <div className="p-3 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5">
                    <span className="text-[11px] text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                      Prom. Diario
                    </span>
                    <strong className="text-base font-bold text-gray-900 dark:text-blue-400">
                      {soles(kpisEstadisticos.promedioDiario)}
                    </strong>
                    <span className="text-[10px] text-gray-400 block mt-0.5">Ritmo por tramo</span>
                  </div>
                </div>

                {analyticsProbabilidades && (
                  <div className="p-3 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5 space-y-2">
                    <span className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                      Probabilidades Empíricas
                    </span>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-gray-600 dark:text-gray-300">P(Venta Pagada):</span>
                      <strong className="text-cyan-400 font-mono">
                        {analyticsProbabilidades.probabilidad_pagado ?? 'N/D'}
                      </strong>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-gray-600 dark:text-gray-300">P(Pagado | Importe Alto):</span>
                      <strong className="text-emerald-400 font-mono">
                        {analyticsProbabilidades.probabilidad_pagado_dado_alto ?? 'N/D'}
                      </strong>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-gray-600 dark:text-gray-300">Umbral Importe Alto:</span>
                      <span className="text-gray-400 font-mono">
                        S/ {analyticsProbabilidades.umbral_importe_alto}
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400 p-4 text-center">
                Módulo estadístico no disponible para este período.
              </p>
            )}
          </div>

          {/* Card 2: Distribución de Frecuencias */}
          <div className="glass p-5 space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-white/5">
              <div className="p-1.5 rounded-lg bg-blue-500/10 text-blue-400">
                <FileSpreadsheet className="w-4 h-4" />
              </div>
              <h4 className="font-semibold text-sm text-gray-900 dark:text-white">
                Distribución de Pagos & Frecuencias
              </h4>
            </div>

            {analyticsProbabilidades?.variable_aleatoria_estado_pago?.length ? (
              <div className="space-y-3">
                {analyticsProbabilidades.variable_aleatoria_estado_pago.map((item) => {
                  const maxObs = Math.max(
                    ...analyticsProbabilidades.variable_aleatoria_estado_pago.map((i) => i.frecuencia_absoluta),
                    1
                  );
                  const pct = (item.frecuencia_absoluta / maxObs) * 100;
                  return (
                    <div key={item.estado} className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span className="font-medium text-gray-800 dark:text-gray-200">
                          {capitalizar(item.estado)}
                        </span>
                        <span className="text-cyan-400 font-mono">{item.probabilidad ?? 'N/D'}</span>
                      </div>
                      <div className="h-2 rounded-full bg-gray-100 dark:bg-white/10 overflow-hidden">
                        <div
                          className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full transition-all duration-500"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-gray-400 block">
                        {item.frecuencia_absoluta} observaciones registradas
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : distribucionChartData.length > 0 ? (
              <div className="h-44">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={distribucionChartData}>
                    <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="etiqueta" tick={{ fill: '#9ca3af', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1a1a2e',
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderRadius: '0.5rem',
                        color: '#f3f4f6',
                        fontSize: '12px',
                      }}
                    />
                    <Bar dataKey="frecuencia" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400 p-4 text-center">
                Sin datos suficientes para graficar distribuciones.
              </p>
            )}
          </div>

          {/* Card 3: Dispersión e Hipótesis Semana 08 */}
          <div className="glass p-5 space-y-4">
            <div className="flex items-center gap-2 pb-2 border-b border-gray-100 dark:border-white/5">
              <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
                <Sigma className="w-4 h-4" />
              </div>
              <h4 className="font-semibold text-sm text-gray-900 dark:text-white">
                Dispersión & Contraste (Semana 08)
              </h4>
            </div>

            {analyticsSemana08 ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5">
                    <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                      Desv. Muestral (s)
                    </span>
                    <strong className="text-sm font-bold text-gray-900 dark:text-white">
                      {decimal(
                        analyticsSemana08.resultados?.desviacion_muestral ??
                          analyticsSemana08.desviacion_muestral
                      )}
                    </strong>
                  </div>
                  <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5">
                    <span className="text-[10px] text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                      Varianza (s²)
                    </span>
                    <strong className="text-sm font-bold text-gray-900 dark:text-white">
                      {decimal(
                        analyticsSemana08.resultados?.varianza_muestral ??
                          analyticsSemana08.varianza_muestral
                      )}
                    </strong>
                  </div>
                </div>

                {/* Contraste de hipótesis */}
                {(() => {
                  const contraste =
                    analyticsSemana08.resultados?.contraste ?? analyticsSemana08.contraste;
                  if (!contraste) return null;
                  return (
                    <div className="p-3 rounded-lg bg-gray-50 dark:bg-white/5 border border-gray-100 dark:border-white/5 space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                          Prueba de Hipótesis
                        </span>
                        {contraste.rechazar_hipotesis_nula !== undefined && (
                          <span
                            className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                              contraste.rechazar_hipotesis_nula
                                ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                                : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                            }`}
                          >
                            {contraste.rechazar_hipotesis_nula ? 'Rechaza H₀' : 'No rechaza H₀'}
                          </span>
                        )}
                      </div>
                      {contraste.hipotesis_nula && (
                        <p className="text-[11px] text-gray-600 dark:text-gray-300">
                          <strong>H₀:</strong> {contraste.hipotesis_nula}
                        </p>
                      )}
                      <div className="flex gap-4 text-[11px] text-gray-400">
                        {contraste.estadistico_t !== undefined && (
                          <span>t = {decimal(contraste.estadistico_t)}</span>
                        )}
                        {contraste.valor_p !== undefined && (
                          <span>p = {decimal(contraste.valor_p, 4)}</span>
                        )}
                        {contraste.alfa !== undefined && (
                          <span>α = {contraste.alfa}</span>
                        )}
                      </div>
                      {contraste.explicacion && (
                        <p className="text-[11px] text-gray-500 dark:text-gray-400 italic pt-1 border-t border-gray-100 dark:border-white/5">
                          {contraste.explicacion}
                        </p>
                      )}
                    </div>
                  );
                })()}
              </div>
            ) : (
              <p className="text-xs text-gray-500 dark:text-gray-400 p-4 text-center">
                Módulo Semana 08 no cargado para el rango de fechas actual.
              </p>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};
