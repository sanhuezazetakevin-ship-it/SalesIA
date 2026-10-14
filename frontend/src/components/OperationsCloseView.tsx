import React,{useEffect,useState} from 'react';
import {api} from '../services/api';

type Item={inventario_id:number|null;producto_id:number;producto:string;sku:string;cantidad_disponible:string};
type Movimiento={id:number;producto_id:number;tipo:string;cantidad_delta:string;motivo:string;referencia:string|null;fecha:string};
type Vendedor={id:number;nombre:string;email:string;activo:boolean};
const PAGE=20;
export const OperationsCloseView:React.FC=()=>{
 const [tab,setTab]=useState<'stock'|'movimientos'|'vendedores'>('stock');
 const [pagina,setPagina]=useState(1); const [busqueda,setBusqueda]=useState('');
 const [items,setItems]=useState<Item[]>([]);const [movimientos,setMovimientos]=useState<Movimiento[]>([]);const [vendedores,setVendedores]=useState<Vendedor[]>([]);
 const [total,setTotal]=useState(0);const [loading,setLoading]=useState(false);const [error,setError]=useState('');const [mensaje,setMensaje]=useState('');
 const [producto,setProducto]=useState('');const [delta,setDelta]=useState('');const [motivo,setMotivo]=useState('');const [referencia,setReferencia]=useState('');const [guardando,setGuardando]=useState(false);
 const [version,setVersion]=useState(0);
 useEffect(()=>{let vivo=true;setLoading(true);setError('');
  (async()=>{try{
   if(tab==='stock'){const r=await api.listarInventarioOperativo(pagina,PAGE,busqueda);if(vivo){setItems(r.items);setTotal(r.total);}}
   else if(tab==='movimientos'){const r=await api.listarMovimientosOperativos(pagina,PAGE);if(vivo){setMovimientos(r.items);setTotal(r.total);}}
   else{const r=await api.listarVendedoresOperativos(pagina,PAGE,busqueda);if(vivo){setVendedores(r.items);setTotal(r.total);}}
  }catch(e){if(vivo)setError(e instanceof Error?e.message:'No se pudo consultar el módulo.');}finally{if(vivo)setLoading(false)}})();return()=>{vivo=false};
 },[tab,pagina,busqueda,version]);
 const ajustar=async(e:React.FormEvent)=>{e.preventDefault();const id=Number(producto);const n=Number(delta);
  if(!Number.isInteger(id)||id<=0||!Number.isFinite(n)||n===0||Math.round(n*1000)!==n*1000||motivo.trim().length<8){setError('Selecciona un producto, indica una cantidad válida y escribe un motivo de al menos 8 caracteres.');return;}
  if(!window.confirm(`¿Confirmas un ajuste de ${delta} unidades? Se registrará en el historial de auditoría.`))return;
  setGuardando(true);setError('');setMensaje('');try{const r=await api.ajustarInventario({producto_id:id,cantidad_delta:delta,motivo:motivo.trim(),referencia:referencia.trim()||undefined});setMensaje(`Stock anterior: ${r.stock_anterior}. Stock actual: ${r.stock_actual}. Movimiento registrado.`);setDelta('');setMotivo('');setReferencia('');setVersion(v=>v+1);}catch(ex){setError(ex instanceof Error?ex.message:'No se pudo registrar el ajuste.');}finally{setGuardando(false)}
 };
 const cambiar=(v:'stock'|'movimientos'|'vendedores')=>{setTab(v);setPagina(1);setBusqueda('');setError('');};
 const max=Math.max(1,Math.ceil(total/PAGE));
 return <section className="section-box">
  <h2 className="section-title">Operación de inventario y vendedores</h2>
  <p>Consulta existencias, registra ajustes autorizados y revisa quiénes tienen el rol de vendedor. Las listas se consultan por páginas desde el servidor.</p>
  <div className="filter-bar" style={{marginTop:16}}>
   <button className={tab==='stock'?'btn-primary':''} onClick={()=>cambiar('stock')}>Existencias y ajustes</button>
   <button className={tab==='movimientos'?'btn-primary':''} onClick={()=>cambiar('movimientos')}>Historial de movimientos</button>
   <button className={tab==='vendedores'?'btn-primary':''} onClick={()=>cambiar('vendedores')}>Directorio de vendedores</button>
  </div>
  {tab!=='movimientos'&&<div className="form-group" style={{marginBottom:16}}><label htmlFor="buscar-operaciones">Buscar por nombre{tab==='stock'?' o SKU':''}</label><input id="buscar-operaciones" placeholder="Escribe para buscar..." value={busqueda} onChange={e=>{setBusqueda(e.target.value);setPagina(1)}}/></div>}
  {error&&<div className="alert alert-error" role="alert">{error}</div>}
  {mensaje&&<div className="alert alert-success" role="status">{mensaje}</div>}
  {loading?<div className="alert alert-info">Consultando datos...</div>:<div style={{overflowX:'auto'}}>
   {tab==='stock'?<table><thead><tr><th>Producto</th><th>SKU</th><th>Stock disponible</th></tr></thead><tbody>{items.map(p=><tr key={p.producto_id}><td>{p.producto}</td><td>{p.sku}</td><td>{p.cantidad_disponible}</td></tr>)}</tbody></table>:
   tab==='movimientos'?<table><thead><tr><th>Fecha</th><th>Producto ID</th><th>Tipo</th><th>Variación</th><th>Motivo</th><th>Referencia</th></tr></thead><tbody>{movimientos.map(m=><tr key={m.id}><td>{new Date(m.fecha).toLocaleString('es-PE')}</td><td>{m.producto_id}</td><td>{m.tipo}</td><td>{m.cantidad_delta}</td><td>{m.motivo}</td><td>{m.referencia||'—'}</td></tr>)}</tbody></table>:
   <table><thead><tr><th>Vendedor</th><th>Correo</th><th>Estado</th></tr></thead><tbody>{vendedores.map(v=><tr key={v.id}><td>{v.nombre}</td><td>{v.email}</td><td>{v.activo?'Activo':'Inactivo'}</td></tr>)}</tbody></table>}
   {total===0&&<p className="empty-state">No se encontraron registros. Comprueba los filtros o permisos disponibles.</p>}
  </div>}
  <div className="dashboard-actions" style={{marginTop:16}}><span>Mostrando página {pagina} de {max} · {total} registros</span><div style={{display:'flex',gap:8}}><button disabled={pagina<=1||loading} onClick={()=>setPagina(p=>p-1)}>Anterior</button><button disabled={pagina>=max||loading} onClick={()=>setPagina(p=>p+1)}>Siguiente</button></div></div>
  {tab==='stock'&&<form onSubmit={ajustar} className="section-box" style={{marginTop:24}}>
   <h3>Ajuste manual de inventario</h3><p>Solo usuarios con permiso de ajuste. Una cantidad positiva suma stock; una negativa resta stock. Todos los cambios se registran.</p>
   <div className="filter-bar" style={{marginTop:12}}><div className="form-group"><label>Producto</label><select value={producto} onChange={e=>setProducto(e.target.value)} required><option value="">Seleccionar producto</option>{items.map(p=><option key={p.producto_id} value={p.producto_id}>{p.producto} ({p.sku})</option>)}</select></div>
   <div className="form-group"><label>Variación de stock</label><input type="number" step="0.001" required value={delta} onChange={e=>setDelta(e.target.value)} placeholder="Ej. 5 o -2"/></div>
   <div className="form-group"><label>Motivo obligatorio</label><input required minLength={8} maxLength={255} value={motivo} onChange={e=>setMotivo(e.target.value)} placeholder="Ej. Corrección por conteo físico"/></div>
   <div className="form-group"><label>Referencia (opcional)</label><input maxLength={100} value={referencia} onChange={e=>setReferencia(e.target.value)} placeholder="Ej. Acta de inventario"/></div></div>
   <button className="btn-primary" type="submit" disabled={guardando||loading}>{guardando?'Registrando...':'Registrar ajuste'}</button>
   <p style={{fontSize:12,marginTop:8}}>Si recibes HTTP 403, tu cuenta no dispone del permiso <code>inventario.ajustar</code>. Los administradores deben asignarlo desde el sistema de roles.</p>
  </form>}
  {tab==='vendedores'&&<p className="alert alert-info">Para añadir o retirar vendedores, utiliza Usuarios y roles: asigna o revoca el rol VENDEDOR. No se crean cuentas duplicadas.</p>}
 </section>
};
