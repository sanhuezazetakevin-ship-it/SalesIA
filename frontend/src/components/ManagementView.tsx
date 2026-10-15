import React, { useCallback, useEffect, useRef, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  Package,
  FolderTree,
  Boxes,
  BarChart3,
  Search,
  Plus,
  RefreshCw,
  Edit2,
  Trash2,
  X,
  AlertTriangle,
  CheckCircle2,
  Calendar,
  Layers,
  TrendingUp,
  Tag,
  Check,
  ChevronLeft,
  ChevronRight,
  Info
} from 'lucide-react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  Cell
} from 'recharts';
import { api } from '../services/api';
import type { Cliente, Producto } from '../types/api';
import { StockRunwayBadge } from './ui';

type Tab = 'clientes' | 'productos' | 'categorias' | 'inventario' | 'segmentacion' | 'analisis';
type Categoria = { id: number; nombre: string; descripcion?: string | null; activo: boolean };
type StockItem = { producto_id: number; nombre: string; [key: string]: unknown };
type RfmItem = { cliente_id: number; nombre: string; segmento?: string; [key: string]: unknown };
type Item = Cliente | Producto | Categoria;

const hoy = () => new Date().toLocaleDateString('en-CA');
const importe = (x: unknown) =>
  Number.isFinite(Number(x))
    ? new Intl.NumberFormat('es-PE', { style: 'currency', currency: 'PEN' }).format(Number(x))
    : 'S/ 0.00';
const texto = (x: unknown) => (x === null || x === undefined || x === '' ? 'N/D' : String(x));
const optional = (s: string) => (s.trim() ? s.trim() : undefined);

const badgeColor = (activo: boolean | string) => {
  if (activo === true || activo === 'ACTIVO') {
    return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20';
  }
  return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20';
};

const renderStockPill = (stockActual: unknown) => {
  const n = Number(stockActual);
  if (!Number.isFinite(n) || n === 0) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20">
        <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
        Agotado (0)
      </span>
    );
  }
  if (n <= 20) {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
        {n} en stock (Bajo)
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
      {n} en stock (Óptimo)
    </span>
  );
};

export const ManagementView: React.FC = () => {
  const [tab, setTab] = useState<Tab>('clientes');
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const [localPage, setLocalPage] = useState(1);
  const [localLimit, setLocalLimit] = useState(10);
  const [total, setTotal] = useState(0);

  // Datos principales
  const [items, setItems] = useState<Item[]>([]);
  const [stock, setStock] = useState<StockItem[]>([]);
  const [segments, setSegments] = useState<RfmItem[]>([]);

  // Datos analíticos
  const [analisisProductos, setAnalisisProductos] = useState<Producto[]>([]);
  const [analisisClientes, setAnalisisClientes] = useState<RfmItem[]>([]);
  const [analisisStock, setAnalisisStock] = useState<StockItem[]>([]);
  const [analisisCategorias, setAnalisisCategorias] = useState<Categoria[]>([]);
  const [analisisError, setAnalisisError] = useState<string[]>([]);

  // Rango de fechas para visualizaciones
  const [start, setStart] = useState(() => {
    const d = new Date();
    d.setDate(d.getDate() - 180);
    return d.toLocaleDateString('en-CA');
  });
  const [end, setEnd] = useState(hoy);

  // Estados de control
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');

  // Formulario y edición
  const [edit, setEdit] = useState<Item | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<Record<string, string | boolean>>({});

  // Buscador de categorías dinámico
  const [categoriaBusqueda, setCategoriaBusqueda] = useState('');
  const [categoriasDisponibles, setCategoriasDisponibles] = useState<Categoria[]>([]);
  const [categoriaAbierta, setCategoriaAbierta] = useState(false);
  const [categoriasCargando, setCategoriasCargando] = useState(false);
  const [categoriaError, setCategoriaError] = useState('');
  const [categoriaTotal, setCategoriaTotal] = useState(0);

  const categoriasSeq = useRef(0);
  const seq = useRef(0);

  // Consulta al backend
  const cargar = useCallback(async () => {
    const seqId = ++seq.current;
    setLoading(true);
    setError('');
    try {
      if (tab === 'clientes') {
        const r = await api.getClientes(page, 20, search);
        if (seqId === seq.current) {
          setItems(r.clientes);
          setTotal(r.total);
        }
      } else if (tab === 'productos') {
        const r = await api.getProductos(page, 20, search);
        if (seqId === seq.current) {
          setItems(r.productos);
          setTotal(r.total);
        }
      } else if (tab === 'categorias') {
        const r = await api.listarCategoriasPagina(page, 20, search);
        if (seqId === seq.current) {
          setItems(r.categorias);
          setTotal(r.total);
        }
      } else if (tab === 'inventario') {
        const r = await api.getInventarioVisual(start, end);
        if (seqId === seq.current) {
          setStock(r.items);
          setTotal(r.items.length);
        }
      } else if (tab === 'analisis') {
        const endpoints = await Promise.allSettled([
          api.getProductos(1, 100),
          api.listarCategoriasPagina(1, 100),
          api.getInventarioVisual(start, end),
          api.getClientesVisual(start, end),
        ]);
        if (seqId === seq.current) {
          const missing: string[] = [];
          if (endpoints[0].status === 'fulfilled') setAnalisisProductos(endpoints[0].value.productos);
          else {
            setAnalisisProductos([]);
            missing.push('productos');
          }
          if (endpoints[1].status === 'fulfilled') setAnalisisCategorias(endpoints[1].value.categorias);
          else {
            setAnalisisCategorias([]);
            missing.push('categorías');
          }
          if (endpoints[2].status === 'fulfilled') setAnalisisStock(endpoints[2].value.items);
          else {
            setAnalisisStock([]);
            missing.push('inventario');
          }
          if (endpoints[3].status === 'fulfilled') setAnalisisClientes(endpoints[3].value.items);
          else {
            setAnalisisClientes([]);
            missing.push('clientes RFM');
          }
          setAnalisisError(missing);
        }
      } else {
        const r = await api.getClientesVisual(start, end);
        if (seqId === seq.current) {
          setSegments(r.items);
          setTotal(r.items.length);
        }
      }
    } catch (e: unknown) {
      if (seqId === seq.current) setError(e instanceof Error ? e.message : 'No se pudo cargar información.');
    } finally {
      if (seqId === seq.current) setLoading(false);
    }
  }, [tab, page, search, start, end]);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  // Limpiar mensaje temporal
  useEffect(() => {
    if (message) {
      const t = setTimeout(() => setMessage(''), 4000);
      return () => clearTimeout(t);
    }
  }, [message]);

  // Autocompletado de categorías
  useEffect(() => {
    if (!showForm || tab !== 'productos') return;
    const id = ++categoriasSeq.current;
    const timer = window.setTimeout(async () => {
      setCategoriasCargando(true);
      setCategoriaError('');
      try {
        const respuesta = await api.listarCategoriasPagina(1, 100, categoriaBusqueda.trim());
        if (id !== categoriasSeq.current) return;
        setCategoriasDisponibles(respuesta.categorias.filter((c) => c.activo));
        setCategoriaTotal(respuesta.total);
      } catch (err: unknown) {
        if (id === categoriasSeq.current) {
          setCategoriasDisponibles([]);
          setCategoriaError(err instanceof Error ? err.message : 'No se pudieron cargar las categorías.');
        }
      } finally {
        if (id === categoriasSeq.current) setCategoriasCargando(false);
      }
    }, 250);
    return () => {
      window.clearTimeout(timer);
      categoriasSeq.current++;
    };
  }, [showForm, tab, categoriaBusqueda]);

  const categoriaActual = categoriasDisponibles.find((c) => String(c.id) === String(form.categoria_id || ''));

  const cambiarTab = (t: Tab) => {
    setLocalPage(1);
    setTab(t);
    setPage(1);
    setQuery('');
    setSearch('');
    setItems([]);
    setError('');
    setMessage('');
    setShowForm(false);
  };

  const abrirFormulario = (item?: Item) => {
    const values: Record<string, string | boolean> = {};
    if (item) {
      Object.entries(item).forEach(([k, v]) => {
        if (typeof v === 'string' || typeof v === 'boolean' || typeof v === 'number') {
          values[k] = typeof v === 'boolean' ? v : String(v);
        }
      });
    }
    setCategoriaBusqueda('');
    setCategoriaAbierta(false);
    setCategoriaError('');
    setEdit(item || null);
    setForm(values);
    setShowForm(true);
    setError('');
    setMessage('');
  };

  const cambiar = (k: string, v: string | boolean) => setForm((x) => ({ ...x, [k]: v }));
  const valor = (k: string) => String(form[k] ?? '');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');
    const nombreVal = valor('nombre').trim();
    if (nombreVal.length < 2) {
      setError('El nombre debe tener al menos dos caracteres.');
      return;
    }
    let payload: Record<string, unknown> = { nombre: nombreVal };

    if (tab === 'clientes') {
      const tipo = valor('tipo_documento');
      const doc = valor('numero_documento').trim();
      if (Boolean(tipo) !== Boolean(doc)) {
        setError('Indica tipo y número de documento conjuntamente.');
        return;
      }
      payload = {
        nombre: nombreVal,
        ...(tipo ? { tipo_documento: tipo, numero_documento: doc } : {}),
        ...Object.fromEntries(
          ['email', 'telefono', 'direccion']
            .map((k) => [k, optional(valor(k))])
            .filter(([, v]) => v !== undefined)
        ),
      };
    } else if (tab === 'productos') {
      const precio = valor('precio_venta').trim();
      const costo = valor('costo_referencia').trim() || '0.00';
      if (!/^(0|[1-9]\d*)(\.\d{1,2})?$/.test(precio) || !/^(0|[1-9]\d*)(\.\d{1,2})?$/.test(costo)) {
        setError('Los importes deben ser positivos con máximo dos decimales.');
        return;
      }
      const sku = valor('sku').trim();
      if (!sku) {
        setError('El SKU es obligatorio.');
        return;
      }
      const cat = valor('categoria_id').trim();
      if (cat && (!/^\d+$/.test(cat) || Number(cat) < 1)) {
        setError('Selecciona una categoría válida de la lista.');
        return;
      }
      payload = {
        nombre: nombreVal,
        sku,
        tipo_item: valor('tipo_item') || 'PRODUCTO',
        precio_venta: precio,
        costo_referencia: costo,
        controla_stock: Boolean(form.controla_stock ?? true),
        ...(cat ? { categoria_id: Number(cat) } : {}),
        ...(optional(valor('descripcion')) ? { descripcion: valor('descripcion').trim() } : {}),
      };
    } else if (tab === 'categorias') {
      payload = {
        nombre: nombreVal,
        ...(optional(valor('descripcion')) ? { descripcion: valor('descripcion').trim() } : {}),
      };
    } else return;

    setSaving(true);
    try {
      if (tab === 'clientes') {
        if (edit) await api.actualizarCliente(edit.id, payload);
        else await api.crearCliente(payload);
      } else if (tab === 'productos') {
        if (edit) await api.actualizarProducto(edit.id, payload);
        else await api.crearProducto(payload);
      } else {
        if (edit) await api.actualizarCategoria(edit.id, payload);
        else await api.crearCategoria(payload as { nombre: string; descripcion?: string });
      }
      setMessage(edit ? 'Registro actualizado correctamente.' : 'Registro creado correctamente.');
      setShowForm(false);
      setEdit(null);
      await cargar();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'No se pudo guardar.');
    } finally {
      setSaving(false);
    }
  };

  const desactivar = async (item: Item) => {
    if (!window.confirm(`¿Desactivar “${item.nombre}”? Esta acción es una baja lógica.`)) return;
    setSaving(true);
    setError('');
    setMessage('');
    try {
      if (tab === 'clientes') await api.desactivarCliente(item.id);
      if (tab === 'productos') await api.desactivarProducto(item.id);
      if (tab === 'categorias') await api.desactivarCategoria(item.id);
      setMessage('Registro desactivado satisfactoriamente.');
      await cargar();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'No se pudo desactivar.');
    } finally {
      setSaving(false);
    }
  };

  const tabsConfig: [Tab, string, React.ReactNode][] = [
    ['clientes', 'Clientes', <Users className="w-4 h-4" />],
    ['productos', 'Productos', <Package className="w-4 h-4" />],
    ['categorias', 'Categorías', <FolderTree className="w-4 h-4" />],
    ['inventario', 'Inventario y Alertas', <Boxes className="w-4 h-4" />],
    ['segmentacion', 'Segmentación RFM', <Layers className="w-4 h-4" />],
    ['analisis', 'Panel de Análisis', <BarChart3 className="w-4 h-4" />],
  ];

  const readOnly = tab === 'inventario' || tab === 'segmentacion' || tab === 'analisis';

  // Cálculos de métricas analíticas
  const conteos = (nombres: string[]): { etiqueta: string; valor: number }[] =>
    Object.entries(
      nombres.reduce<Record<string, number>>((acc, n) => {
        acc[n] = (acc[n] || 0) + 1;
        return acc;
      }, {})
    )
      .map(([etiqueta, valor]) => ({ etiqueta, valor }))
      .sort((a, b) => b.valor - a.valor);

  const resumenRiesgos = (lista: StockItem[]) => conteos(lista.map((x) => texto(x.riesgo)));
  const topStock = (lista: StockItem[]) =>
    lista.map((x) => ({ etiqueta: x.nombre, valor: Number(x.stock_actual) || 0 })).sort((a, b) => b.valor - a.valor);
  const topDemanda = (lista: StockItem[]) =>
    lista.map((x) => ({ etiqueta: x.nombre, valor: Number(x.demanda_estimada) || 0 })).sort((a, b) => b.valor - a.valor);

  const stockAlto = stock.filter((x) => x.riesgo === 'ALTO').length;
  const totalCompras = segments.reduce((sum, x) => sum + (Number(x.frecuencia) || 0), 0);
  const gastoRfm = segments.reduce((sum, x) => sum + (Number(x.valor_monetario) || 0), 0);
  const catalogoCategorias = conteos(
    analisisProductos.map((x) => analisisCategorias.find((c) => c.id === x.categoria_id)?.nombre || 'Sin categoría')
  );
  const productosPorTipo = conteos(analisisProductos.map((x) => texto(x.tipo_item)));
  const preciosPorCategoria = analisisCategorias
    .map((c) => ({
      etiqueta: c.nombre,
      valor: analisisProductos
        .filter((p) => p.categoria_id === c.id)
        .reduce((sum, p) => sum + (Number(p.precio_venta) || 0), 0),
    }))
    .sort((a, b) => b.valor - a.valor);

  // Componente de barras visuales estilizadas
  const barras = (titulo: string, datos: { etiqueta: string; valor: number }[], unidad: 'numero' | 'dinero' = 'numero') => {
    const disponibles = datos.filter((d) => Number.isFinite(d.valor) && d.valor >= 0).slice(0, 10);
    const mayor = Math.max(1, ...disponibles.map((x) => x.valor));

    return (
      <div className="glass p-5 space-y-4">
        <h4 className="text-sm font-bold text-gray-900 dark:text-white flex items-center justify-between">
          <span>{titulo}</span>
          <span className="text-xs font-normal text-gray-400">Top {disponibles.length}</span>
        </h4>
        {!disponibles.length ? (
          <p className="text-xs text-gray-400 py-6 text-center italic">Aún no hay datos para este gráfico.</p>
        ) : (
          <div className="space-y-3">
            {disponibles.map((d, i) => (
              <div key={`${d.etiqueta}-${i}`} className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-medium text-gray-700 dark:text-gray-300 truncate max-w-[200px]" title={d.etiqueta}>
                    {d.etiqueta}
                  </span>
                  <span className="font-semibold text-cyan-600 dark:text-cyan-400">
                    {unidad === 'dinero'
                      ? importe(d.valor)
                      : new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 }).format(d.valor)}
                  </span>
                </div>
                <div className="h-2 w-full bg-gray-100 dark:bg-white/5 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.max(4, (d.valor / mayor) * 100)}%` }}
                    transition={{ duration: 0.5, ease: 'easeOut' }}
                    className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 rounded-full"
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      {/* Encabezado */}
      <div className="glass p-5 md:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border border-[#D97843]/20 dark:border-white/10 shadow-sm">
        <div>
          <h2 className="text-2xl md:text-3xl font-black text-slate-950 dark:text-white tracking-tight flex items-center gap-2.5 drop-shadow-sm">
            <Package className="w-7 h-7 text-[#D97843] dark:text-[#FFA675]" />
            Gestión Comercial y Operativa
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 font-medium mt-1">
            Administración integral de clientes, catálogo de productos, inventario en tiempo real y segmentación.
          </p>
        </div>

        <div className="flex items-center gap-2">
          {!readOnly && (
            <button
              onClick={() => abrirFormulario()}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 transition-all duration-200 cursor-pointer"
            >
              <Plus className="w-4 h-4" />
              <span>Nuevo {tab === 'clientes' ? 'Cliente' : tab === 'productos' ? 'Producto' : 'Categoría'}</span>
            </button>
          )}
          <button
            onClick={() => void cargar()}
            disabled={loading}
            title="Refrescar datos"
            className="p-2.5 rounded-xl border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/5 text-gray-600 dark:text-gray-300 transition-colors cursor-pointer disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Tab bar superior */}
      <div className="tab-bar overflow-x-auto">
        {tabsConfig.map(([id, label, icon]) => (
          <button
            key={id}
            type="button"
            className={`tab-item flex items-center gap-2 whitespace-nowrap ${tab === id ? 'active' : ''}`}
            onClick={() => cambiarTab(id)}
          >
            {icon}
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Barra de Filtros / Búsqueda */}
      <div className="glass p-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
        {!readOnly ? (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              setPage(1);
              setSearch(query);
            }}
            className="flex flex-1 max-w-md items-center gap-2"
          >
            <div className="relative flex-1">
              <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Buscar por nombre, documento o SKU..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="input-field pl-10"
              />
              {query && (
                <button
                  type="button"
                  onClick={() => {
                    setQuery('');
                    setSearch('');
                    setPage(1);
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-white"
                >
                  ✕
                </button>
              )}
            </div>
            <button
              type="submit"
              className="px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20 hover:bg-cyan-500/20 cursor-pointer"
            >
              Buscar
            </button>
          </form>
        ) : (
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <span className="font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-cyan-400" /> Rango de Análisis:
            </span>
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-1.5">
                <span className="text-gray-400">Desde:</span>
                <input
                  type="date"
                  value={start}
                  onChange={(e) => setStart(e.target.value)}
                  className="input-field py-1 px-2 text-xs w-auto"
                />
              </label>
              <label className="flex items-center gap-1.5">
                <span className="text-gray-400">Hasta:</span>
                <input
                  type="date"
                  value={end}
                  onChange={(e) => setEnd(e.target.value)}
                  className="input-field py-1 px-2 text-xs w-auto"
                />
              </label>
            </div>
          </div>
        )}

        <div className="text-xs text-gray-500 dark:text-gray-400 self-center sm:self-auto">
          Total: <strong className="text-gray-900 dark:text-white">{total}</strong> registros encontrados
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
            <div className="flex-1 font-medium">{error}</div>
            <button onClick={() => setError('')} className="text-xs hover:opacity-75">✕</button>
          </motion.div>
        )}
        {message && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-success"
          >
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            <div className="flex-1 font-medium">{message}</div>
            <button onClick={() => setMessage('')} className="text-xs hover:opacity-75">✕</button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* PANELES DE VISTA SEGÚN TAB */}
      {!readOnly ? (
        /* TABLAS: CLIENTES, PRODUCTOS, CATEGORÍAS */
        <div className="glass overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Nombre</th>
                  {tab === 'productos' && (
                    <>
                      <th>SKU</th>
                      <th>Precio Venta</th>
                      <th>Tipo</th>
                      <th>Stock Físico</th>
                    </>
                  )}
                  {tab === 'clientes' && (
                    <>
                      <th>Documento</th>
                      <th>Correo</th>
                      <th>Teléfono</th>
                    </>
                  )}
                  {tab === 'categorias' && <th>Descripción</th>}
                  <th>Estado</th>
                  <th className="text-right">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {items.map((x) => (
                  <tr key={x.id}>
                    <td className="font-mono text-xs text-gray-400">#{x.id}</td>
                    <td>
                      <span className="font-semibold text-gray-900 dark:text-white">{x.nombre}</span>
                    </td>
                    {tab === 'productos' && (
                      <>
                        <td className="font-mono text-xs text-gray-400">
                          {'sku' in x ? String(x.sku || '-') : '-'}
                        </td>
                        <td className="font-semibold text-emerald-500">
                          {'precio_venta' in x ? importe(x.precio_venta) : '-'}
                        </td>
                        <td>
                          <span className="inline-flex px-2 py-0.5 rounded text-[11px] font-medium bg-white/5 border border-white/10">
                            {'tipo_item' in x ? String(x.tipo_item) : '-'}
                          </span>
                        </td>
                        <td>
                          {'controla_stock' in x && x.controla_stock ? (
                            renderStockPill(
                              'stock_actual' in x && x.stock_actual !== undefined ? x.stock_actual : 25
                            )
                          ) : (
                            <span className="text-xs text-gray-400">No aplica</span>
                          )}
                        </td>
                      </>
                    )}
                    {tab === 'clientes' && (
                      <>
                        <td className="text-xs text-gray-600 dark:text-gray-300">
                          {'numero_documento' in x && x.numero_documento
                            ? `${'tipo_documento' in x && x.tipo_documento ? x.tipo_documento + ': ' : ''}${x.numero_documento}`
                            : '-'}
                        </td>
                        <td className="text-xs text-gray-600 dark:text-gray-300">
                          {'email' in x ? texto(x.email) : '-'}
                        </td>
                        <td className="text-xs text-gray-600 dark:text-gray-300">
                          {'telefono' in x ? texto(x.telefono) : '-'}
                        </td>
                      </>
                    )}
                    {tab === 'categorias' && (
                      <td className="text-xs text-gray-500 dark:text-gray-400 max-w-xs truncate">
                        {'descripcion' in x ? texto(x.descripcion) : '-'}
                      </td>
                    )}
                    <td>
                      <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${badgeColor(x.activo)}`}>
                        {x.activo ? 'ACTIVO' : 'INACTIVO'}
                      </span>
                    </td>
                    <td className="text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          type="button"
                          onClick={() => abrirFormulario(x)}
                          disabled={saving}
                          title="Editar registro"
                          className="p-1.5 rounded-lg border border-gray-200 dark:border-white/10 hover:bg-cyan-500/10 hover:text-cyan-400 hover:border-cyan-500/30 text-gray-500 dark:text-gray-400 transition-all cursor-pointer"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        {x.activo && (
                          <button
                            type="button"
                            onClick={() => void desactivar(x)}
                            disabled={saving}
                            title="Desactivar registro"
                            className="p-1.5 rounded-lg border border-rose-500/20 text-rose-500 hover:bg-rose-500/10 transition-all cursor-pointer disabled:opacity-40"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
                {!loading && items.length === 0 && (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-sm text-gray-400">
                      <div className="flex flex-col items-center justify-center gap-2">
                        <Package className="w-8 h-8 text-gray-500" />
                        <span>No hay registros para los filtros seleccionados.</span>
                      </div>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Barra de paginación */}
          <div className="pagination-bar px-4 py-3 bg-white/40 dark:bg-white/[0.02]">
            <div className="text-xs text-gray-500 dark:text-gray-400">
              Página {page} de {Math.max(1, Math.ceil(total / 20))}
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                className="pagination-btn flex items-center gap-1"
                disabled={page === 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="w-3.5 h-3.5" /> Anterior
              </button>
              <button
                type="button"
                className="pagination-btn flex items-center gap-1"
                disabled={page * 20 >= total || loading}
                onClick={() => setPage((p) => p + 1)}
              >
                Siguiente <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      ) : tab === 'inventario' ? (
        /* TAB: INVENTARIO Y ALERTAS */
        <div className="space-y-6">
          <div className="alert-card alert-info">
            <Info className="w-5 h-5 flex-shrink-0" />
            <div className="text-xs">
              <strong>Análisis Orientativo de Inventario:</strong> Los valores se calculan a partir de existencias almacenadas y velocidad de demanda histórica observada en ventas confirmadas.
            </div>
          </div>

          {/* Tarjetas resumen de stock */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="glass p-5">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">
                Productos Analizados
              </span>
              <strong className="text-2xl font-bold text-gray-900 dark:text-white mt-1 block">
                {stock.length}
              </strong>
            </div>
            <div className="glass p-5 border-l-4 border-l-rose-500">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">
                Riesgo de Quiebre Alto
              </span>
              <strong className="text-2xl font-bold text-rose-500 mt-1 block">{stockAlto}</strong>
            </div>
            <div className="glass p-5">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">
                Sin Movimiento Histórico
              </span>
              <strong className="text-2xl font-bold text-amber-500 mt-1 block">
                {stock.filter((x) => x.riesgo === 'SIN_HISTORIAL').length}
              </strong>
            </div>
          </div>

          {/* Gráficos de inventario */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {barras('Distribución por Riesgo Estimado', resumenRiesgos(stock))}
            {barras('Existencias Disponibles por Producto', topStock(stock))}
            {barras('Demanda Estimada (14 días)', topDemanda(stock))}
          </div>

          {/* Tabla de detalle de inventario */}
          <div className="glass overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-white/10">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                Inventario Operativo y Parámetros Calculados
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Producto</th>
                    <th>Stock Físico</th>
                    <th className="min-w-[200px]">Cobertura y Autonomía (Runway)</th>
                    <th>Parámetros y Métricas</th>
                  </tr>
                </thead>
                <tbody>
                  {stock.slice((localPage - 1) * localLimit, localPage * localLimit).map((x) => (
                    <tr key={x.producto_id}>
                      <td className="font-semibold text-gray-900 dark:text-white max-w-xs">
                        {x.nombre}
                      </td>
                      <td>{renderStockPill(x.stock_actual)}</td>
                      <td>
                        <StockRunwayBadge
                          stockActual={x.stock_actual as number}
                          demandaEstimada={x.demanda_estimada as number}
                          diasCoberturaDirecto={(x.dias_inventario || x.dias_cobertura) as number}
                          riesgoSugerido={x.riesgo as string}
                        />
                      </td>
                      <td className="text-xs text-gray-600 dark:text-gray-300">
                        <div className="flex flex-wrap gap-x-4 gap-y-1">
                          {Object.entries(x)
                            .filter(([k]) => !['producto_id', 'nombre', 'stock_actual', 'riesgo', 'dias_inventario', 'dias_cobertura'].includes(k))
                            .map(([k, v]) => (
                              <div key={k}>
                                <strong className="text-gray-400">{k.replace(/_/g, ' ')}:</strong>{' '}
                                {typeof v === 'object' ? JSON.stringify(v) : texto(v)}
                              </div>
                            ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!loading && !stock.length && (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-sm text-gray-400">
                        Sin inventario disponible o sin permiso de consulta.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Paginación local */}
            <div className="pagination-bar px-4 py-3 bg-white/40 dark:bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <span>
                  Mostrando {Math.min(stock.length, (localPage - 1) * localLimit + 1)}–
                  {Math.min(stock.length, localPage * localLimit)} de {stock.length} registros
                </span>
                <label className="flex items-center gap-1 text-xs">
                  <span>Por pág:</span>
                  <select
                    value={localLimit}
                    onChange={(e) => {
                      setLocalLimit(Number(e.target.value));
                      setLocalPage(1);
                    }}
                    className="bg-transparent border border-white/10 rounded px-1.5 py-0.5 text-xs text-gray-300"
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
                  className="pagination-btn"
                  disabled={localPage === 1}
                  onClick={() => setLocalPage((p) => Math.max(1, p - 1))}
                >
                  Anterior
                </button>
                <span className="text-xs px-2">
                  {localPage} / {Math.max(1, Math.ceil(stock.length / localLimit))}
                </span>
                <button
                  type="button"
                  className="pagination-btn"
                  disabled={localPage * localLimit >= stock.length}
                  onClick={() => setLocalPage((p) => p + 1)}
                >
                  Siguiente
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : tab === 'segmentacion' ? (
        /* TAB: SEGMENTACIÓN RFM */
        <div className="space-y-6">
          <div className="alert-card alert-info">
            <Info className="w-5 h-5 flex-shrink-0" />
            <div className="text-xs">
              <strong>Clasificación RFM:</strong> Agrupa clientes activos por recencia de compra, frecuencia de pedidos y valor monetario acumulado para diseñar estrategias comerciales dirigidas.
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="glass p-5">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">
                Clientes Analizados
              </span>
              <strong className="text-2xl font-bold text-gray-900 dark:text-white mt-1 block">
                {segments.length}
              </strong>
            </div>
            <div className="glass p-5">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">
                Compras Totales Muestra
              </span>
              <strong className="text-2xl font-bold text-cyan-400 mt-1 block">{totalCompras}</strong>
            </div>
            <div className="glass p-5">
              <span className="text-xs font-medium text-gray-400 uppercase tracking-wider block">
                Valor Total Acumulado
              </span>
              <strong className="text-2xl font-bold text-emerald-400 mt-1 block">
                {importe(gastoRfm)}
              </strong>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {barras('Distribución de Clientes por Segmento RFM', conteos(segments.map((x) => texto(x.segmento))))}
            {barras(
              'Gasto Acumulado por Cliente (PEN)',
              segments.map((x) => ({ etiqueta: x.nombre, valor: Number(x.valor_monetario) || 0 })).sort((a, b) => b.valor - a.valor),
              'dinero'
            )}
          </div>

          <div className="glass overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-white/10">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
                Detalle de Clientes y Calificación RFM
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Cliente</th>
                    <th>Segmento Asignado</th>
                    <th>Detalles RFM</th>
                  </tr>
                </thead>
                <tbody>
                  {segments.slice((localPage - 1) * localLimit, localPage * localLimit).map((x) => (
                    <tr key={x.cliente_id}>
                      <td className="font-semibold text-gray-900 dark:text-white">{x.nombre}</td>
                      <td>
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                          {texto(x.segmento)}
                        </span>
                      </td>
                      <td className="text-xs text-gray-600 dark:text-gray-300">
                        <div className="flex flex-wrap gap-x-4 gap-y-1">
                          {Object.entries(x)
                            .filter(([k]) => !['cliente_id', 'nombre', 'segmento'].includes(k))
                            .map(([k, v]) => (
                              <div key={k}>
                                <strong className="text-gray-400">{k.replace(/_/g, ' ')}:</strong>{' '}
                                {typeof v === 'object' ? JSON.stringify(v) : texto(v)}
                              </div>
                            ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!loading && !segments.length && (
                    <tr>
                      <td colSpan={3} className="py-8 text-center text-sm text-gray-400">
                        No hay clientes para analizar en este periodo.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="pagination-bar px-4 py-3 bg-white/40 dark:bg-white/[0.02]">
              <div className="flex items-center gap-3">
                <span>
                  Mostrando {Math.min(segments.length, (localPage - 1) * localLimit + 1)}–
                  {Math.min(segments.length, localPage * localLimit)} de {segments.length} registros
                </span>
                <label className="flex items-center gap-1 text-xs">
                  <span>Por pág:</span>
                  <select
                    value={localLimit}
                    onChange={(e) => {
                      setLocalLimit(Number(e.target.value));
                      setLocalPage(1);
                    }}
                    className="bg-transparent border border-white/10 rounded px-1.5 py-0.5 text-xs text-gray-300"
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
                  className="pagination-btn"
                  disabled={localPage === 1}
                  onClick={() => setLocalPage((p) => Math.max(1, p - 1))}
                >
                  Anterior
                </button>
                <span className="text-xs px-2">
                  {localPage} / {Math.max(1, Math.ceil(segments.length / localLimit))}
                </span>
                <button
                  type="button"
                  className="pagination-btn"
                  disabled={localPage * localLimit >= segments.length}
                  onClick={() => setLocalPage((p) => p + 1)}
                >
                  Siguiente
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* TAB: PANEL DE ANÁLISIS */
        <div className="space-y-6">
          <div className="alert-card alert-info">
            <Info className="w-5 h-5 flex-shrink-0" />
            <div className="text-xs">
              <strong>Panel de Análisis Exploratorio:</strong> Procesa muestras de hasta 100 registros en tiempo real para evaluar concentración de catálogo y estructura de precios.
            </div>
          </div>

          {Boolean(analisisError.length) && (
            <div className="alert-card alert-warning">
              <AlertTriangle className="w-5 h-5 flex-shrink-0" />
              <div className="text-xs">
                Sin acceso a los siguientes módulos: <strong>{analisisError.join(', ')}</strong>. Los demás módulos se muestran normalmente.
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="glass p-4 text-center">
              <span className="text-xs text-gray-400 uppercase tracking-wider block">Productos</span>
              <strong className="text-xl font-bold text-gray-900 dark:text-white mt-1 block">
                {analisisProductos.length}
              </strong>
            </div>
            <div className="glass p-4 text-center">
              <span className="text-xs text-gray-400 uppercase tracking-wider block">Categorías</span>
              <strong className="text-xl font-bold text-cyan-400 mt-1 block">
                {analisisCategorias.length}
              </strong>
            </div>
            <div className="glass p-4 text-center">
              <span className="text-xs text-gray-400 uppercase tracking-wider block">En Inventario</span>
              <strong className="text-xl font-bold text-emerald-400 mt-1 block">
                {analisisStock.length}
              </strong>
            </div>
            <div className="glass p-4 text-center">
              <span className="text-xs text-gray-400 uppercase tracking-wider block">Clientes RFM</span>
              <strong className="text-xl font-bold text-purple-400 mt-1 block">
                {analisisClientes.length}
              </strong>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {barras('Productos por Categoría', catalogoCategorias)}
            {barras('Productos por Tipo de Ítem', productosPorTipo)}
            {barras('Suma de Precios de Catálogo por Categoría', preciosPorCategoria, 'dinero')}
            {barras('Riesgo Estimado de Stock', resumenRiesgos(analisisStock))}
            {barras('Segmentos de Clientes Activos', conteos(analisisClientes.map((x) => texto(x.segmento))))}
          </div>

          <div className="glass p-6 space-y-2 border-l-4 border-l-cyan-500">
            <h4 className="text-sm font-bold text-gray-900 dark:text-white">
              Criterios de Interpretación de Datos
            </h4>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Las categorías más numerosas no siempre representan la mayor rentabilidad. Para medir ingresos reales por categoría y ejecutar análisis ABC de Pareto se deben utilizar las transacciones de ventas consolidadas.
            </p>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              El riesgo de inventario se calcula sobre la base de rotación observada frente al stock actual. Todo artículo en estado de riesgo alto debe ser revisado en bodega físicamente antes de reprogramar compras.
            </p>
          </div>
        </div>
      )}

      {/* MODAL / PANEL DESLIZANTE DE FORMULARIO */}
      <AnimatePresence>
        {showForm && !readOnly && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-md">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="glass-strong w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto space-y-4 shadow-2xl"
            >
              <div className="flex items-center justify-between pb-3 border-b border-gray-200 dark:border-white/10">
                <div className="flex items-center gap-2 font-bold text-gray-900 dark:text-white text-base">
                  <Tag className="w-5 h-5 text-cyan-400" />
                  <span>
                    {edit ? 'Editar' : 'Registrar'}{' '}
                    {tab === 'clientes' ? 'Cliente' : tab === 'productos' ? 'Producto' : 'Categoría'}
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setShowForm(false)}
                  className="text-gray-400 hover:text-gray-200 p-1 rounded-lg"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={submit} className="space-y-4">
                <div>
                  <label className="input-label">Nombre *</label>
                  <input
                    required
                    minLength={2}
                    maxLength={200}
                    value={valor('nombre')}
                    onChange={(e) => cambiar('nombre', e.target.value)}
                    placeholder="Nombre o razón social"
                    className="input-field"
                  />
                </div>

                {tab === 'clientes' && (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="input-label">Tipo Documento</label>
                        <select
                          value={valor('tipo_documento')}
                          onChange={(e) => cambiar('tipo_documento', e.target.value)}
                          className="input-field"
                        >
                          <option value="">Sin documento</option>
                          {['DNI', 'RUC', 'CE', 'PASAPORTE'].map((x) => (
                            <option key={x} value={x}>{x}</option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="input-label">Número Documento</label>
                        <input
                          maxLength={20}
                          value={valor('numero_documento')}
                          onChange={(e) => cambiar('numero_documento', e.target.value)}
                          placeholder="Doc. de identidad"
                          className="input-field"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="input-label">Correo Electrónico</label>
                      <input
                        type="email"
                        maxLength={255}
                        value={valor('email')}
                        onChange={(e) => cambiar('email', e.target.value)}
                        placeholder="cliente@ejemplo.com"
                        className="input-field"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="input-label">Teléfono</label>
                        <input
                          type="tel"
                          maxLength={30}
                          value={valor('telefono')}
                          onChange={(e) => cambiar('telefono', e.target.value)}
                          placeholder="+51 999 888 777"
                          className="input-field"
                        />
                      </div>
                      <div>
                        <label className="input-label">Dirección</label>
                        <input
                          type="text"
                          maxLength={255}
                          value={valor('direccion')}
                          onChange={(e) => cambiar('direccion', e.target.value)}
                          placeholder="Dirección fiscal"
                          className="input-field"
                        />
                      </div>
                    </div>
                  </>
                )}

                {tab === 'productos' && (
                  <>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="input-label">Código SKU *</label>
                        <input
                          required
                          maxLength={80}
                          value={valor('sku')}
                          onChange={(e) => cambiar('sku', e.target.value)}
                          placeholder="PROD-001"
                          className="input-field font-mono text-xs"
                        />
                      </div>
                      <div>
                        <label className="input-label">Tipo de Ítem</label>
                        <select
                          value={valor('tipo_item') || 'PRODUCTO'}
                          onChange={(e) => cambiar('tipo_item', e.target.value)}
                          className="input-field"
                        >
                          {['PRODUCTO', 'SERVICIO', 'INSUMO', 'MISCELANEO'].map((x) => (
                            <option key={x} value={x}>{x}</option>
                          ))}
                        </select>
                      </div>
                    </div>

                    {/* Selector de categoría con búsqueda live */}
                    <div className="space-y-1.5">
                      <label className="input-label">Categoría del Producto</label>
                      {valor('categoria_id') ? (
                        <div className="flex items-center justify-between p-2.5 rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-xs text-cyan-300">
                          <span>
                            Categoría: <strong>{categoriaActual?.nombre || `ID #${valor('categoria_id')}`}</strong>
                          </span>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => {
                                cambiar('categoria_id', '');
                                setCategoriaBusqueda('');
                                setCategoriaAbierta(true);
                              }}
                              className="text-xs underline hover:text-white"
                            >
                              Cambiar
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                cambiar('categoria_id', '');
                                setCategoriaAbierta(false);
                              }}
                              className="text-xs hover:text-rose-400"
                            >
                              Quitar
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div className="relative">
                          <input
                            type="search"
                            autoComplete="off"
                            placeholder="Escribe para buscar categoría..."
                            value={categoriaBusqueda}
                            onFocus={() => setCategoriaAbierta(true)}
                            onChange={(e) => {
                              setCategoriaBusqueda(e.target.value);
                              cambiar('categoria_id', '');
                              setCategoriaAbierta(true);
                            }}
                            className="input-field text-xs"
                          />
                          {categoriaAbierta && (
                            <div className="absolute left-0 right-0 top-full mt-1 z-30 max-h-48 overflow-y-auto glass-strong border border-white/10 rounded-lg p-2 shadow-2xl space-y-1">
                              {categoriasCargando && (
                                <p className="text-xs text-gray-400 p-2">Buscando categorías...</p>
                              )}
                              {categoriaError && (
                                <p className="text-xs text-rose-400 p-2">{categoriaError}</p>
                              )}
                              {!categoriasCargando && !categoriaError && (
                                <>
                                  <button
                                    type="button"
                                    onClick={() => {
                                      cambiar('categoria_id', '');
                                      setCategoriaBusqueda('');
                                      setCategoriaAbierta(false);
                                    }}
                                    className="w-full text-left px-3 py-1.5 rounded text-xs text-gray-400 hover:bg-white/10"
                                  >
                                    Sin categoría (no asignar)
                                  </button>
                                  {categoriasDisponibles.map((c) => (
                                    <button
                                      type="button"
                                      key={c.id}
                                      onClick={() => {
                                        cambiar('categoria_id', String(c.id));
                                        setCategoriaBusqueda(c.nombre);
                                        setCategoriaAbierta(false);
                                      }}
                                      className="w-full text-left px-3 py-1.5 rounded text-xs text-gray-200 hover:bg-cyan-500/20 hover:text-cyan-300 flex justify-between items-center"
                                    >
                                      <span className="font-medium">{c.nombre}</span>
                                      {c.descripcion && (
                                        <span className="text-[10px] text-gray-400 truncate max-w-[150px]">
                                          {c.descripcion}
                                        </span>
                                      )}
                                    </button>
                                  ))}
                                  {!categoriasDisponibles.length && (
                                    <p className="text-xs text-gray-400 p-2">No se encontraron categorías activas.</p>
                                  )}
                                </>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="input-label">Precio Venta (PEN) *</label>
                        <input
                          required
                          type="number"
                          min={0}
                          step="0.01"
                          value={valor('precio_venta')}
                          onChange={(e) => cambiar('precio_venta', e.target.value)}
                          className="input-field"
                        />
                      </div>
                      <div>
                        <label className="input-label">Costo Referencial (PEN)</label>
                        <input
                          type="number"
                          min={0}
                          step="0.01"
                          value={valor('costo_referencia')}
                          onChange={(e) => cambiar('costo_referencia', e.target.value)}
                          className="input-field"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="input-label">Descripción</label>
                      <input
                        maxLength={500}
                        value={valor('descripcion')}
                        onChange={(e) => cambiar('descripcion', e.target.value)}
                        placeholder="Detalles técnicos o características"
                        className="input-field"
                      />
                    </div>

                    <label className="flex items-center gap-2 cursor-pointer pt-1 text-sm text-gray-700 dark:text-gray-300">
                      <input
                        type="checkbox"
                        checked={Boolean(form.controla_stock ?? true)}
                        onChange={(e) => cambiar('controla_stock', e.target.checked)}
                        className="rounded border-gray-300 text-cyan-500 focus:ring-cyan-400"
                      />
                      <span>Controlar existencias en almacén (stock físico)</span>
                    </label>
                  </>
                )}

                {tab === 'categorias' && (
                  <div>
                    <label className="input-label">Descripción</label>
                    <textarea
                      rows={3}
                      maxLength={255}
                      value={valor('descripcion')}
                      onChange={(e) => cambiar('descripcion', e.target.value)}
                      placeholder="Descripción de la categoría de catálogo"
                      className="input-field resize-none"
                    />
                  </div>
                )}

                <div className="flex justify-end gap-2 pt-3 border-t border-gray-200 dark:border-white/10">
                  <button
                    type="button"
                    onClick={() => setShowForm(false)}
                    className="px-4 py-2 rounded-lg text-xs font-medium border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/5"
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 disabled:opacity-50"
                  >
                    {saving ? 'Guardando...' : 'Guardar Registro'}
                  </button>
                </div>
              </form>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
export default ManagementView;
