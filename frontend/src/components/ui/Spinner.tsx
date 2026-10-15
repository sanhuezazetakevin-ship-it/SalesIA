import React from 'react';

export interface SpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
  centered?: boolean;
}

export const Spinner: React.FC<SpinnerProps> = ({
  size = 'md',
  className = '',
  centered = true,
}) => {
  const sizeClasses = {
    sm: 'h-4 w-4 border-2',
    md: 'h-8 w-8 border-[3px]',
    lg: 'h-12 w-12 border-4',
  }[size];

  const spinner = (
    <div
      role="status"
      aria-label="Cargando"
      className={`${sizeClasses} border-cyan-500 border-t-transparent rounded-full animate-spin shrink-0 ${className}`}
    >
      <span className="sr-only">Cargando...</span>
    </div>
  );

  if (centered) {
    return <div className="flex items-center justify-center p-4 w-full">{spinner}</div>;
  }

  return spinner;
};

export default Spinner;
