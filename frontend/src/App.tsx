import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { LoginView } from './components/LoginView';
import { DashboardView } from './components/DashboardView';
import { CommercialView } from './components/CommercialView';
import { AnalyticsView } from './components/AnalyticsView';
import { UsersManagementView } from './components/UsersManagementView';
import { InvitationRegistrationView } from './components/InvitationRegistrationView';
import { CommercialTestingView } from './components/CommercialTestingView';
import { ReportsView } from './components/ReportsView';
import { api, authStorage } from './services/api';
import { User } from './types/api';

export const App: React.FC = () => {
  const [user, setUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<string>('auth');
  const [verificandoSesion, setVerificandoSesion] = useState(true);

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
    setActiveTab('auth');
  };

  if (verificandoSesion) {
    return (
      <div className="container" style={{ paddingTop: '3rem', textAlign: 'center' }}>
        <p>Iniciando entorno SalesIA Enterprise...</p>
      </div>
    );
  }

  return (
    <div className="container">
      <Header
        user={user}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onLogout={handleLogout}
      />

      <main>
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
        {user && activeTab === 'analytics' && <AnalyticsView />}
        {user && activeTab === 'reportes' && <ReportsView />}
        {user && activeTab === 'usuarios' && <UsersManagementView />}
        {user && activeTab === 'comercial-fase3' && <CommercialTestingView />}
      </main>

      <footer style={{ marginTop: '3rem', borderTop: '1px solid #ccc', paddingTop: '1rem', fontSize: '0.75rem', color: '#666', textAlign: 'center' }}>
        SalesIA Enterprise — Prototipo Funcional de Integración Académica &middot; React + Vite + TypeScript &middot; Modo Monocromático
      </footer>
    </div>
  );
};

export default App;
