import React, { useState } from 'react';
import { api } from '../services/api';

export const InvitationRegistrationView: React.FC = () => {
  const [token, setToken] = useState('');
  const [nombre, setNombre] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmacion, setConfirmacion] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const registrar = async (e: React.FormEvent) => {
    e.preventDefault(); setError(''); setMessage('');
    if (password !== confirmacion) { setError('Las contraseñas no coinciden.'); return; }
    setLoading(true);
    try {
      const result = await api.registrarInvitado({token:token.trim(), nombre:nombre.trim(), email:email.trim(), password});
      setMessage(`Registro completado: ${result.estado}. Espera la aprobación administrativa antes de iniciar sesión.`);
      setToken(''); setPassword(''); setConfirmacion('');
    } catch (e) { setError(e instanceof Error ? e.message : 'No fue posible completar el registro.'); }
    finally { setLoading(false); }
  };
  return <div className="section-box">
    <h2 className="section-title">Registro por invitación — Pruebas</h2>
    <p style={{fontSize:'0.85rem', marginBottom:'1rem'}}>Introduce el token generado por un administrador. Esta cuenta quedará inactiva hasta su aprobación.</p>
    {error && <div className="alert alert-error" role="alert">{error}</div>}
    {message && <div className="alert alert-success" role="status">{message}</div>}
    <form onSubmit={e => void registrar(e)} className="filter-bar" style={{alignItems:'stretch', flexDirection:'column', maxWidth:'600px'}}>
      <div className="form-group"><label htmlFor="reg-token">Token de invitación (43 caracteres)</label><input id="reg-token" required minLength={43} maxLength={43} autoComplete="off" value={token} onChange={e => setToken(e.target.value)} /></div>
      <div className="form-group"><label htmlFor="reg-name">Nombre</label><input id="reg-name" required minLength={2} maxLength={120} value={nombre} onChange={e => setNombre(e.target.value)} /></div>
      <div className="form-group"><label htmlFor="reg-email">Correo invitado</label><input id="reg-email" type="email" required value={email} onChange={e => setEmail(e.target.value)} /></div>
      <div className="form-group"><label htmlFor="reg-password">Contraseña (mínimo 12 caracteres)</label><input id="reg-password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" value={password} onChange={e => setPassword(e.target.value)} /></div>
      <div className="form-group"><label htmlFor="reg-password-confirm">Confirmar contraseña</label><input id="reg-password-confirm" type="password" required value={confirmacion} onChange={e => setConfirmacion(e.target.value)} /></div>
      <button className="btn-primary" disabled={loading}>{loading ? 'Registrando...' : 'Completar registro'}</button>
    </form>
  </div>;
};
