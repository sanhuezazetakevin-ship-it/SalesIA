import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
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
  const [theme, setTheme] = useState<'light' | 'dark'>(() => localStorage.getItem('salesia_theme') === 'dark' ? 'dark' : 'light');
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => { document.documentElement.setAttribute('data-theme', theme); localStorage.setItem('salesia_theme', theme); }, [theme]);

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
      <div className="container" style={{ paddingTop: '3rem', textAlign: 'center' }}>
        <p>Iniciando entorno SalesIA Enterprise...</p>
      </div>
    );
  }

  if (!user) {
    const publicPage = activeTab === 'auth' ? 'login' : activeTab === 'registro' ? 'invitacion' : activeTab === 'empresa' ? 'empresa' : 'inicio';
    const navigate = (page: 'inicio' | 'login' | 'empresa' | 'invitacion') => setActiveTab(page === 'login' ? 'auth' : page === 'invitacion' ? 'registro' : page);
    return <PublicSite page={publicPage} navigate={navigate} theme={theme} toggleTheme={() => setTheme(t => t === 'light' ? 'dark' : 'light')}>
      {publicPage === 'login' && <div className="public-form-card"><span className="public-form-kicker">ACCESO EMPRESARIAL</span><h2>Inicia sesión</h2><p>Accede con las credenciales autorizadas de tu organización.</p><LoginView publicMode user={null} onLoginSuccess={handleLoginSuccess} onLogout={handleLogout}/><div className="public-form-bottom">¿Tu empresa aún no está registrada? <button onClick={()=>navigate('empresa')}>Solicitar alta</button></div><div className="public-form-bottom">¿Recibiste una invitación? <button onClick={()=>navigate('invitacion')}>Registrarme con invitación</button></div></div>}
      {publicPage === 'empresa' && <CompanyRegistration goLogin={()=>navigate('login')}/>}
      {publicPage === 'invitacion' && <div className="public-form-card"><InvitationRegistrationView/><div className="public-form-bottom"><button onClick={()=>navigate('login')}>Volver al acceso</button></div></div>}
    </PublicSite>;
  }

  return (
    <div className={`container erp-app ${user ? "erp-authenticated" : ""}`}>
      <Header
        user={user}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onLogout={handleLogout}
        theme={theme}
        onToggleTheme={() => setTheme(t => t === 'light' ? 'dark' : 'light')}
        menuOpen={menuOpen}
        onToggleMenu={() => setMenuOpen(v => !v)}
      />

      <main className="erp-main">
        {!user && activeTab !== 'auth' && <div className="alert alert-info">Inicia sesión para acceder a este módulo.</div>}
        {!user && activeTab === 'registro' && <InvitationRegistrationView />}
        {activeTab === 'auth' && (
          <LoginView
            user={user}
            onLoginSuccess={handleLoginSuccess}
            onLogout={handleLogout}
          />
        )}

        {user && activeTab === 'dashboard' && <DashboardView />}
        {user && activeTab === 'comercial' && <CommercialView />}
        {user && activeTab === 'gestion' && <ManagementView />}
        {user && activeTab === 'operaciones-cierre' && <OperationsCloseView />}
        {user && activeTab === 'compras' && <PurchasesView />}
        {user && activeTab === 'inteligencia' && <IntelligenceView />}
        {user && activeTab === 'analytics' && <AnalyticsView />}
        {user && activeTab === 'reportes' && <ReportsView />}
        {user && activeTab === 'usuarios' && <UsersManagementView />}
        {user && activeTab === 'configuracion' && <EnterpriseSettingsView user={user} />}
        {user && activeTab === 'comercial-fase3' && <CommercialTestingView />}
      </main>

      <footer style={{ marginTop: '3rem', borderTop: '1px solid #ccc', paddingTop: '1rem', fontSize: '0.75rem', color: '#666', textAlign: 'center' }}>
        SalesIA Enterprise · Plataforma de gestión empresarial · React + FastAPI
      </footer>
    </div>
  );
};

export default App;
