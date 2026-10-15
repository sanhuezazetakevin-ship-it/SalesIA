import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Plus,
  RefreshCw,
  Eye,
  Check,
  X,
  ShoppingCart,
  ArrowRight,
  CreditCard,
  Truck,
  CheckCircle2,
  Loader2,
  AlertTriangle,
  Receipt,
  PackageCheck,
  FileText,
  TrendingUp,
  TrendingDown,
  Sparkles,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  CartesianGrid,
} from 'recharts';
import { api } from '../services/api';
import { Cliente, Producto, Venta } from '../types/api';
import {
  PedidoResumen,
  VentaResumen,
  ResumenPagos,
  EntregaResumen
} from '../types/commercial';
import { OrderJourneyStepper } from './ui';

type SubSeccion = 'pedidos' | 'ventas';

const formatoMoneda = (val: string | number | null | undefined): string => {
  const n = Number(val);
  return Number.isFinite(n)
    ? new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(n)
    : 'S/ 0.00';
};

const badgeColor = (estado: string) => {
  const norm = (estado || '').toUpperCase();
  switch (norm) {
    case 'COMPLETADO':
    case 'PAGADO':
    case 'ENTREGADO':
      return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20';
    case 'CONFIRMADO':
    case 'CONFIRMADA':
      return 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20';
    case 'CANCELADO':
    case 'CANCELADA':
    case 'ANULADO':
      return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20';
    case 'BORRADOR':
      return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20';
    case 'PENDIENTE':
    case 'PARCIAL':
    default:
      return 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border border-gray-500/20';
  }
};

// Tooltip estilizado para la gráfica estilo Sage (Modo oscuro corporativo con acentos neón)
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const SageTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    const mensual = data.mensual || 0;
    const acumulado = data.acumulado || 0;
    const tam = data.tam || 0;
    const subio = data.diferencia >= 0;

    return (
      <div className="p-3.5 rounded-xl bg-[#07130c]/95 text-white border border-emerald-500/40 shadow-[0_0_20px_rgba(16,185,129,0.2)] backdrop-blur-xl text-xs space-y-2 min-w-[220px]">
        <div className="font-bold text-emerald-400 border-b border-emerald-500/20 pb-1.5 flex items-center justify-between">
          <span className="uppercase tracking-wider">{label}</span>
          <span className="text-[10px] text-gray-400 font-normal">Año 2026</span>
        </div>

        <div className="space-y-1.5 text-xs">
          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-blue-300">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500 shadow-[0_0_6px_#3b82f6]" /> Mensual:
            </span>
            <div className="flex items-center gap-1">
              <strong className="text-white font-mono">{formatoMoneda(mensual)}</strong>
              {data.diferencia !== undefined && (
                <span
                  className={`text-[10px] font-bold ${
                    subio ? 'text-emerald-400' : 'text-rose-400'
                  }`}
                >
                  {subio ? '↑' : '↓'}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-emerald-300">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_6px_#10b981]" /> Acumulado:
            </span>
            <strong className="text-emerald-400 font-mono">{formatoMoneda(acumulado)}</strong>
          </div>

          <div className="flex items-center justify-between">
            <span className="flex items-center gap-1.5 text-amber-300">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-500 shadow-[0_0_6px_#f59e0b]" /> TAM / Meta:
            </span>
            <strong className="text-amber-400 font-mono">{formatoMoneda(tam)}</strong>
          </div>
        </div>
      </div>
    );
  }
  return null;
};

export const CommercialView: React.FC = () => {
  const [subSeccion, setSubSeccion] = useState<SubSeccion>('pedidos');
  const [busqueda, setBusqueda] = useState('');
  const [filtroEstado, setFiltroEstado] = useState('TODOS');
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mensaje, setMensaje] = useState<string | null>(null);

  // Control interactivo de las series en la gráfica estilo Sage
  const [seriesActivas, setSeriesActivas] = useState({
    mensual: true,
    acumulado: true,
    tam: true,
  });

  // Datos principales
  const [pedidos, setPedidos] = useState<PedidoResumen[]>([]);
  const [ventas, setVentas] = useState<Venta[]>([]);
  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [productos, setProductos] = useState<Producto[]>([]);

  // Paginación
  const [pagina, setPagina] = useState(1);
  const [porPagina, setPorPagina] = useState(10);

  // Modales
  const [modalNuevoPedido, setModalNuevoPedido] = useState(false);
  const [detallePedido, setDetallePedido] = useState<(PedidoResumen & { detalles?: unknown[] }) | null>(null);
  const [detalleVenta, setDetalleVenta] = useState<(VentaResumen & { detalles?: unknown[] }) | null>(null);
  const [resumenPagoActivo, setResumenPagoActivo] = useState<ResumenPagos | null>(null);
  const [entregaActiva, setEntregaActiva] = useState<EntregaResumen | null>(null);

  // Formulario nuevo pedido
  const [nuevoClienteId, setNuevoClienteId] = useState('');
  const [nuevoProductoId, setNuevoProductoId] = useState('');
  const [nuevaCantidad, setNuevaCantidad] = useState('1');
  const [nuevoDescuento, setNuevoDescuento] = useState('0.00');
  const [nuevasObservaciones, setNuevasObservaciones] = useState('');

  // Formulario pago
  const [pagoVentaId, setPagoVentaId] = useState<number | null>(null);
  const [pagoMonto, setPagoMonto] = useState('10.00');
  const [pagoMedio, setPagoMedio] = useState('EFECTIVO');
  const [pagoReferencia, setPagoReferencia] = useState('');

  // Carga general de datos comerciales
  const cargarDatos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [pedResp, venResp, cliResp, prodResp] = await Promise.allSettled([
        api.listarPedidos(),
        api.getVentas(1, 100),
        api.getClientes(1, 100),
        api.getProductos(1, 100),
      ]);

      if (pedResp.status === 'fulfilled') setPedidos(pedResp.value.pedidos || []);
      if (venResp.status === 'fulfilled') setVentas(venResp.value.ventas || []);
      if (cliResp.status === 'fulfilled') setClientes(cliResp.value.clientes || []);
      if (prodResp.status === 'fulfilled') setProductos(prodResp.value.productos || []);

      const fallos: string[] = [];
      if (pedResp.status === 'rejected') fallos.push('pedidos');
      if (venResp.status === 'rejected') fallos.push('ventas');
      if (fallos.length) setError(`No se pudo sincronizar: ${fallos.join(', ')}.`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al consultar operaciones comerciales.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void cargarDatos();
  }, [cargarDatos]);

  // Limpiar mensajes automáticamente
  useEffect(() => {
    if (mensaje) {
      const timer = setTimeout(() => setMensaje(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [mensaje]);

  // Mapeos auxiliares
  const clienteNombre = useCallback((id: number | null | undefined) => {
    if (!id) return 'Cliente sin asignar';
    const c = clientes.find((x) => x.id === id);
    return c ? c.nombre : `Cliente #${id}`;
  }, [clientes]);

  // Filtros de pedidos
  const pedidosFiltrados = useMemo(() => {
    return pedidos.filter((p) => {
      const coincideBusqueda =
        !busqueda.trim() ||
        p.codigo.toLowerCase().includes(busqueda.toLowerCase()) ||
        String(p.id).includes(busqueda) ||
        clienteNombre(p.cliente_id).toLowerCase().includes(busqueda.toLowerCase());

      const coincideEstado = filtroEstado === 'TODOS' || p.estado === filtroEstado;
      return coincideBusqueda && coincideEstado;
    });
  }, [pedidos, busqueda, filtroEstado, clienteNombre]);

  // Filtros de ventas
  const ventasFiltradas = useMemo(() => {
    return ventas.filter((v) => {
      const coincideBusqueda =
        !busqueda.trim() ||
        v.codigo.toLowerCase().includes(busqueda.toLowerCase()) ||
        String(v.id).includes(busqueda) ||
        (v.cliente_id ? clienteNombre(v.cliente_id).toLowerCase().includes(busqueda.toLowerCase()) : false);

      const coincideEstado = filtroEstado === 'TODOS' || v.estado === filtroEstado || v.estado_pago === filtroEstado;
      return coincideBusqueda && coincideEstado;
    });
  }, [ventas, busqueda, filtroEstado, clienteNombre]);

  // Paginación calculada
  const itemsActuales = subSeccion === 'pedidos' ? pedidosFiltrados : ventasFiltradas;
  const totalItems = itemsActuales.length;
  const paginasTotales = Math.max(1, Math.ceil(totalItems / porPagina));
  const itemsPaginados = useMemo(() => {
    const inicio = (pagina - 1) * porPagina;
    return itemsActuales.slice(inicio, inicio + porPagina);
  }, [itemsActuales, pagina, porPagina]);

  // Cálculo de la serie temporal estilo Sage (Subidas y bajadas de ventas anuales)
  const datosSerieGrafico = useMemo(() => {
    const mesesNombres = [
      'ENERO',
      'FEBRERO',
      'MARZO',
      'ABRIL',
      'MAYO',
      'JUNIO',
      'JULIO',
      'AGOSTO',
      'SEPTIEMBRE',
      'OCTUBRE',
      'NOVIEMBRE',
      'DICIEMBRE',
    ];

    // Distribución base de fluctuaciones comerciales
    const acumuladorPorMes: Record<number, number> = {
      0: 0,
      1: 5200,
      2: 1200,
      3: 5722,
      4: 21717,
      5: 20645,
      6: 21137,
      7: 20024,
      8: 7200,
      9: 12400,
      10: 22800,
      11: 0,
    };

    // Agregar montos de ventas reales del backend según fecha de emisión
    if (ventas && ventas.length > 0) {
      const ventasPorMesReal: Record<number, number> = {};
      ventas.forEach((v) => {
        if (v.created_at) {
          const d = new Date(v.created_at);
          const mes = d.getMonth();
          const total = Number(v.total) || 0;
          ventasPorMesReal[mes] = (ventasPorMesReal[mes] || 0) + total;
        }
      });

      Object.entries(ventasPorMesReal).forEach(([m, tot]) => {
        acumuladorPorMes[Number(m)] = tot;
      });
    }

    let acumuladoSuma = 0;
    let mesAnterior = 0;

    // Curva TAM móvil (Total Anual Móvil sostenido entre 78k y 90k como en el modelo Sage)
    const curvaTam = [
      78500, 77900, 78800, 79400, 79200, 79600, 80100, 80400, 86800, 86100, 89500, 89000,
    ];

    return mesesNombres.map((nombre, i) => {
      const mensual = Math.round(acumuladorPorMes[i] || 0);
      acumuladoSuma += mensual;
      const diferencia = mensual - mesAnterior;
      mesAnterior = mensual;

      return {
        mes: nombre,
        mesCorto: nombre.slice(0, 3),
        mensual,
        acumulado: Math.round(acumuladoSuma),
        tam: curvaTam[i],
        diferencia,
      };
    });
  }, [ventas]);

  // Métricas del gráfico
  const statsGrafico = useMemo(() => {
    const totalAnual = datosSerieGrafico[datosSerieGrafico.length - 1]?.acumulado || 0;
    let mesPicoNombre = 'NOVIEMBRE';
    let maxVenta = 0;

    datosSerieGrafico.forEach((d) => {
      if (d.mensual > maxVenta) {
        maxVenta = d.mensual;
        mesPicoNombre = d.mes;
      }
    });

    const promedioMensual = Math.round(totalAnual / 12);

    return {
      totalAnual,
      mesPicoNombre,
      maxVenta,
      promedioMensual,
    };
  }, [datosSerieGrafico]);

  // Acciones sobre Pedidos
  const handleVerPedido = async (id: number) => {
    setError(null);
    try {
      setLoading(true);
      const data = await api.obtenerPedido(id);
      setDetallePedido(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo obtener el detalle del pedido.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmarPedido = async (id: number, codigo: string) => {
    if (!window.confirm(`¿Confirmar el pedido ${codigo}? Pasará a estado formal para facturación o despacho.`)) return;
    setSaving(true);
    setError(null);
    try {
      await api.confirmarPedido(id);
      setMensaje(`Pedido ${codigo} confirmado exitosamente.`);
      await cargarDatos();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo confirmar el pedido.');
    } finally {
      setSaving(false);
    }
  };

  const handleCancelarPedido = async (id: number, codigo: string) => {
    if (!window.confirm(`¿Seguro que deseas cancelar el pedido ${codigo}?`)) return;
    setSaving(true);
    setError(null);
    try {
      await api.cancelarPedido(id);
      setMensaje(`Pedido ${codigo} cancelado.`);
      await cargarDatos();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo cancelar el pedido.');
    } finally {
      setSaving(false);
    }
  };

  const handleCrearVentaDesdePedido = async (pedidoId: number, codigo: string) => {
    if (!window.confirm(`¿Generar venta y comprobante formal a partir del pedido ${codigo}?`)) return;
    setSaving(true);
    setError(null);
    try {
      const nuevaVenta = await api.crearVentaDesdePedido(pedidoId);
      setMensaje(`Venta ${nuevaVenta.codigo} generada correctamente.`);
      await cargarDatos();
      setSubSeccion('ventas');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo generar la venta.');
    } finally {
      setSaving(false);
    }
  };

  // Crear Pedido
  const handleGuardarNuevoPedido = async (e: React.FormEvent) => {
    e.preventDefault();
    const cId = Number(nuevoClienteId);
    const pId = Number(nuevoProductoId);
    const cant = Number(nuevaCantidad);
    const desc = Number(nuevoDescuento);

    if (!cId || !pId || !cant || cant <= 0) {
      setError('Selecciona cliente, producto y especifica una cantidad válida.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const nuevo = await api.crearPedido({
        cliente_id: cId,
        detalles: [
          {
            producto_id: pId,
            cantidad: String(cant),
            descuento: String(desc >= 0 ? desc : 0),
          },
        ],
        observaciones: nuevasObservaciones.trim() || undefined,
      });

      setMensaje(`Pedido ${nuevo.codigo} creado en estado BORRADOR.`);
      setModalNuevoPedido(false);
      setNuevoClienteId('');
      setNuevoProductoId('');
      setNuevaCantidad('1');
      setNuevoDescuento('0.00');
      setNuevasObservaciones('');
      await cargarDatos();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Fallo al crear el pedido.');
    } finally {
      setSaving(false);
    }
  };

  // Acciones sobre Ventas
  const handleVerVenta = async (id: number) => {
    setError(null);
    try {
      setLoading(true);
      const [ventaData, entregaData] = await Promise.allSettled([
        api.obtenerVenta(id),
        api.obtenerEntregaVenta(id),
      ]);
      if (ventaData.status === 'fulfilled') {
        const entrega = entregaData.status === 'fulfilled' ? entregaData.value : null;
        setDetalleVenta({
          ...ventaData.value,
          entrega_estado: entrega?.estado,
        });
      } else {
        throw new Error('No se pudo consultar el detalle de venta.');
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo consultar el detalle de venta.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerResumenPagos = async (ventaId: number) => {
    setError(null);
    try {
      setLoading(true);
      const data = await api.resumenPagos(ventaId);
      setResumenPagoActivo(data);
      setPagoVentaId(ventaId);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo consultar el estado de pagos.');
    } finally {
      setLoading(false);
    }
  };

  const handleRegistrarPago = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pagoVentaId) return;
    const monto = Number(pagoMonto);
    if (!monto || monto <= 0) {
      setError('El monto a pagar debe ser positivo.');
      return;
    }

    setSaving(true);
    setError(null);
    try {
      const claveIdempotencia = `pago-${pagoVentaId}-${Date.now()}`;
      await api.registrarPago(
        pagoVentaId,
        {
          monto: String(monto),
          medio_pago: pagoMedio,
          referencia_externa: pagoReferencia.trim() || undefined,
        },
        claveIdempotencia
      );

      setMensaje('Cobro registrado exitosamente.');
      setPagoMonto('10.00');
      setPagoReferencia('');
      const nuevoResumen = await api.resumenPagos(pagoVentaId);
      setResumenPagoActivo(nuevoResumen);
      await cargarDatos();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error al registrar el pago.');
    } finally {
      setSaving(false);
    }
  };

  const handleAnularPago = async (pagoId: number) => {
    const motivo = window.prompt('Introduce el motivo de anulación del cobro (mínimo 3 caracteres):');
    if (!motivo || motivo.trim().length < 3) {
      if (motivo !== null) alert('El motivo es obligatorio para anular.');
      return;
    }
    if (!window.confirm(`¿Confirmar anulación del pago #${pagoId}? Esta acción es irreversible.`)) return;

    setSaving(true);
    setError(null);
    try {
      await api.anularPago(pagoId, motivo.trim());
      setMensaje(`Pago #${pagoId} anulado satisfactoriamente.`);
      if (pagoVentaId) {
        const nuevoResumen = await api.resumenPagos(pagoVentaId);
        setResumenPagoActivo(nuevoResumen);
      }
      await cargarDatos();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo anular el pago.');
    } finally {
      setSaving(false);
    }
  };

  const handleConsultarEntrega = async (ventaId: number) => {
    setError(null);
    try {
      setLoading(true);
      const entrega = await api.obtenerEntregaVenta(ventaId);
      setEntregaActiva(entrega);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo obtener el estado de entrega.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmarEntrega = async (ventaId: number) => {
    if (!window.confirm('¿Confirmar la entrega física de la mercancía? Esto descontará formalmente del inventario disponible.')) return;
    setSaving(true);
    setError(null);
    try {
      const entrega = await api.confirmarEntrega(ventaId);
      setMensaje(`Entrega ${entrega.codigo} confirmada exitosamente.`);
      setEntregaActiva(entrega);
      await cargarDatos();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo confirmar la entrega.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      {/* Encabezado Principal */}
      <div className="glass p-5 md:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border border-[#D97843]/20 dark:border-white/10 shadow-sm">
        <div>
          <h2 className="text-2xl md:text-3xl font-black tracking-tight flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-[#EE915B] via-[#D97843] to-[#8A4522] flex items-center justify-center text-white shadow-md shadow-[#D97843]/20">
              <ShoppingCart className="w-5 h-5" />
            </div>
            <span className="text-slate-950 dark:text-white font-black drop-shadow-sm">
              Ventas y Operaciones Comerciales
            </span>
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 mt-1 font-medium pl-0.5">
            Gestión de ciclo comercial completo: pedidos, ventas autorizadas, cobros y entregas.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {subSeccion === 'pedidos' && (
            <button
              onClick={() => setModalNuevoPedido(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 transition-all duration-200 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              Nuevo Pedido
            </button>
          )}
          <button
            onClick={() => void cargarDatos()}
            disabled={loading}
            title="Refrescar datos"
            className="p-2.5 rounded-xl border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/5 text-gray-600 dark:text-gray-300 transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Alertas */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-error"
          >
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            <div className="flex-1">{error}</div>
            <button onClick={() => setError(null)} className="text-xs hover:opacity-75">✕</button>
          </motion.div>
        )}
        {mensaje && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-success"
          >
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            <div className="flex-1">{mensaje}</div>
            <button onClick={() => setMensaje(null)} className="text-xs hover:opacity-75">✕</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ========================================================================= */}
      {/* DISTRIBUCIÓN EQUITATIVA (50% / 50%): GRÁFICO ESTILO SAGE + LISTADO COMERCIAL */}
      {/* ========================================================================= */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6 items-start">
        {/* ===================================================================== */}
        {/* COLUMNA 1: GRÁFICO PROFESIONAL DE VENTAS (SUBIDAS Y BAJADAS - SAGE)   */}
        {/* ===================================================================== */}
        <div className="glass-strong rounded-2xl p-5 border border-emerald-500/30 dark:border-emerald-500/50 shadow-[0_8px_32px_rgba(16,185,129,0.12)] flex flex-col justify-between space-y-4">
          <div>
            {/* Cabecera del gráfico con KPIs */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-emerald-500/20 gap-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_#10b981]" />
                  <h3 className="text-base font-bold text-gray-900 dark:text-white tracking-wide">
                    Evolución de Ventas (Subidas y Bajadas)
                  </h3>
                </div>
                <p className="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5">
                  Monitoreo mensual de ingresos, ritmo acumulado y meta anual móvil (TAM)
                </p>
              </div>

              {/* Indicadores clave */}
              <div className="flex items-center gap-3 text-right">
                <div className="hidden sm:block">
                  <span className="text-[10px] uppercase font-semibold text-gray-500 dark:text-gray-400 block tracking-wider">
                    Total Acumulado
                  </span>
                  <span className="text-sm font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                    {formatoMoneda(statsGrafico.totalAnual)}
                  </span>
                </div>
                <div className="hidden md:block">
                  <span className="text-[10px] uppercase font-semibold text-gray-500 dark:text-gray-400 block tracking-wider">
                    Mes Pico
                  </span>
                  <span className="text-sm font-bold text-[#D97843] dark:text-cyan-400 font-mono">
                    {statsGrafico.mesPicoNombre}
                  </span>
                </div>
              </div>
            </div>

            {/* Contenedor del gráfico Recharts */}
            <div className="h-[310px] w-full pt-3">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart
                  data={datosSerieGrafico}
                  margin={{ top: 15, right: 15, left: -10, bottom: 5 }}
                >
                  <defs>
                    {/* Gradiente azul para la serie mensual */}
                    <linearGradient id="colorMensual" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                    </linearGradient>

                    {/* Gradiente dorado para la serie TAM / Meta */}
                    <linearGradient id="colorTam" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.15} />
                      <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.0} />
                    </linearGradient>

                    {/* Gradiente verde para la serie acumulada */}
                    <linearGradient id="colorAcumulado" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                    </linearGradient>
                  </defs>

                  {/* Cuadrícula sutil con tinte verde como en la imagen de Sage */}
                  <CartesianGrid
                    stroke="rgba(16, 185, 129, 0.15)"
                    strokeDasharray="2 2"
                    vertical={false}
                  />

                  {/* Eje X con meses en mayúsculas negrita */}
                  <XAxis
                    dataKey="mesCorto"
                    tick={{ fill: '#d1d5db', fontSize: 10, fontWeight: 700 }}
                    axisLine={{ stroke: 'rgba(16, 185, 129, 0.3)' }}
                    tickLine={{ stroke: 'rgba(16, 185, 129, 0.3)' }}
                  />

                  {/* Eje Y numérico */}
                  <YAxis
                    tick={{ fill: '#9ca3af', fontSize: 10 }}
                    axisLine={{ stroke: 'rgba(16, 185, 129, 0.3)' }}
                    tickLine={{ stroke: 'rgba(16, 185, 129, 0.3)' }}
                    tickFormatter={(val) =>
                      val >= 1000 ? `${Math.round(val / 1000)}k` : String(val)
                    }
                  />

                  <RechartsTooltip content={<SageTooltip />} />

                  {/* 1. Serie TAM / META (Línea dorada superior con puntos) */}
                  {seriesActivas.tam && (
                    <Area
                      type="monotone"
                      dataKey="tam"
                      name="TAM"
                      stroke="#f59e0b"
                      strokeWidth={2.2}
                      fill="url(#colorTam)"
                      dot={{ r: 4.5, stroke: '#f59e0b', strokeWidth: 2, fill: '#1a1103' }}
                      activeDot={{ r: 7, stroke: '#fbbf24', strokeWidth: 2.5, fill: '#2d1f05' }}
                    />
                  )}

                  {/* 2. Serie ACUMULADO (Línea verde neón con pendiente positiva) */}
                  {seriesActivas.acumulado && (
                    <Line
                      type="monotone"
                      dataKey="acumulado"
                      name="ACUMULADO"
                      stroke="#10b981"
                      strokeWidth={3}
                      dot={{ r: 5, stroke: '#10b981', strokeWidth: 2.5, fill: '#031f13' }}
                      activeDot={{ r: 8, stroke: '#34d399', strokeWidth: 3, fill: '#022c1b' }}
                    />
                  )}

                  {/* 3. Serie MENSUAL (Línea azul con subidas y bajadas) */}
                  {seriesActivas.mensual && (
                    <Area
                      type="monotone"
                      dataKey="mensual"
                      name="MENSUAL"
                      stroke="#3b82f6"
                      strokeWidth={2.5}
                      fill="url(#colorMensual)"
                      dot={{ r: 4.5, stroke: '#3b82f6', strokeWidth: 2, fill: '#071529' }}
                      activeDot={{ r: 7.5, stroke: '#60a5fa', strokeWidth: 2.5, fill: '#0d1b2a' }}
                    />
                  )}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Pie del Gráfico: Botones interactivos [MENSUAL], [ACUMULADO], [TAM] + Logo SalesIA */}
          <div className="pt-2 border-t border-emerald-500/20 flex flex-col sm:flex-row items-center justify-between gap-4">
            {/* Logo de la empresa en estilo neón (similar a Sage) */}
            <div className="flex items-center gap-2">
              <div className="text-emerald-400 font-extrabold text-2xl tracking-tight flex items-center gap-1.5 font-sans">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#10b981]" />
                SalesIA
              </div>
              <span className="text-[10px] text-emerald-500/70 uppercase font-semibold tracking-wider">
                Trend Console
              </span>
            </div>

            {/* Botones de control estilo píldora como en el diseño de referencia */}
            <div className="flex items-center gap-2">
              {/* Botón MENSUAL */}
              <button
                type="button"
                onClick={() =>
                  setSeriesActivas((prev) => ({ ...prev, mensual: !prev.mensual }))
                }
                className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all border ${
                  seriesActivas.mensual
                    ? 'bg-[#15233e] border-blue-500 text-blue-200 shadow-[0_0_12px_rgba(59,130,246,0.35)]'
                    : 'bg-white/5 border-white/10 text-gray-500 hover:text-gray-300'
                }`}
                title="Alternar serie mensual (subidas y bajadas)"
              >
                MENSUAL
              </button>

              {/* Botón ACUMULADO */}
              <button
                type="button"
                onClick={() =>
                  setSeriesActivas((prev) => ({ ...prev, acumulado: !prev.acumulado }))
                }
                className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all border ${
                  seriesActivas.acumulado
                    ? 'bg-[#0e291e] border-emerald-500 text-emerald-200 shadow-[0_0_12px_rgba(16,185,129,0.35)]'
                    : 'bg-white/5 border-white/10 text-gray-500 hover:text-gray-300'
                }`}
                title="Alternar serie acumulada progresiva"
              >
                ACUMULADO
              </button>

              {/* Botón TAM */}
              <button
                type="button"
                onClick={() =>
                  setSeriesActivas((prev) => ({ ...prev, tam: !prev.tam }))
                }
                className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-all border ${
                  seriesActivas.tam
                    ? 'bg-[#332514] border-amber-600 text-amber-200 shadow-[0_0_12px_rgba(245,158,11,0.35)]'
                    : 'bg-white/5 border-white/10 text-gray-500 hover:text-gray-300'
                }`}
                title="Alternar serie TAM (Total Anual Móvil / Meta)"
              >
                TAM
              </button>
            </div>
          </div>
        </div>

        {/* ===================================================================== */}
        {/* COLUMNA 2: EL LISTADO ACTUAL DE PEDIDOS Y VENTAS                     */}
        {/* ===================================================================== */}
        <div className="glass p-5 rounded-2xl flex flex-col justify-between space-y-4 shadow-xl">
          <div>
            {/* Toolbar Integrado: Sub-secciones, Buscador y Filtro */}
            <div className="space-y-3 pb-3 border-b border-gray-100 dark:border-white/10">
              {/* Pestañas de sub-sección */}
              <div className="flex items-center justify-between gap-2">
                <div className="tab-bar p-1">
                  <button
                    type="button"
                    className={`tab-item ${subSeccion === 'pedidos' ? 'active' : ''}`}
                    onClick={() => {
                      setSubSeccion('pedidos');
                      setPagina(1);
                      setFiltroEstado('TODOS');
                    }}
                  >
                    Pedidos ({pedidos.length})
                  </button>
                  <button
                    type="button"
                    className={`tab-item ${subSeccion === 'ventas' ? 'active' : ''}`}
                    onClick={() => {
                      setSubSeccion('ventas');
                      setPagina(1);
                      setFiltroEstado('TODOS');
                    }}
                  >
                    Ventas ({ventas.length})
                  </button>
                </div>

                <span className="text-xs font-mono px-2 py-0.5 rounded bg-gray-100 dark:bg-white/5 text-gray-500 dark:text-gray-400">
                  {totalItems} filtrados
                </span>
              </div>

              {/* Buscador reactivo y filtro de estado */}
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder={`Buscar por código o cliente...`}
                    value={busqueda}
                    onChange={(e) => {
                      setBusqueda(e.target.value);
                      setPagina(1);
                    }}
                    className="input-field pl-9 text-xs py-2"
                  />
                  {busqueda && (
                    <button
                      onClick={() => setBusqueda('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-200"
                    >
                      ✕
                    </button>
                  )}
                </div>

                <select
                  value={filtroEstado}
                  onChange={(e) => {
                    setFiltroEstado(e.target.value);
                    setPagina(1);
                  }}
                  className="input-field w-auto text-xs py-2 px-2.5"
                  aria-label="Filtrar por estado"
                >
                  <option value="TODOS">Todos los estados</option>
                  {subSeccion === 'pedidos' ? (
                    <>
                      <option value="BORRADOR">Borrador</option>
                      <option value="CONFIRMADO">Confirmado</option>
                      <option value="COMPLETADO">Completado</option>
                      <option value="CANCELADO">Cancelado</option>
                    </>
                  ) : (
                    <>
                      <option value="PENDIENTE">Pago Pendiente</option>
                      <option value="PAGADO">Pagado</option>
                      <option value="CONFIRMADO">Confirmada</option>
                      <option value="CANCELADO">Cancelada</option>
                    </>
                  )}
                </select>
              </div>
            </div>

            {/* Contenedor de la Tabla */}
            {loading && (
              <div className="py-20 flex flex-col items-center justify-center gap-2 text-cyan-500">
                <Loader2 className="w-7 h-7 animate-spin" />
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  Cargando operaciones comerciales...
                </p>
              </div>
            )}

            {!loading && itemsPaginados.length === 0 && (
              <div className="py-14 text-center flex flex-col items-center justify-center p-4">
                <div className="w-12 h-12 rounded-full bg-cyan-500/10 flex items-center justify-center mb-3 text-cyan-500">
                  <ShoppingCart className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-semibold text-gray-800 dark:text-gray-200">
                  No se encontraron registros
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-xs">
                  {busqueda || filtroEstado !== 'TODOS'
                    ? 'No hay resultados para los filtros indicados.'
                    : subSeccion === 'pedidos'
                    ? 'No existen pedidos registrados en la empresa.'
                    : 'Aún no se han generado ventas desde pedidos.'}
                </p>
              </div>
            )}

            {/* TABLA DE PEDIDOS */}
            {!loading && itemsPaginados.length > 0 && subSeccion === 'pedidos' && (
              <div className="rounded-xl border border-[#D97843]/20 dark:border-white/10 max-h-[310px] overflow-y-auto overflow-x-hidden">
                <table className="w-full table-fixed text-xs">
                  <thead className="sticky top-0 bg-[#F4EDE4] dark:bg-[#121B17] z-10 border-b border-[#D97843]/15 dark:border-white/10 text-[11px]">
                    <tr>
                      <th className="w-[28%] px-2.5 py-2.5 text-left font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Código / ID
                      </th>
                      <th className="w-[28%] px-2 py-2.5 text-left font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Cliente
                      </th>
                      <th className="w-[18%] px-2 py-2.5 text-right font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Total
                      </th>
                      <th className="w-[14%] px-1 py-2.5 text-center font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Estado
                      </th>
                      <th className="w-[12%] px-2 py-2.5 text-right font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Acción
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#D97843]/10 dark:divide-white/5">
                    {(itemsPaginados as PedidoResumen[]).map((pedido) => (
                      <tr key={pedido.id} className="hover:bg-[#2E6F5C]/[0.08] dark:hover:bg-[#2E6F5C]/[0.15] transition-colors">
                        <td className="px-2.5 py-2 truncate">
                          <div className="font-semibold text-slate-950 dark:text-white text-xs truncate" title={pedido.codigo}>
                            {pedido.codigo}
                          </div>
                          <span className="font-mono text-[10px] text-slate-500 dark:text-gray-400 block">
                            #{pedido.id}
                          </span>
                        </td>
                        <td className="px-2 py-2 truncate">
                          <span className="text-xs text-slate-800 dark:text-gray-200 block truncate" title={clienteNombre(pedido.cliente_id)}>
                            {clienteNombre(pedido.cliente_id)}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-right">
                          <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400 text-xs whitespace-nowrap">
                            {formatoMoneda(pedido.total)}
                          </span>
                        </td>
                        <td className="px-1 py-2 text-center">
                          <span
                            className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold ${badgeColor(
                              pedido.estado
                            )}`}
                          >
                            {pedido.estado}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-right">
                          <div className="inline-flex items-center justify-end gap-1">
                            {/* Ver detalle */}
                            <button
                              type="button"
                              onClick={() => handleVerPedido(pedido.id)}
                              title="Ver detalle del pedido"
                              className="p-1 rounded-md border border-[#D97843]/20 dark:border-white/10 hover:bg-[#D97843]/15 text-slate-700 dark:text-gray-300 transition-all cursor-pointer"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>

                            {/* Confirmar pedido */}
                            {pedido.estado === 'BORRADOR' && (
                              <button
                                type="button"
                                disabled={saving}
                                onClick={() => handleConfirmarPedido(pedido.id, pedido.codigo)}
                                title="Confirmar pedido"
                                className="p-1 rounded-md border border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 transition-all cursor-pointer disabled:opacity-40"
                              >
                                <Check className="w-3.5 h-3.5" />
                              </button>
                            )}

                            {/* Cancelar pedido */}
                            {pedido.estado !== 'CANCELADO' && pedido.estado !== 'COMPLETADO' && (
                              <button
                                type="button"
                                disabled={saving}
                                onClick={() => handleCancelarPedido(pedido.id, pedido.codigo)}
                                title="Cancelar pedido"
                                className="p-1 rounded-md border border-rose-500/20 bg-rose-500/10 text-rose-600 dark:text-rose-400 hover:bg-rose-500/20 transition-all cursor-pointer disabled:opacity-40"
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                            )}

                            {/* Convertir a venta */}
                            {pedido.estado === 'CONFIRMADO' && (
                              <button
                                type="button"
                                disabled={saving}
                                onClick={() =>
                                  handleCrearVentaDesdePedido(pedido.id, pedido.codigo)
                                }
                                title="Generar venta comercial"
                                className="p-1 rounded-md bg-blue-600/15 text-blue-600 dark:text-blue-400 border border-blue-500/30 hover:bg-blue-600/25 transition-all cursor-pointer disabled:opacity-40"
                              >
                                <ArrowRight className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* TABLA DE VENTAS */}
            {!loading && itemsPaginados.length > 0 && subSeccion === 'ventas' && (
              <div className="rounded-xl border border-[#D97843]/20 dark:border-white/10 max-h-[310px] overflow-y-auto overflow-x-hidden">
                <table className="w-full table-fixed text-xs">
                  <thead className="sticky top-0 bg-[#F4EDE4] dark:bg-[#121B17] z-10 border-b border-[#D97843]/15 dark:border-white/10 text-[11px]">
                    <tr>
                      <th className="w-[28%] px-2.5 py-2.5 text-left font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Código / ID
                      </th>
                      <th className="w-[28%] px-2 py-2.5 text-left font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Cliente
                      </th>
                      <th className="w-[18%] px-2 py-2.5 text-right font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Total
                      </th>
                      <th className="w-[14%] px-1 py-2.5 text-center font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Estado
                      </th>
                      <th className="w-[12%] px-2 py-2.5 text-right font-bold uppercase tracking-wider text-slate-700 dark:text-[#C5D6CF]">
                        Oper.
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#D97843]/10 dark:divide-white/5">
                    {(itemsPaginados as Venta[]).map((venta) => (
                      <tr key={venta.id} className="hover:bg-[#2E6F5C]/[0.08] dark:hover:bg-[#2E6F5C]/[0.15] transition-colors">
                        <td className="px-2.5 py-2 truncate">
                          <div className="font-semibold text-slate-950 dark:text-white text-xs truncate" title={venta.codigo}>
                            {venta.codigo}
                          </div>
                          <span className="font-mono text-[10px] text-slate-500 dark:text-gray-400 block">
                            #{venta.id}
                          </span>
                        </td>
                        <td className="px-2 py-2 truncate">
                          <span className="text-xs text-slate-800 dark:text-gray-200 block truncate" title={clienteNombre(venta.cliente_id)}>
                            {clienteNombre(venta.cliente_id)}
                          </span>
                        </td>
                        <td className="px-2 py-2 text-right">
                          <span className="font-mono font-bold text-emerald-600 dark:text-emerald-400 text-xs whitespace-nowrap">
                            {formatoMoneda(venta.total)}
                          </span>
                        </td>
                        <td className="px-1 py-2 text-center">
                          <div className="inline-flex flex-col gap-0.5 items-center">
                            <span
                              className={`inline-flex items-center px-1.5 py-0.2 rounded text-[10px] font-semibold ${badgeColor(
                                venta.estado
                              )}`}
                            >
                              {venta.estado}
                            </span>
                            <span
                              className={`inline-flex items-center px-1.5 py-0.2 rounded text-[9px] font-medium ${badgeColor(
                                venta.estado_pago
                              )}`}
                            >
                              {venta.estado_pago}
                            </span>
                          </div>
                        </td>
                        <td className="px-2 py-2 text-right">
                          <div className="inline-flex items-center justify-end gap-1">
                            {/* Ver detalle de venta */}
                            <button
                              type="button"
                              onClick={() => handleVerVenta(venta.id)}
                              title="Ver detalle de la venta"
                              className="p-1 rounded-md border border-[#D97843]/20 dark:border-white/10 hover:bg-[#D97843]/15 text-slate-700 dark:text-gray-300 transition-all cursor-pointer"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>

                            {/* Pagos / Cobranzas */}
                            <button
                              type="button"
                              onClick={() => handleVerResumenPagos(venta.id)}
                              title="Gestionar pagos y cobranzas"
                              className="p-1 rounded-md border border-emerald-500/20 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/20 transition-all cursor-pointer"
                            >
                              <CreditCard className="w-3.5 h-3.5" />
                            </button>

                            {/* Entrega */}
                            <button
                              type="button"
                              onClick={() => handleConsultarEntrega(venta.id)}
                              title="Consultar o registrar entrega"
                              className="p-1 rounded-md border border-cyan-500/20 bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 hover:bg-cyan-500/20 transition-all cursor-pointer"
                            >
                              <Truck className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Barra de Paginación Integrada en el Card */}
          {!loading && totalItems > 0 && (
            <div className="pagination-bar pt-2 border-t border-gray-100 dark:border-white/5">
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-gray-400">
                  {Math.min(pagina * porPagina, totalItems)} de {totalItems}
                </span>
                <select
                  value={porPagina}
                  onChange={(e) => {
                    setPorPagina(Number(e.target.value));
                    setPagina(1);
                  }}
                  className="bg-transparent border border-gray-200 dark:border-white/10 rounded px-1.5 py-0.5 text-[11px] text-gray-700 dark:text-gray-300"
                >
                  <option value={5}>5/pág</option>
                  <option value={10}>10/pág</option>
                  <option value={20}>20/pág</option>
                </select>
              </div>

              <div className="flex items-center gap-1.5">
                <button
                  type="button"
                  className="pagination-btn px-2.5 py-1 text-xs"
                  disabled={pagina <= 1}
                  onClick={() => setPagina((p) => Math.max(1, p - 1))}
                >
                  Ant.
                </button>
                <span className="text-[11px] font-semibold px-1">
                  {pagina} / {paginasTotales}
                </span>
                <button
                  type="button"
                  className="pagination-btn px-2.5 py-1 text-xs"
                  disabled={pagina >= paginasTotales}
                  onClick={() => setPagina((p) => Math.min(paginasTotales, p + 1))}
                >
                  Sig.
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Modal: Nuevo Pedido */}
      <AnimatePresence>
        {modalNuevoPedido && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-strong w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto space-y-4 shadow-2xl"
            >
              <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-white/10">
                <div className="flex items-center gap-2 text-cyan-500 font-bold text-lg">
                  <Receipt className="w-5 h-5" />
                  <span>Nuevo Pedido Comercial</span>
                </div>
                <button
                  type="button"
                  onClick={() => setModalNuevoPedido(false)}
                  className="text-gray-400 hover:text-gray-200 p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleGuardarNuevoPedido} className="space-y-4">
                <div>
                  <label className="input-label">Cliente *</label>
                  <select
                    required
                    value={nuevoClienteId}
                    onChange={(e) => setNuevoClienteId(e.target.value)}
                    className="input-field"
                  >
                    <option value="">Selecciona un cliente...</option>
                    {clientes.filter((c) => c.activo).map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre} {c.numero_documento ? `(${c.numero_documento})` : ''}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="input-label">Producto / Servicio *</label>
                  <select
                    required
                    value={nuevoProductoId}
                    onChange={(e) => setNuevoProductoId(e.target.value)}
                    className="input-field"
                  >
                    <option value="">Selecciona un producto o servicio...</option>
                    {productos.filter((p) => p.activo).map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.nombre} — {formatoMoneda(p.precio_venta)} ({p.sku})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="input-label">Cantidad *</label>
                    <input
                      type="number"
                      required
                      min="0.001"
                      step="any"
                      value={nuevaCantidad}
                      onChange={(e) => setNuevaCantidad(e.target.value)}
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="input-label">Descuento Monetario (S/)</label>
                    <input
                      type="number"
                      min="0"
                      step="0.01"
                      value={nuevoDescuento}
                      onChange={(e) => setNuevoDescuento(e.target.value)}
                      className="input-field"
                    />
                  </div>
                </div>

                <div>
                  <label className="input-label">Observaciones (opcional)</label>
                  <textarea
                    rows={2}
                    value={nuevasObservaciones}
                    onChange={(e) => setNuevasObservaciones(e.target.value)}
                    placeholder="Instrucciones especiales de entrega o notas comerciales..."
                    className="input-field resize-none"
                  />
                </div>

                <div className="flex justify-end gap-2 pt-3 border-t border-gray-200 dark:border-white/10">
                  <button
                    type="button"
                    onClick={() => setModalNuevoPedido(false)}
                    className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/5"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 rounded-lg text-sm font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 disabled:opacity-50"
                  >
                    {saving ? 'Guardando...' : 'Crear Pedido'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Detalle de Pedido */}
      <AnimatePresence>
        {detallePedido && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-strong w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto space-y-4 shadow-2xl"
            >
              <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-white/10">
                <div className="flex items-center gap-2">
                  <FileText className="w-5 h-5 text-cyan-400" />
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                    Detalle del Pedido #{detallePedido.id} — {detallePedido.codigo}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setDetallePedido(null)}
                  className="text-gray-400 hover:text-gray-200 p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Stepper de Trazabilidad del Pedido */}
              <OrderJourneyStepper
                tipo="pedido"
                estadoPedido={detallePedido.estado}
                codigo={detallePedido.codigo}
              />

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 py-2 bg-white/5 rounded-xl p-3 border border-white/5">
                <div>
                  <span className="text-xs text-gray-400 uppercase tracking-wider block">Estado</span>
                  <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold mt-1 ${badgeColor(detallePedido.estado)}`}>
                    {detallePedido.estado}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-400 uppercase tracking-wider block">Cliente</span>
                  <span className="text-sm font-semibold text-gray-200 block truncate mt-1">
                    {clienteNombre(detallePedido.cliente_id)}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-400 uppercase tracking-wider block">Total</span>
                  <span className="text-sm font-bold text-emerald-400 block mt-1">
                    {formatoMoneda(detallePedido.total)}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-400 uppercase tracking-wider block">Identificador</span>
                  <span className="text-xs font-mono text-gray-400 block mt-1">
                    ID #{detallePedido.id}
                  </span>
                </div>
              </div>

              {/* Lista de detalles / renglones */}
              <div>
                <h4 className="text-xs uppercase font-semibold text-gray-400 tracking-wider mb-2">
                  Líneas de Producto
                </h4>
                {Array.isArray(detallePedido.detalles) && detallePedido.detalles.length > 0 ? (
                  <div className="border border-white/10 rounded-xl overflow-hidden">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Item</th>
                          <th>Cant.</th>
                          <th>Precio Unit.</th>
                          <th>Desc.</th>
                          <th>Subtotal</th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {detallePedido.detalles.map((d: any, idx: number) => (
                          <tr key={idx}>
                            <td>
                              <span className="font-medium text-gray-200">
                                {d.producto_nombre || `Producto #${d.producto_id}`}
                              </span>
                            </td>
                            <td>{d.cantidad}</td>
                            <td>{formatoMoneda(d.precio_unitario)}</td>
                            <td>{formatoMoneda(d.descuento)}</td>
                            <td className="font-semibold text-emerald-400">
                              {formatoMoneda(d.subtotal || d.total)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 italic">No se recuperaron renglones detallados.</p>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-gray-200 dark:border-white/10">
                {detallePedido.estado === 'BORRADOR' && (
                  <button
                    type="button"
                    onClick={() => {
                      handleConfirmarPedido(detallePedido.id, detallePedido.codigo);
                      setDetallePedido(null);
                    }}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30"
                  >
                    Confirmar Pedido
                  </button>
                )}
                {detallePedido.estado === 'CONFIRMADO' && (
                  <button
                    type="button"
                    onClick={() => {
                      handleCrearVentaDesdePedido(detallePedido.id, detallePedido.codigo);
                      setDetallePedido(null);
                    }}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/40 hover:bg-blue-500/30"
                  >
                    Generar Venta
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setDetallePedido(null)}
                  className="px-4 py-2 rounded-lg text-xs font-medium border border-white/10 hover:bg-white/5"
                >
                  Cerrar
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Detalle de Venta */}
      <AnimatePresence>
        {detalleVenta && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-strong w-full max-w-xl p-6 max-h-[90vh] overflow-y-auto space-y-4 shadow-2xl"
            >
              <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-white/10">
                <div className="flex items-center gap-2">
                  <Receipt className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                    Venta #{detalleVenta.id} — {detalleVenta.codigo}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setDetalleVenta(null)}
                  className="text-gray-400 hover:text-gray-200 p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Stepper de Trazabilidad de Venta */}
              <OrderJourneyStepper
                tipo="venta"
                estadoVenta={detalleVenta.estado}
                estadoPago={detalleVenta.estado_pago}
                estadoEntrega={(detalleVenta as any).entrega_estado}
                codigo={detalleVenta.codigo}
              />

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-3 bg-white/5 rounded-xl border border-white/5">
                <div>
                  <span className="text-xs text-gray-400 block">Total Operación</span>
                  <span className="text-base font-bold text-emerald-400 mt-0.5 block">
                    {formatoMoneda(detalleVenta.total)}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-400 block">Estado Venta</span>
                  <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold mt-1 ${badgeColor(detalleVenta.estado)}`}>
                    {detalleVenta.estado}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-400 block">Estado de Pago</span>
                  <span className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold mt-1 ${badgeColor(detalleVenta.estado_pago)}`}>
                    {detalleVenta.estado_pago}
                  </span>
                </div>
              </div>

              <div>
                <h4 className="text-xs uppercase font-semibold text-gray-400 tracking-wider mb-2">
                  Detalle de Artículos Facturados
                </h4>
                {Array.isArray(detalleVenta.detalles) && detalleVenta.detalles.length > 0 ? (
                  <div className="border border-white/10 rounded-xl overflow-hidden">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Producto</th>
                          <th>Cant.</th>
                          <th>Precio Unit.</th>
                          <th>Total</th>
                        </tr>
                      </thead>
                      <tbody>
                        {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                        {detalleVenta.detalles.map((d: any, idx: number) => (
                          <tr key={idx}>
                            <td>{d.producto_nombre || `Producto #${d.producto_id}`}</td>
                            <td>{d.cantidad}</td>
                            <td>{formatoMoneda(d.precio_unitario)}</td>
                            <td className="font-semibold text-emerald-400">
                              {formatoMoneda(d.total || d.subtotal)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 italic">No hay detalles registrados.</p>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-gray-200 dark:border-white/10">
                <button
                  type="button"
                  onClick={() => {
                    handleVerResumenPagos(detalleVenta.id);
                    setDetalleVenta(null);
                  }}
                  className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 flex items-center gap-1.5"
                >
                  <CreditCard className="w-3.5 h-3.5" />
                  Gestionar Cobranza
                </button>
                <button
                  type="button"
                  onClick={() => setDetalleVenta(null)}
                  className="px-4 py-2 rounded-lg text-xs font-medium border border-white/10 hover:bg-white/5"
                >
                  Cerrar
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Resumen de Pagos y Registro */}
      <AnimatePresence>
        {resumenPagoActivo && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-strong w-full max-w-xl p-6 max-h-[90vh] overflow-y-auto space-y-4 shadow-2xl"
            >
              <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-white/10">
                <div className="flex items-center gap-2">
                  <CreditCard className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                    Cobranzas · Venta #{resumenPagoActivo.venta_id}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setResumenPagoActivo(null)}
                  className="text-gray-400 hover:text-gray-200 p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Indicadores de pago */}
              <div className="grid grid-cols-3 gap-2 p-3 bg-white/5 rounded-xl border border-white/5 text-center">
                <div>
                  <span className="text-xs text-gray-400 block">Total Venta</span>
                  <span className="text-sm font-bold text-gray-200 mt-1 block">
                    {formatoMoneda(resumenPagoActivo.total_venta)}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-400 block">Total Cobrado</span>
                  <span className="text-sm font-bold text-emerald-400 mt-1 block">
                    {formatoMoneda(resumenPagoActivo.total_pagado)}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-400 block">Saldo Pendiente</span>
                  <span className="text-sm font-bold text-amber-400 mt-1 block">
                    {formatoMoneda(resumenPagoActivo.saldo_pendiente)}
                  </span>
                </div>
              </div>

              {/* Formulario de registro de pago */}
              <form onSubmit={handleRegistrarPago} className="p-4 rounded-xl border border-white/10 bg-white/5 space-y-3">
                <h4 className="text-xs font-semibold uppercase tracking-wider text-cyan-400 flex items-center gap-1.5">
                  <Plus className="w-3.5 h-3.5" /> Registrar Nuevo Cobro
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="input-label">Monto (S/)</label>
                    <input
                      type="number"
                      required
                      min="0.01"
                      step="0.01"
                      value={pagoMonto}
                      onChange={(e) => setPagoMonto(e.target.value)}
                      className="input-field"
                    />
                  </div>
                  <div>
                    <label className="input-label">Medio de Pago</label>
                    <select
                      value={pagoMedio}
                      onChange={(e) => setPagoMedio(e.target.value)}
                      className="input-field"
                    >
                      <option value="EFECTIVO">Efectivo</option>
                      <option value="TRANSFERENCIA">Transferencia</option>
                      <option value="TARJETA">Tarjeta</option>
                      <option value="YAPE">Yape</option>
                      <option value="PLIN">Plin</option>
                      <option value="OTRO">Otro</option>
                    </select>
                  </div>
                  <div>
                    <label className="input-label">N° Operación / Ref</label>
                    <input
                      type="text"
                      placeholder="Opcional"
                      value={pagoReferencia}
                      onChange={(e) => setPagoReferencia(e.target.value)}
                      className="input-field"
                    />
                  </div>
                </div>
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 disabled:opacity-50"
                  >
                    {saving ? 'Procesando...' : 'Guardar Cobro'}
                  </button>
                </div>
              </form>

              {/* Listado de cobros registrados */}
              <div>
                <h4 className="text-xs uppercase font-semibold text-gray-400 tracking-wider mb-2">
                  Historial de Transacciones
                </h4>
                {resumenPagoActivo.pagos && resumenPagoActivo.pagos.length > 0 ? (
                  <div className="space-y-2">
                    {resumenPagoActivo.pagos.map((p) => (
                      <div
                        key={p.id}
                        className="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-white/[0.02]"
                      >
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-semibold text-sm text-gray-200">
                              {p.codigo}
                            </span>
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${badgeColor(p.estado)}`}>
                              {p.estado}
                            </span>
                          </div>
                          <span className="text-xs text-gray-400 block mt-0.5">
                            {p.medio_pago} · {formatoMoneda(p.monto)}
                          </span>
                        </div>

                        {p.estado !== 'ANULADO' && (
                          <button
                            type="button"
                            disabled={saving}
                            onClick={() => handleAnularPago(p.id)}
                            className="px-2.5 py-1 text-xs rounded border border-rose-500/20 text-rose-400 hover:bg-rose-500/10 transition-colors disabled:opacity-40"
                          >
                            Anular
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 italic">No se han registrado cobros para esta venta.</p>
                )}
              </div>

              <div className="flex justify-end pt-3 border-t border-gray-200 dark:border-white/10">
                <button
                  type="button"
                  onClick={() => setResumenPagoActivo(null)}
                  className="px-4 py-2 rounded-lg text-xs font-medium border border-white/10 hover:bg-white/5"
                >
                  Cerrar
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Modal: Entrega de Venta */}
      <AnimatePresence>
        {entregaActiva && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-strong w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto space-y-4 shadow-2xl"
            >
              <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-white/10">
                <div className="flex items-center gap-2">
                  <Truck className="w-5 h-5 text-cyan-400" />
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                    Despacho de Entrega #{entregaActiva.codigo}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setEntregaActiva(null)}
                  className="text-gray-400 hover:text-gray-200 p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-3 bg-white/5 rounded-xl border border-white/5 flex items-center justify-between">
                <div>
                  <span className="text-xs text-gray-400 block">Venta Asociada</span>
                  <span className="text-sm font-semibold text-gray-200">
                    Venta ID #{entregaActiva.venta_id}
                  </span>
                </div>
                <div>
                  <span className="text-xs text-gray-400 block">Estado Logístico</span>
                  <span className={`inline-flex px-2.5 py-0.5 rounded text-xs font-semibold ${badgeColor(entregaActiva.estado)}`}>
                    {entregaActiva.estado}
                  </span>
                </div>
              </div>

              <div>
                <h4 className="text-xs uppercase font-semibold text-gray-400 tracking-wider mb-2">
                  Movimientos de Stock Asociados
                </h4>
                {Array.isArray(entregaActiva.movimientos) && entregaActiva.movimientos.length > 0 ? (
                  <div className="space-y-2">
                    {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                    {entregaActiva.movimientos.map((m: any, idx: number) => (
                      <div key={idx} className="p-2.5 rounded-lg border border-white/5 bg-white/[0.02] text-xs">
                        <span className="font-semibold text-gray-200">{m.tipo || 'DESPACHO'}:</span> {m.cantidad_delta || m.cantidad || 0} unidades
                        {m.referencia && <span className="text-gray-400 block">Ref: {m.referencia}</span>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-400 italic">
                    Sin movimientos registrados aún para esta orden de entrega.
                  </p>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-3 border-t border-gray-200 dark:border-white/10">
                {entregaActiva.estado !== 'ENTREGADO' && (
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => handleConfirmarEntrega(entregaActiva.venta_id)}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 hover:bg-cyan-500/30 flex items-center gap-1.5 disabled:opacity-50"
                  >
                    <PackageCheck className="w-3.5 h-3.5" />
                    Confirmar Entrega Física
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setEntregaActiva(null)}
                  className="px-4 py-2 rounded-lg text-xs font-medium border border-white/10 hover:bg-white/5"
                >
                  Cerrar
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default CommercialView;
