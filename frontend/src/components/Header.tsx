import React from 'react';
import { User } from '../types/api';

interface HeaderProps {
  user: User | null;
  activeTab: string;
  onSelectTab: (tab: string) => void;
  onLogout: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  user,
  activeTab,
  onSelectTab,
  onLogout,
}) => {
  return (
    <header>
      <div className="header-top">
        <div>
          <div className="brand-title">SALESIA ENTERPRISE</div>
          <div style={{ fontSize: '0.8rem', color: '#555' }}>
            Consola de Pruebas y Verificación de Contratos (B&W)
          </div>
        </div>

        <div className="user-status">
          {user ? (
            <>
              <span className="badge badge-connected">AUTENTICADO</span>
              <span>
                <strong>{user.nombre}</strong> (Empresa ID: #{user.empresa_id})
              </span>
              <button onClick={onLogout} style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>
                Cerrar Sesión
              </button>
            </>
          ) : (
            <>
              <span className="badge badge-disconnected">NO AUTENTICADO</span>
              <span style={{ color: '#666' }}>Sesión requerida para la mayoría de endpoints</span>
            </>
          )}
        </div>
      </div>

      <nav className="tabs">
        <button
          className={`tab-btn ${activeTab === 'auth' ? 'active' : ''}`}
          onClick={() => onSelectTab('auth')}
        >
          1. Autenticación
        </button>
        <button
          className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => onSelectTab('dashboard')}
        >
          2. Dashboard Comercial
        </button>
        <button
          className={`tab-btn ${activeTab === 'comercial' ? 'active' : ''}`}
          onClick={() => onSelectTab('comercial')}
        >
          3. Operación Comercial
        </button>
        <button
          className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
          onClick={() => onSelectTab('analytics')}
        >
          4. Analytics & Estadísticas
        </button>
        <button
          className={`tab-btn ${activeTab === 'reportes' ? 'active' : ''}`}
          onClick={() => onSelectTab('reportes')}
        >
          5. Reportes PDF
        </button>
        {user && <button className={`tab-btn ${activeTab === 'usuarios' ? 'active' : ''}`} onClick={() => onSelectTab('usuarios')}>6. Usuarios y Roles (Pruebas)</button>}
        {!user && <button className={`tab-btn ${activeTab === 'registro' ? 'active' : ''}`} onClick={() => onSelectTab('registro')}>Registro por Invitación</button>}
      </nav>
    </header>
  );
};
