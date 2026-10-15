import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  KeyRound,
  User,
  Mail,
  Lock,
  Eye,
  EyeOff,
  UserCheck,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Shield,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';
import { api } from '../services/api';

export const InvitationRegistrationView: React.FC = () => {
  const [token, setToken] = useState('');
  const [nombre, setNombre] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmacion, setConfirmacion] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const registrar = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (token.trim().length !== 43) {
      setError('El token de invitación debe tener exactamente 43 caracteres.');
      return;
    }

    if (password !== confirmacion) {
      setError('Las contraseñas no coinciden. Por favor verifícalas.');
      return;
    }

    if (password.length < 12) {
      setError('La contraseña debe contener al menos 12 caracteres de longitud por seguridad corporativa.');
      return;
    }

    setLoading(true);
    try {
      const result = await api.registrarInvitado({
        token: token.trim(),
        nombre: nombre.trim(),
        email: email.trim(),
        password,
      });
      setMessage(
        `Registro completado exitosamente con estado: ${result.estado}. Tu cuenta ha sido creada y quedará activa tras la aprobación administrativa de tu empresa.`
      );
      setToken('');
      setPassword('');
      setConfirmacion('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No fue posible completar el registro.');
    } finally {
      setLoading(false);
    }
  };

  const passwordsMatch = password.length > 0 && password === confirmacion;

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="max-w-xl mx-auto py-6"
    >
      <div className="glass p-8 space-y-6 shadow-glass relative overflow-hidden">
        {/* Glow accent */}
        <div className="absolute top-0 right-0 w-48 h-48 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />

        {/* Header */}
        <div className="text-center space-y-2 pb-2 border-b border-gray-100 dark:border-white/5">
          <div className="inline-flex p-3 rounded-2xl bg-cyan-500/10 text-cyan-500 border border-cyan-500/20 mb-1">
            <KeyRound className="h-6 w-6" />
          </div>
          <h2 className="text-2xl font-black tracking-tight text-slate-950 dark:text-white drop-shadow-sm">
            Registro por Invitación
          </h2>
          <p className="text-xs text-slate-700 dark:text-slate-200 font-medium max-w-sm mx-auto">
            Introduce el token exclusivo de 43 caracteres otorgado por tu administrador empresarial para crear tu credencial de acceso en SalesIA.
          </p>
        </div>

        {/* Alerts */}
        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="alert-card alert-error"
              role="alert"
            >
              <AlertCircle className="h-5 w-5 shrink-0 text-red-500" />
              <div className="flex-1 text-sm font-medium">{error}</div>
              <button
                type="button"
                onClick={() => setError('')}
                className="text-red-400 hover:text-red-600 dark:hover:text-red-300"
              >
                <XCircle className="h-4 w-4" />
              </button>
            </motion.div>
          )}

          {message && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="alert-card alert-success"
              role="status"
            >
              <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
              <div className="flex-1 text-sm font-medium leading-relaxed">{message}</div>
              <button
                type="button"
                onClick={() => setMessage('')}
                className="text-emerald-400 hover:text-emerald-600 dark:hover:text-emerald-300"
              >
                <XCircle className="h-4 w-4" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Form */}
        <form onSubmit={registrar} className="space-y-4">
          {/* Token Field */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label htmlFor="reg-token" className="input-label mb-0">
                Token de Invitación (43 caracteres) *
              </label>
              <span
                className={`text-[11px] font-mono ${
                  token.length === 43
                    ? 'text-emerald-600 dark:text-emerald-400 font-semibold'
                    : 'text-gray-400'
                }`}
              >
                {token.length}/43
              </span>
            </div>
            <div className="relative">
              <KeyRound className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
              <input
                id="reg-token"
                required
                minLength={43}
                maxLength={43}
                autoComplete="off"
                className="input-field pl-10 font-mono text-xs"
                placeholder="Pega aquí el token alfanumérico generado"
                value={token}
                onChange={(e) => setToken(e.target.value)}
              />
            </div>
          </div>

          {/* Name Field */}
          <div>
            <label htmlFor="reg-name" className="input-label">
              Nombre Completo *
            </label>
            <div className="relative">
              <User className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
              <input
                id="reg-name"
                required
                minLength={2}
                maxLength={120}
                className="input-field pl-10"
                placeholder="Ej. Carlos Mendoza"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
              />
            </div>
          </div>

          {/* Email Field */}
          <div>
            <label htmlFor="reg-email" className="input-label">
              Correo Electrónico del Invitado *
            </label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
              <input
                id="reg-email"
                type="email"
                required
                className="input-field pl-10"
                placeholder="carlos.mendoza@empresa.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          {/* Password Field */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label htmlFor="reg-password" className="input-label mb-0">
                Contraseña Segura (mínimo 12 caracteres) *
              </label>
              <span className="text-[11px] text-gray-400">Min. 12 carac.</span>
            </div>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
              <input
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                required
                minLength={12}
                maxLength={128}
                autoComplete="new-password"
                className="input-field pl-10 pr-10"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3.5 top-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Confirm Password Field */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label htmlFor="reg-password-confirm" className="input-label mb-0">
                Confirmar Contraseña *
              </label>
              {passwordsMatch && (
                <span className="text-[11px] text-emerald-600 dark:text-emerald-400 flex items-center gap-1 font-medium">
                  <CheckCircle2 className="h-3 w-3" /> Coinciden
                </span>
              )}
            </div>
            <div className="relative">
              <Lock className="absolute left-3.5 top-3 h-4 w-4 text-gray-400" />
              <input
                id="reg-password-confirm"
                type={showConfirm ? 'text' : 'password'}
                required
                className="input-field pl-10 pr-10"
                placeholder="Repite la contraseña"
                value={confirmacion}
                onChange={(e) => setConfirmacion(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowConfirm(!showConfirm)}
                className="absolute right-3.5 top-3 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                {showConfirm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Notice */}
          <div className="flex items-start gap-2 p-3 rounded-lg bg-gray-50/70 dark:bg-white/[0.02] border border-gray-200 dark:border-white/10 text-xs text-gray-500 dark:text-gray-400">
            <Shield className="h-4 w-4 text-cyan-500 shrink-0 mt-0.5" />
            <span>
              Por directiva de seguridad, la cuenta permanecerá inactiva hasta que el administrador de la empresa confirme la solicitud.
            </span>
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full inline-flex items-center justify-center gap-2 py-3 px-4 rounded-lg text-sm font-semibold text-white bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 shadow-[0_0_15px_rgba(6,182,212,0.3)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed mt-2"
          >
            {loading ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin" />
                Registrando cuenta...
              </>
            ) : (
              <>
                <UserCheck className="h-4 w-4" />
                Completar Registro
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </motion.div>
  );
};
