import React from 'react';

export interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  hover = false,
  ...rest
}) => {
  const baseClasses =
    'backdrop-blur-2xl bg-white/70 dark:bg-[#1A100B]/60 border border-[#D97843]/15 dark:border-white/10 dark:border-t-white/20 rounded-2xl shadow-[0_8px_32px_rgba(168,84,42,0.06)] dark:shadow-[0_8px_32px_rgba(0,0,0,0.5)]';

  const hoverClasses = hover
    ? 'hover:shadow-[0_0_25px_rgba(217,120,67,0.25)] hover:border-[#D97843]/40 transition-all duration-300'
    : 'transition-all duration-200';

  return (
    <div className={`${baseClasses} ${hoverClasses} ${className}`} {...rest}>
      {children}
    </div>
  );
};

export default GlassCard;
