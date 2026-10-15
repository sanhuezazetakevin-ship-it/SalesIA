import React from 'react';
import {
  LayoutDashboard,
  ShoppingCart,
  Package,
  Warehouse,
  Truck,
  Brain,
  BarChart3,
  FileText,
  Users,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Play,
  Sparkles,
} from 'lucide-react';
import { User } from '../../types/api';

export interface SidebarProps {
  activeTab: string;
  onSelectTab: (tab: string) => void;
  onLogout: () => void;
  user: User | { id: number; empresa_id: number; nombre: string; email: string; activo?: boolean } | null;
  collapsed: boolean;
  onToggleCollapsed: () => void;
}

interface NavItem {
  id: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const navItems: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'comercial', label: 'Ventas', icon: ShoppingCart },
  { id: 'gestion', label: 'Gestión', icon: Package },
  { id: 'operaciones-cierre', label: 'Inventario', icon: Warehouse },
  { id: 'compras', label: 'Compras', icon: Truck },
  { id: 'inteligencia', label: 'Inteligencia', icon: Brain },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
  { id: 'reportes', label: 'Reportes', icon: FileText },
  { id: 'usuarios', label: 'Usuarios', icon: Users },
  { id: 'configuracion', label: 'Configuración', icon: Settings },
];

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onSelectTab,
  onLogout,
  user,
  collapsed,
  onToggleCollapsed,
}) => {
  return (
    <aside
      className={`fixed left-0 top-0 h-screen z-40 bg-[#F8F5F0]/85 dark:bg-[#0A0F0D]/85 backdrop-blur-2xl border-r border-[#D97843]/15 dark:border-white/10 flex flex-col justify-between transition-all duration-300 ${
        collapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Top Section: Header & Navigation */}
      <div className="flex flex-col flex-1 min-h-0">
        {/* Header (h-16) */}
        <div className="h-16 px-3.5 flex items-center justify-between border-b border-[#D97843]/15 dark:border-white/10 shrink-0">
          <div className={`flex items-center gap-3 overflow-hidden ${collapsed ? 'mx-auto' : ''}`}>
            {/* Logo cuadrado con gradiente cálido de cobre y brillo Vitromorfosis */}
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#EE915B] via-[#D97843] to-[#8A4522] flex items-center justify-center text-white shadow-[0_0_20px_rgba(217,120,67,0.4)] shrink-0">
              <Play className="w-4 h-4 fill-white text-white translate-x-0.5" />
            </div>

            {/* Brand text (only when not collapsed) */}
            {!collapsed && (
              <div className="flex items-baseline whitespace-nowrap select-none">
                <span className="font-extrabold text-lg text-[#24150E] dark:text-white tracking-tight">SALES</span>
                <span className="font-light text-lg text-[#D97843] dark:text-[#EE915B]">IA</span>
              </div>
            )}
          </div>

          {/* Collapse toggle button at the header when expanded */}
          {!collapsed && (
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="p-1.5 rounded-lg text-gray-400 hover:text-[#24150E] dark:hover:text-white hover:bg-[#D97843]/10 dark:hover:bg-white/5 transition-colors"
              title="Colapsar barra lateral"
              aria-label="Colapsar barra lateral"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Collapse toggle button under header when collapsed */}
        {collapsed && (
          <div className="flex justify-center py-2 border-b border-[#D97843]/10 dark:border-white/5 shrink-0">
            <button
              type="button"
              onClick={onToggleCollapsed}
              className="p-1.5 rounded-lg text-gray-400 hover:text-[#24150E] dark:hover:text-white hover:bg-[#D97843]/10 dark:hover:bg-white/5 transition-colors"
              title="Expandir barra lateral"
              aria-label="Expandir barra lateral"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Navigation Section */}
        <div className="flex-1 overflow-y-auto px-2 py-3">
          {/* Section label */}
          {!collapsed ? (
            <div className="px-3 pb-2 text-[10px] uppercase font-extrabold tracking-widest text-slate-800 dark:text-slate-200 select-none">
              PRINCIPAL
            </div>
          ) : (
            <div className="py-1 flex justify-center">
              <div className="w-4 h-0.5 bg-[#D97843]/40 dark:bg-white/20 rounded-full" />
            </div>
          )}

          {/* Nav Items */}
          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => onSelectTab(item.id)}
                  title={collapsed ? item.label : undefined}
                  className={`w-full flex items-center transition-all duration-200 group text-sm relative ${
                    collapsed
                      ? 'justify-center py-2.5 rounded-lg'
                      : 'gap-3 px-3 py-2.5 rounded-r-xl'
                  } ${
                    isActive
                      ? 'bg-[#D97843]/15 text-[#A8542A] dark:bg-gradient-to-r dark:from-[#D97843]/25 dark:to-transparent dark:text-[#FFA675] border-l-2 border-[#D97843] dark:border-[#FFA675] font-bold dark:shadow-[inset_0_0_12px_rgba(217,120,67,0.15)]'
                      : 'text-slate-700 dark:text-slate-300 hover:bg-[#D97843]/10 dark:hover:bg-white/10 hover:text-slate-950 dark:hover:text-white font-medium border-l-2 border-transparent'
                  }`}
                >
                  <Icon
                    className={`w-5 h-5 shrink-0 transition-transform duration-200 group-hover:scale-105 ${
                      isActive ? 'text-[#D97843] dark:text-[#FFA675]' : ''
                    }`}
                  />
                  {!collapsed && <span className="truncate">{item.label}</span>}

                  {/* Tooltip on collapsed hover */}
                  {collapsed && (
                    <div className="absolute left-full ml-2 px-2.5 py-1 bg-[#140C08] border border-white/10 text-white text-xs font-normal rounded-md shadow-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 whitespace-nowrap">
                      {item.label}
                    </div>
                  )}
                </button>
              );
            })}
          </nav>
        </div>
      </div>

      {/* Footer Section */}
      <div className="p-3 border-t border-[#D97843]/15 dark:border-white/10 bg-[#F8F5F0]/90 dark:bg-[#0A0F0D]/90 shrink-0">
        <div
          className={`flex items-center ${
            collapsed ? 'flex-col gap-3 justify-center' : 'justify-between gap-2'
          }`}
        >
          {/* User Profile */}
          <div
            className={`flex items-center gap-2.5 min-w-0 ${
              collapsed ? 'justify-center' : ''
            }`}
          >
            <div
              className="w-8 h-8 rounded-full bg-gradient-to-tr from-[#EE915B] to-[#8A4522] text-white font-bold text-xs flex items-center justify-center shrink-0 shadow-[0_0_10px_rgba(217,120,67,0.3)]"
              title={user?.nombre || 'Usuario'}
            >
              {user?.nombre ? user.nombre.charAt(0).toUpperCase() : 'U'}
            </div>

            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-slate-900 dark:text-white truncate">
                  {user?.nombre || 'Usuario'}
                </p>
                <p className="text-[11px] text-slate-600 dark:text-slate-300 font-medium truncate">
                  {user?.email || 'usuario@empresa.com'}
                </p>
              </div>
            )}
          </div>

          {/* Logout Button */}
          <button
            type="button"
            onClick={onLogout}
            className="p-2 rounded-lg text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-500/10 transition-colors shrink-0"
            title="Cerrar sesión"
            aria-label="Cerrar sesión"
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
};

export default Sidebar;
