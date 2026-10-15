import React from 'react';
import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import { Button } from './Button';

export interface EmptyStateAction {
  label: string;
  onClick: () => void;
}

export interface EmptyStateProps {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: EmptyStateAction;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
  className = '',
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex flex-col items-center justify-center text-center p-8 sm:p-12 ${className}`}
    >
      <div className="mb-4 flex items-center justify-center rounded-2xl bg-gray-100 dark:bg-white/5 p-4 ring-1 ring-gray-200/50 dark:ring-white/10">
        <Icon className="w-12 h-12 text-gray-400 dark:text-gray-500" strokeWidth={1.5} />
      </div>
      <h3 className="text-lg font-black text-slate-950 dark:text-white mb-1.5 drop-shadow-sm">
        {title}
      </h3>
      <p className="text-sm text-slate-600 dark:text-slate-300 font-medium max-w-sm mb-6">
        {description}
      </p>
      {action && (
        <Button variant="primary" onClick={action.onClick}>
          {action.label}
        </Button>
      )}
    </motion.div>
  );
};

export default EmptyState;
