import React from 'react';
import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { GlassCard } from './GlassCard';

export interface KPICardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon: LucideIcon;
  description?: string;
  className?: string;
}

export const KPICard: React.FC<KPICardProps> = ({
  title,
  value,
  change,
  changeType = 'positive',
  icon: Icon,
  description,
  className = '',
}) => {
  const changeStyles = {
    positive:
      'bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/30',
    negative:
      'bg-red-100 text-red-800 dark:bg-red-500/20 dark:text-red-400 border border-red-200 dark:border-red-500/30',
    neutral:
      'bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-400 border border-gray-200 dark:border-white/10',
  }[changeType];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={className}
    >
      <GlassCard hover className="p-5 h-full flex flex-col justify-between">
        <div>
          <div className="flex items-start justify-between gap-3 mb-2">
            <span className="text-xs uppercase tracking-wider font-extrabold text-slate-700 dark:text-slate-300">
              {title}
            </span>
            <div className="p-2.5 rounded-xl bg-[#D97843]/12 text-[#D97843] dark:text-[#EE915B] border border-[#D97843]/25 shrink-0 shadow-[0_0_12px_rgba(217,120,67,0.15)]">
              <Icon className="w-5 h-5" />
            </div>
          </div>
          <div className="flex items-baseline gap-2.5 mb-1.5 flex-wrap">
            <span className="text-2xl font-black text-slate-950 dark:text-white tracking-tight drop-shadow-sm">
              {value}
            </span>
            {change && (
              <span
                className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold ${changeStyles}`}
              >
                {change}
              </span>
            )}
          </div>
        </div>
        {description && (
          <p className="text-xs text-slate-600 dark:text-slate-300 font-medium mt-2">
            {description}
          </p>
        )}
      </GlassCard>
    </motion.div>
  );
};

export default KPICard;
