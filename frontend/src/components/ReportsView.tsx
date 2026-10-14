import React, { useCallback, useEffect, useState } from 'react';
import { api, ReporteHistorialF8, ReportePreviewF8 } from '../services/api';
import { ReporteTipo } from '../types/api';
import { ListPagination } from './ListPagination';

const TIPOS: {value:ReporteTipo; nombre:string; descripcion:string}[] = [
  {value:'VENTAS',nombre:'Ventas',descripcion:'Operaciones comerciales registradas durante el periodo.'},
  {value:'ESTADISTICO',nombre:'Estadísticas',descripcion:'Resumen de importes, valores extremos y promedios.'},
  {value:'INVENTARIO',nombre:'Inventario',descripcion:'Existencias y valores disponibles según el reporte del backend.'},
  {value:'CLIENTES',nombre:'Clientes',descripcion:'Actividad comercial agrupada por cliente.'},
  {value:'RENDIMIENTO',nombre:'Vendedores',descripcion:'Rendimiento comercial por vendedor.'},
];
const fecha = (d:Date) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const safeDate = (s:string) => {const d=new Date(s); return isNaN(d.getTime()) ? s : d.toLocaleString('es-PE');};
export const ReportsView:React.FC = () => {
  const [tipo,setTipo] = useState<ReporteTipo>('VENTAS');
  const [inicio,setInicio] = useState(fecha(new Date(Date.now()-30*86400000)));
  const [fin,setFin] = useState(fecha(new Date()));
  const [preview,setPreview] = useState<ReportePreviewF8|null>(null);
  const [historial,setHistorial] = useState<ReporteHistorialF8[]>([]);
  const [filtro,setFiltro] = useState('');
  const [cargando,setCargando] = useState(false);
  const [procesando,setProcesando] = useState(false);
  const [error,setError] = useState('');
  const [aviso,setAviso] = useState('');
  const [errorHistorial,setErrorHistorial] = useState('');
  const invalido = !inicio || !fin || inicio>fin || ((new Date(fin).getTime()-new Date(inicio).getTime())/86400000 > 366);

  const cargarHistorial = useCallback(async () => {
    try { const data=await api.historialReportesF8(100); setHistorial(data.items); setErrorHistorial(''); }
    catch(e) { setErrorHistorial(e instanceof Error ? e.message : 'No se pudo consultar el historial.'); }
  },[]);
  useEffect(()=>{void cargarHistorial();},[cargarHistorial]);
  useEffect(()=>{
    if(invalido){setPreview(null);return;}
    let activo=true;
    setCargando(true);setError('');setPreview(null);
    const t=window.setTimeout(()=>{
      api.previsualizarReporteF8(tipo,inicio,fin,100)
        .then(data=>{if(activo)setPreview(data);})
        .catch(e=>{if(activo)setError(e instanceof Error?e.message:'No se pudo cargar el reporte.');})
        .finally(()=>{if(activo)setCargando(false);});
    },350);
    return ()=>{activo=false;window.clearTimeout(t);};
  },[tipo,inicio,fin,invalido]);

  const generar = async(formato:'CSV'|'XLSX'|'PDF') => {
    if(invalido)return;
    setProcesando(true);setError('');setAviso('');
    try {
      const r=await api.generarReporteF8(tipo,formato,inicio,fin);
      setAviso(`Reporte ${formato} generado y registrado con el número ${r.id}.`);
      await cargarHistorial();
      try { await api.descargarReporteGuardadoF8(r.id,formato); }
      catch { setAviso(`Reporte ${r.id} registrado. La descarga no está disponible desde este servidor; puedes reintentar desde el historial.`); }
    } catch(e) {setError(e instanceof Error?e.message:'No se pudo generar el reporte.');}
    finally {setProcesando(false);}
  };
  const descargarDirecto=async()=>{
    if(invalido)return;
    setProcesando(true);setError('');setAviso('');
    try {await api.descargarReportePdf(tipo,inicio,fin);setAviso('PDF visual descargado. Este formato directo no se guarda en el historial.');}
    catch(e){setError(e instanceof Error?e.message:'No se pudo descargar el PDF.');}
    finally {setProcesando(false);}
  };
  const filas=historial.filter(r=>`${r.nombre} ${r.tipo} ${r.formato} ${r.estado}`.toLowerCase().includes(filtro.toLowerCase()));
  return <div className="section-box">
    <h2 className="section-title">Reportes empresariales — Fase 8</h2>
    <p style={{marginBottom:'1rem'}}>Consulta primero los datos y después descarga el formato que necesites. La información proviene de tu empresa y se consulta mediante FastAPI.</p>
    <div className="filter-bar">
      <div className="form-group"><label htmlFor="r8tipo">¿Qué deseas consultar?</label><select id="r8tipo" value={tipo} onChange={e=>setTipo(e.target.value as ReporteTipo)}>{TIPOS.map(x=><option key={x.value} value={x.value}>{x.nombre}</option>)}</select></div>
      <div className="form-group"><label htmlFor="r8inicio">Desde</label><input id="r8inicio" type="date" value={inicio} onChange={e=>setInicio(e.target.value)}/></div>
      <div className="form-group"><label htmlFor="r8fin">Hasta</label><input id="r8fin" type="date" value={fin} onChange={e=>setFin(e.target.value)}/></div>
    </div>
    <p style={{marginBottom:'1rem',color:'#555'}}>{TIPOS.find(x=>x.value===tipo)?.descripcion} El periodo no puede superar 367 días.</p>
    {invalido&&<div className="alert alert-error">Selecciona fechas válidas, en orden, y un periodo máximo de 367 días.</div>}
    {error&&<div role="alert" className="alert alert-error">{error}</div>}
    {aviso&&<div role="status" className="alert alert-success">{aviso}</div>}
    <div className="dashboard-actions">
      <strong>Previsualización automática</strong><span>{cargando?'Consultando datos...':preview?`${preview.total_filas} filas encontradas · ${preview.moneda} · ${preview.zona_horaria}`:'Sin resultados aún'}</span>
    </div>
    {preview&&<>
      <div style={{overflowX:'auto',marginBottom:'1rem'}}><table><thead><tr>{preview.columnas.map((col,i)=><th key={i}>{col}</th>)}</tr></thead></table></div>
      <ListPagination items={preview.filas} title="Filas mostradas" sourceLimit={100} pageSize={10} getKey={(_,i)=>i} emptyText="No se encontraron operaciones para este tipo de reporte y periodo." renderItem={(row,i)=><div key={i} style={{overflowX:'auto'}}><table><tbody><tr>{row.map((valor,j)=><td key={j} style={{minWidth:'115px'}}>{valor===null?'—':String(valor)}</td>)}</tr></tbody></table></div>}/>
      {preview.total_filas>preview.filas.length&&<p className="alert alert-info">La vista preliminar muestra {preview.filas.length} de {preview.total_filas} filas. Genera un archivo para consultar el reporte completo.</p>}
    </>}
    <div className="section-box" style={{marginTop:'1rem'}}>
      <h3 style={{marginBottom:'0.75rem'}}>Generar y descargar</h3>
      <div style={{display:'flex',gap:'0.6rem',flexWrap:'wrap'}}>
        <button type="button" className="btn-primary" disabled={invalido||procesando} onClick={()=>generar('CSV')}>Descargar CSV</button>
        <button type="button" disabled={invalido||procesando} onClick={()=>generar('XLSX')}>Descargar Excel</button>
        <button type="button" disabled={invalido||procesando} onClick={()=>generar('PDF')}>Generar PDF y guardar</button>
        <button type="button" disabled={invalido||procesando} onClick={descargarDirecto}>PDF visual inmediato</button>
      </div>
      <p style={{fontSize:'0.8rem',marginTop:'0.65rem',color:'#555'}}>El PDF visual se genera al momento; los otros formatos se registran en el historial. Los archivos del historial requieren almacenamiento persistente para conservarse tras despliegues.</p>
    </div>
    <div className="section-box" style={{marginTop:'1rem'}}>
      <h3 style={{marginBottom:'0.7rem'}}>Historial de reportes generados</h3>
      <div className="filter-bar"><div className="form-group"><label htmlFor="r8buscar">Buscar por tipo, nombre o formato</label><input id="r8buscar" value={filtro} onChange={e=>setFiltro(e.target.value)} placeholder="Ej. ventas, PDF..."/></div><button type="button" onClick={()=>void cargarHistorial()}>Actualizar historial</button></div>
      {errorHistorial&&<div className="alert alert-info">{errorHistorial}</div>}
      <ListPagination items={filas} sourceLimit={100} pageSize={10} title="Reportes" emptyText="Todavía no hay reportes guardados que coincidan con la búsqueda." getKey={item=>item.id} renderItem={item=><div className="card" style={{marginBottom:'0.5rem',display:'flex',justifyContent:'space-between',alignItems:'center',gap:'1rem',flexWrap:'wrap'}}><div><strong>#{item.id} · {item.nombre}</strong><div className="card-sub">{item.formato} · {item.estado} · {safeDate(item.created_at)} · {item.tamano_bytes??0} bytes</div></div><button disabled={procesando||item.estado!=='COMPLETADO'} onClick={async()=>{setError('');try{await api.descargarReporteGuardadoF8(item.id,item.formato);}catch(e){setError(e instanceof Error?e.message:'Archivo no disponible.');}}}>Descargar</button></div>}/>
      {historial.length>=100&&<div className="alert alert-info">Se consultaron los 100 reportes más recientes. El backend todavía no ofrece desplazamiento para consultar el historial más antiguo.</div>}
    </div>
  </div>;
};
