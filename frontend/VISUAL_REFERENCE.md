# Visual Reference Guide - Before & After

## Component Comparison

### 1. Button States

#### Before
```tsx
<button
  onClick={handleSubmit}
  disabled={loading}
  className="px-4 py-2 bg-pink-600 text-white rounded-md hover:bg-pink-700 disabled:opacity-50"
>
  {loading ? 'Saving...' : 'Save'}
</button>
```
**Issues**:
- ❌ No loading spinner
- ❌ Abrupt color change on hover
- ❌ No press feedback
- ❌ Text changes during loading (layout shift)

#### After
```tsx
import { Button } from '@/components/ui/Button';

<Button
  onClick={handleSubmit}
  loading={loading}
  variant="primary"
>
  Save
</Button>
```
**Improvements**:
- ✅ Animated spinner appears
- ✅ Smooth scale animation on hover (102%)
- ✅ Press feedback (scale down to 97%)
- ✅ No layout shift (spinner replaces text smoothly)
- ✅ Consistent sizing across all states

---

### 2. Loading States

#### Before
```tsx
{loading && (
  <div className="flex justify-center items-center h-64">
    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-pink-500"></div>
  </div>
)}
```
**Issues**:
- ❌ Generic spinner
- ❌ No indication of content structure
- ❌ Jarring when content loads (layout shift)
- ❌ Users don't know what's loading

#### After
```tsx
import { DashboardSkeleton } from '@/components/ui/SkeletonLoader';
import { FadeIn } from '@/components/ui/FadeIn';

{loading ? (
  <FadeIn><DashboardSkeleton /></FadeIn>
) : (
  <FadeIn><DashboardContent /></FadeIn>
)}
```
**Improvements**:
- ✅ Shows layout structure (users see what's coming)
- ✅ Shimmer animation indicates progress
- ✅ Zero layout shift (skeleton matches content dimensions)
- ✅ Smooth fade transition between states
- ✅ Professional, modern appearance

---

### 3. Message Sending

#### Before
```tsx
const onSubmit = async (data) => {
  setSending(true);
  try {
    await apiClient.sendMessage(data.content);
    await fetchMessages(); // Refetch all messages
  } catch (err) {
    setError(err.message);
  } finally {
    setSending(false);
  }
};

// UI waits for server response before showing message
```
**Issues**:
- ❌ UI freezes during send (400-800ms delay)
- ❌ No immediate feedback
- ❌ Error handling unclear
- ❌ User uncertain if action worked

#### After
```tsx
import { useToast } from '@/components/ui/Toast';
import { generateId } from '@/lib/utils';

const { showToast } = useToast();

const onSubmit = async (data) => {
  // Optimistic update - instant UI feedback
  const optimisticMsg = {
    _id: generateId(),
    content: data.content,
    timestamp: new Date().toISOString(),
    optimistic: true,
  };

  setMessages(prev => [...prev, optimisticMsg]);
  setSending(true);

  try {
    const response = await apiClient.sendMessage(data.content);

    // Replace optimistic with real message
    setMessages(prev =>
      prev.map(msg => msg._id === optimisticMsg._id ? response : msg)
    );

    showToast('Message sent!', 'success');
  } catch (err) {
    // Remove optimistic message on error
    setMessages(prev => prev.filter(msg => msg._id !== optimisticMsg._id));
    showToast('Failed to send message', 'error');
  } finally {
    setSending(false);
  }
};

// Message appears instantly with "Sending..." indicator
```
**Improvements**:
- ✅ Message appears instantly (0ms perceived delay)
- ✅ Visual indicator shows pending state (lighter color)
- ✅ Graceful rollback on error
- ✅ Toast notification confirms success
- ✅ Feels responsive and modern

---

### 4. List Animations

#### Before
```tsx
<div className="space-y-4">
  {items.map(item => (
    <div key={item.id} className="border rounded-lg p-4">
      {item.content}
    </div>
  ))}
</div>
```
**Issues**:
- ❌ Items appear instantly (jarring)
- ❌ No visual hierarchy
- ❌ Feels static and boring
- ❌ Hard to track changes

#### After
```tsx
import { motion } from 'framer-motion';
import { staggerContainer, staggerItem } from '@/lib/animations';

<motion.div
  variants={staggerContainer}
  initial="hidden"
  animate="visible"
  className="space-y-4"
>
  {items.map(item => (
    <motion.div
      key={item.id}
      variants={staggerItem}
      layout // Smooth reordering
      whileHover={{ y: -4 }}
      className="border rounded-lg p-4 cursor-pointer"
    >
      {item.content}
    </motion.div>
  ))}
</motion.div>
```
**Improvements**:
- ✅ Items appear sequentially (100ms stagger)
- ✅ Smooth hover lift effect
- ✅ Automatic position animation on reorder
- ✅ Feels alive and polished
- ✅ Easier to scan visually

---

### 5. Navigation Active State

#### Before
```tsx
<Link
  href="/dashboard"
  className={pathname === '/dashboard'
    ? 'border-b-2 border-pink-500 text-gray-900'
    : 'border-b-2 border-transparent text-gray-500'
  }
>
  Dashboard
</Link>
```
**Issues**:
- ❌ Underline jumps between links
- ❌ No smooth transition
- ❌ Feels abrupt and cheap

#### After
```tsx
import { motion } from 'framer-motion';

<Link
  href="/dashboard"
  className="relative text-gray-900"
>
  Dashboard

  {pathname === '/dashboard' && (
    <motion.div
      layoutId="navbar-indicator"
      className="absolute bottom-0 left-0 right-0 h-0.5 bg-pink-500"
      transition={{
        type: 'spring',
        stiffness: 380,
        damping: 30,
      }}
    />
  )}
</Link>
```
**Improvements**:
- ✅ Underline slides smoothly between links
- ✅ Spring physics for natural motion
- ✅ Shared element transition (layoutId)
- ✅ Matches Apple/Linear quality
- ✅ Delightful interaction

---

### 6. Toast Notifications

#### Before
```tsx
{error && (
  <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-md">
    {error}
  </div>
)}
```
**Issues**:
- ❌ Static error message
- ❌ Stays visible until user leaves page
- ❌ No animation
- ❌ Can't dismiss manually
- ❌ Only shows errors (no success messages)

#### After
```tsx
import { useToast } from '@/components/ui/Toast';

const { showToast } = useToast();

// In event handler:
try {
  await saveData();
  showToast('Data saved successfully!', 'success', 3000);
} catch (err) {
  showToast('Failed to save data', 'error', 5000);
}
```
**Improvements**:
- ✅ Animated entrance (slide + fade from top)
- ✅ Auto-dismisses after configurable duration
- ✅ Manual dismiss button (X)
- ✅ Success/error/info variants
- ✅ Stacks multiple toasts
- ✅ Non-blocking (fixed position)

---

### 7. Card Hover Effects

#### Before
```tsx
<div className="bg-white rounded-lg p-6 shadow-sm border">
  <h3>Card Title</h3>
  <p>Card content here</p>
</div>
```
**Issues**:
- ❌ No hover feedback
- ❌ Unclear if clickable
- ❌ Static appearance

#### After
```tsx
import { Card, CardHeader, CardBody } from '@/components/ui/Card';

<Card hoverable clickable onClick={handleClick}>
  <CardHeader>
    <h3>Card Title</h3>
  </CardHeader>
  <CardBody>
    <p>Card content here</p>
  </CardBody>
</Card>
```
**Improvements**:
- ✅ Lifts on hover (y: -4px)
- ✅ Shadow intensifies
- ✅ Cursor changes to pointer
- ✅ Smooth 200ms transition
- ✅ Clear affordance

---

### 8. Agent Monitor Live Indicator

#### Before
```tsx
<div className="text-sm">
  <span>Status: {agentStreamError ? 'Degraded' : 'Online'}</span>
</div>
```
**Issues**:
- ❌ Static text
- ❌ No visual indicator
- ❌ Easy to miss

#### After
```tsx
import { motion } from 'framer-motion';
import { pulse } from '@/lib/animations';

<div className="flex items-center space-x-2">
  <motion.div
    variants={pulse}
    initial="initial"
    animate={isLive ? "animate" : "initial"}
    className="w-2 h-2 bg-green-500 rounded-full"
  />
  <span className="text-sm text-gray-600">
    {isLive ? 'Live' : 'Offline'}
  </span>
</div>
```
**Improvements**:
- ✅ Pulsing green dot (scale + opacity animation)
- ✅ Clear visual indicator
- ✅ Stops pulsing when offline
- ✅ Matches live streaming conventions

---

## Animation Timing Reference

### Duration Guidelines
- **Micro-interactions**: 100-200ms (button press, hover)
- **Transitions**: 200-400ms (fade, slide)
- **Page loads**: 400-600ms (entrance animations)
- **Complex sequences**: 600-1000ms (multi-step animations)

### Easing Functions
```tsx
// Quick and sharp
ease: [0.4, 0, 1, 1]

// Smooth and natural (recommended)
ease: [0.4, 0, 0.2, 1]

// Bouncy (for playful interactions)
type: 'spring'
stiffness: 500
damping: 25

// Sluggish (for heavy elements)
type: 'spring'
stiffness: 300
damping: 30
```

---

## Color Palette

### Brand Colors
```css
--pink-50:  #fdf2f8;
--pink-100: #fce7f3;
--pink-500: #ec4899;  /* Primary */
--pink-600: #db2777;  /* Primary Dark */
--pink-700: #be185d;  /* Primary Darker */

--purple-500: #a855f7; /* Secondary */
--purple-600: #9333ea; /* Secondary Dark */
```

### Semantic Colors
```css
--green-500: #10b981;  /* Success */
--red-500:   #ef4444;  /* Error */
--blue-500:  #3b82f6;  /* Info */
--gray-500:  #6b7280;  /* Neutral */
```

### Usage
```tsx
// Success
<Button variant="primary" className="bg-green-600 hover:bg-green-700">
  Save
</Button>

// Danger
<Button variant="danger">
  Delete
</Button>

// Loading state
<Skeleton className="bg-gray-200" />
```

---

## Accessibility Notes

### Motion Preferences
Always respect `prefers-reduced-motion`:

```tsx
const prefersReducedMotion = window.matchMedia(
  '(prefers-reduced-motion: reduce)'
).matches;

<motion.div
  initial={prefersReducedMotion ? false : { opacity: 0 }}
  animate={prefersReducedMotion ? false : { opacity: 1 }}
>
  Content
</motion.div>
```

### Keyboard Navigation
All interactive elements must be keyboard accessible:

```tsx
<Button onClick={handleClick} onKeyDown={(e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    handleClick();
  }
}}>
  Click me
</Button>
```

### ARIA Labels
```tsx
<Button
  loading={loading}
  aria-label={loading ? 'Saving your data' : 'Save data'}
  aria-busy={loading}
>
  Save
</Button>
```

---

## Mobile Considerations

### Touch Targets
Minimum 44x44px for touch targets:

```tsx
<Button size="lg" className="min-h-[44px] min-w-[44px]">
  Tap me
</Button>
```

### Gesture Support
```tsx
import { motion } from 'framer-motion';

<motion.div
  drag="x"
  dragConstraints={{ left: 0, right: 300 }}
  onDragEnd={(e, info) => {
    if (info.offset.x > 150) {
      handleSwipeRight();
    }
  }}
>
  Swipeable content
</motion.div>
```

### Viewport Units
Avoid `vh` on mobile (address bar issues):

```tsx
// Bad
<div className="h-screen">Content</div>

// Good
<div className="min-h-screen">Content</div>
```

---

## Performance Tips

### 1. Use CSS Transforms
```tsx
// Bad - triggers layout
animate={{ left: 100 }}

// Good - uses GPU
animate={{ x: 100 }}
```

### 2. Memoize Variants
```tsx
const variants = useMemo(() => ({
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
}), []);

<motion.div variants={variants}>Content</motion.div>
```

### 3. Lazy Load Animations
```tsx
import dynamic from 'next/dynamic';

const AnimatedComponent = dynamic(
  () => import('./AnimatedComponent'),
  { ssr: false }
);
```

### 4. Use `will-change` Sparingly
```css
/* Only for elements that WILL animate soon */
.about-to-animate {
  will-change: transform, opacity;
}

/* Remove after animation */
.finished-animating {
  will-change: auto;
}
```

---

## Quick Reference

### Common Patterns

**Fade in on mount**:
```tsx
<FadeIn>{content}</FadeIn>
```

**Stagger list items**:
```tsx
<FadeIn stagger>
  {items.map(item => (
    <FadeInItem key={item.id}>{item}</FadeInItem>
  ))}
</FadeIn>
```

**Loading skeleton**:
```tsx
{loading ? <DashboardSkeleton /> : <DashboardContent />}
```

**Optimistic update**:
```tsx
setItems(prev => [...prev, optimisticItem]);
// Then replace with real item from server
```

**Toast notification**:
```tsx
const { showToast } = useToast();
showToast('Success!', 'success', 3000);
```

**Hover effect**:
```tsx
<motion.div whileHover={{ scale: 1.05 }}>
  Hover me
</motion.div>
```

---

**This guide provides visual context for the UI upgrade. Refer to IMPLEMENTATION_GUIDE.md for step-by-step integration instructions.**
