import React, { useEffect, useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Users,
  FolderTree,
  Package,
  ShoppingCart,
  Receipt,
  CreditCard,
  Settings,
  RefreshCw,
  Plus,
  Edit2,
  Trash2,
  Eye,
  Check,
  X,
  CheckCircle2,
  AlertTriangle,
  Code,
  Terminal,
  Send,
  Truck
} from 'lucide-react';
import { api } from '../services/api';
import type { CatalogItem, PedidoResumen, VentaResumen, ResumenPagos } from '../types/commercial';

type Seccion = 'clientes' | 'categorias' | 'productos' | 'pedidos' | 'ventas' | 'pagos' | 'configuracion';

const mensajeError = (e: unknown) => (e instanceof Error ? e.message : 'Error inesperado');
const numero = (v: string) => Number(v);
const optional = (key: string, value: string) => (value.trim() ? { [key]: value.trim() } : {});

const badgeColor = (estado: string | boolean) => {
  const norm = String(estado).toUpperCase();
  if (estado === true || norm === 'ACTIVO' || norm === 'COMPLETADO' || norm === 'PAGADO' || norm === 'ENTREGADO') {
    return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20';
  }
  if (norm === 'CONFIRMADO' || norm === 'CONFIRMADA') {
    return 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20';
  }
  if (estado === false || norm === 'INACTIVO' || norm === 'CANCELADO' || norm === 'CANCELADA' || norm === 'ANULADO') {
    return 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20';
  }
  if (norm === 'BORRADOR') {
    return 'bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20';
  }
  return 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border border-gray-500/20';
};

export const CommercialTestingView: React.FC = () => {
  const [seccion, setSeccion] = useState<Seccion>('clientes');
  const [error, setError] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [busy, setBusy] = useState(false);

  // Catálogos cargados
  const [clientes, setClientes] = useState<CatalogItem[]>([]);
  const [categorias, setCategorias] = useState<CatalogItem[]>([]);
  const [productos, setProductos] = useState<CatalogItem[]>([]);
  const [pedidos, setPedidos] = useState<PedidoResumen[]>([]);
  const [ventas, setVentas] = useState<VentaResumen[]>([]);

  // Campos de formulario compartidos
  const [nombre, setNombre] = useState('');
  const [tipoDoc, setTipoDoc] = useState('');
  const [documento, setDocumento] = useState('');
  const [email, setEmail] = useState('');
  const [telefono, setTelefono] = useState('');
  const [direccion, setDireccion] = useState('');
  const [descripcion, setDescripcion] = useState('');
  const [observaciones, setObservaciones] = useState('');
  const [sku, setSku] = useState('');
  const [tipoItem, setTipoItem] = useState('PRODUCTO');
  const [precio, setPrecio] = useState('0.00');
  const [costo, setCosto] = useState('0.00');
  const [controlaStock, setControlaStock] = useState(false);
  const [categoriaId, setCategoriaId] = useState('');

  // Pedidos y ventas
  const [clienteId, setClienteId] = useState('');
  const [productoId, setProductoId] = useState('');
  const [cantidad, setCantidad] = useState('1');
  const [descuento, setDescuento] = useState('0.00');
  const [pedidoId, setPedidoId] = useState('');
  const [ventaId, setVentaId] = useState('');

  // Pagos y entregas
  const [pagoId, setPagoId] = useState('');
  const [monto, setMonto] = useState('1.00');
  const [medio, setMedio] = useState('EFECTIVO');
  const [resumen, setResumen] = useState<ResumenPagos | null>(null);

  // Configuración IGV
  const [igv, setIgv] = useState('18.0000');
  const [igvActual, setIgvActual] = useState<string | null>(null);

  // Estado de edición y visualizador de respuestas
  const [editando, setEditando] = useState<number | null>(null);
  const [detalle, setDetalle] = useState<unknown>(null);

  const ejecutar = async (accion: () => Promise<unknown>, success = 'Operación completada') => {
    setError('');
    setMensaje('');
    setBusy(true);
    try {
      const r = await accion();
      setMensaje(success);
      setDetalle(r);
      await cargar();
    } catch (e) {
      setError(mensajeError(e));
    } finally {
      setBusy(false);
    }
  };

  const cargar = async () => {
    setError('');
    try {
      const [c, cat, pro, p, v] = await Promise.allSettled([
        api.getClientes(1, 100),
        api.listarCategorias(),
        api.getProductos(1, 100),
        api.listarPedidos(),
        api.getVentas(1, 100),
      ]);
      const notas: string[] = [];
      if (c.status === 'fulfilled') setClientes(c.value.clientes as unknown as CatalogItem[]);
      else notas.push('clientes: ' + mensajeError(c.reason));

      if (cat.status === 'fulfilled') setCategorias(cat.value.categorias);
      else notas.push('categorías: ' + mensajeError(cat.reason));

      if (pro.status === 'fulfilled') setProductos(pro.value.productos as unknown as CatalogItem[]);
      else notas.push('productos: ' + mensajeError(pro.reason));

      if (p.status === 'fulfilled') setPedidos(p.value.pedidos);
      else notas.push('pedidos: ' + mensajeError(p.reason));

      if (v.status === 'fulfilled') setVentas(v.value.ventas as unknown as VentaResumen[]);
      else notas.push('ventas: ' + mensajeError(v.reason));

      if (notas.length) setError(notas.join(' | '));
    } catch (e) {
      setError(mensajeError(e));
    }
  };

  useEffect(() => {
    void cargar();
  }, []);

  const confirmar = (etiqueta: string, accion: () => Promise<unknown>) => {
    if (window.confirm(`${etiqueta}. Esta operación modifica Supabase Testing. ¿Continuar?`)) {
      void ejecutar(accion, etiqueta + ' completado');
    }
  };

  const resetFormulario = () => {
    setEditando(null);
    setNombre('');
    setTipoDoc('');
    setDocumento('');
    setEmail('');
    setTelefono('');
    setDireccion('');
    setDescripcion('');
    setObservaciones('');
    setSku('');
    setTipoItem('PRODUCTO');
    setPrecio('0.00');
    setCosto('0.00');
    setControlaStock(false);
    setCategoriaId('');
  };

  const seccionesConfig: { id: Seccion; label: string; icon: React.ReactNode }[] = [
    { id: 'clientes', label: 'Clientes', icon: <Users className="w-4 h-4" /> },
    { id: 'categorias', label: 'Categorías', icon: <FolderTree className="w-4 h-4" /> },
    { id: 'productos', label: 'Productos', icon: <Package className="w-4 h-4" /> },
    { id: 'pedidos', label: 'Pedidos', icon: <ShoppingCart className="w-4 h-4" /> },
    { id: 'ventas', label: 'Ventas', icon: <Receipt className="w-4 h-4" /> },
    { id: 'pagos', label: 'Pagos & Entregas', icon: <CreditCard className="w-4 h-4" /> },
    { id: 'configuracion', label: 'Configuración IGV', icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-6"
    >
      {/* Título de la sección */}
      <div className="glass p-5 md:p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border border-[#D97843]/20 dark:border-white/10 shadow-sm">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold bg-[#D97843]/15 text-[#B35D2F] dark:text-[#FFA675] border border-[#D97843]/30 mb-2">
            <Terminal className="w-3.5 h-3.5" />
            <span>Módulo de Pruebas de Integración</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-black text-slate-950 dark:text-white tracking-tight drop-shadow-sm">
            Consola Comercial de Pruebas
          </h2>
          <p className="text-sm text-slate-700 dark:text-slate-200 mt-1 font-medium">
            Valida contratos comerciales, pedidos, ventas y transacciones directamente con FastAPI y Supabase.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void cargar()}
          disabled={busy}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium border border-gray-200 dark:border-white/10 hover:bg-gray-100 dark:hover:bg-white/5 text-gray-700 dark:text-gray-200 transition-colors disabled:opacity-50 cursor-pointer"
        >
          <RefreshCw className={`w-4 h-4 ${busy ? 'animate-spin' : ''}`} />
          <span>Actualizar Datos</span>
        </button>
      </div>

      {/* Tabs superiores */}
      <div className="tab-bar overflow-x-auto">
        {seccionesConfig.map((s) => (
          <button
            key={s.id}
            type="button"
            className={`tab-item flex items-center gap-2 whitespace-nowrap ${seccion === s.id ? 'active' : ''}`}
            onClick={() => {
              setSeccion(s.id);
              resetFormulario();
              setDetalle(null);
              setError('');
            }}
          >
            {s.icon}
            <span>{s.label}</span>
          </button>
        ))}
      </div>

      {/* Alertas */}
      <AnimatePresence>
        {mensaje && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="alert-card alert-success"
          >
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            <div className="flex-1 font-medium">{mensaje}</div>
            <button onClick={() => setMensaje('')} className="text-xs hover:opacity-75">✕</button>
          </motion.div>
        )}
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
      </AnimatePresence>

      {/* SECCIÓN: CLIENTES */}
      {seccion === 'clientes' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Formulario Cliente */}
          <div className="glass p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-cyan-500" />
              {editando !== null ? `Editar Cliente #${editando}` : 'Registrar Cliente'}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Datos comerciales y de facturación del cliente.
            </p>

            <div className="space-y-3">
              <div>
                <label className="input-label">Nombre o Razón Social *</label>
                <input
                  type="text"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder="Ej: Distribuidora Los Andes SAC"
                  className="input-field"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="input-label">Tipo Doc.</label>
                  <select
                    value={tipoDoc}
                    onChange={(e) => setTipoDoc(e.target.value)}
                    className="input-field"
                  >
                    <option value="">Seleccionar...</option>
                    <option value="DNI">DNI</option>
                    <option value="RUC">RUC</option>
                    <option value="CE">CE</option>
                    <option value="PASAPORTE">Pasaporte</option>
                  </select>
                </div>
                <div>
                  <label className="input-label">Número Doc.</label>
                  <input
                    type="text"
                    value={documento}
                    onChange={(e) => setDocumento(e.target.value)}
                    placeholder="20123456789"
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="input-label">Correo Electrónico</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="contacto@empresa.pe"
                  className="input-field"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="input-label">Teléfono</label>
                  <input
                    type="tel"
                    value={telefono}
                    onChange={(e) => setTelefono(e.target.value)}
                    placeholder="+51 987654321"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="input-label">Dirección</label>
                  <input
                    type="text"
                    value={direccion}
                    onChange={(e) => setDireccion(e.target.value)}
                    placeholder="Av. Principal 123"
                    className="input-field"
                  />
                </div>
              </div>
            </div>

            <div className="pt-2 flex flex-col gap-2">
              {editando === null ? (
                <button
                  type="button"
                  disabled={
                    busy ||
                    nombre.trim().length < 2 ||
                    Boolean(tipoDoc) !== Boolean(documento.trim()) ||
                    Boolean(email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim()))
                  }
                  onClick={() =>
                    confirmar('Crear cliente', () =>
                      api.crearCliente({
                        nombre: nombre.trim(),
                        ...(tipoDoc && documento.trim()
                          ? { tipo_documento: tipoDoc, numero_documento: documento.trim() }
                          : {}),
                        ...optional('email', email),
                        ...optional('telefono', telefono),
                        ...optional('direccion', direccion),
                      })
                    )
                  }
                  className="w-full py-2.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 disabled:opacity-40 transition-all cursor-pointer"
                >
                  Guardar Cliente
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={
                      busy ||
                      nombre.trim().length < 2 ||
                      Boolean(tipoDoc) !== Boolean(documento.trim())
                    }
                    onClick={() =>
                      confirmar('Actualizar cliente', async () => {
                        const r = await api.actualizarCliente(editando, {
                          nombre: nombre.trim(),
                          ...(tipoDoc && documento.trim()
                            ? { tipo_documento: tipoDoc, numero_documento: documento.trim() }
                            : {}),
                          ...optional('email', email),
                          ...optional('telefono', telefono),
                          ...optional('direccion', direccion),
                        });
                        resetFormulario();
                        return r;
                      })
                    }
                    className="flex-1 py-2 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 disabled:opacity-40"
                  >
                    Guardar Cambios
                  </button>
                  <button
                    type="button"
                    onClick={resetFormulario}
                    className="px-3 py-2 rounded-lg text-xs font-medium border border-white/10 hover:bg-white/5"
                  >
                    Cancelar
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Tabla Clientes */}
          <div className="lg:col-span-2 glass overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-white/10 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                Clientes Registrados ({clientes.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nombre / Razón Social</th>
                    <th>Estado</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {clientes.map((c) => (
                    <tr key={c.id}>
                      <td className="font-mono text-xs text-gray-400">#{c.id}</td>
                      <td className="font-medium text-gray-900 dark:text-white">{c.nombre}</td>
                      <td>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${badgeColor(c.activo)}`}>
                          {c.activo ? 'ACTIVO' : 'INACTIVO'}
                        </span>
                      </td>
                      <td className="text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => {
                              setEditando(c.id);
                              setNombre(c.nombre);
                              setTipoDoc(String(c.tipo_documento || ''));
                              setDocumento(String(c.numero_documento || ''));
                              setEmail(String(c.email || ''));
                              setTelefono(String(c.telefono || ''));
                              setDireccion(String(c.direccion || ''));
                            }}
                            title="Editar cliente"
                            className="p-1.5 rounded-lg border border-gray-200 dark:border-white/10 hover:bg-cyan-500/10 hover:text-cyan-400 hover:border-cyan-500/30 transition-all cursor-pointer"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          {c.activo && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => confirmar('Desactivar cliente', () => api.desactivarCliente(c.id))}
                              title="Desactivar cliente"
                              className="p-1.5 rounded-lg border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-all cursor-pointer disabled:opacity-40"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {clientes.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-sm text-gray-400">
                        No hay clientes registrados.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECCIÓN: CATEGORÍAS */}
      {seccion === 'categorias' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="glass p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <FolderTree className="w-5 h-5 text-cyan-500" />
              {editando !== null ? `Editar Categoría #${editando}` : 'Nueva Categoría'}
            </h3>

            <div className="space-y-3">
              <div>
                <label className="input-label">Nombre de Categoría *</label>
                <input
                  type="text"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder="Ej: Lácteos, Ferretería, Servicios"
                  className="input-field"
                />
              </div>

              <div>
                <label className="input-label">Descripción</label>
                <textarea
                  rows={3}
                  value={descripcion}
                  onChange={(e) => setDescripcion(e.target.value)}
                  placeholder="Detalles de la categoría comercial..."
                  className="input-field resize-none"
                />
              </div>
            </div>

            <div className="pt-2">
              {editando === null ? (
                <button
                  type="button"
                  disabled={busy || nombre.trim().length < 2}
                  onClick={() =>
                    confirmar('Crear categoría', () =>
                      api.crearCategoria({ nombre: nombre.trim(), ...optional('descripcion', descripcion) })
                    )
                  }
                  className="w-full py-2.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 disabled:opacity-40 transition-all cursor-pointer"
                >
                  Guardar Categoría
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busy || nombre.trim().length < 2}
                    onClick={() =>
                      confirmar('Actualizar categoría', async () => {
                        const r = await api.actualizarCategoria(editando, {
                          nombre: nombre.trim(),
                          ...optional('descripcion', descripcion),
                        });
                        resetFormulario();
                        return r;
                      })
                    }
                    className="flex-1 py-2 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 disabled:opacity-40"
                  >
                    Guardar Cambios
                  </button>
                  <button
                    type="button"
                    onClick={resetFormulario}
                    className="px-3 py-2 rounded-lg text-xs font-medium border border-white/10 hover:bg-white/5"
                  >
                    Cancelar
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 glass overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-white/10">
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                Categorías Disponibles ({categorias.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Estado</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {categorias.map((cat) => (
                    <tr key={cat.id}>
                      <td className="font-mono text-xs text-gray-400">#{cat.id}</td>
                      <td className="font-medium text-gray-900 dark:text-white">{cat.nombre}</td>
                      <td>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${badgeColor(cat.activo)}`}>
                          {cat.activo ? 'ACTIVO' : 'INACTIVO'}
                        </span>
                      </td>
                      <td className="text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => {
                              setEditando(cat.id);
                              setNombre(cat.nombre);
                              setDescripcion(String(cat.descripcion || ''));
                            }}
                            title="Editar categoría"
                            className="p-1.5 rounded-lg border border-gray-200 dark:border-white/10 hover:bg-cyan-500/10 hover:text-cyan-400 transition-all cursor-pointer"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          {cat.activo && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => confirmar('Desactivar categoría', () => api.desactivarCategoria(cat.id))}
                              title="Desactivar categoría"
                              className="p-1.5 rounded-lg border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-all cursor-pointer disabled:opacity-40"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {categorias.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-8 text-center text-sm text-gray-400">
                        No hay categorías registradas.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECCIÓN: PRODUCTOS */}
      {seccion === 'productos' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="glass p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Package className="w-5 h-5 text-cyan-500" />
              {editando !== null ? `Editar Producto #${editando}` : 'Registrar Producto'}
            </h3>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="input-label">SKU *</label>
                  <input
                    type="text"
                    value={sku}
                    onChange={(e) => setSku(e.target.value)}
                    placeholder="PROD-001"
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="input-label">Tipo *</label>
                  <select
                    value={tipoItem}
                    onChange={(e) => setTipoItem(e.target.value)}
                    className="input-field"
                  >
                    <option value="PRODUCTO">Producto</option>
                    <option value="SERVICIO">Servicio</option>
                    <option value="INSUMO">Insumo</option>
                    <option value="MISCELANEO">Misceláneo</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="input-label">Nombre del Producto *</label>
                <input
                  type="text"
                  value={nombre}
                  onChange={(e) => setNombre(e.target.value)}
                  placeholder="Laptop HP ProBook"
                  className="input-field"
                />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="input-label">Precio Venta (PEN) *</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={precio}
                    onChange={(e) => setPrecio(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="input-label">Costo Referencial</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={costo}
                    onChange={(e) => setCosto(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="input-label">Categoría</label>
                <select
                  value={categoriaId}
                  onChange={(e) => setCategoriaId(e.target.value)}
                  className="input-field"
                >
                  <option value="">Sin categoría asignada</option>
                  {categorias.filter((c) => c.activo).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="input-label">Descripción</label>
                <input
                  type="text"
                  value={descripcion}
                  onChange={(e) => setDescripcion(e.target.value)}
                  placeholder="Especificaciones o notas..."
                  className="input-field"
                />
              </div>

              <label className="flex items-center gap-2 cursor-pointer pt-1 text-sm text-gray-700 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={controlaStock}
                  onChange={(e) => setControlaStock(e.target.checked)}
                  className="rounded border-gray-300 text-cyan-500 focus:ring-cyan-400"
                />
                <span>Controlar existencias en almacén (stock físico)</span>
              </label>
            </div>

            <div className="pt-2">
              {editando === null ? (
                <button
                  type="button"
                  disabled={
                    busy ||
                    !sku.trim() ||
                    nombre.trim().length < 2 ||
                    !precio.trim() ||
                    numero(precio) < 0 ||
                    numero(costo) < 0
                  }
                  onClick={() =>
                    confirmar('Crear producto', () =>
                      api.crearProducto({
                        sku: sku.trim(),
                        nombre: nombre.trim(),
                        ...optional('descripcion', descripcion),
                        tipo_item: tipoItem,
                        precio_venta: precio,
                        costo_referencia: costo,
                        controla_stock: controlaStock,
                        ...(categoriaId ? { categoria_id: numero(categoriaId) } : {}),
                      })
                    )
                  }
                  className="w-full py-2.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 disabled:opacity-40 transition-all cursor-pointer"
                >
                  Guardar Producto
                </button>
              ) : (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={
                      busy ||
                      !sku.trim() ||
                      nombre.trim().length < 2 ||
                      numero(precio) < 0 ||
                      numero(costo) < 0
                    }
                    onClick={() =>
                      confirmar('Actualizar producto', async () => {
                        const r = await api.actualizarProducto(editando, {
                          sku: sku.trim(),
                          nombre: nombre.trim(),
                          ...optional('descripcion', descripcion),
                          tipo_item: tipoItem,
                          precio_venta: precio,
                          costo_referencia: costo,
                          controla_stock: controlaStock,
                          ...(categoriaId ? { categoria_id: numero(categoriaId) } : {}),
                        });
                        resetFormulario();
                        return r;
                      })
                    }
                    className="flex-1 py-2 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 disabled:opacity-40"
                  >
                    Guardar Cambios
                  </button>
                  <button
                    type="button"
                    onClick={resetFormulario}
                    className="px-3 py-2 rounded-lg text-xs font-medium border border-white/10 hover:bg-white/5"
                  >
                    Cancelar
                  </button>
                </div>
              )}
            </div>
          </div>

          <div className="lg:col-span-2 glass overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-white/10">
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                Catálogo de Productos ({productos.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>SKU / Nombre</th>
                    <th>Precio</th>
                    <th>Estado</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {productos.map((prod) => (
                    <tr key={prod.id}>
                      <td className="font-mono text-xs text-gray-400">#{prod.id}</td>
                      <td>
                        <div className="font-semibold text-gray-900 dark:text-white">
                          {prod.nombre}
                        </div>
                        <div className="text-xs font-mono text-gray-400">{String(prod.sku || '')}</div>
                      </td>
                      <td className="font-medium text-emerald-500">
                        PEN {String(prod.precio_venta || '0.00')}
                      </td>
                      <td>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${badgeColor(prod.activo)}`}>
                          {prod.activo ? 'ACTIVO' : 'INACTIVO'}
                        </span>
                      </td>
                      <td className="text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            disabled={busy}
                            onClick={() => {
                              setEditando(prod.id);
                              setSku(String(prod.sku || ''));
                              setNombre(prod.nombre);
                              setDescripcion(String(prod.descripcion || ''));
                              setTipoItem(String(prod.tipo_item || 'PRODUCTO'));
                              setPrecio(String(prod.precio_venta || '0.00'));
                              setCosto(String(prod.costo_referencia || '0.00'));
                              setCategoriaId(prod.categoria_id ? String(prod.categoria_id) : '');
                              setControlaStock(Boolean(prod.controla_stock));
                            }}
                            title="Editar producto"
                            className="p-1.5 rounded-lg border border-gray-200 dark:border-white/10 hover:bg-cyan-500/10 hover:text-cyan-400 transition-all cursor-pointer"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>
                          {prod.activo && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => confirmar('Desactivar producto', () => api.desactivarProducto(prod.id))}
                              title="Desactivar producto"
                              className="p-1.5 rounded-lg border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-all cursor-pointer disabled:opacity-40"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {productos.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-sm text-gray-400">
                        No hay productos registrados en el catálogo.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECCIÓN: PEDIDOS */}
      {seccion === 'pedidos' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="glass p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <ShoppingCart className="w-5 h-5 text-cyan-500" />
              Nuevo Pedido de Prueba
            </h3>

            <div className="space-y-3">
              <div>
                <label className="input-label">Cliente *</label>
                <select
                  value={clienteId}
                  onChange={(e) => setClienteId(e.target.value)}
                  className="input-field"
                >
                  <option value="">Selecciona cliente...</option>
                  {clientes.filter((c) => c.activo).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre} (#{c.id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="input-label">Producto *</label>
                <select
                  value={productoId}
                  onChange={(e) => setProductoId(e.target.value)}
                  className="input-field"
                >
                  <option value="">Selecciona producto...</option>
                  {productos.filter((p) => p.activo).map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.nombre} (#{p.id})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="input-label">Cantidad</label>
                  <input
                    type="number"
                    min="1"
                    value={cantidad}
                    onChange={(e) => setCantidad(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="input-label">Descuento (S/)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    value={descuento}
                    onChange={(e) => setDescuento(e.target.value)}
                    className="input-field"
                  />
                </div>
              </div>

              <div>
                <label className="input-label">Observaciones</label>
                <input
                  type="text"
                  value={observaciones}
                  onChange={(e) => setObservaciones(e.target.value)}
                  placeholder="Nota comercial opcional..."
                  className="input-field"
                />
              </div>
            </div>

            <button
              type="button"
              disabled={
                busy ||
                numero(clienteId) <= 0 ||
                numero(productoId) <= 0 ||
                numero(cantidad) <= 0 ||
                numero(descuento) < 0
              }
              onClick={() =>
                confirmar('Crear pedido', () =>
                  api.crearPedido({
                    cliente_id: numero(clienteId),
                    detalles: [{ producto_id: numero(productoId), cantidad, descuento }],
                    ...optional('observaciones', observaciones),
                  })
                )
              }
              className="w-full py-2.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 disabled:opacity-40 transition-all cursor-pointer"
            >
              Crear Pedido de Una Línea
            </button>
          </div>

          <div className="lg:col-span-2 glass overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-white/10">
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                Listado de Pedidos ({pedidos.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Código</th>
                    <th>Estado</th>
                    <th>Total</th>
                    <th className="text-right">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {pedidos.map((p) => (
                    <tr key={p.id}>
                      <td className="font-mono text-xs text-gray-400">#{p.id}</td>
                      <td className="font-semibold text-gray-900 dark:text-white">{p.codigo}</td>
                      <td>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${badgeColor(p.estado)}`}>
                          {p.estado}
                        </span>
                      </td>
                      <td className="font-medium text-emerald-500">PEN {p.total}</td>
                      <td className="text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            type="button"
                            onClick={() => void ejecutar(() => api.obtenerPedido(p.id), 'Detalle cargado')}
                            title="Ver respuesta JSON completa"
                            className="p-1.5 rounded-lg border border-gray-200 dark:border-white/10 hover:bg-cyan-500/10 hover:text-cyan-400 transition-all cursor-pointer"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          {p.estado === 'BORRADOR' && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => confirmar('Confirmar pedido', () => api.confirmarPedido(p.id))}
                              title="Confirmar pedido"
                              className="p-1.5 rounded-lg border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20 transition-all cursor-pointer disabled:opacity-40"
                            >
                              <Check className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {!['CANCELADO', 'COMPLETADO'].includes(p.estado) && (
                            <button
                              type="button"
                              disabled={busy}
                              onClick={() => confirmar('Cancelar pedido', () => api.cancelarPedido(p.id))}
                              title="Cancelar pedido"
                              className="p-1.5 rounded-lg border border-rose-500/20 text-rose-400 hover:bg-rose-500/20 transition-all cursor-pointer disabled:opacity-40"
                            >
                              <X className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {pedidos.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-8 text-center text-sm text-gray-400">
                        No hay pedidos registrados.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECCIÓN: VENTAS */}
      {seccion === 'ventas' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="glass p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Receipt className="w-5 h-5 text-cyan-500" />
              Generar Venta
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Convierte un pedido en estado CONFIRMADO a comprobante comercial de venta.
            </p>

            <div>
              <label className="input-label">Pedido Confirmado *</label>
              <select
                value={pedidoId}
                onChange={(e) => setPedidoId(e.target.value)}
                className="input-field"
              >
                <option value="">Selecciona un pedido...</option>
                {pedidos.filter((p) => p.estado === 'CONFIRMADO').map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.codigo} (#{p.id}) · PEN {p.total}
                  </option>
                ))}
              </select>
            </div>

            <button
              type="button"
              disabled={busy || numero(pedidoId) <= 0}
              onClick={() =>
                confirmar('Crear venta desde pedido', () =>
                  api.crearVentaDesdePedido(numero(pedidoId))
                )
              }
              className="w-full py-2.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 disabled:opacity-40 transition-all cursor-pointer"
            >
              Crear Venta desde Pedido
            </button>
          </div>

          <div className="lg:col-span-2 glass overflow-hidden">
            <div className="p-4 border-b border-gray-200 dark:border-white/10">
              <h3 className="font-semibold text-gray-900 dark:text-white text-sm">
                Ventas Registradas ({ventas.length})
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Código</th>
                    <th>Estado Venta</th>
                    <th>Pago</th>
                    <th>Total</th>
                    <th className="text-right">Acción</th>
                  </tr>
                </thead>
                <tbody>
                  {ventas.map((v) => (
                    <tr key={v.id}>
                      <td className="font-mono text-xs text-gray-400">#{v.id}</td>
                      <td className="font-semibold text-gray-900 dark:text-white">{v.codigo}</td>
                      <td>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${badgeColor(v.estado)}`}>
                          {v.estado}
                        </span>
                      </td>
                      <td>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${badgeColor(v.estado_pago)}`}>
                          {v.estado_pago}
                        </span>
                      </td>
                      <td className="font-medium text-emerald-500">PEN {v.total}</td>
                      <td className="text-right">
                        <button
                          type="button"
                          onClick={() => void ejecutar(() => api.obtenerVenta(v.id), 'Detalle de venta cargado')}
                          className="px-2.5 py-1 text-xs rounded border border-gray-200 dark:border-white/10 hover:bg-cyan-500/10 hover:text-cyan-400 transition-colors"
                        >
                          Detalle JSON
                        </button>
                      </td>
                    </tr>
                  ))}
                  {ventas.length === 0 && (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-sm text-gray-400">
                        No hay ventas registradas.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* SECCIÓN: PAGOS Y ENTREGAS */}
      {seccion === 'pagos' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="glass p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-cyan-500" />
              Gestión de Cobranzas y Pagos
            </h3>

            <div>
              <label className="input-label">Venta *</label>
              <select
                value={ventaId}
                onChange={(e) => setVentaId(e.target.value)}
                className="input-field"
              >
                <option value="">Selecciona una venta...</option>
                {ventas.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.codigo} · {v.estado_pago} · PEN {v.total}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                disabled={busy || numero(ventaId) <= 0}
                onClick={() =>
                  void ejecutar(async () => {
                    const r = await api.resumenPagos(numero(ventaId));
                    setResumen(r);
                    return r;
                  }, 'Resumen de pagos cargado')
                }
                className="px-4 py-2 rounded-lg text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 hover:bg-cyan-500/20 disabled:opacity-40"
              >
                Consultar Resumen de Pagos
              </button>
            </div>

            {resumen && (
              <div className="p-3 rounded-lg border border-white/10 bg-white/5 space-y-1 text-xs">
                <div><strong>Total Venta:</strong> PEN {resumen.total_venta}</div>
                <div><strong>Total Pagado:</strong> PEN {resumen.total_pagado}</div>
                <div><strong>Saldo Pendiente:</strong> PEN {resumen.saldo_pendiente}</div>
                <div><strong>Estado de Pago:</strong> <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${badgeColor(resumen.estado_pago)}`}>{resumen.estado_pago}</span></div>
              </div>
            )}

            <div className="pt-2 border-t border-gray-200 dark:border-white/10 space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Registrar Nuevo Pago
              </h4>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="input-label">Monto (PEN)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={monto}
                    onChange={(e) => setMonto(e.target.value)}
                    className="input-field"
                  />
                </div>
                <div>
                  <label className="input-label">Medio de Pago</label>
                  <select
                    value={medio}
                    onChange={(e) => setMedio(e.target.value)}
                    className="input-field"
                  >
                    {['EFECTIVO', 'TARJETA', 'TRANSFERENCIA', 'YAPE', 'PLIN', 'OTRO'].map((x) => (
                      <option key={x} value={x}>{x}</option>
                    ))}
                  </select>
                </div>
              </div>

              <button
                type="button"
                disabled={busy || numero(ventaId) <= 0 || numero(monto) <= 0}
                onClick={() =>
                  confirmar('Registrar pago', () =>
                    api.registrarPago(numero(ventaId), { monto, medio_pago: medio }, crypto.randomUUID())
                  )
                }
                className="w-full py-2 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 disabled:opacity-40"
              >
                Registrar Pago
              </button>
            </div>

            <div className="pt-2 border-t border-gray-200 dark:border-white/10 space-y-2">
              <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                Anulación de Pago
              </h4>
              <div className="flex gap-2">
                <input
                  type="number"
                  placeholder="ID del pago a anular"
                  value={pagoId}
                  onChange={(e) => setPagoId(e.target.value)}
                  className="input-field flex-1 text-xs"
                />
                <button
                  type="button"
                  disabled={busy || numero(pagoId) <= 0}
                  onClick={() => {
                    const m = window.prompt('Motivo de anulación (mínimo 3 caracteres):');
                    if (m && m.trim().length >= 3) {
                      confirmar('Anular pago', () => api.anularPago(numero(pagoId), m.trim()));
                    }
                  }}
                  className="px-3 py-2 rounded-lg text-xs font-medium border border-rose-500/30 text-rose-400 hover:bg-rose-500/10 disabled:opacity-40"
                >
                  Anular Pago
                </button>
              </div>
            </div>
          </div>

          {/* Entregas y Almacén */}
          <div className="glass p-6 space-y-4">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
              <Truck className="w-5 h-5 text-cyan-500" />
              Operaciones de Entrega
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Verifica o confirma la salida física de mercancía para la venta seleccionada.
            </p>

            <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02] space-y-3">
              <div className="text-xs text-gray-400">
                Venta objetivo actual: <strong>{ventaId ? `#${ventaId}` : 'Ninguna seleccionada'}</strong>
              </div>

              <div className="flex flex-col sm:flex-row gap-2">
                <button
                  type="button"
                  disabled={busy || numero(ventaId) <= 0}
                  onClick={() => void ejecutar(() => api.obtenerEntregaVenta(numero(ventaId)), 'Entrega consultada')}
                  className="flex-1 py-2 rounded-lg text-xs font-medium border border-white/10 hover:bg-white/5 disabled:opacity-40"
                >
                  Consultar Entrega
                </button>
                <button
                  type="button"
                  disabled={busy || numero(ventaId) <= 0}
                  onClick={() =>
                    confirmar('Confirmar entrega (puede descontar stock)', () =>
                      api.confirmarEntrega(numero(ventaId))
                    )
                  }
                  className="flex-1 py-2 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/30 disabled:opacity-40"
                >
                  Confirmar Entrega
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* SECCIÓN: CONFIGURACIÓN IGV */}
      {seccion === 'configuracion' && (
        <div className="glass p-6 max-w-2xl space-y-4">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Settings className="w-5 h-5 text-cyan-500" />
            Configuración Tributaria — IGV
          </h3>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Solo ADMIN_EMPRESA puede consultar y actualizar este ajuste. La tasa se introduce como porcentaje (18 significa 18%). Cambiarla puede impedir confirmar borradores con tasas anteriores; no modifica ventas históricas.
          </p>

          <div className="p-4 rounded-xl border border-white/5 bg-white/[0.02] flex items-center justify-between">
            <div>
              <span className="text-xs text-gray-400 block">Tasa Vigente Configurada</span>
              <span className="text-base font-bold text-cyan-400 mt-1 block">
                {igvActual === null ? 'Sin consultar o no configurada' : `${igvActual} %`}
              </span>
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={() =>
                void ejecutar(async () => {
                  const r = await api.consultarIgv();
                  setIgvActual(r?.tasa ?? null);
                  if (r) setIgv(r.tasa);
                  return r;
                }, 'IGV consultado')
              }
              className="px-3 py-1.5 rounded-lg text-xs font-medium border border-white/10 hover:bg-white/5"
            >
              Consultar IGV Vigente
            </button>
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <label className="input-label">Nueva Tasa IGV (%)</label>
              <input
                type="number"
                step="0.0001"
                min="0"
                max="100"
                value={igv}
                onChange={(e) => setIgv(e.target.value)}
                className="input-field"
              />
            </div>

            <button
              type="button"
              disabled={
                busy ||
                !igv.trim() ||
                !Number.isFinite(Number(igv)) ||
                Number(igv) < 0 ||
                Number(igv) > 100
              }
              onClick={() =>
                confirmar('Actualizar IGV empresarial', async () => {
                  const r = await api.actualizarIgv(igv);
                  setIgvActual(r.tasa);
                  return r;
                })
              }
              className="py-2.5 px-4 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 disabled:opacity-40"
            >
              Guardar Configuración Tributaria
            </button>
          </div>
        </div>
      )}

      {/* Inspector de Respuestas JSON de la API */}
      {detalle !== null && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass p-5 border border-cyan-500/20 shadow-glow space-y-3"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-mono font-semibold text-cyan-400">
              <Code className="w-4 h-4" />
              <span>Respuesta del Servidor (FastAPI / Supabase)</span>
            </div>
            <button
              onClick={() => setDetalle(null)}
              className="text-xs text-gray-400 hover:text-white"
            >
              Cerrar visualizador
            </button>
          </div>

          <pre className="p-4 rounded-xl bg-black/50 border border-white/5 text-xs font-mono text-cyan-300 overflow-x-auto max-h-72">
            {JSON.stringify(detalle, null, 2)}
          </pre>
        </motion.div>
      )}
    </motion.div>
  );
};
export default CommercialTestingView;
