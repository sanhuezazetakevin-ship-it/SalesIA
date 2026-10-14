import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { InvitacionCreada, RolEmpresa, RolPermisos, UsuarioPendiente } from '../types/api';

const errorText = (e: unknown) => e instanceof Error ? e.message : 'Error desconocido';

export const UsersManagementView: React.FC = () => {
  const [paginaPendientes,setPaginaPendientes] = useState(1);
  const [paginaRoles,setPaginaRoles] = useState(1);
  const limiteLista=10;
  const [pendientes, setPendientes] = useState<UsuarioPendiente[]>([]);
  const [roles, setRoles] = useState<RolEmpresa[]>([]);
  const [email, setEmail] = useState('');
  const [invitacion, setInvitacion] = useState<InvitacionCreada | null>(null);
  const [permisos, setPermisos] = useState<RolPermisos | null>(null);
  const [usuarioId, setUsuarioId] = useState('');
  const [rolId, setRolId] = useState('');
  const [busy, setBusy] = useState(false);
  const [pendingBusy, setPendingBusy] = useState(false);
  const [rolesBusy, setRolesBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const cargarPendientes = async () => {
    setPendingBusy(true);
    try { setPendientes(await api.listarUsuariosPendientes()); setError(''); }
    catch (e) { setError(`Pendientes: ${errorText(e)}`); }
    finally { setPendingBusy(false); }
  };
  const cargarRoles = async () => {
    setRolesBusy(true);
    try { const rows = await api.listarRoles(); setRoles(rows); setRolId(current => current || String(rows[0]?.rol_id || '')); setError(''); }
    catch (e) { setError(`Roles: ${errorText(e)}`); }
    finally { setRolesBusy(false); }
  };
  useEffect(() => { void cargarPendientes(); void cargarRoles(); }, []);

  const run = async (action: () => Promise<string>) => {
    setBusy(true); setError(''); setMessage('');
    try { setMessage(await action()); }
    catch (e) { setError(errorText(e)); }
    finally { setBusy(false); }
  };
  const validId = (v: string): number | null => {
    const number = Number(v);
    return /^\d+$/.test(v.trim()) && Number.isSafeInteger(number) && number > 0 ? number : null;
  };
  const cambiarRol = (operacion: 'asignar' | 'revocar') => {
    const usuario = validId(usuarioId), rol = validId(rolId);
    if (!usuario || !rol) { setError('Introduce identificadores positivos válidos.'); return; }
    const roleLabel = roles.find(r => r.rol_id === rol)?.nombre || String(rol);
    if (!window.confirm(`${operacion === 'asignar' ? 'Asignar' : 'Revocar'} el rol ${roleLabel} al usuario #${usuario}? Esta operación modificará datos de testing.`)) return;
    void run(async () => {
      const response = operacion === 'asignar' ? await api.asignarRol(usuario, rol) : await api.revocarRol(usuario, rol);
      return `Rol ${response.rol_nombre}: ${response.estado}${response.sesiones_revocadas !== undefined ? `. Sesiones revocadas: ${response.sesiones_revocadas}` : ''}.`;
    });
  };

  return <div>
    <div className="section-box">
      <h2 className="section-title">6. Gestión de Usuarios y Roles — Pruebas API</h2>
      <p style={{fontSize: '0.85rem', marginBottom: '1rem'}}>Panel temporal de integración; mantiene el estilo monocromático del proyecto. Todas las acciones se ejecutan en el backend configurado. Utilizar únicamente la base de testing.</p>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      {message && <div className="alert alert-success" role="status">{message}</div>}
      <h3 style={{marginBottom:'0.75rem'}}>6-A. Usuarios pendientes</h3>
      <button onClick={() => void cargarPendientes()} disabled={pendingBusy}> {pendingBusy ? 'Consultando...' : 'Actualizar pendientes'} </button>
      <div style={{overflowX:'auto', marginTop:'0.75rem'}}>
        <table style={{width:'100%', borderCollapse:'collapse', fontSize:'0.85rem'}}><thead><tr><th>Usuario ID</th><th>Nombre</th><th>Correo</th><th>Fecha</th><th>Acción</th></tr></thead><tbody>
          {pendientes.slice((paginaPendientes-1)*limiteLista,paginaPendientes*limiteLista).map(u => <tr key={u.usuario_id}><td>{u.usuario_id}</td><td>{u.nombre}</td><td>{u.email}</td><td>{new Date(u.created_at).toLocaleString()}</td><td><button disabled={busy} onClick={() => {
            if (!window.confirm(`¿Aprobar la cuenta de ${u.nombre}? Esta acción activa al usuario.`)) return;
            void run(async () => { const result = await api.aprobarUsuario(u.usuario_id); await cargarPendientes(); return `Usuario #${result.usuario_id}: ${result.estado}.`; });
          }}>Aprobar</button></td></tr>)}
          {!pendingBusy && pendientes.length === 0 && <tr><td colSpan={5}>No hay usuarios pendientes o no se pudieron consultar (comprueba el mensaje de error).</td></tr>}
        </tbody></table>
        <div className="list-pagination-footer"><span>Página {paginaPendientes} de {Math.max(1,Math.ceil(pendientes.length/limiteLista))} · {pendientes.length} pendientes</span><button disabled={paginaPendientes<=1} onClick={()=>setPaginaPendientes(p=>p-1)}>Anterior</button><button disabled={paginaPendientes*limiteLista>=pendientes.length} onClick={()=>setPaginaPendientes(p=>p+1)}>Siguiente</button></div>
      </div>
    </div>
    <div className="section-box">
      <h3 className="section-title">6-B. Crear invitación</h3>
      <p style={{fontSize:'0.85rem', marginBottom:'0.75rem'}}>El token se presenta solo tras crear la invitación. Es una credencial temporal: no lo publiques ni lo guardes en el repositorio.</p>
      <form className="filter-bar" onSubmit={e => {e.preventDefault(); setInvitacion(null); void run(async () => { const response = await api.crearInvitacion(email.trim()); setInvitacion(response); setEmail(''); return 'Invitación creada. Comparte el token únicamente por un canal privado.'; });}}>
        <div className="form-group"><label htmlFor="invite-email">Correo del invitado</label><input id="invite-email" type="email" required value={email} onChange={e => setEmail(e.target.value)} /></div>
        <button className="btn-primary" disabled={busy}>Crear invitación</button>
      </form>
      {invitacion && <div className="alert alert-info">
        <p>Correo: {invitacion.email} — Vence: {new Date(invitacion.fecha_expiracion).toLocaleString()}</p>
        <p><strong>Token de invitación (temporal):</strong></p>
        <input aria-label="Token de invitación" readOnly value={invitacion.token} style={{width:'100%', margin:'0.5rem 0'}} />
        <button onClick={() => void navigator.clipboard.writeText(invitacion.token).then(() => setMessage('Token copiado. Compártelo de forma privada.')).catch(e => setError(errorText(e)))}>Copiar token</button>{' '}
        <button onClick={() => setInvitacion(null)}>Ocultar token</button>
      </div>}
    </div>
    <div className="section-box">
      <h3 className="section-title">6-C. Roles y permisos</h3>
      <button onClick={() => void cargarRoles()} disabled={rolesBusy}>{rolesBusy ? 'Consultando...' : 'Actualizar roles'}</button>
      <div style={{overflowX:'auto', margin:'1rem 0'}}><table style={{width:'100%', fontSize:'0.85rem'}}><thead><tr><th>ID</th><th>Rol</th><th>Descripción</th><th>Permisos</th></tr></thead><tbody>
        {roles.slice((paginaRoles-1)*limiteLista,paginaRoles*limiteLista).map(r => <tr key={r.rol_id}><td>{r.rol_id}</td><td>{r.nombre}</td><td>{r.descripcion || '—'}</td><td><button disabled={busy} onClick={() => void run(async () => { const result = await api.listarPermisosRol(r.rol_id); setPermisos(result); return `Permisos consultados: ${result.nombre}.`; })}>Ver permisos</button></td></tr>)}
        {roles.length===0 && <tr><td colSpan={4}>Sin resultados. Comprueba que la cuenta tenga el permiso roles.ver.</td></tr>}
      </tbody></table><div className="list-pagination-footer"><span>Página {paginaRoles} de {Math.max(1,Math.ceil(roles.length/limiteLista))} · {roles.length} roles</span><button disabled={paginaRoles<=1} onClick={()=>setPaginaRoles(p=>p-1)}>Anterior</button><button disabled={paginaRoles*limiteLista>=roles.length} onClick={()=>setPaginaRoles(p=>p+1)}>Siguiente</button></div></div>
      {permisos && <div className="alert alert-info"><strong>Permisos de {permisos.nombre}:</strong><ul style={{paddingLeft:'1.5rem'}}>{permisos.permisos.map(p => <li key={p}><code>{p}</code></li>)}</ul></div>}
      <h4 style={{margin:'1rem 0 0.5rem'}}>Asignar o revocar rol (testing)</h4>
      <p style={{fontSize:'0.85rem', marginBottom:'0.75rem'}}>Introduce el ID de un usuario activo de la misma empresa. No se permite modificar los propios roles. La aprobación de una cuenta no asigna roles automáticamente.</p>
      <div className="filter-bar">
        <div className="form-group"><label htmlFor="target-user">Usuario ID</label><input id="target-user" type="number" min="1" step="1" value={usuarioId} onChange={e => setUsuarioId(e.target.value)} /></div>
        <div className="form-group"><label htmlFor="target-role">Rol</label><select id="target-role" value={rolId} onChange={e => setRolId(e.target.value)}>{roles.map(r => <option key={r.rol_id} value={r.rol_id}>{r.nombre} (#{r.rol_id})</option>)}</select></div>
        <button disabled={busy || !roles.length} onClick={() => cambiarRol('asignar')}>Asignar</button>
        <button disabled={busy || !roles.length} onClick={() => cambiarRol('revocar')}>Revocar</button>
      </div>
    </div>
  </div>;
};
