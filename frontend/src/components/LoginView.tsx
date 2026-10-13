import React, { useState } from 'react';
import { api, authStorage } from '../services/api';
import { User } from '../types/api';

interface LoginViewProps {
  user: User | null;
  onLoginSuccess: (user: User) => void;
  onLogout: () => void;
}

export const LoginView: React.FC<LoginViewProps> = ({
  user,
  onLoginSuccess,
  onLogout,
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage(null);
    setError(null);

    try {
      const resp = await api.login(email, password);
      setMessage(`Inicio de sesión correcto. Token recibido (expira en ${resp.expires_in}s).`);
      const me = await api.getMe();
      onLoginSuccess(me);
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : 'Error desconocido al iniciar sesión';
      setError(errMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleVerificarIdentidad = async () => {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const me = await api.getMe();
      setMessage(`Identidad confirmada: ID ${me.id}, ${me.nombre} (${me.email}) - Empresa #${me.empresa_id}`);
      onLoginSuccess(me);
    } catch (err: unknown) {
      const errMessage = err instanceof Error ? err.message : 'Error al verificar sesión';
      setError(errMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleSimularError401 = async () => {
    setLoading(true);
    setMessage(null);
    setError(null);
    try {
      const status = await api.testUnauthorized();
      if (status === 401) {
        setMessage('Prueba 401 correcta: petición sin credenciales rechazada; sesión original intacta.');
      } else {
        setError(`Se esperaba HTTP 401, pero la API respondió HTTP ${status}.`);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Error de conexión en la prueba 401');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="section-box">
        <h2 className="section-title">1. Autenticación y Control de Sesión</h2>

        {message && <div className="alert alert-success">{message}</div>}
        {error && <div className="alert alert-error">{error}</div>}

        {user ? (
          <div>
            <div className="alert alert-info">
              Sesión activa para <strong>{user.nombre}</strong> &lt;{user.email}&gt;.
              <br />
              Empresa ID: <strong>{user.empresa_id}</strong> | Estado: {user.activo ? 'ACTIVO' : 'INACTIVO'}
            </div>

            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
              <button onClick={handleVerificarIdentidad} disabled={loading}>
                {loading ? 'Consultando...' : 'Re-verificar Identidad (/api/auth/me)'}
              </button>
              <button onClick={onLogout} style={{ border: '1px solid #000' }}>
                Cerrar Sesión
              </button>
              <button onClick={handleSimularError401} title="Comprueba que la API devuelva 401 sin token">
                Probar Rechazo 401
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleLogin} style={{ maxWidth: '450px' }}>
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Correo Electrónico:</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="ej: usuario@empresa.com"
              />
            </div>

            <div className="form-group" style={{ marginBottom: '1.25rem' }}>
              <label>Contraseña:</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>

            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <button type="submit" className="btn-primary" disabled={loading}>
                {loading ? 'Autenticando...' : 'Iniciar Sesión'}
              </button>
              <button
                type="button"
                onClick={handleVerificarIdentidad}
                disabled={loading || !authStorage.getToken()}
              >
                Verificar Token Almacenado
              </button>
            </div>
          </form>
        )}
      </div>

      <div className="section-box">
        <h3 className="section-title">Parámetros de Conexión</h3>
        <p style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>
          Backend URL configurada: <code>{import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}</code>
        </p>
        <p style={{ fontSize: '0.8rem', color: '#555' }}>
          * Las solicitudes envían el token JWT en la cabecera <code>Authorization: Bearer &lt;token&gt;</code>.
          Todas las consultas de la empresa quedan aisladas en base al usuario autenticado.
        </p>
      </div>
    </div>
  );
};
