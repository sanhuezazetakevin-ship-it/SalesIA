import React, { useState, useEffect } from 'react';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { OperationsCloseView } from './components/OperationsCloseView';
import { EnterpriseSettingsView } from './components/EnterpriseSettingsView';
import { IntelligenceView } from './components/IntelligenceView';
import { PurchasesView } from './components/PurchasesView';
import { LoginView } from './components/LoginView';
import { DashboardView } from './components/DashboardView';
import { ManagementView } from './components/ManagementView';
import { CommercialView } from './components/CommercialView';
import { AnalyticsView } from './components/AnalyticsView';
import { UsersManagementView } from './components/UsersManagementView';
import { InvitationRegistrationView } from './components/InvitationRegistrationView';
import { CommercialTestingView } from './components/CommercialTestingView';
import { ReportsView } from './components/ReportsView';
import { api, authStorage } from './services/api';
import { User } from './types/api';
import { PublicSite, CompanyRegistration } from './components/PublicSite';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<string>('inicio');
  const [verificandoSesion, setVerificandoSesion] = useState(true);
  const [theme, setTheme] = useState<'light' | 'dark'>(() =>
    localStorage.getItem('salesia_theme') === 'light' ? 'light' : 'dark'
  );

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('salesia_theme', theme);
  }, [theme]);

  useEffect(() => {
    const token = authStorage.getToken();
    if (token) {
      api
        .getMe()
        .then((u) => {
          setUser(u);
          setActiveTab('dashboard');
        })
        .catch(() => {
          authStorage.clear();
          setUser(null);
        })
        .finally(() => {
          setVerificandoSesion(false);
        });
    } else {
      setVerificandoSesion(false);
    }
  }, []);

  const handleLoginSuccess = (usuario: User) => {
    setUser(usuario);
    setActiveTab('dashboard');
  };

  const handleLogout = async () => {
    await api.logout();
    setUser(null);
    setActiveTab('inicio');
  };

  if (verificandoSesion) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-gray-50 dark:bg-[#0A0A0F] gap-3">
        <div className="w-10 h-10 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs uppercase tracking-widest text-gray-500 font-semibold">
          Iniciando entorno SalesIA Enterprise...
        </p>
      </div>
    );
  }

  if (!user) {
    const publicPage =
      activeTab === 'auth'
        ? 'login'
        : activeTab === 'registro'
        ? 'invitacion'
        : activeTab === 'empresa'
        ? 'empresa'
        : 'inicio';

    const navigate = (page: 'inicio' | 'login' | 'empresa' | 'invitacion') =>
      setActiveTab(page === 'login' ? 'auth' : page === 'invitacion' ? 'registro' : page);

    return (
      <PublicSite
        page={publicPage}
        navigate={navigate}
        theme={theme}
        toggleTheme={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
      >
        {publicPage === 'login' && (
          <div className="public-form-card">
            <span className="public-form-kicker">ACCESO EMPRESARIAL</span>
            <h2>Inicia sesión</h2>
            <p>Accede con las credenciales autorizadas de tu organización.</p>
            <LoginView
              publicMode
              user={null}
              onLoginSuccess={handleLoginSuccess}
              onLogout={handleLogout}
            />
            <div className="public-form-bottom">
              ¿Tu empresa aún no está registrada?{' '}
              <button onClick={() => navigate('empresa')}>Solicitar alta</button>
            </div>
            <div className="public-form-bottom">
              ¿Recibiste una invitación?{' '}
              <button onClick={() => navigate('invitacion')}>Registrarme con invitación</button>
            </div>
          </div>
        )}
        {publicPage === 'empresa' && <CompanyRegistration goLogin={() => navigate('login')} />}
        {publicPage === 'invitacion' && (
          <div className="public-form-card">
            <InvitationRegistrationView />
            <div className="public-form-bottom">
              <button onClick={() => navigate('login')}>Volver al acceso</button>
            </div>
          </div>
        )}
      </PublicSite>
    );
  }

  return (
    <DashboardLayout
      activeTab={activeTab}
      onSelectTab={setActiveTab}
      user={user}
      onLogout={handleLogout}
      theme={theme}
      onToggleTheme={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
    >
      {activeTab === 'dashboard' && <DashboardView />}
      {activeTab === 'comercial' && <CommercialView />}
      {activeTab === 'gestion' && <ManagementView />}
      {activeTab === 'operaciones-cierre' && <OperationsCloseView />}
      {activeTab === 'compras' && <PurchasesView />}
      {activeTab === 'inteligencia' && <IntelligenceView />}
      {activeTab === 'analytics' && <AnalyticsView />}
      {activeTab === 'reportes' && <ReportsView />}
      {activeTab === 'usuarios' && <UsersManagementView />}
      {activeTab === 'configuracion' && <EnterpriseSettingsView user={user} />}
      {activeTab === 'comercial-fase3' && <CommercialTestingView />}
    </DashboardLayout>
  );
};

export default App;
