import React from 'react';
import { User } from '../types/api';

interface HeaderProps {
  user: User | null;
  activeTab: string;
  onSelectTab: (tab: string) => void;
  onLogout: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  menuOpen: boolean;
  onToggleMenu: () => void;
}

const items = [
  { id: 'dashboard', label: 'Panel ejecutivo', icon: '▦', group: 'VISIÓN GENERAL' },
  { id: 'comercial', label: 'Ventas y pedidos', icon: '◈', group: 'OPERACIONES' },
  { id: 'gestion', label: 'Clientes y productos', icon: '▣', group: 'OPERACIONES' },
  { id: 'operaciones-cierre', label: 'Inventario y vendedores', icon: '▤', group: 'OPERACIONES' },
  { id: 'compras', label: 'Compras y proveedores', icon: '◧', group: 'OPERACIONES' },
  { id: 'analytics', label: 'Analítica', icon: '▥', group: 'INTELIGENCIA' },
  { id: 'inteligencia', label: 'Centro inteligente', icon: '✦', group: 'INTELIGENCIA' },
  { id: 'reportes', label: 'Reportes', icon: '▧', group: 'INTELIGENCIA' },
  { id: 'usuarios', label: 'Usuarios y roles', icon: '♧', group: 'ADMINISTRACIÓN' },
  { id: 'configuracion', label: 'Configuración', icon: '⚙', group: 'ADMINISTRACIÓN' },
  { id: 'comercial-fase3', label: 'Pruebas comerciales', icon: '✓', group: 'ADMINISTRACIÓN' },
];

export const Header: React.FC<HeaderProps> = ({user, activeTab, onSelectTab, onLogout, theme, onToggleTheme, menuOpen, onToggleMenu}) => {
  const active = items.find(x => x.id === activeTab);
  return <>
    {user && menuOpen && <button type="button" className="sidebar-backdrop" onClick={onToggleMenu} aria-label="Cerrar menú" />}
    {user && <aside className={`erp-sidebar ${menuOpen ? 'is-open' : ''}`}>
      <div className="erp-brand"><div className="erp-brand-mark">S</div><div><strong>SalesIA</strong><small>ENTERPRISE ERP</small></div></div>
      <div className="sidebar-context"><span className="context-dot"/> Entorno empresarial <small>Empresa #{user.empresa_id}</small></div>
      <nav className="erp-nav" aria-label="Navegación principal">
        {items.map((item, i) => <React.Fragment key={item.id}>
          {(i === 0 || items[i - 1].group !== item.group) && <div className="erp-nav-group">{item.group}</div>}
          <button type="button" className={`erp-nav-item ${activeTab === item.id ? 'active' : ''}`} aria-current={activeTab === item.id ? 'page' : undefined} onClick={() => { onSelectTab(item.id); if(menuOpen) onToggleMenu(); }}><span className="erp-nav-icon" aria-hidden="true">{item.icon}</span>{item.label}</button>
        </React.Fragment>)}
      </nav>
      <div className="sidebar-bottom">Gestión inteligente, decisiones claras.<small>SalesIA Enterprise · Versión de exposición</small></div>
    </aside>}
    <header className="erp-topbar">
      <div className="erp-heading">
        {user && <button type="button" className="mobile-menu-trigger" onClick={onToggleMenu} aria-label="Abrir menú">☰</button>}
        <div><span className="erp-top-eyebrow">SalesIA / {active?.group?.toLowerCase() ?? 'acceso'}</span><h1>{active?.label ?? (user ? 'Mi sesión' : 'Acceso empresarial')}</h1></div>
      </div>
      <div className="erp-top-actions">
        <button type="button" className="theme-toggle" aria-label={`Cambiar a tema ${theme === 'light' ? 'oscuro' : 'claro'}`} title={`Cambiar a tema ${theme === 'light' ? 'oscuro' : 'claro'}`} onClick={onToggleTheme}><span aria-hidden="true">{theme === 'light' ? '☾' : '☀'}</span><span className="theme-label">{theme === 'light' ? 'Oscuro' : 'Claro'}</span></button>
        {user ? <><div className="erp-user"><span className="erp-avatar">{user.nombre.charAt(0).toUpperCase()}</span><div><strong>{user.nombre}</strong><small>Sesión activa</small></div></div><button type="button" onClick={onLogout} className="logout-button">Salir</button></> : <span className="erp-guest">Acceso protegido</span>}
      </div>
    </header>
  </>;
};
