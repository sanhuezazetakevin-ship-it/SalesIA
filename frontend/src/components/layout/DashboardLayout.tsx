import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Sidebar } from './Sidebar';
import { Topbar } from './Topbar';
import { User } from '../../types/api';

export interface DashboardLayoutProps {
  children: React.ReactNode;
  activeTab: string;
  onSelectTab: (tab: string) => void;
  user: User | { id: number; empresa_id: number; nombre: string; email: string; activo?: boolean } | null;
  onLogout: () => void;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
}

const TAB_TITLES: Record<string, { title: string; subtitle: string }> = {
  dashboard: {
    title: 'Dashboard',
    subtitle: 'Consola de ventas y analítica',
  },
  comercial: {
    title: 'Ventas',
    subtitle: 'Gestión comercial',
  },
  gestion: {
    title: 'Gestión',
    subtitle: 'Clientes, productos y categorías',
  },
  'operaciones-cierre': {
    title: 'Inventario',
    subtitle: 'Stock y vendedores',
  },
  compras: {
    title: 'Compras',
    subtitle: 'Proveedores y abastecimiento',
  },
  inteligencia: {
    title: 'Inteligencia',
    subtitle: 'Insights y notificaciones',
  },
  analytics: {
    title: 'Analytics',
    subtitle: 'Análisis estadístico',
  },
  reportes: {
    title: 'Reportes',
    subtitle: 'Informes empresariales',
  },
  usuarios: {
    title: 'Usuarios',
    subtitle: 'Gestión de acceso',
  },
  configuracion: {
    title: 'Configuración',
    subtitle: 'Ajustes empresariales',
  },
  'comercial-fase3': {
    title: 'Pruebas Comerciales',
    subtitle: 'Entorno de verificación de fases comerciales',
  },
};

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  activeTab,
  onSelectTab,
  user,
  onLogout,
  theme,
  onToggleTheme,
}) => {
  const [collapsed, setCollapsed] = useState(false);

  const headerInfo = TAB_TITLES[activeTab] || {
    title: 'SalesIA Enterprise',
    subtitle: 'Plataforma de gestión empresarial',
  };

  return (
    <div className="h-screen w-screen overflow-hidden flex bg-[#F8F5F0] dark:bg-[#0A0F0D] relative">
      {/* Fondo Orgánico Vitromorfosis: efecto ribbon 3D fluido en cobre/jade/espresso */}
      <div aria-hidden="true" className="vitromorphism-bg" />
      {/* Sidebar on the left */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={onSelectTab}
        onLogout={onLogout}
        user={user}
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((prev) => !prev)}
      />

      {/* Right content area */}
      <div
        className={`flex-1 flex flex-col overflow-hidden transition-all duration-300 ${
          collapsed ? 'ml-16' : 'ml-64'
        }`}
      >
        {/* Topbar at top */}
        <Topbar
          title={headerInfo.title}
          subtitle={headerInfo.subtitle}
          theme={theme}
          onToggleTheme={onToggleTheme}
          onToggleSidebar={() => setCollapsed((prev) => !prev)}
        />

        {/* Main content area */}
        <main className="flex-1 overflow-y-auto p-6">
          <motion.div
            key={activeTab}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full"
          >
            {children}
          </motion.div>
        </main>
      </div>
    </div>
  );
};

export default DashboardLayout;
