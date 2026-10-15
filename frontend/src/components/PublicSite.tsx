import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Play,
  BarChart3,
  Users,
  Package,
  Shield,
  Activity,
  Sun,
  Moon,
  ArrowRight,
  ArrowUpRight,
  CheckCircle2,
  AlertCircle,
  Building2,
  Phone,
  User,
  Mail,
  Loader2,
  Check,
  TrendingUp,
  Lock,
} from 'lucide-react';

export type Page = 'inicio' | 'login' | 'empresa' | 'invitacion';

export interface Props {
  page: Page;
  navigate: (page: Page) => void;
  theme: 'light' | 'dark';
  toggleTheme: () => void;
  children?: React.ReactNode;
}

interface FeatureItem {
  icon: React.ElementType;
  title: string;
  desc: string;
}

const features: FeatureItem[] = [
  {
    icon: BarChart3,
    title: 'Visibilidad comercial',
    desc: 'Indicadores de ventas, evolución temporal y desempeño en una sola vista.',
  },
  {
    icon: Package,
    title: 'Operación conectada',
    desc: 'Clientes, productos, pedidos, pagos, inventario y proveedores sincronizados.',
  },
  {
    icon: Activity,
    title: 'Análisis inteligente',
    desc: 'Estadística, segmentación comercial e insights avanzados basados en datos.',
  },
  {
    icon: Play,
    title: 'Reportes ejecutivos',
    desc: 'Informes y exportaciones para interpretar resultados estratégicos de negocio.',
  },
  {
    icon: Shield,
    title: 'Empresas independientes',
    desc: 'Separación estricta de información empresarial mediante permisos y accesos.',
  },
  {
    icon: Users,
    title: 'Trazabilidad y Roles',
    desc: 'Historial de actividades, roles granulares y registro de operaciones críticas.',
  },
];

export const CompanyRegistration: React.FC<{ goLogin: () => void }> = ({ goLogin }) => {
  const [form, setForm] = useState({
    razon_social: '',
    ruc: '',
    nombre_contacto: '',
    email_contacto: '',
    telefono: '',
    sitio_web: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState(false);

  const update = (key: keyof typeof form, value: string) =>
    setForm((s) => ({ ...s, [key]: value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      const response = await fetch(`${base}/api/publico/solicitudes-empresa`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });

      if (!response.ok) {
        const json = await response.json().catch(() => ({}));
        throw new Error(
          typeof json.detail === 'string'
            ? json.detail
            : 'No fue posible enviar la solicitud. Verifica los datos.'
        );
      }
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  if (done) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
        className="backdrop-blur-xl bg-white/90 dark:bg-[#12121A]/90 p-8 rounded-2xl shadow-2xl border border-emerald-500/30 text-center space-y-4 max-w-md w-full"
        role="status"
      >
        <div className="w-14 h-14 mx-auto rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 flex items-center justify-center">
          <CheckCircle2 className="w-8 h-8" />
        </div>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Solicitud recibida
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
          El registro de tu empresa está{' '}
          <strong className="text-gray-900 dark:text-white">pendiente de revisión</strong>. No se crea una sesión ni una cuenta administradora automáticamente.
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400 leading-relaxed">
          El responsable de SalesIA deberá confirmar el alta y comunicarte los siguientes pasos de incorporación.
        </p>
        <button
          onClick={goLogin}
          className="w-full mt-4 bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2.5 font-medium transition-all shadow-md flex items-center justify-center gap-2 cursor-pointer"
        >
          <span>Ir a iniciar sesión</span>
          <ArrowRight className="w-4 h-4" />
        </button>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="backdrop-blur-xl bg-white/90 dark:bg-[#12121A]/90 p-8 rounded-2xl shadow-2xl border border-gray-200/50 dark:border-white/10 space-y-5 max-w-md w-full"
    >
      <div>
        <span className="text-xs font-bold tracking-wider text-cyan-500 uppercase block mb-1">
          ALTA DE ORGANIZACIÓN
        </span>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
          Registra tu empresa
        </h2>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
          Envíanos los datos de tu organización para revisar su incorporación a SalesIA.
        </p>
      </div>

      {error && (
        <motion.div
          initial={{ opacity: 0, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          className="alert-card alert-error"
          role="alert"
        >
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-red-500" />
          <span className="text-sm">{error}</span>
        </motion.div>
      )}

      <form onSubmit={submit} className="space-y-4">
        {/* Razon Social */}
        <div className="space-y-1.5">
          <label className="input-label" htmlFor="reg-razon-social">
            Razón Social
          </label>
          <div className="relative">
            <Building2 className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
            <input
              id="reg-razon-social"
              required
              maxLength={200}
              minLength={3}
              value={form.razon_social}
              onChange={(e) => update('razon_social', e.target.value)}
              placeholder="Nombre legal de la empresa"
              className="input-field pl-10"
            />
          </div>
        </div>

        {/* RUC & Telefono */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="input-label" htmlFor="reg-ruc">
              RUC (11 dígitos)
            </label>
            <input
              id="reg-ruc"
              required
              inputMode="numeric"
              pattern="[0-9]{11}"
              maxLength={11}
              value={form.ruc}
              onChange={(e) => update('ruc', e.target.value.replace(/\D/g, ''))}
              placeholder="20XXXXXXXXX"
              className="input-field"
            />
          </div>
          <div className="space-y-1.5">
            <label className="input-label" htmlFor="reg-tel">
              Teléfono (opcional)
            </label>
            <div className="relative">
              <Phone className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
              <input
                id="reg-tel"
                maxLength={25}
                value={form.telefono}
                onChange={(e) => update('telefono', e.target.value)}
                placeholder="Teléfono"
                className="input-field pl-10"
              />
            </div>
          </div>
        </div>

        {/* Responsable */}
        <div className="space-y-1.5">
          <label className="input-label" htmlFor="reg-contacto">
            Responsable de la solicitud
          </label>
          <div className="relative">
            <User className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
            <input
              id="reg-contacto"
              required
              minLength={2}
              maxLength={120}
              value={form.nombre_contacto}
              onChange={(e) => update('nombre_contacto', e.target.value)}
              placeholder="Nombre y apellido"
              className="input-field pl-10"
            />
          </div>
        </div>

        {/* Email Corporativo */}
        <div className="space-y-1.5">
          <label className="input-label" htmlFor="reg-email">
            Correo corporativo
          </label>
          <div className="relative">
            <Mail className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 dark:text-gray-500 pointer-events-none" />
            <input
              id="reg-email"
              required
              type="email"
              value={form.email_contacto}
              onChange={(e) => update('email_contacto', e.target.value)}
              placeholder="contacto@empresa.com"
              className="input-field pl-10"
            />
          </div>
        </div>

        {/* Honeypot hidden field */}
        <div className="hidden" aria-hidden="true">
          <label>
            Sitio web
            <input
              tabIndex={-1}
              autoComplete="off"
              value={form.sitio_web}
              onChange={(e) => update('sitio_web', e.target.value)}
            />
          </label>
        </div>

        <p className="text-[11px] text-gray-500 dark:text-gray-400 leading-relaxed pt-1">
          El envío constituye una solicitud de evaluación. No habilita acceso automático. No ingreses contraseñas en este formulario.
        </p>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg py-2.5 font-medium transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 cursor-pointer mt-2"
        >
          {loading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin text-white" />
              <span>Enviando solicitud…</span>
            </>
          ) : (
            <>
              <span>Solicitar registro empresarial</span>
              <ArrowRight className="w-4 h-4" />
            </>
          )}
        </button>
      </form>

      <div className="text-center text-xs text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200/50 dark:border-white/10">
        ¿Ya tienes una cuenta?{' '}
        <button
          type="button"
          onClick={goLogin}
          className="text-cyan-500 hover:text-cyan-400 font-semibold underline-offset-2 hover:underline ml-1"
        >
          Inicia sesión
        </button>
      </div>
    </motion.div>
  );
};

export const PublicSite: React.FC<Props> = ({
  page,
  navigate,
  theme,
  toggleTheme,
  children,
}) => {
  // Sync dark class on document element with theme state
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const scrollToFeatures = () => {
    if (page !== 'inicio') {
      navigate('inicio');
      setTimeout(() => {
        document.getElementById('funciones')?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } else {
      document.getElementById('funciones')?.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#F8F4EF] text-[#24150E] dark:bg-[#0D0806] dark:text-[#FAF5F0] transition-colors duration-300 relative overflow-hidden">
      {/* Background Vitromorfosis 3D organic fluid background */}
      <div aria-hidden="true" className="vitromorphism-bg" />

      {/* Navigation bar: sticky top, glass effect */}
      <header className="sticky top-0 z-50 backdrop-blur-2xl bg-[#F8F4EF]/85 dark:bg-[#0E0907]/85 border-b border-[#D97843]/15 dark:border-white/10 transition-colors">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo left */}
          <button
            onClick={() => navigate('inicio')}
            className="flex items-center gap-2.5 text-left focus:outline-none group cursor-pointer"
          >
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-[#EE915B] via-[#D97843] to-[#8A4522] shadow-[0_0_15px_rgba(217,120,67,0.4)] flex items-center justify-center text-white font-extrabold text-sm">
              S
            </div>
            <div className="flex flex-col">
              <span className="text-xl leading-none tracking-tight text-[#24150E] dark:text-white">
                <span className="font-extrabold">SALES</span>
                <span className="font-light text-[#D97843] dark:text-[#EE915B]">IA</span>
              </span>
              <span className="text-[9px] tracking-widest text-[#8C776D] dark:text-[#BAA89E] font-bold uppercase">
                ENTERPRISE
              </span>
            </div>
          </button>

          {/* Nav buttons center */}
          <nav
            aria-label="Navegación pública"
            className="hidden md:flex items-center gap-1 bg-[#EFE5DB]/70 dark:bg-[#140C08]/80 p-1 rounded-xl border border-[#D97843]/15 dark:border-white/10 backdrop-blur-lg"
          >
            <button
              onClick={() => navigate('inicio')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                page === 'inicio'
                  ? 'bg-white dark:bg-gradient-to-r dark:from-[#D97843]/25 dark:to-[#A8542A]/25 text-[#C66532] dark:text-[#EE915B] font-semibold shadow-sm'
                  : 'text-[#5E4A40] dark:text-[#BAA89E] hover:text-[#24150E] dark:hover:text-white'
              }`}
            >
              Inicio
            </button>
            <button
              onClick={scrollToFeatures}
              className="px-4 py-1.5 rounded-lg text-sm font-medium text-[#5E4A40] dark:text-[#BAA89E] hover:text-[#24150E] dark:hover:text-white transition-all cursor-pointer"
            >
              Funcionalidades
            </button>
            <button
              onClick={() => navigate('empresa')}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                page === 'empresa'
                  ? 'bg-white dark:bg-gradient-to-r dark:from-[#D97843]/25 dark:to-[#A8542A]/25 text-[#C66532] dark:text-[#EE915B] font-semibold shadow-sm'
                  : 'text-[#5E4A40] dark:text-[#BAA89E] hover:text-[#24150E] dark:hover:text-white'
              }`}
            >
              Registrar empresa
            </button>
          </nav>

          {/* Theme toggle + 'Iniciar sesión' button right */}
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={toggleTheme}
              aria-label={theme === 'light' ? 'Cambiar a modo oscuro' : 'Cambiar a modo claro'}
              title={theme === 'light' ? 'Cambiar a modo oscuro' : 'Cambiar a modo claro'}
              className="p-2 rounded-xl text-[#5E4A40] dark:text-[#BAA89E] bg-white/70 dark:bg-white/5 border border-[#D97843]/20 dark:border-white/10 hover:bg-[#D97843]/15 dark:hover:bg-white/10 transition-colors cursor-pointer"
            >
              {theme === 'light' ? (
                <Moon className="w-4 h-4 text-[#8A4522]" />
              ) : (
                <Sun className="w-4 h-4 text-[#EE915B]" />
              )}
            </button>

            <button
              type="button"
              onClick={() => navigate('login')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-semibold bg-gradient-to-r from-[#D97843] to-[#B35D2F] hover:from-[#E08A55] hover:to-[#C66532] text-white shadow-[0_0_18px_rgba(217,120,67,0.35)] transition-all cursor-pointer"
            >
              <span>Iniciar sesión</span>
              <ArrowUpRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 relative z-10">
        {page === 'inicio' ? (
          <>
            {/* Hero section */}
            <section className="relative pt-12 pb-20 lg:pt-20 lg:pb-28">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
                  {/* Hero Copy */}
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                    className="lg:col-span-7 space-y-6 text-left"
                  >
                    {/* Eyebrow badge */}
                    <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-semibold bg-[#D97843]/12 text-[#D97843] dark:text-[#EE915B] border border-[#D97843]/25 shadow-[0_0_12px_rgba(217,120,67,0.15)]">
                      <span className="w-2 h-2 rounded-full bg-[#D97843] dark:bg-[#EE915B] animate-pulse" />
                      SOFTWARE DE GESTIÓN EMPRESARIAL
                    </div>

                    {/* Headline */}
                    <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-[#24150E] dark:text-white leading-[1.1]">
                      Controla tus operaciones.
                      <span className="text-gradient block mt-1">Decide con datos.</span>
                    </h1>

                    {/* Subtitle */}
                    <p className="text-lg sm:text-xl text-[#5E4A40] dark:text-[#BAA89E] max-w-2xl leading-relaxed">
                      Conecta ventas, inventario, clientes y análisis comercial en una plataforma diseñada para dar claridad a tu negocio.
                    </p>

                    {/* CTA Actions */}
                    <div className="flex flex-wrap items-center gap-4 pt-2">
                      <button
                        onClick={() => navigate('empresa')}
                        className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-semibold bg-gradient-to-r from-[#D97843] to-[#B35D2F] hover:from-[#E08A55] hover:to-[#C66532] text-white shadow-[0_0_20px_rgba(217,120,67,0.35)] transition-all text-base cursor-pointer"
                      >
                        <span>Registrar mi empresa</span>
                        <ArrowRight className="w-4 h-4" />
                      </button>

                      <button
                        onClick={() => navigate('login')}
                        className="inline-flex items-center justify-center px-6 py-3 rounded-xl font-semibold text-[#24150E] dark:text-[#FAF5F0] bg-white/70 hover:bg-white/90 dark:bg-white/5 dark:hover:bg-white/10 border border-[#D97843]/20 dark:border-white/10 transition-all text-base cursor-pointer shadow-sm"
                      >
                        Ya tengo una cuenta
                      </button>
                    </div>

                    {/* Trust badges below */}
                    <div className="pt-6 border-t border-gray-200/60 dark:border-white/10 flex flex-wrap gap-6 text-xs font-medium text-gray-600 dark:text-gray-400">
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-500" />
                        <span>Gestión multiempresa</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-500" />
                        <span>Accesos por rol</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Check className="w-4 h-4 text-emerald-500" />
                        <span>Analítica integrada</span>
                      </div>
                    </div>
                  </motion.div>

                  {/* Hero Visual Card */}
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5, delay: 0.15 }}
                    className="lg:col-span-5"
                    aria-label="Vista ilustrativa de análisis"
                  >
                    <div className="glass-strong p-6 rounded-2xl shadow-2xl border border-cyan-500/30 relative overflow-hidden group">
                      {/* Top bar */}
                      <div className="flex items-center justify-between pb-4 border-b border-gray-200/50 dark:border-white/10">
                        <div className="flex items-center gap-2">
                          <span className="w-2.5 h-2.5 rounded-full bg-cyan-500 shadow-[0_0_8px_rgba(6,182,212,0.8)]" />
                          <span className="text-xs font-mono font-semibold tracking-wider text-gray-800 dark:text-gray-200">
                            SALESIA / ANALÍTICA
                          </span>
                        </div>
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-500/10 text-cyan-600 dark:text-cyan-400 border border-cyan-500/20">
                          Resumen general
                        </span>
                      </div>

                      {/* Metric banner */}
                      <div className="py-5 flex items-start justify-between">
                        <div>
                          <small className="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider block">
                            Visión comercial
                          </small>
                          <strong className="text-xl font-bold text-gray-900 dark:text-white block mt-0.5">
                            Decisiones informadas
                          </strong>
                          <span className="text-xs text-gray-500 dark:text-gray-400 mt-1 block">
                            Visualiza el movimiento de tu negocio
                          </span>
                        </div>
                        <div className="w-10 h-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-500">
                          <TrendingUp className="w-5 h-5" />
                        </div>
                      </div>

                      {/* Dynamic Preview Bars */}
                      <div
                        className="h-32 flex items-end gap-2.5 pt-4 pb-2 px-1 border-b border-gray-200/50 dark:border-white/10"
                        aria-hidden="true"
                      >
                        {[40, 53, 47, 72, 62, 80, 76, 94, 85, 99].map((val, idx) => (
                          <div
                            key={idx}
                            className="flex-1 bg-gradient-to-t from-cyan-500 to-blue-600 rounded-t-sm opacity-85 hover:opacity-100 transition-opacity"
                            style={{ height: `${val}%` }}
                          />
                        ))}
                      </div>

                      {/* Bottom tags */}
                      <div className="pt-4 flex items-center justify-between text-[11px] font-semibold tracking-wider text-gray-500 dark:text-gray-400">
                        <span className="text-cyan-600 dark:text-cyan-400">VENTAS</span>
                        <span>INVENTARIO</span>
                        <span>CLIENTES</span>
                      </div>
                    </div>
                  </motion.div>
                </div>
              </div>
            </section>

            {/* Features section: 6 feature cards in 3-column grid */}
            <section
              id="funciones"
              className="py-20 border-t border-gray-200/60 dark:border-white/10 scroll-mt-16"
            >
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                {/* Section intro */}
                <motion.div
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4 }}
                  className="text-center max-w-3xl mx-auto mb-16 space-y-3"
                >
                  <span className="text-xs font-extrabold tracking-widest text-[#D97843] dark:text-[#FFA675] uppercase">
                    UNA PLATAFORMA, MÁS CONTROL
                  </span>
                  <h2 className="text-3xl sm:text-4xl font-black text-slate-950 dark:text-white drop-shadow-sm">
                    Lo que necesitas para gestionar mejor
                  </h2>
                  <p className="text-base text-slate-700 dark:text-slate-200 font-medium">
                    Herramientas conectadas para organizar el trabajo diario y convertir la información en oportunidades comerciales reales.
                  </p>
                </motion.div>

                {/* Features 3-column grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {features.map((feature, i) => {
                    const IconComponent = feature.icon;
                    return (
                      <motion.article
                        key={feature.title}
                        initial={{ opacity: 0, y: 15 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.4, delay: i * 0.08 }}
                        className="glass p-6 rounded-xl hover:border-[#D97843]/40 hover:shadow-glow transition-all duration-300 group flex flex-col justify-between"
                      >
                        <div>
                          <div className="w-12 h-12 rounded-lg bg-[#D97843]/10 border border-[#D97843]/20 text-[#D97843] dark:text-[#FFA675] flex items-center justify-center mb-4 group-hover:scale-105 group-hover:bg-[#D97843]/20 transition-all">
                            <IconComponent className="w-6 h-6" />
                          </div>
                          <h3 className="text-lg font-black text-slate-950 dark:text-white mb-2 drop-shadow-sm">
                            {feature.title}
                          </h3>
                          <p className="text-sm text-slate-600 dark:text-slate-300 font-medium leading-relaxed">
                            {feature.desc}
                          </p>
                        </div>
                      </motion.article>
                    );
                  })}
                </div>
              </div>
            </section>

            {/* Bottom CTA section */}
            <section className="py-20">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <motion.div
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4 }}
                  className="glass-strong rounded-2xl p-8 sm:p-12 border border-[#D97843]/30 relative overflow-hidden flex flex-col md:flex-row items-center justify-between gap-8 text-center md:text-left"
                >
                  <div className="space-y-2 max-w-2xl">
                    <h2 className="text-2xl sm:text-3xl font-black text-slate-950 dark:text-white drop-shadow-sm">
                      Tu empresa, tu información, tus decisiones.
                    </h2>
                    <p className="text-sm sm:text-base text-slate-700 dark:text-slate-200 font-medium">
                      Solicita el registro de tu organización y comienza el proceso de incorporación con SalesIA Enterprise.
                    </p>
                  </div>
                  <button
                    onClick={() => navigate('empresa')}
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-lg font-medium bg-blue-600 hover:bg-blue-700 active:bg-blue-800 text-white shadow-lg hover:shadow-cyan-500/30 transition-all text-base flex-shrink-0 cursor-pointer"
                  >
                    <span>Solicitar incorporación</span>
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </motion.div>
              </div>
            </section>
          </>
        ) : (
          /* Auth layout (for login / register / empresa pages): Two-column layout */
          <div className="min-h-[calc(100vh-4rem)] flex flex-col lg:flex-row">
            {/* Left info panel: dark gradient bg */}
            <motion.div
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4 }}
              className="bg-gradient-to-br from-[#0A0A0F] via-[#12121A] to-[#1e1b4b] text-white p-8 lg:p-14 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-white/10 lg:w-5/12 min-h-[400px] relative overflow-hidden"
            >
              {/* Background ambient glow */}
              <div className="absolute -bottom-20 -left-20 w-80 h-80 bg-cyan-500/10 blur-3xl rounded-full pointer-events-none" />

              {/* Brand Top */}
              <div>
                <button
                  onClick={() => navigate('inicio')}
                  className="flex items-center gap-2.5 text-left mb-8 cursor-pointer focus:outline-none"
                >
                  <div className="w-8 h-8 rounded-lg bg-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.5)] flex items-center justify-center text-white font-bold text-sm">
                    S
                  </div>
                  <div>
                    <span className="text-lg font-bold text-white tracking-tight">SALES</span>
                    <span className="text-lg font-light text-cyan-400 tracking-tight">IA</span>
                  </div>
                </button>
              </div>

              {/* Center message */}
              <div className="space-y-4 my-8">
                <span className="text-xs font-bold tracking-widest text-cyan-400 uppercase block">
                  SALESIA ENTERPRISE
                </span>
                <h2 className="text-3xl sm:text-4xl font-extrabold text-white leading-tight">
                  {page === 'login'
                    ? 'Bienvenido de nuevo.'
                    : page === 'empresa'
                    ? 'Da el primer paso hacia una gestión más clara.'
                    : 'Tu invitación empresarial.'}
                </h2>
                <p className="text-gray-300 text-sm leading-relaxed max-w-md">
                  Una plataforma con operaciones conectadas, información organizada y análisis para decisiones comerciales de alto nivel.
                </p>

                {/* Highlights */}
                <div className="pt-6 space-y-3">
                  <div className="flex items-center gap-3 text-xs text-gray-300">
                    <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-cyan-400">
                      <BarChart3 className="w-4 h-4" />
                    </div>
                    <span>Ventas, cotizaciones y pedidos en tiempo real</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-300">
                    <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-cyan-400">
                      <Package className="w-4 h-4" />
                    </div>
                    <span>Inventario y catálogo de productos sincronizado</span>
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-300">
                    <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center text-cyan-400">
                      <Shield className="w-4 h-4" />
                    </div>
                    <span>Aislamiento seguro multiempresa y permisos por rol</span>
                  </div>
                </div>
              </div>

              {/* Bottom badge */}
              <div className="pt-6 border-t border-white/10 flex items-center gap-2 text-xs text-gray-400">
                <Lock className="w-3.5 h-3.5 text-cyan-400" />
                <span>Entorno protegido con autenticación JWT y roles granulares</span>
              </div>
            </motion.div>

            {/* Right form panel */}
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4 }}
              className="flex-1 flex items-center justify-center p-6 lg:p-12"
            >
              <div className="w-full max-w-md [&_.public-form-card]:backdrop-blur-xl [&_.public-form-card]:bg-white/90 [&_.public-form-card]:dark:bg-[#12121A]/90 [&_.public-form-card]:p-8 [&_.public-form-card]:rounded-2xl [&_.public-form-card]:shadow-2xl [&_.public-form-card]:border [&_.public-form-card]:border-gray-200/50 [&_.public-form-card]:dark:border-white/10 [&_.public-form-card]:space-y-4 [&_.public-form-kicker]:text-xs [&_.public-form-kicker]:font-bold [&_.public-form-kicker]:tracking-wider [&_.public-form-kicker]:text-cyan-500 [&_.public-form-kicker]:uppercase [&_.public-form-kicker]:block [&_.public-form-card_h2]:text-2xl [&_.public-form-card_h2]:font-bold [&_.public-form-card_h2]:text-gray-900 [&_.public-form-card_h2]:dark:text-white [&_.public-form-card_p]:text-sm [&_.public-form-card_p]:text-gray-600 [&_.public-form-card_p]:dark:text-gray-400 [&_.public-form-bottom]:text-xs [&_.public-form-bottom]:text-gray-500 [&_.public-form-bottom]:dark:text-gray-400 [&_.public-form-bottom]:pt-1 [&_.public-form-bottom_button]:text-cyan-500 [&_.public-form-bottom_button]:font-medium [&_.public-form-bottom_button]:hover:text-cyan-400 [&_.public-form-bottom_button]:ml-1.5 [&_.public-form-bottom_button]:underline-offset-2 [&_.public-form-bottom_button]:hover:underline [&_.section-box]:space-y-4 [&_.section-title]:text-xl [&_.section-title]:font-bold [&_.section-title]:text-gray-900 [&_.section-title]:dark:text-white [&_.form-group]:space-y-1.5 [&_.form-group_label]:input-label [&_.form-group_input]:input-field [&_.btn-primary]:w-full [&_.btn-primary]:bg-blue-600 [&_.btn-primary]:hover:bg-blue-700 [&_.btn-primary]:text-white [&_.btn-primary]:rounded-lg [&_.btn-primary]:py-2.5 [&_.btn-primary]:font-medium [&_.btn-primary]:transition-all [&_.btn-primary]:cursor-pointer">
                {children}
              </div>
            </motion.div>
          </div>
        )}
      </main>

      {/* Footer: simple centered */}
      <footer className="border-t border-gray-200/60 dark:border-white/10 py-6 text-center text-xs text-gray-500 dark:text-gray-400 relative z-10 transition-colors">
        <div className="max-w-7xl mx-auto px-4 space-y-1">
          <p>© {new Date().getFullYear()} SalesIA Enterprise. Todos los derechos reservados.</p>
          <p className="text-[11px] text-gray-400 dark:text-gray-500">
            Plataforma de gestión empresarial multiempresa · Versión de demostración
          </p>
        </div>
      </footer>
    </div>
  );
};

export default PublicSite;
