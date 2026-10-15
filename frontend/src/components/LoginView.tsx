import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Mail,
  Lock,
  AlertCircle,
  CheckCircle2,
  LogOut,
  RefreshCw,
  ShieldAlert,
  Eye,
  EyeOff,
  Loader2,
  ArrowRight,
  ShieldCheck,
  Server,
} from 'lucide-react';
import { api, authStorage } from '../services/api';
import { User } from '../types/api';

export interface LoginViewProps {
  user: User | null;
  onLoginSuccess: (user: User) => void;
  onLogout: () => void;
  publicMode?: boolean;
}

export const Spinner: React.FC<{ className?: string }> = ({ className = 'w-4 h-4' }) => (
  <Loader2 className={`animate-spin ${className}`} />
);

export const LoginView: React.FC<LoginViewProps> = ({
  user,
  onLoginSuccess,
  onLogout,
  publicMode = false,
}) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
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

  const handleLogoutAction = async () => {
    try {
      await api.logout();
    } catch {
      // Logout even if the remote request fails
    }
    onLogout();
  };

  // Content for when a user is logged in (only shown when publicMode is false)
  if (user && !publicMode) {
    return (
      <div className="min-h-[80vh] flex flex-col items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          className="backdrop-blur-xl bg-white/90 dark:bg-[#0A0A0F]/90 rounded-2xl shadow-2xl border border-gray-200/50 dark:border-white/10 max-w-lg w-full p-8 space-y-6"
        >
          {/* Logo at top */}
          <div className="flex flex-col items-center justify-center text-center">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-4 h-4 rounded-md bg-gradient-to-br from-[#EE915B] to-[#A8542A] shadow-[0_0_12px_rgba(217,120,67,0.8)]" />
              <span className="text-2xl tracking-tight text-gray-900 dark:text-white">
                <span className="font-bold">SALES</span>
                <span className="font-light text-[#D97843]">IA</span>
              </span>
            </div>
            <p className="text-xs uppercase tracking-widest text-gray-500 dark:text-gray-400 font-medium">
              Sesión Activa
            </p>
          </div>

          {/* Feedback messages */}
          {error && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="alert-card alert-error"
            >
              <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-500" />
              <div className="text-sm">{error}</div>
            </motion.div>
          )}

          {message && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="alert-card alert-success"
            >
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-500" />
              <div className="text-sm">{message}</div>
            </motion.div>
          )}

          {/* User Info Card */}
          <div className="glass p-5 rounded-2xl border border-gray-200/60 dark:border-white/10 space-y-4">
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-[#D97843] to-[#8A4522] text-white font-bold text-lg flex items-center justify-center shadow-[0_0_15px_rgba(217,120,67,0.35)]">
                  {user.nombre?.charAt(0)?.toUpperCase() || 'U'}
                </div>
                <div>
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white leading-tight">
                    {user.nombre}
                  </h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                    {user.email}
                  </p>
                </div>
              </div>
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                  user.activo
                    ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                    : 'bg-red-500/10 text-red-600 dark:text-red-400 border border-red-500/20'
                }`}
              >
                {user.activo ? 'ACTIVO' : 'INACTIVO'}
              </span>
            </div>

            <div className="pt-3 border-t border-gray-200/50 dark:border-white/10 flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
              <span>Empresa Asociada:</span>
              <span className="font-semibold text-gray-800 dark:text-gray-200">
                Empresa #{user.empresa_id}
              </span>
            </div>
          </div>

          {/* Action buttons */}
          <div className="space-y-2 pt-2">
            <button
              onClick={handleVerificarIdentidad}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 text-gray-800 dark:text-gray-200 border border-gray-200/60 dark:border-white/10 text-sm font-medium transition-all disabled:opacity-50"
            >
              {loading ? (
                <Spinner className="w-4 h-4 text-cyan-500" />
              ) : (
                <RefreshCw className="w-4 h-4 text-cyan-500" />
              )}
              <span>Re-verificar Identidad (/api/auth/me)</span>
            </button>

            <button
              onClick={handleSimularError401}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 text-gray-800 dark:text-gray-200 border border-gray-200/60 dark:border-white/10 text-sm font-medium transition-all disabled:opacity-50"
              title="Comprueba que la API devuelva 401 sin token"
            >
              <ShieldAlert className="w-4 h-4 text-amber-500" />
              <span>Probar Rechazo 401</span>
            </button>

            <button
              onClick={handleLogoutAction}
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-lg bg-red-50 hover:bg-red-100 dark:bg-red-500/10 dark:hover:bg-red-500/20 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-500/20 text-sm font-medium transition-all cursor-pointer"
            >
              <LogOut className="w-4 h-4" />
              <span>Cerrar Sesión</span>
            </button>
          </div>

          {/* Connection parameters */}
          <div className="pt-4 border-t border-gray-200/60 dark:border-white/10 space-y-2 text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center justify-between">
              <span className="font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
                <Server className="w-3.5 h-3.5 text-cyan-500" />
                Backend API
              </span>
              <code className="font-mono bg-gray-100 dark:bg-white/5 px-2 py-0.5 rounded text-cyan-600 dark:text-cyan-400">
                {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}
              </code>
            </div>
            <p className="text-[11px] leading-relaxed">
              * Las solicitudes envían el token JWT en la cabecera{' '}
              <code className="font-mono text-gray-700 dark:text-gray-300">
                Authorization: Bearer &lt;token&gt;
              </code>
              . Todas las consultas de la empresa quedan aisladas en base al usuario autenticado.
            </p>
          </div>
        </motion.div>
      </div>
    );
  }

  // Form markup for both publicMode and non-publicMode
  const formContent = (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full space-y-4"
    >
      {/* Notifications */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="alert-card alert-error"
        >
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 text-red-500" />
          <div className="text-sm">{error}</div>
        </motion.div>
      )}

      {message && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="alert-card alert-success"
        >
          <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5 text-emerald-500" />
          <div className="text-sm">{message}</div>
        </motion.div>
      )}

      <form onSubmit={handleLogin} className="space-y-4">
        {/* Email Field */}
        <div className="space-y-1.5">
          <label className="input-label" htmlFor="login-email">
            Correo Electrónico
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
            <input
              id="login-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="ej: usuario@empresa.com"
              className="input-field pl-10"
              autoComplete="username"
            />
          </div>
        </div>

        {/* Password Field */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="input-label" htmlFor="login-password">
              Contraseña
            </label>
          </div>
          <div className="relative">
            <Lock className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
            <input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="input-field pl-10 pr-10"
              autoComplete="current-password"
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? 'Ocultar contraseña' : 'Ver contraseña'}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors focus:outline-none"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>
        </div>

        {/* Submit button */}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-gradient-to-r from-[#D97843] to-[#B35D2F] hover:from-[#E08A55] hover:to-[#C66532] text-white rounded-xl py-2.5 font-semibold transition-all shadow-[0_0_18px_rgba(217,120,67,0.35)] hover:shadow-[0_0_25px_rgba(217,120,67,0.5)] disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer mt-2"
        >
          {loading ? (
            <>
              <Spinner className="w-4 h-4 text-white" />
              <span>Autenticando...</span>
            </>
          ) : (
            <>
              <span>Iniciar Sesión</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>

        {/* Action for non-publicMode */}
        {!publicMode && (
          <div className="pt-2">
            <button
              type="button"
              onClick={handleVerificarIdentidad}
              disabled={loading || !authStorage.getToken()}
              className="w-full py-2 px-3 text-xs font-medium text-gray-600 dark:text-gray-400 bg-gray-100 hover:bg-gray-200 dark:bg-white/5 dark:hover:bg-white/10 rounded-lg border border-gray-200/50 dark:border-white/10 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Verificar Token Almacenado
            </button>
          </div>
        )}
      </form>

      {/* Backend connection note for non-publicMode */}
      {!publicMode && (
        <div className="mt-6 pt-5 border-t border-gray-200/60 dark:border-white/10 space-y-2 text-xs text-gray-500 dark:text-gray-400">
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1.5">
              <Server className="w-3.5 h-3.5 text-cyan-500" />
              Backend API
            </span>
            <code className="font-mono bg-gray-100 dark:bg-white/5 px-2 py-0.5 rounded text-cyan-600 dark:text-cyan-400">
              {import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}
            </code>
          </div>
          <p className="text-[11px] leading-relaxed">
            * Las solicitudes envían el token JWT en la cabecera{' '}
            <code className="font-mono text-gray-700 dark:text-gray-300">
              Authorization: Bearer &lt;token&gt;
            </code>
            . Todas las consultas quedan aisladas por empresa.
          </p>
        </div>
      )}
    </motion.div>
  );

  // If publicMode is true, render just the form without extra outer card wrapper
  if (publicMode) {
    return formContent;
  }

  // Standalone non-publicMode: full-screen centered with glass card
  return (
    <div className="min-h-[85vh] flex flex-col items-center justify-center p-4">
      <motion.div
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="backdrop-blur-3xl bg-white/85 dark:bg-[#180E09]/80 rounded-3xl shadow-[0_16px_48px_rgba(0,0,0,0.45)] border border-[#D97843]/20 dark:border-white/10 max-w-md w-full p-8"
      >
        {/* Logo at top */}
        <div className="flex flex-col items-center justify-center text-center mb-6">
          <div className="flex items-center gap-2 mb-2">
            <div className="w-4 h-4 rounded-md bg-gradient-to-br from-[#EE915B] to-[#A8542A] shadow-[0_0_12px_rgba(217,120,67,0.8)]" />
            <span className="text-2xl tracking-tight text-gray-900 dark:text-white">
              <span className="font-bold">SALES</span>
              <span className="font-light text-[#D97843]">IA</span>
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Control de Acceso y Gestión de Sesión
          </p>
        </div>

        {formContent}
      </motion.div>
    </div>
  );
};

export default LoginView;
