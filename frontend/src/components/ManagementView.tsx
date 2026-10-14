import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import type { Cliente, Producto } from '../types/api';

type Tab = 'clientes' | 'productos' | 'categorias' | 'inventario' | 'segmentacion' | 'analisis';
type Categoria = {id:number;nombre:string;descripcion?:string|null;activo:boolean};
type StockItem = {producto_id:number;nombre:string;[key:string]:unknown};
type RfmItem = {cliente_id:number;nombre:string;segmento?:string;[key:string]:unknown};
type Item = Cliente | Producto | Categoria;
const hoy = () => new Date().toLocaleDateString('en-CA');
const importe = (x:unknown) => Number.isFinite(Number(x)) ? new Intl.NumberFormat('es-PE',{style:'currency',currency:'PEN'}).format(Number(x)) : 'N/D';
const texto = (x:unknown) => x === null || x === undefined || x === '' ? 'N/D' : String(x);
const optional = (s:string) => s.trim() ? s.trim() : undefined;

export const ManagementView: React.FC = () => {
  const [tab,setTab] = useState<Tab>('clientes');
  const [query,setQuery] = useState('');
  const [search,setSearch] = useState('');
  const [page,setPage] = useState(1);
  const [localPage,setLocalPage] = useState(1);
  const [localLimit,setLocalLimit] = useState(10);
  const [total,setTotal] = useState(0);
  const [items,setItems] = useState<Item[]>([]);
  const [stock,setStock] = useState<StockItem[]>([]);
  const [segments,setSegments] = useState<RfmItem[]>([]);
  const [analisisProductos,setAnalisisProductos] = useState<Producto[]>([]);
  const [analisisClientes,setAnalisisClientes] = useState<RfmItem[]>([]);
  const [analisisStock,setAnalisisStock] = useState<StockItem[]>([]);
  const [analisisCategorias,setAnalisisCategorias] = useState<Categoria[]>([]);
  const [analisisError,setAnalisisError] = useState<string[]>([]);
  const [start,setStart] = useState(() => { const d=new Date();d.setDate(d.getDate()-180);return d.toLocaleDateString('en-CA'); });
  const [end,setEnd] = useState(hoy);
  const [loading,setLoading] = useState(false);
  const [saving,setSaving] = useState(false);
  const [error,setError] = useState('');
  const [message,setMessage] = useState('');
  const [edit,setEdit] = useState<Item|null>(null);
  const [showForm,setShowForm] = useState(false);
  const [form,setForm] = useState<Record<string,string|boolean>>({});
  const [categoriaBusqueda,setCategoriaBusqueda] = useState('');
  const [categoriasDisponibles,setCategoriasDisponibles] = useState<Categoria[]>([]);
  const [categoriaAbierta,setCategoriaAbierta] = useState(false);
  const [categoriasCargando,setCategoriasCargando] = useState(false);
  const [categoriaError,setCategoriaError] = useState('');
  const [categoriaTotal,setCategoriaTotal] = useState(0);
  const categoriasSeq = useRef(0);
  const seq=useRef(0);

  const cargar = useCallback(async () => {
    const seqId=++seq.current;
    setLoading(true); setError('');
    try {
      if (tab==='clientes') {
        const r=await api.getClientes(page,20,search);
        if(seqId===seq.current){setItems(r.clientes);setTotal(r.total);}
      } else if(tab==='productos') {
        const r=await api.getProductos(page,20,search);
        if(seqId===seq.current){setItems(r.productos);setTotal(r.total);}
      } else if(tab==='categorias') {
        const r=await api.listarCategoriasPagina(page,20,search);
        if(seqId===seq.current){setItems(r.categorias);setTotal(r.total);}
      } else if(tab==='inventario') {
        const r=await api.getInventarioVisual(start,end);
        if(seqId===seq.current){setStock(r.items);setTotal(r.items.length);}
      } else if(tab==='analisis') {
        const endpoints=await Promise.allSettled([
          api.getProductos(1,100),api.listarCategoriasPagina(1,100),
          api.getInventarioVisual(start,end),api.getClientesVisual(start,end),
        ]);
        if(seqId===seq.current){
          const missing:string[]=[];
          if(endpoints[0].status==='fulfilled')setAnalisisProductos(endpoints[0].value.productos);else{setAnalisisProductos([]);missing.push('productos');}
          if(endpoints[1].status==='fulfilled')setAnalisisCategorias(endpoints[1].value.categorias);else{setAnalisisCategorias([]);missing.push('categorías');}
          if(endpoints[2].status==='fulfilled')setAnalisisStock(endpoints[2].value.items);else{setAnalisisStock([]);missing.push('inventario');}
          if(endpoints[3].status==='fulfilled')setAnalisisClientes(endpoints[3].value.items);else{setAnalisisClientes([]);missing.push('clientes RFM');}
          setAnalisisError(missing);
        }
      } else {
        const r=await api.getClientesVisual(start,end);
        if(seqId===seq.current){setSegments(r.items);setTotal(r.items.length);}
      }
    } catch(e:unknown) {
      if(seqId===seq.current) setError(e instanceof Error?e.message:'No se pudo cargar información.');
    } finally { if(seqId===seq.current)setLoading(false); }
  },[tab,page,search,start,end]);
  useEffect(()=>{void cargar();},[cargar]);

  // Búsqueda en el backend: no obliga a conocer el ID de una categoría.
  useEffect(() => {
    if (!showForm || tab !== 'productos') return;
    const id=++categoriasSeq.current;
    const timer=window.setTimeout(async () => {
      setCategoriasCargando(true);
      setCategoriaError('');
      try {
        const respuesta=await api.listarCategoriasPagina(1,100,categoriaBusqueda.trim());
        if (id!==categoriasSeq.current) return;
        setCategoriasDisponibles(respuesta.categorias.filter(c=>c.activo));
        setCategoriaTotal(respuesta.total);
      } catch (err:unknown) {
        if (id===categoriasSeq.current) {
          setCategoriasDisponibles([]);
          setCategoriaError(err instanceof Error?err.message:'No se pudieron cargar las categorías.');
        }
      } finally {
        if (id===categoriasSeq.current) setCategoriasCargando(false);
      }
    },250);
    return () => {window.clearTimeout(timer); categoriasSeq.current++;};
  },[showForm,tab,categoriaBusqueda]);

  const categoriaActual=categoriasDisponibles.find(c=>String(c.id)===String(form.categoria_id||''));

  const cambiarTab=(t:Tab)=>{setLocalPage(1);setTab(t);setPage(1);setQuery('');setSearch('');setItems([]);setError('');setMessage('');setShowForm(false);};
  const abrirFormulario=(item?:Item)=>{
    const values:Record<string,string|boolean>={};
    if(item) Object.entries(item).forEach(([k,v])=>{if(typeof v==='string'||typeof v==='boolean'||typeof v==='number')values[k]=typeof v==='boolean'?v:String(v);});
    setCategoriaBusqueda('');setCategoriaAbierta(false);setCategoriaError('');
    setEdit(item||null);setForm(values);setShowForm(true);setError('');setMessage('');
  };
  const cambiar=(k:string,v:string|boolean)=>setForm(x=>({...x,[k]:v}));
  const valor=(k:string)=>String(form[k]??'');
  const submit=async(e:React.FormEvent)=>{
    e.preventDefault();setError('');setMessage('');
    const nombre=valor('nombre').trim();
    if(nombre.length<2){setError('El nombre debe tener al menos dos caracteres.');return;}
    let payload:Record<string,unknown>={nombre};
    if(tab==='clientes') {
      const tipo=valor('tipo_documento'); const doc=valor('numero_documento').trim();
      if(Boolean(tipo)!==Boolean(doc)){setError('Indica tipo y número de documento conjuntamente.');return;}
      payload={nombre,...(tipo?{tipo_documento:tipo,numero_documento:doc}:{}),
        ...Object.fromEntries(['email','telefono','direccion'].map(k=>[k,optional(valor(k))]).filter(([,v])=>v!==undefined))};
    } else if(tab==='productos') {
      const precio=valor('precio_venta').trim(); const costo=valor('costo_referencia').trim()||'0.00';
      if(!/^(0|[1-9]\d*)(\.\d{1,2})?$/.test(precio)||!/^(0|[1-9]\d*)(\.\d{1,2})?$/.test(costo)) {setError('Los importes deben ser positivos con máximo dos decimales.');return;}
      const sku=valor('sku').trim();if(!sku){setError('El SKU es obligatorio.');return;}
      const cat=valor('categoria_id').trim();
      if (cat && (!/^\d+$/.test(cat) || Number(cat)<1)) {setError('Selecciona una categoría válida de la lista.');return;}
      payload={nombre,sku,tipo_item:valor('tipo_item')||'PRODUCTO',precio_venta:precio,costo_referencia:costo,
        controla_stock:Boolean(form.controla_stock??true),...(cat?{categoria_id:Number(cat)}:{}),
        ...(optional(valor('descripcion'))?{descripcion:valor('descripcion').trim()}:{})};
    } else if(tab==='categorias') payload={nombre,...(optional(valor('descripcion'))?{descripcion:valor('descripcion').trim()}:{})};
    else return;
    setSaving(true);
    try {
      if(tab==='clientes') {
        if(edit)await api.actualizarCliente(edit.id,payload);else await api.crearCliente(payload);
      } else if(tab==='productos') {
        if(edit)await api.actualizarProducto(edit.id,payload);else await api.crearProducto(payload);
      } else {
        if(edit)await api.actualizarCategoria(edit.id,payload);else await api.crearCategoria(payload as {nombre:string;descripcion?:string});
      }
      setMessage(edit?'Registro actualizado correctamente.':'Registro creado correctamente.');setShowForm(false);setEdit(null);await cargar();
    } catch(err:unknown){setError(err instanceof Error?err.message:'No se pudo guardar.');}
    finally{setSaving(false);}
  };
  const desactivar=async(item:Item)=>{
    if(!window.confirm(`¿Desactivar “${item.nombre}”? Esta acción es una baja lógica.`))return;
    setSaving(true);setError('');setMessage('');
    try{
      if(tab==='clientes')await api.desactivarCliente(item.id);
      if(tab==='productos')await api.desactivarProducto(item.id);
      if(tab==='categorias')await api.desactivarCategoria(item.id);
      setMessage('Registro desactivado.');await cargar();
    }catch(e:unknown){setError(e instanceof Error?e.message:'No se pudo desactivar.');}
    finally{setSaving(false);}
  };
  const tabs:[Tab,string][]=[['clientes','Clientes'],['productos','Productos'],['categorias','Categorías'],['inventario','Inventario y alertas'],['segmentacion','Segmentación RFM'],['analisis','Panel de análisis']];
  const readOnly=tab==='inventario'||tab==='segmentacion'||tab==='analisis';

  const barras = (titulo:string, datos:{etiqueta:string;valor:number}[], unidad:'numero'|'dinero'='numero') => {
    const disponibles=datos.filter(d=>Number.isFinite(d.valor) && d.valor>=0).slice(0,12);
    const mayor=Math.max(1,...disponibles.map(x=>x.valor));
    return <section className="phase5-visual" aria-label={titulo}>
      <h3>{titulo}</h3>
      {!disponibles.length?<p className="phase5-empty">Aún no hay datos para este gráfico.</p>:
      <div className="phase5-bars">{disponibles.map((d,i)=><div className="phase5-bar-row" key={`${d.etiqueta}-${i}`}>
        <div className="phase5-bar-info"><span title={d.etiqueta}>{d.etiqueta}</span><strong>{unidad==='dinero'?importe(d.valor):new Intl.NumberFormat('es-PE',{maximumFractionDigits:2}).format(d.valor)}</strong></div>
        <div className="phase5-bar-track" role="img" aria-label={`${d.etiqueta}: ${d.valor}`}><div style={{width:`${Math.max(0,d.valor/mayor*100)}%`}} /></div>
      </div>)}</div>}
    </section>;
  };
  const conteos = (nombres:string[]):{etiqueta:string;valor:number}[] =>
    Object.entries(nombres.reduce<Record<string,number>>((acc,n)=>{acc[n]=(acc[n]||0)+1;return acc;},{}))
      .map(([etiqueta,valor])=>({etiqueta,valor})).sort((a,b)=>b.valor-a.valor);
  const resumenRiesgos = (lista:StockItem[]) => conteos(lista.map(x=>texto(x.riesgo)));
  const topStock = (lista:StockItem[]) => lista.map(x=>({etiqueta:x.nombre,valor:Number(x.stock_actual)||0})).sort((a,b)=>b.valor-a.valor);
  const topDemanda = (lista:StockItem[]) => lista.map(x=>({etiqueta:x.nombre,valor:Number(x.demanda_estimada)||0})).sort((a,b)=>b.valor-a.valor);
  const stockAlto = stock.filter(x=>x.riesgo==='ALTO').length;
  const totalCompras = segments.reduce((sum,x)=>sum+(Number(x.frecuencia)||0),0);
  const gastoRfm = segments.reduce((sum,x)=>sum+(Number(x.valor_monetario)||0),0);
  const catalogoCategorias=conteos(analisisProductos.map(x=>analisisCategorias.find(c=>c.id===x.categoria_id)?.nombre||'Sin categoría'));
  const productosPorTipo=conteos(analisisProductos.map(x=>texto(x.tipo_item)));
  const preciosPorCategoria=analisisCategorias.map(c=>({etiqueta:c.nombre,valor:analisisProductos.filter(p=>p.categoria_id===c.id).reduce((sum,p)=>sum+(Number(p.precio_venta)||0),0)})).sort((a,b)=>b.valor-a.valor);

  return <section className="section-box phase5">
    <h2 className="section-title">5. Gestión comercial avanzada</h2>
    <p className="phase5-intro">Gestiona tus registros y comprende las tendencias con gráficos. Las cifras proceden de FastAPI; ningún resultado se calcula con datos inventados.</p>
    <div className="phase5-tabs" role="tablist" aria-label="Módulos de gestión">
      {tabs.map(([id,label])=><button key={id} role="tab" aria-selected={tab===id} className={tab===id?'btn-primary':''} onClick={()=>cambiarTab(id)}>{label}</button>)}
    </div>
    <div className="phase5-toolbar">
      {!readOnly?<form onSubmit={e=>{e.preventDefault();setPage(1);setSearch(query);}} className="phase5-search">
        <label htmlFor="f5search">Buscar registros</label><input id="f5search" placeholder="Nombre, documento o SKU" value={query} onChange={e=>setQuery(e.target.value)}/><button type="submit">Buscar</button>
        <button type="button" onClick={()=>{setQuery('');setSearch('');setPage(1)}}>Limpiar</button>
      </form>:<div className="phase5-search">
        <label>Desde <input aria-label="Desde" type="date" value={start} onChange={e=>setStart(e.target.value)}/></label>
        <label>Hasta <input aria-label="Hasta" type="date" value={end} onChange={e=>setEnd(e.target.value)}/></label>
      </div>}
      {!readOnly&&<button className="btn-primary" onClick={()=>abrirFormulario()}>+ Nuevo {tab==='clientes'?'cliente':tab==='productos'?'producto':'categoría'}</button>}
      <button onClick={()=>void cargar()} disabled={loading}>Actualizar</button>
    </div>
    {error&&<div role="alert" className="alert alert-error">{error}</div>}
    {message&&<div role="status" className="alert alert-success">{message}</div>}
    {loading&&<div role="status" className="alert alert-info">Cargando información...</div>}
    {showForm&&!readOnly&&<form onSubmit={submit} className="phase5-form">
      <div className="phase5-form-heading"><h3>{edit?'Editar':'Registrar'} {tab==='clientes'?'cliente':tab==='productos'?'producto':'categoría'}</h3><button type="button" onClick={()=>setShowForm(false)}>Cerrar</button></div>
      <label>Nombre *<input required minLength={2} maxLength={200} value={valor('nombre')} onChange={e=>cambiar('nombre',e.target.value)}/></label>
      {tab==='clientes'&&<>
        <label>Tipo documento<select value={valor('tipo_documento')} onChange={e=>cambiar('tipo_documento',e.target.value)}><option value="">Sin documento</option>{['DNI','RUC','CE','PASAPORTE'].map(x=><option key={x}>{x}</option>)}</select></label>
        <label>Número documento<input maxLength={20} value={valor('numero_documento')} onChange={e=>cambiar('numero_documento',e.target.value)}/></label>
        {['email','telefono','direccion'].map(k=><label key={k}>{k}<input type={k==='email'?'email':'text'} maxLength={k==='telefono'?30:255} value={valor(k)} onChange={e=>cambiar(k,e.target.value)}/></label>)}
      </>}
      {tab==='productos'&&<>
        <label>SKU *<input required maxLength={80} value={valor('sku')} onChange={e=>cambiar('sku',e.target.value)}/></label>
        <label>Tipo<select value={valor('tipo_item')||'PRODUCTO'} onChange={e=>cambiar('tipo_item',e.target.value)}>{['PRODUCTO','SERVICIO','INSUMO','MISCELANEO'].map(x=><option key={x}>{x}</option>)}</select></label>
        <div className="phase5-category-field">
          <label htmlFor="categoria-busqueda">Categoría del producto (opcional)</label>
          <p className="phase5-field-help">Escribe el nombre o elige una categoría. No necesitas conocer códigos.</p>
          {valor('categoria_id') ? <div className="phase5-category-selected">
            <span>Seleccionada: <strong>{categoriaActual?.nombre || `Categoría actual (#${valor('categoria_id')})`}</strong></span>
            <button type="button" onClick={()=>{cambiar('categoria_id','');setCategoriaBusqueda('');setCategoriaAbierta(true);}}>Cambiar</button>
            <button type="button" onClick={()=>{cambiar('categoria_id','');setCategoriaAbierta(false);}}>Quitar</button>
          </div> : null}
          <div className="phase5-category-picker">
            <input id="categoria-busqueda" type="search" autoComplete="off"
              placeholder="Buscar categoría por nombre..." value={categoriaBusqueda}
              onFocus={()=>setCategoriaAbierta(true)}
              onChange={e=>{setCategoriaBusqueda(e.target.value);cambiar('categoria_id','');setCategoriaAbierta(true);}}
              aria-controls="categorias-opciones" aria-expanded={categoriaAbierta} />
            {categoriaAbierta && <div className="phase5-category-options" id="categorias-opciones">
              {categoriasCargando && <p role="status">Buscando categorías...</p>}
              {categoriaError && <p role="alert">No se pudo consultar la lista: {categoriaError}</p>}
              {!categoriasCargando && !categoriaError && <>
                <button type="button" onClick={()=>{cambiar('categoria_id','');setCategoriaBusqueda('');setCategoriaAbierta(false);}}>
                  Sin categoría <small>Dejar el producto sin clasificar</small>
                </button>
                {categoriasDisponibles.map(c=><button type="button" key={c.id}
                  onClick={()=>{cambiar('categoria_id',String(c.id));setCategoriaBusqueda(c.nombre);setCategoriaAbierta(false);}}>
                  {c.nombre}{c.descripcion ? <small>{c.descripcion}</small>:null}
                </button>)}
                {!categoriasDisponibles.length && <p>No encontramos categorías activas. Prueba otro nombre o crea una en la pestaña Categorías.</p>}
                {categoriaTotal>100 && <p>Se muestran las primeras 100 coincidencias. Escribe más para acotar la búsqueda.</p>}
              </>}
            </div>}
          </div>
        </div>
        <label>Precio venta (PEN) *<input required type="number" min={0} step="0.01" value={valor('precio_venta')} onChange={e=>cambiar('precio_venta',e.target.value)}/></label>
        <label>Costo referencia (PEN)<input type="number" min={0} step="0.01" value={valor('costo_referencia')} onChange={e=>cambiar('costo_referencia',e.target.value)}/></label>
        <label>Descripción<input maxLength={500} value={valor('descripcion')} onChange={e=>cambiar('descripcion',e.target.value)}/></label>
        <label className="phase5-check"><input type="checkbox" checked={Boolean(form.controla_stock??true)} onChange={e=>cambiar('controla_stock',e.target.checked)}/> Controla stock físico</label>
      </>}
      {tab==='categorias'&&<label>Descripción<input maxLength={255} value={valor('descripcion')} onChange={e=>cambiar('descripcion',e.target.value)}/></label>}
      <div className="phase5-actions"><button type="submit" className="btn-primary" disabled={saving}>{saving?'Guardando...':'Guardar'}</button><button type="button" onClick={()=>setShowForm(false)}>Cancelar</button></div>
    </form>}
    {!readOnly?<>
      <div className="phase5-count">{total} registros · página {page} de {Math.max(1,Math.ceil(total/20))}</div>
      <div className="phase5-table-wrap"><table><thead><tr><th>ID</th><th>Nombre</th>{tab==='productos'&&<><th>SKU</th><th>Precio</th><th>Tipo</th></>}{tab==='clientes'&&<><th>Documento</th><th>Correo</th></>}{tab==='categorias'&&<th>Descripción</th>}<th>Estado</th><th>Acciones</th></tr></thead>
        <tbody>{items.map(x=><tr key={x.id}><td>{x.id}</td><td>{x.nombre}</td>{tab==='productos'&&<><td>{'sku' in x?x.sku:''}</td><td>{'precio_venta' in x?importe(x.precio_venta):''}</td><td>{'tipo_item' in x?x.tipo_item:''}</td></>}{tab==='clientes'&&<><td>{'numero_documento' in x?texto(x.numero_documento):''}</td><td>{'email' in x?texto(x.email):''}</td></>}{tab==='categorias'&&<td>{'descripcion' in x?texto(x.descripcion):''}</td>}<td>{x.activo?'Activo':'Inactivo'}</td><td><div className="phase5-actions"><button onClick={()=>abrirFormulario(x)} disabled={saving}>Editar</button>{x.activo&&<button onClick={()=>void desactivar(x)} disabled={saving}>Desactivar</button>}</div></td></tr>)}{!loading&&items.length===0&&<tr><td colSpan={8}>No hay registros para los filtros actuales.</td></tr>}</tbody></table></div>
      <div className="phase5-pagination"><button disabled={page===1||loading} onClick={()=>setPage(p=>Math.max(1,p-1))}>Anterior</button><span>Página {page}</span><button disabled={page*20>=total||loading} onClick={()=>setPage(p=>p+1)}>Siguiente</button></div>
    </>:tab==='inventario'?<>
      <div className="alert alert-info">Análisis orientativo: el stock es el valor almacenado; la demanda se estima a partir de ventas confirmadas. No equivale a un movimiento físico ni a un pronóstico de IA entrenada.</div>
      <div className="phase5-summary-grid"><div className="phase5-summary-card"><span>Productos analizados</span><strong>{stock.length}</strong></div><div className="phase5-summary-card"><span>Riesgo alto estimado</span><strong>{stockAlto}</strong></div><div className="phase5-summary-card"><span>Sin historial de ventas</span><strong>{stock.filter(x=>x.riesgo==='SIN_HISTORIAL').length}</strong></div></div>
      <div className="phase5-chart-grid">{barras('Distribución por riesgo estimado',resumenRiesgos(stock))}{barras('Existencias disponibles por producto',topStock(stock))}{barras('Demanda estimada para 14 días',topDemanda(stock))}</div>
      <div className="phase5-table-wrap"><table><thead><tr><th>Producto</th><th>Indicadores calculados por el backend</th></tr></thead><tbody>{stock.slice((localPage-1)*localLimit,localPage*localLimit).map(x=><tr key={x.producto_id}><td>{x.nombre}</td><td>{Object.entries(x).filter(([k])=>!['producto_id','nombre'].includes(k)).map(([k,v])=><div key={k}><strong>{k.replace(/_/g,' ')}:</strong> {typeof v==='object'?JSON.stringify(v):texto(v)}</div>)}</td></tr>)}{!loading&&!stock.length&&<tr><td colSpan={2}>Sin inventario disponible o sin permiso de consulta.</td></tr>}</tbody></table></div><div className="list-pagination-footer"><span>Mostrando {Math.min(stock.length,(localPage-1)*localLimit+1)}–{Math.min(stock.length,localPage*localLimit)} de {stock.length} registros consultados</span><label>Por página <select value={localLimit} onChange={e=>{setLocalLimit(Number(e.target.value));setLocalPage(1);}}><option value={5}>5</option><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option></select></label><button type="button" disabled={localPage===1} onClick={()=>setLocalPage(p=>p-1)}>Anterior</button><span>Página {localPage} de {Math.max(1,Math.ceil(stock.length/localLimit))}</span><button type="button" disabled={localPage*localLimit>=stock.length} onClick={()=>setLocalPage(p=>p+1)}>Siguiente</button></div>
    </>:tab==='segmentacion'?<>
      <div className="alert alert-info">RFM es una clasificación descriptiva de recencia, frecuencia y gasto. El backend devuelve una muestra de hasta 100 clientes activos, ordenados por ID.</div>
      <div className="phase5-summary-grid"><div className="phase5-summary-card"><span>Clientes analizados</span><strong>{segments.length}</strong></div><div className="phase5-summary-card"><span>Compras históricas de la muestra</span><strong>{totalCompras}</strong></div><div className="phase5-summary-card"><span>Valor acumulado de la muestra</span><strong>{importe(gastoRfm)}</strong></div></div>
      <div className="phase5-chart-grid">{barras('Clientes por segmento RFM',conteos(segments.map(x=>texto(x.segmento))))}{barras('Clientes por gasto acumulado',segments.map(x=>({etiqueta:x.nombre,valor:Number(x.valor_monetario)||0})).sort((a,b)=>b.valor-a.valor),'dinero')}</div>
      <div className="phase5-table-wrap"><table><thead><tr><th>Cliente</th><th>Segmento</th><th>Indicadores RFM</th></tr></thead><tbody>{segments.slice((localPage-1)*localLimit,localPage*localLimit).map(x=><tr key={x.cliente_id}><td>{x.nombre}</td><td>{texto(x.segmento)}</td><td>{Object.entries(x).filter(([k])=>!['cliente_id','nombre','segmento'].includes(k)).map(([k,v])=><div key={k}><strong>{k.replace(/_/g,' ')}:</strong> {typeof v==='object'?JSON.stringify(v):texto(v)}</div>)}</td></tr>)}{!loading&&!segments.length&&<tr><td colSpan={3}>No hay clientes para analizar en este periodo.</td></tr>}</tbody></table></div><div className="list-pagination-footer"><span>Mostrando {Math.min(segments.length,(localPage-1)*localLimit+1)}–{Math.min(segments.length,localPage*localLimit)} de {segments.length} registros consultados</span><label>Por página <select value={localLimit} onChange={e=>{setLocalLimit(Number(e.target.value));setLocalPage(1);}}><option value={5}>5</option><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option></select></label><button type="button" disabled={localPage===1} onClick={()=>setLocalPage(p=>p-1)}>Anterior</button><span>Página {localPage} de {Math.max(1,Math.ceil(segments.length/localLimit))}</span><button type="button" disabled={localPage*localLimit>=segments.length} onClick={()=>setLocalPage(p=>p+1)}>Siguiente</button></div>
    </>:<>
      <div className="alert alert-info">Panel de análisis exploratorio: productos y categorías utilizan hasta 100 registros cada uno; inventario y RFM consultan muestras de hasta 100. Los gráficos de precios no equivalen a ingresos ni a rentabilidad.</div>
      {!!analisisError.length&&<div className="alert alert-info">Sin acceso a: {analisisError.join(', ')}. Los demás módulos se muestran normalmente.</div>}
      <div className="phase5-summary-grid">
        <div className="phase5-summary-card"><span>Productos consultados (muestra)</span><strong>{analisisProductos.length}</strong></div>
        <div className="phase5-summary-card"><span>Categorías consultadas (muestra)</span><strong>{analisisCategorias.length}</strong></div>
        <div className="phase5-summary-card"><span>Productos con inventario consultados</span><strong>{analisisStock.length}</strong></div>
        <div className="phase5-summary-card"><span>Clientes RFM consultados</span><strong>{analisisClientes.length}</strong></div>
      </div>
      <div className="phase5-chart-grid">
        {barras('Productos por categoría · muestra',catalogoCategorias)}
        {barras('Productos por tipo · muestra',productosPorTipo)}
        {barras('Suma de precios de catálogo por categoría · no son ventas',preciosPorCategoria,'dinero')}
        {barras('Riesgo estimado de stock · muestra',resumenRiesgos(analisisStock))}
        {barras('Segmentos de clientes · muestra',conteos(analisisClientes.map(x=>texto(x.segmento))))}
      </div>
      <div className="phase5-visual"><h3>Cómo interpretar los gráficos</h3><p>Las categorías más numerosas no siempre son las más rentables. Para medir ingresos por categoría y hacer análisis ABC por ventas hacen falta agregaciones de ventas y detalles de venta. No se debe usar la suma de precios de catálogo como sustituto de ingresos.</p><p>El riesgo de inventario se basa en velocidad histórica observada, no en una predicción garantizada. Revisa manualmente los casos de riesgo alto.</p></div>
    </>}
  </section>;
};
