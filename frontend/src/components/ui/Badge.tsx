import React from 'react';

export interface BadgeProps {
  variant?: 'success' | 'warning' | 'danger' | 'info' | 'neutral';
  children: React.ReactNode;
  className?: string;
  dot?: boolean;
}

export const Badge: React.FC<BadgeProps> = ({
  variant = 'neutral',
  children,
  className = '',
  dot = false,
}) => {
  const variantStyles = {
    success: {
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-400 dark:border-emerald-500/20',
      dot: 'bg-emerald-500',
    },
    warning: {
      badge: 'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/15 dark:text-amber-400 dark:border-amber-500/20',
      dot: 'bg-amber-500',
    },
    danger: {
      badge: 'bg-red-50 text-red-700 border-red-200 dark:bg-red-500/15 dark:text-red-400 dark:border-red-500/20',
      dot: 'bg-red-500',
    },
    info: {
      badge: 'bg-[#D97843]/10 text-[#C66532] border-[#D97843]/25 dark:bg-[#D97843]/15 dark:text-[#EE915B] dark:border-[#D97843]/30',
      dot: 'bg-[#D97843]',
    },
    neutral: {
      badge: 'bg-gray-100 text-gray-700 border-gray-200 dark:bg-white/10 dark:text-gray-300 dark:border-white/10',
      dot: 'bg-gray-400 dark:bg-gray-500',
    },
  }[variant];

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium border transition-colors ${variantStyles.badge} ${className}`}
    >
      {dot && (
        <span className="relative flex h-1.5 w-1.5 mr-1.5 shrink-0">
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${variantStyles.dot}`}
          />
          <span
            className={`relative inline-flex rounded-full h-1.5 w-1.5 ${variantStyles.dot}`}
          />
        </span>
      )}
      {children}
    </span>
  );
};

export default Badge;
