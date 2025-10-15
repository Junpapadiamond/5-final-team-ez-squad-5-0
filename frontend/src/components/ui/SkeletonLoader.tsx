/**
 * Skeleton Loader Component
 * Displays shimmer effect while content loads
 */

import { motion } from 'framer-motion';
import { shimmer } from '@/lib/animations';
import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular' | 'card';
  lines?: number; // For text variant
  animated?: boolean;
}

export function Skeleton({
  className,
  variant = 'rectangular',
  lines = 3,
  animated = true
}: SkeletonProps) {
  const baseClasses = 'bg-gradient-to-r from-gray-200 via-gray-300 to-gray-200 bg-[length:200%_100%]';

  const Component = animated ? motion.div : 'div';
  const animationProps = animated ? { variants: shimmer, initial: 'initial', animate: 'animate' } : {};

  if (variant === 'text') {
    return (
      <div className="space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <Component
            key={i}
            className={cn(
              baseClasses,
              'h-4 rounded',
              i === lines - 1 ? 'w-4/5' : 'w-full',
              className
            )}
            {...animationProps}
          />
        ))}
      </div>
    );
  }

  if (variant === 'circular') {
    return (
      <Component
        className={cn(baseClasses, 'rounded-full', className)}
        {...animationProps}
      />
    );
  }

  if (variant === 'card') {
    return (
      <div className={cn('bg-white rounded-lg shadow-sm border p-6 space-y-4', className)}>
        <div className="flex items-center space-x-4">
          <Skeleton variant="circular" className="w-12 h-12" />
          <div className="flex-1 space-y-2">
            <Skeleton variant="rectangular" className="h-4 w-3/4" />
            <Skeleton variant="rectangular" className="h-3 w-1/2" />
          </div>
        </div>
        <Skeleton variant="text" lines={3} />
      </div>
    );
  }

  return (
    <Component
      className={cn(baseClasses, 'rounded', className)}
      {...animationProps}
    />
  );
}

// Specialized skeleton loaders for common patterns

export function MessageSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((i) => (
        <div key={i} className={i % 2 === 0 ? 'flex justify-end' : 'flex justify-start'}>
          <div className={cn(
            'max-w-xs space-y-2 p-4 rounded-lg',
            i % 2 === 0 ? 'bg-pink-50' : 'bg-gray-50'
          )}>
            <Skeleton variant="rectangular" className="h-4 w-48" />
            <Skeleton variant="rectangular" className="h-4 w-32" />
            <Skeleton variant="rectangular" className="h-3 w-16" />
          </div>
        </div>
      ))}
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-pink-100 to-purple-100 rounded-lg p-6">
        <Skeleton variant="rectangular" className="h-8 w-64 mb-4" />
        <Skeleton variant="rectangular" className="h-4 w-48" />
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="bg-white rounded-lg p-6 shadow-sm border">
            <div className="flex items-center">
              <Skeleton variant="circular" className="w-12 h-12" />
              <div className="ml-4 flex-1 space-y-2">
                <Skeleton variant="rectangular" className="h-4 w-24" />
                <Skeleton variant="rectangular" className="h-8 w-16" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[1, 2].map((i) => (
          <Skeleton key={i} variant="card" />
        ))}
      </div>
    </div>
  );
}

export function AgentMonitorSkeleton() {
  return (
    <div className="bg-white rounded-lg p-6 shadow-sm border space-y-6">
      <Skeleton variant="rectangular" className="h-6 w-64 mb-2" />
      <Skeleton variant="rectangular" className="h-4 w-96" />

      {/* Pipeline stages */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="border rounded-lg p-4 space-y-3">
            <div className="flex items-center space-x-3">
              <Skeleton variant="circular" className="w-10 h-10" />
              <div className="flex-1 space-y-2">
                <Skeleton variant="rectangular" className="h-4 w-20" />
                <Skeleton variant="rectangular" className="h-3 w-32" />
              </div>
            </div>
            <Skeleton variant="rectangular" className="h-1.5 w-full" />
          </div>
        ))}
      </div>

      {/* Events list */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {[1, 2].map((section) => (
          <div key={section} className="space-y-3">
            <Skeleton variant="rectangular" className="h-5 w-40" />
            {[1, 2, 3].map((item) => (
              <div key={item} className="border rounded-md p-3 bg-gray-50">
                <Skeleton variant="rectangular" className="h-4 w-full mb-2" />
                <Skeleton variant="rectangular" className="h-3 w-24" />
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export function ListItemSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="border rounded-lg p-4 bg-white shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <Skeleton variant="rectangular" className="h-5 w-32" />
            <Skeleton variant="rectangular" className="h-4 w-20" />
          </div>
          <Skeleton variant="rectangular" className="h-4 w-full mb-2" />
          <Skeleton variant="rectangular" className="h-4 w-3/4" />
        </div>
      ))}
    </div>
  );
}
