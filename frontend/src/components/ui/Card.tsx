/**
 * Enhanced Card Component with hover animations
 */

import { motion, HTMLMotionProps } from 'framer-motion';
import { forwardRef } from 'react';
import { hoverLift, fadeInUp } from '@/lib/animations';
import { cn } from '@/lib/utils';

export interface CardProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  hoverable?: boolean;
  clickable?: boolean;
  animated?: boolean;
  variant?: 'default' | 'outlined' | 'elevated';
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      className,
      hoverable = false,
      clickable = false,
      animated = true,
      variant = 'default',
      ...props
    },
    ref
  ) => {
    const baseClasses = 'rounded-lg transition-shadow';

    const variantClasses = {
      default: 'bg-white border border-gray-200 shadow-sm',
      outlined: 'bg-white border-2 border-gray-300',
      elevated: 'bg-white shadow-md',
    };

    const interactiveClasses = clickable ? 'cursor-pointer' : '';

    return (
      <motion.div
        ref={ref}
        className={cn(
          baseClasses,
          variantClasses[variant],
          interactiveClasses,
          className
        )}
        variants={animated ? fadeInUp : undefined}
        initial={animated ? 'hidden' : undefined}
        animate={animated ? 'visible' : undefined}
        whileHover={hoverable || clickable ? hoverLift : undefined}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);

Card.displayName = 'Card';

// Sub-components for better composition
const CardHeader = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('p-6 border-b border-gray-200', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardHeader.displayName = 'CardHeader';

const CardBody = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('p-6', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardBody.displayName = 'CardBody';

const CardFooter = forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn('p-6 border-t border-gray-200 bg-gray-50', className)}
        {...props}
      >
        {children}
      </div>
    );
  }
);

CardFooter.displayName = 'CardFooter';

export { Card, CardHeader, CardBody, CardFooter };
