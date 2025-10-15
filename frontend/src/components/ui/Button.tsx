/**
 * Enhanced Button Component with animations and loading states
 */

import { motion, HTMLMotionProps } from 'framer-motion';
import { forwardRef } from 'react';
import { tapScale, hoverScale } from '@/lib/animations';
import { cn } from '@/lib/utils';
import { Loader2 } from 'lucide-react';

export interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'children'> {
  children: React.ReactNode;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      className,
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled = false,
      fullWidth = false,
      icon,
      iconPosition = 'left',
      ...props
    },
    ref
  ) => {
    const baseClasses = 'inline-flex items-center justify-center font-medium rounded-md focus:outline-none focus:ring-2 focus:ring-offset-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed';

    const variantClasses = {
      primary: 'bg-pink-600 text-white hover:bg-pink-700 focus:ring-pink-500',
      secondary: 'bg-purple-600 text-white hover:bg-purple-700 focus:ring-purple-500',
      outline: 'border-2 border-pink-600 text-pink-600 hover:bg-pink-50 focus:ring-pink-500',
      ghost: 'text-gray-700 hover:bg-gray-100 focus:ring-gray-500',
      danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
    };

    const sizeClasses = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-4 py-2 text-sm',
      lg: 'px-6 py-3 text-base',
    };

    const widthClass = fullWidth ? 'w-full' : '';

    return (
      <motion.button
        ref={ref}
        className={cn(
          baseClasses,
          variantClasses[variant],
          sizeClasses[size],
          widthClass,
          className
        )}
        whileHover={!disabled && !loading ? hoverScale : undefined}
        whileTap={!disabled && !loading ? tapScale : undefined}
        disabled={disabled || loading}
        {...props}
      >
        {loading && (
          <motion.div
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            className="mr-2"
          >
            <Loader2 className="w-4 h-4 animate-spin" />
          </motion.div>
        )}

        {!loading && icon && iconPosition === 'left' && (
          <span className="mr-2">{icon}</span>
        )}

        {children}

        {!loading && icon && iconPosition === 'right' && (
          <span className="ml-2">{icon}</span>
        )}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';

export { Button };
