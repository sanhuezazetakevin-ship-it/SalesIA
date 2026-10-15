import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  children?: React.ReactNode;
  disabled?: boolean;
  className?: string;
  onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  type?: 'button' | 'submit' | 'reset';
  icon?: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  children,
  disabled = false,
  className = '',
  onClick,
  type = 'button',
  icon,
  ...rest
}) => {
  const baseClasses =
    'inline-flex items-center justify-center font-semibold transition-all duration-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]';

  const variantClasses = {
    primary:
      'bg-gradient-to-r from-[#D97843] to-[#B35D2F] hover:from-[#E08A55] hover:to-[#C66532] active:from-[#A8542A] active:to-[#8A4522] text-white focus:ring-[#D97843]/50 shadow-[0_0_15px_rgba(217,120,67,0.3)] hover:shadow-[0_0_22px_rgba(217,120,67,0.45)] focus:ring-offset-white dark:focus:ring-offset-[#0D0806]',
    outline:
      'border border-[#D97843]/30 text-[#24150E] dark:border-white/20 dark:text-[#FAF5F0] hover:bg-[#D97843]/10 dark:hover:bg-white/10 focus:ring-[#D97843]/50 focus:ring-offset-white dark:focus:ring-offset-[#0D0806]',
    ghost:
      'text-[#24150E] dark:text-[#FAF5F0] hover:bg-[#D97843]/10 dark:hover:bg-white/5 focus:ring-[#D97843]/50 focus:ring-offset-white dark:focus:ring-offset-[#0D0806]',
    danger:
      'bg-red-600 hover:bg-red-700 active:bg-red-800 text-white focus:ring-red-500 shadow-sm hover:shadow focus:ring-offset-white dark:focus:ring-offset-[#0D0806]',
  }[variant];

  const sizeClasses = {
    sm: 'px-3 py-1.5 text-xs gap-1.5',
    md: 'px-4 py-2 text-sm gap-2',
    lg: 'px-5 py-2.5 text-base gap-2.5',
  }[size];

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      className={`${baseClasses} ${variantClasses} ${sizeClasses} ${className}`}
      {...rest}
    >
      {icon && <span className="inline-flex shrink-0">{icon}</span>}
      {children}
    </button>
  );
};

export default Button;
