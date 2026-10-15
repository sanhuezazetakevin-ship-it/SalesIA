import React from 'react';
import { Menu, Sun, Moon } from 'lucide-react';

export interface TopbarProps {
  title: string;
  subtitle: string;
  theme: 'light' | 'dark';
  onToggleTheme: () => void;
  onToggleSidebar: () => void;
}

export const Topbar: React.FC<TopbarProps> = ({
  title,
  subtitle,
  theme,
  onToggleTheme,
  onToggleSidebar,
}) => {
  return (
    <header className="h-16 sticky top-0 z-30 bg-[#F8F5F0]/85 dark:bg-[#0A0F0D]/85 backdrop-blur-2xl border-b border-[#D97843]/15 dark:border-white/10 flex items-center justify-between px-6 shrink-0 transition-colors">
      {/* Left side: Menu toggle & View Titles */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="p-2 rounded-xl text-slate-700 dark:text-[#C5D6CF] hover:bg-[#D97843]/10 dark:hover:bg-[#2E6F5C]/20 transition-colors focus:outline-none"
          title="Alternar menú lateral"
          aria-label="Alternar menú lateral"
        >
          <Menu className="w-5 h-5" />
        </button>

        <div className="flex flex-col">
          <h1 className="font-extrabold text-lg text-slate-950 dark:text-white tracking-tight leading-tight">
            {title}
          </h1>
          {subtitle && (
            <span className="text-xs text-slate-700 dark:text-slate-200 leading-tight font-semibold">
              {subtitle}
            </span>
          )}
        </div>
      </div>

      {/* Right side: Live indicator, Theme toggle & Export CSV */}
      <div className="flex items-center gap-3">
        {/* Live data indicator con verde esmeralda brillante */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/15 dark:bg-emerald-500/20 border border-emerald-600/30 dark:border-emerald-400/30 text-emerald-800 dark:text-emerald-300 text-[11px] font-bold tracking-wider select-none shadow-[0_0_12px_rgba(16,185,129,0.2)]">
          <span className="w-2 h-2 rounded-full bg-[#10b981] shadow-[0_0_8px_#10b981] animate-pulse" />
          <span>LIVE DATA 2026</span>
        </div>

        {/* Botón redondo para alternar tema */}
        <button
          type="button"
          onClick={onToggleTheme}
          className="w-9 h-9 rounded-full flex items-center justify-center text-[#5E4A40] dark:text-[#BAA89E] bg-white/70 dark:bg-white/5 border border-[#D97843]/20 dark:border-white/10 hover:bg-[#D97843]/15 dark:hover:bg-white/10 transition-colors focus:outline-none"
          title={theme === 'light' ? 'Cambiar a modo oscuro' : 'Cambiar a modo claro'}
          aria-label={theme === 'light' ? 'Cambiar a modo oscuro' : 'Cambiar a modo claro'}
        >
          {theme === 'light' ? (
            <Moon className="w-4 h-4 text-[#8A4522]" />
          ) : (
            <Sun className="w-4 h-4 text-[#EE915B]" />
          )}
        </button>

        {/* Botón primario Export CSV con gradiente cobre y sombra cálida */}
        <button
          type="button"
          onClick={() => {
            const ev = new CustomEvent('salesia-export-csv');
            window.dispatchEvent(ev);
          }}
          className="px-4 py-2 rounded-xl bg-gradient-to-r from-[#D97843] to-[#B35D2F] hover:from-[#E08A55] hover:to-[#C66532] text-white text-xs font-semibold shadow-[0_0_15px_rgba(217,120,67,0.3)] transition-all focus:outline-none focus:ring-2 focus:ring-[#D97843]/50"
        >
          Export CSV
        </button>
      </div>
    </header>
  );
};

export default Topbar;
