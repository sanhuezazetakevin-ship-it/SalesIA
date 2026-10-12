import React, { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import { Cliente, Producto, Venta } from '../types/api';

export const CommercialView: React.FC = () => {
  const [subTab, setSubTab] = useState<'clientes' | 'productos' | 'ventas'>('clientes');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busqueda, setBusqueda] = useState('');

  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [totalClientes, setTotalClientes] = useState(0);

  const [productos, setProductos] = useState<Producto[]>([]);
  const [totalProductos, setTotalProductos] = useState(0);

  const [ventas, setVentas] = useState<Venta[]>([]);
  const [totalVentas, setTotalVentas] = useState(0);

  const cargarDatos = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (subTab === 'clientes') {
        const resp = await api.getClientes(1, 20, busqueda);
        setClientes(resp.clientes || []);
        setTotalClientes(resp.total || 0);
      } else if (subTab === 'productos') {
        const resp = await api.getProductos(1, 20, busqueda);
        setProductos(resp.productos || []);
        setTotalProductos(resp.total || 0);
      } else if (subTab === 'ventas') {
        const resp = await api.getVentas(1, 20);
        setVentas(resp.ventas || []);
        setTotalVentas(resp.total || 0);
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Error al cargar datos comerciales';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, [subTab, busqueda]);

  useEffect(() => {
    cargarDatos();
  }, [cargarDatos]);

  return (
    <div>
      <div className="section-box">
        <h2 className="section-title">3. Operaciones Comerciales</h2>

        {/* Sub-pestañas */}
        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
          <button
            className={subTab === 'clientes' ? 'btn-primary' : ''}
            onClick={() => { setSubTab('clientes'); setBusqueda(''); }}
          >
            Clientes ({totalClientes})
          </button>
          <button
            className={subTab === 'productos' ? 'btn-primary' : ''}
            onClick={() => { setSubTab('productos'); setBusqueda(''); }}
          >
            Catálogo Productos ({totalProductos})
          </button>
          <button
            className={subTab === 'ventas' ? 'btn-primary' : ''}
            onClick={() => { setSubTab('ventas'); setBusqueda(''); }}
          >
            Registro de Ventas ({totalVentas})
          </button>
        </div>

        {/* Buscador */}
        {subTab !== 'ventas' && (
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem', maxWidth: '400px' }}>
            <input
              type="text"
              placeholder={`Buscar en ${subTab}...`}
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && cargarDatos()}
              style={{ flex: 1 }}
            />
            <button onClick={cargarDatos} disabled={loading}>
              Buscar
            </button>
          </div>
        )}

        {error && <div className="alert alert-error">{error}</div>}

        {/* Tabla Clientes */}
        {subTab === 'clientes' && (
          <div>
            {clientes.length === 0 ? (
              <div className="empty-state">No se encontraron clientes registrados en la empresa.</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Nombre / Razón Social</th>
                    <th>Documento</th>
                    <th>Email</th>
                    <th>Teléfono</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {clientes.map((c) => (
                    <tr key={c.id}>
                      <td>#{c.id}</td>
                      <td><strong>{c.nombre}</strong></td>
                      <td>{c.tipo_documento ? `${c.tipo_documento}: ${c.numero_documento}` : '-'}</td>
                      <td>{c.email || '-'}</td>
                      <td>{c.telefono || '-'}</td>
                      <td>
                        <span className={`badge ${c.activo ? 'badge-connected' : 'badge-disconnected'}`}>
                          {c.activo ? 'ACTIVO' : 'INACTIVO'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Tabla Productos */}
        {subTab === 'productos' && (
          <div>
            {productos.length === 0 ? (
              <div className="empty-state">No hay productos registrados en el catálogo.</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>SKU</th>
                    <th>Nombre</th>
                    <th>Tipo</th>
                    <th>Precio Venta</th>
                    <th>Costo Referencia</th>
                    <th>Controla Stock</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  {productos.map((p) => (
                    <tr key={p.id}>
                      <td>#{p.id}</td>
                      <td><code>{p.sku}</code></td>
                      <td><strong>{p.nombre}</strong></td>
                      <td>{p.tipo_item}</td>
                      <td>PEN {p.precio_venta}</td>
                      <td>PEN {p.costo_referencia}</td>
                      <td>{p.controla_stock ? 'SÍ' : 'NO'}</td>
                      <td>
                        <span className={`badge ${p.activo ? 'badge-connected' : 'badge-disconnected'}`}>
                          {p.activo ? 'ACTIVO' : 'INACTIVO'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}

        {/* Tabla Ventas */}
        {subTab === 'ventas' && (
          <div>
            {ventas.length === 0 ? (
              <div className="empty-state">No se registran ventas para esta empresa.</div>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Código</th>
                    <th>Fecha UTC</th>
                    <th>Estado</th>
                    <th>Estado de Pago</th>
                    <th>Total (PEN)</th>
                  </tr>
                </thead>
                <tbody>
                  {ventas.map((v) => (
                    <tr key={v.id}>
                      <td>#{v.id}</td>
                      <td><strong>{v.codigo}</strong></td>
                      <td>{v.created_at ? v.created_at.replace('T', ' ').slice(0, 19) : '-'}</td>
                      <td><span className="badge badge-connected">{v.estado}</span></td>
                      <td>
                        <span className={`badge ${v.estado_pago === 'PAGADO' ? 'badge-connected' : 'badge-disconnected'}`}>
                          {v.estado_pago}
                        </span>
                      </td>
                      <td><strong>PEN {v.total}</strong></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
