import React, { useEffect, useState } from 'react';
import { api, ApiError } from '../services/api';
import type { User, RolEmpresa, RolPermisos } from '../types/api';
import { ListPagination } from './ListPagination';

type Igv = {id:number;codigo:string;nombre:string;tasa:string;activo:boolean;incluido_en_precio:boolean};

export const EnterpriseSettingsView: React.FC<{user:User}> = ({user}) => {
  const [igv,setIgv] = useState<Igv|null>(null);
  const [tasa,setTasa] = useState('');
  const [roles,setRoles] = useState<RolEmpresa[]>([]);
  const [detalle,setDetalle] = useState<RolPermisos|null>(null);
  const [loading,setLoading] = useState(true);
  const [saving,setSaving] = useState(false);
  const [error,setError] = useState('');
  const [notice,setNotice] = useState('');
  const [igvForbidden,setIgvForbidden] = useState(false);
  const [rolesForbidden,setRolesForbidden] = useState(false);
  const [testStatus,setTestStatus] = useState<'idle'|'loading'|'ok'|'error'>('idle');
  const [testResults,setTestResults] = useState<string[]>([]);

  useEffect(()=>{
    let active = true;
    const cargar = async()=>{
      setLoading(true);
      const [rIgv,rRoles] = await Promise.allSettled([api.consultarIgv(),api.listarRoles()]);
      if (!active) return;
      if(rIgv.status==='fulfilled') {setIgv(rIgv.value); setTasa(rIgv.value?.tasa ?? ''); setIgvForbidden(false);}
      else {setIgvForbidden(rIgv.reason instanceof ApiError && rIgv.reason.status===403); setError('No se pudo consultar la configuración tributaria.');}
      if(rRoles.status==='fulfilled') {setRoles(rRoles.value);setRolesForbidden(false);}
      else {setRolesForbidden(rRoles.reason instanceof ApiError && rRoles.reason.status===403);}
      setLoading(false);
    };
    void cargar();
    return ()=>{active=false;};
  },[]);

  const guardar = async()=>{
    setNotice('');setError('');
    const n=Number(tasa);
    if (!/^\d+(\.\d{1,4})?$/.test(tasa.trim()) || !Number.isFinite(n) || n<0 || n>100) {setError('Introduce una tasa entre 0 y 100, con hasta cuatro decimales.');return;}
    if (!window.confirm(`¿Confirmas cambiar el IGV a ${tasa}%? Este cambio afectará la configuración de la empresa.`)) return;
    setSaving(true);
    try {const actual=await api.actualizarIgv(tasa);setIgv(prev=>({...prev,id:actual.id,tasa:actual.tasa,codigo:prev?.codigo??'IGV',nombre:prev?.nombre??'Impuesto General a las Ventas',activo:true,incluido_en_precio:true}));setNotice('Configuración tributaria guardada. El backend registró la operación para auditoría.');}
    catch(e){setError(e instanceof Error?e.message:'No fue posible guardar el IGV.');}
    finally{setSaving(false);}
  };

  const verRol = async(id:number)=>{
    setError('');setDetalle(null);
    try {setDetalle(await api.listarPermisosRol(id));}
    catch(e){setError(e instanceof Error?e.message:'No fue posible consultar los permisos.');}
  };

  const comprobar = async()=>{
    setTestStatus('loading');setTestResults([]);
    const tests:[string,()=>Promise<unknown>][] = [
      ['Sesión autenticada',()=>api.getMe()],
      ['Dashboard comercial',()=>{const hoy=new Date();const desde=new Date(hoy.getTime()-30*86400000);const fmt=(d:Date)=>`${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;return api.getDashboardComercial(fmt(desde),fmt(hoy),5);}],
      ['Listado de productos',()=>api.getProductos(1,5)],
      ['Listado de clientes',()=>api.getClientes(1,5)],
      ['Listado de proveedores',()=>api.getProveedores(1,5)],
    ];
    const result=await Promise.allSettled(tests.map(([,fn])=>fn()));
    setTestResults(result.map((r,i)=>`${r.status==='fulfilled'?'CORRECTO':'NO DISPONIBLE'} — ${tests[i][0]}${r.status==='rejected' && r.reason instanceof ApiError?` (HTTP ${r.reason.status})`:''}`));
    setTestStatus(result.every(r=>r.status==='fulfilled')?'ok':'error');
  };

  return <div className="section-box">
    <h2 className="section-title">Configuración e integración empresarial</h2>
    <p className="settings-intro">Consulta la configuración de tu empresa y verifica la conexión entre SalesIA y sus módulos. Los permisos se comprueban en el backend.</p>
    <div className="grid-cards">
      <div className="card"><div className="card-label">Empresa activa</div><div className="card-value">#{user.empresa_id}</div><div className="card-sub">Identificada desde tu sesión, sin selección manual.</div></div>
      <div className="card"><div className="card-label">Usuario</div><div className="card-value" style={{fontSize:'1.05rem'}}>{user.nombre}</div><div className="card-sub">{user.email}</div></div>
      <div className="card"><div className="card-label">Sesión</div><div className="card-value">Activa</div><div className="card-sub">Autenticación JWT validada en el servidor.</div></div>
    </div>
    {loading && <div className="alert alert-info" role="status">Consultando configuración y roles...</div>}
    {error && <div className="alert alert-error" role="alert">{error}</div>}
    {notice && <div className="alert alert-success" role="status">{notice}</div>}
    <div className="settings-columns">
      <section className="chart-box">
        <h3>Impuesto sobre ventas (IGV)</h3>
        <p className="settings-desc">Tasa empresarial configurada para los precios. Solo un administrador autorizado puede modificarla.</p>
        {igvForbidden ? <div className="alert alert-info">La configuración de impuestos requiere el rol ADMIN_EMPRESA.</div> : <>
          <div className="form-group"><label htmlFor="settings-igv">Tasa del IGV (%)</label><input id="settings-igv" type="number" min="0" max="100" step="0.0001" value={tasa} onChange={e=>setTasa(e.target.value)} placeholder="Ej. 18"/></div>
          <p className="settings-desc">{igv ? `Configurado: ${igv.tasa}%. Incluido en el precio: ${igv.incluido_en_precio?'Sí':'No'}.`:'No hay un IGV activo configurado.'}</p>
          <button className="btn-primary" onClick={guardar} disabled={saving||loading}>{saving?'Guardando...':'Guardar IGV'}</button>
        </>}
      </section>
      <section className="chart-box">
        <h3>Roles y permisos de la empresa</h3>
        <p className="settings-desc">Consulta qué puede hacer cada rol. Las asignaciones de usuarios se gestionan en Usuarios y roles.</p>
        {rolesForbidden ? <div className="alert alert-info">Tu cuenta no tiene permiso para consultar roles.</div> : roles.length===0 ? <div className="empty-state">No se encontraron roles accesibles.</div> : <>
          <div className="settings-role-list"><ListPagination items={roles} getKey={r=>r.rol_id} pageSize={5} title="Roles" renderItem={r=><button type="button" onClick={()=>verRol(r.rol_id)} className="settings-role-button">{r.nombre}<span>Ver permisos</span></button>}/></div>
          {detalle && <div className="settings-role-detail"><strong>{detalle.nombre}</strong><p>{detalle.permisos.length} permisos asignados</p><ul>{detalle.permisos.map(p=><li key={p}>{p}</li>)}</ul></div>}
        </>}
      </section>
    </div>
    <section className="chart-box">
      <h3>Comprobación de integración</h3>
      <p className="settings-desc">Realiza consultas de solo lectura a los módulos principales. Esto no crea ni modifica registros y no sustituye las pruebas funcionales.</p>
      <button className="btn-primary" onClick={comprobar} disabled={testStatus==='loading'}>{testStatus==='loading'?'Verificando...':'Comprobar integración'}</button>
      {testResults.length>0 && <ul className="settings-test-results">{testResults.map(r=><li key={r}>{r}</li>)}</ul>}
    </section>
  </div>;
};
