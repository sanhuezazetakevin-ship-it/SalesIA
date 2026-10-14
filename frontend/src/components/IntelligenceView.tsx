import React, { useCallback, useEffect, useRef, useState } from 'react';
import {ListPagination} from './ListPagination';
import {api, InsightF7, NotificacionF7, AnalisisF7, EventoAuditoriaF7, ApiError} from '../services/api';

type Vista = 'insights'|'notificaciones'|'historial'|'auditoria';
const fecha = (d: Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const hoy = fecha(new Date());
const inicioInicial = fecha(new Date(Date.now()-180*86400000));
const human = (s:string|null|undefined) => s ? new Date(s).toLocaleString('es-PE') : 'Sin fecha';
const detalleError = (error:unknown) => {
  if (error instanceof ApiError && error.status===403) return 'No cuentas con permisos para consultar o ejecutar esta operación.';
  return error instanceof Error ? error.message : 'No se pudo completar la operación.';
};

export const IntelligenceView:React.FC = () => {
  const [vista,setVista] = useState<Vista>('insights');
  const [desde,setDesde] = useState(inicioInicial);
  const [hasta,setHasta] = useState(hoy);
  const [tipo,setTipo] = useState<'estadistico'|'probabilidad'>('estadistico');
  const [nombre,setNombre] = useState('Resumen comercial');
  const [umbral,setUmbral] = useState('100.00');
  const [soloNoLeidas,setSoloNoLeidas] = useState(false);
  const [accion,setAccion] = useState('');
  const [pagina,setPagina] = useState(0);
  const [tamPagina,setTamPagina] = useState(25);
  const ultimaSincronizacion = useRef('');
  const [loading,setLoading] = useState(false);
  const [procesando,setProcesando] = useState(false);
  const [error,setError] = useState('');
  const [aviso,setAviso] = useState('');
  const [insights,setInsights] = useState<InsightF7[]>([]);
  const [notificaciones,setNotificaciones] = useState<NotificacionF7[]>([]);
  const [analisis,setAnalisis] = useState<AnalisisF7[]>([]);
  const [auditoria,setAuditoria] = useState<{total:number;items:EventoAuditoriaF7[]}>({total:0,items:[]});
  const [ampliado,setAmpliado] = useState<number|null>(null);
  const [revision,setRevision] = useState<'REVISADO'|'DESCARTADO'>('REVISADO');

  const cargar = useCallback(async () => {
    setLoading(true);setError('');setAviso('');
    try {
      if(vista==='insights') setInsights((await api.listarInsights()).items);
      if(vista==='notificaciones') setNotificaciones((await api.listarNotificaciones(soloNoLeidas)).items);
      if(vista==='historial') setAnalisis((await api.listarHistorialAnalisis(tipo)).items);
      if(vista==='auditoria') {const r=await api.listarAuditoria(pagina*tamPagina,tamPagina,accion);setAuditoria({total:r.total,items:r.items});}
    } catch(e) {setError(detalleError(e));}
    finally {setLoading(false);}
  },[vista,soloNoLeidas,tipo,pagina,tamPagina,accion]);
  useEffect(()=>{void cargar();},[cargar]);
  useEffect(()=>{
    if (vista!=='notificaciones'||!fechasValidas) return;
    const clave = `${desde}|${hasta}`;
    if (ultimaSincronizacion.current===clave) return;
    ultimaSincronizacion.current=clave;
    let activo=true;
    api.sincronizarNotificaciones(desde,hasta)
      .then(()=>{if(activo) void cargar();})
      .catch(()=>{if(activo) setAviso('Las alertas existentes están disponibles; la sincronización automática no pudo completarse.');});
    return ()=>{activo=false;};
  // La sincronización no se repite cada vez que refresca la consulta.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[vista,desde,hasta]);
  useEffect(()=>{
    if(vista!=='notificaciones') return;
    const timer = window.setInterval(()=>{if(document.visibilityState==='visible') void cargar();},60000);
    return ()=>window.clearInterval(timer);
  },[vista,cargar]);

  const ejecutar = async (operacion:()=>Promise<unknown>,mensaje:string) => {
    setProcesando(true);setError('');setAviso('');
    try {await operacion(); await cargar();setAviso(mensaje);} catch(e) {setError(detalleError(e));}
    finally {setProcesando(false);}
  };
  const fechasValidas = desde<=hasta && !!desde && !!hasta;
  const umbralValido = Number.isFinite(Number(umbral)) && Number(umbral)>=0;

  return <section className="section-box phase7">
    <h2 className="section-title">Centro inteligente y trazabilidad — Fase 7</h2>
    <p className="p7-muted">La información se carga al abrir cada sección. Las alertas se sincronizan automáticamente una vez por periodo y se actualizan mientras esta pantalla esté abierta.</p>
    <nav className="p7-tabs" aria-label="Secciones de inteligencia">
      {([['insights','Recomendaciones'],['notificaciones','Notificaciones'],['historial','Historial analítico'],['auditoria','Auditoría']] as const).map(([id,text])=><button type="button" key={id} aria-pressed={vista===id} className={vista===id?'btn-primary':''} onClick={()=>{setVista(id);setAmpliado(null);}}>{text}</button>)}
    </nav>
    <div className="filter-bar">
      <div className="form-group"><label htmlFor="p7desde">Desde</label><input id="p7desde" type="date" value={desde} onChange={e=>setDesde(e.target.value)}/></div>
      <div className="form-group"><label htmlFor="p7hasta">Hasta</label><input id="p7hasta" type="date" value={hasta} onChange={e=>setHasta(e.target.value)}/></div>
      <button disabled={loading||procesando} onClick={()=>void cargar()}>Actualizar ahora (opcional)</button>
    </div>
    {!fechasValidas&&<div className="alert alert-error">Selecciona fechas válidas: inicio no puede superar fin.</div>}
    {error&&<div role="alert" className="alert alert-error">{error}</div>}
    {aviso&&<div role="status" className="alert alert-success">{aviso}</div>}
    {loading&&<div role="status" className="alert alert-info">Consultando información...</div>}

    {vista==='insights'&&<>
      <div className="p7-heading"><h3>Recomendaciones del sistema</h3><p>Los insights se generan a partir de análisis guardados por la empresa, no de información inventada en el navegador.</p></div>
      {insights.length===0&&!loading&&<div className="empty-state">Todavía no se han generado recomendaciones para esta empresa. El sistema mostrará aquí oportunidades y advertencias cuando el backend produzca insights a partir de análisis guardados.</div>}
      <div className="p7-grid"><ListPagination items={insights} sourceLimit={50} title="Recomendaciones visibles" getKey={i=>i.id} renderItem={i=><article className="p7-card" key={i.id}>
        <div className="p7-cardtop"><strong>{i.titulo}</strong><span className="badge">{i.prioridad} · {i.estado}</span></div>
        <p>{i.descripcion}</p><p><strong>Acción sugerida:</strong> {i.recomendacion||'Sin recomendación específica'}</p>
        <small>Origen: {i.tipo_insight} · {human(i.created_at)}</small>
        <div className="p7-actions"><button disabled={procesando||i.estado==='REVISADO'} onClick={()=>void ejecutar(()=>api.actualizarInsight(i.id,'REVISADO'),'Recomendación marcada como revisada.')}>Marcar revisada</button><button disabled={procesando||i.estado==='DESCARTADO'} onClick={()=>void ejecutar(()=>api.actualizarInsight(i.id,'DESCARTADO'),'Recomendación descartada.')}>Descartar</button></div>
      </article>}/></div>
    </>}

    {vista==='notificaciones'&&<>
      <div className="p7-heading"><h3>Alertas persistentes</h3><p>Las alertas leídas se conservan como historial.</p></div>
      <div className="p7-actions"><label><input type="checkbox" checked={soloNoLeidas} onChange={e=>setSoloNoLeidas(e.target.checked)}/> Solo no leídas</label><button className="btn-primary" disabled={procesando||!fechasValidas} onClick={()=>void ejecutar(()=>api.sincronizarNotificaciones(desde,hasta),'Sincronización completada. Revisa el historial.')}>Sincronizar alertas</button></div>
      {notificaciones.length===0&&!loading&&<div className="empty-state">No hay notificaciones para este filtro.</div>}
      <div className="p7-list"><ListPagination items={notificaciones} title="Notificaciones visibles" getKey={n=>n.id} renderItem={n=><article className="p7-item" key={n.id}>
        <div><strong>{n.titulo}</strong><p>{n.descripcion}</p><small>{n.nivel} · {human(n.created_at)} · {n.leida?'Leída':'Pendiente de lectura'}</small></div>
        {!n.leida&&<button disabled={procesando} onClick={()=>void ejecutar(()=>api.marcarNotificacionLeida(n.id),'Notificación marcada como leída.')}>Marcar leída</button>}
      </article>}/></div>
    </>}

    {vista==='historial'&&<>
      <div className="p7-heading"><h3>Historial de análisis</h3><p>Los resultados se calculan y guardan en el servidor usando tu empresa autenticada.</p></div>
      <div className="p7-actions"><div className="form-group"><label htmlFor="p7tipo">Tipo de análisis</label><select id="p7tipo" value={tipo} onChange={e=>setTipo(e.target.value as 'estadistico'|'probabilidad')}><option value="estadistico">Estadística</option><option value="probabilidad">Probabilidades</option></select></div>
      {tipo==='estadistico'?<div className="form-group"><label htmlFor="p7nombre">Nombre</label><input id="p7nombre" maxLength={150} value={nombre} onChange={e=>setNombre(e.target.value)}/></div>:<div className="form-group"><label htmlFor="p7umbral">Importe alto desde (S/)</label><input id="p7umbral" type="number" min="0" step="0.01" value={umbral} onChange={e=>setUmbral(e.target.value)}/></div>}
      <button className="btn-primary" disabled={procesando||!fechasValidas||(tipo==='estadistico'?!nombre.trim():!umbralValido)} onClick={()=>void ejecutar(()=>tipo==='estadistico'?api.crearAnalisisEstadistico(desde,hasta,nombre.trim()):api.crearAnalisisProbabilidad(desde,hasta,umbral),'Análisis guardado en el historial.')}>Calcular y guardar</button></div>
      {analisis.length===0&&!loading&&<div className="empty-state">No se encontraron análisis guardados de este tipo.</div>}
      <div className="p7-list"><ListPagination items={analisis} title="Análisis guardados" getKey={a=>a.id} renderItem={a=><article className="p7-item" key={a.id}>
        <div><strong>Análisis #{a.id}</strong><p>{a.tipo} · {a.estado} · {human(a.created_at)}</p></div>
        <div><button onClick={()=>setAmpliado(ampliado===a.id?null:a.id)}>{ampliado===a.id?'Ocultar resultados':'Ver resultados'}</button></div>
        {ampliado===a.id&&<pre className="p7-json">{JSON.stringify(a.resultados,null,2)}</pre>}
        <div className="p7-actions"><button disabled={procesando} onClick={()=>void ejecutar(()=>api.generarInsights(tipo,a.id),'Recomendaciones generadas. Consúltalas en la pestaña Recomendaciones.')}>Generar recomendaciones</button></div>
      </article>}/></div>
    </>}

    {vista==='auditoria'&&<>
      <div className="p7-heading"><h3>Registro de auditoría</h3><p>Consulta protegida de acciones registradas. Esta pantalla no permite editar ni borrar eventos.</p></div>
      <div className="p7-actions"><div className="form-group"><label htmlFor="p7accion">Tipo de acción</label><select id="p7accion" value={accion} onChange={e=>{setPagina(0);setAccion(e.target.value)}}><option value="">Todas</option>{['CREAR','ACTUALIZAR','ELIMINAR','CONFIRMAR','CANCELAR','ANULAR','CONSULTAR','OTRO'].map(x=><option key={x} value={x}>{x}</option>)}</select></div><span>Eventos encontrados: {auditoria.total}</span></div>
      {auditoria.items.length===0&&!loading&&<div className="empty-state">Sin eventos disponibles o sin acceso para este filtro.</div>}
      <div className="p7-table"><table><thead><tr><th>Fecha</th><th>Acción</th><th>Entidad</th><th>Usuario</th><th>Descripción</th><th>Origen</th></tr></thead><tbody>{auditoria.items.map(e=><tr key={e.id}><td>{human(e.created_at)}</td><td>{e.accion}</td><td>{e.entidad}{e.entidad_id?` #${e.entidad_id}`:''}</td><td>{e.usuario_id??'Sistema'}</td><td>{e.descripcion||'—'}</td><td>{e.origen}</td></tr>)}</tbody></table></div>
      <div className="p7-actions"><button disabled={pagina===0||loading} onClick={()=>setPagina(p=>Math.max(0,p-1))}>Anterior</button><span>Página {pagina+1} de {Math.max(1,Math.ceil(auditoria.total/tamPagina))}</span><label>Registros por página <select value={tamPagina} onChange={e=>{setPagina(0);setTamPagina(Number(e.target.value));}}><option value={10}>10</option><option value={25}>25</option><option value={50}>50</option></select></label><button disabled={(pagina+1)*tamPagina>=auditoria.total||loading} onClick={()=>setPagina(p=>p+1)}>Siguiente</button></div>
    </>}
    <p className="p7-muted">Los datos están limitados por el volumen máximo de cada endpoint. Las acciones requieren los permisos otorgados por el administrador empresarial.</p>
  </section>;
};
