/**
 * FadeIn Wrapper Component
 * Provides consistent fade-in animations for any content
 */

import { motion, HTMLMotionProps, Variants } from 'framer-motion';
import { fadeInUp, staggerContainer, staggerItem } from '@/lib/animations';

interface FadeInProps extends HTMLMotionProps<'div'> {
  children: React.ReactNode;
  delay?: number;
  duration?: number;
  stagger?: boolean; // If true, children will stagger
  staggerDelay?: number;
}

export function FadeIn({
  children,
  delay = 0,
  duration = 0.5,
  stagger = false,
  staggerDelay = 0.1,
  ...props
}: FadeInProps) {
  const customVariants: Variants = {
    hidden: {
      opacity: 0,
      y: 20,
    },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        delay,
        duration,
        ease: [0.4, 0, 0.2, 1],
      },
    },
  };

  if (stagger) {
    return (
      <motion.div
        variants={staggerContainer}
        initial="hidden"
        animate="visible"
        {...props}
      >
        {children}
      </motion.div>
    );
  }

  return (
    <motion.div
      variants={customVariants}
      initial="hidden"
      animate="visible"
      {...props}
    >
      {children}
    </motion.div>
  );
}

// For list items within stagger containers
export function FadeInItem({ children, ...props }: HTMLMotionProps<'div'>) {
  return (
    <motion.div variants={staggerItem} {...props}>
      {children}
    </motion.div>
  );
}

// Slide in from bottom (for modals, sheets)
export function SlideIn({ children, ...props }: HTMLMotionProps<'div'>) {
  return (
    <motion.div
      initial={{ y: '100%', opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: '100%', opacity: 0 }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 30,
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

// Scale in (for popovers, tooltips)
export function ScaleIn({ children, ...props }: HTMLMotionProps<'div'>) {
  return (
    <motion.div
      initial={{ scale: 0.95, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      exit={{ scale: 0.95, opacity: 0 }}
      transition={{
        duration: 0.2,
        ease: [0.4, 0, 0.2, 1],
      }}
      {...props}
    >
      {children}
    </motion.div>
  );
}
