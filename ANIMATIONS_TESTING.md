# Testing Your Animations - Quick Guide

## ✅ Setup Complete

The following has been done:
1. ✅ Installed `framer-motion@11` and `tailwind-merge`
2. ✅ Updated dashboard page with animations
3. ✅ Restarted frontend container

## 🎬 What You Should See

### Open Your Browser
```
http://localhost:3000/dashboard
```

### Expected Animations

#### 1. **Welcome Banner** (Top)
**Animation**: Fade in from above
- The pink/purple gradient banner should:
  - Start invisible and slightly above its final position
  - Smoothly fade in and slide down over 0.5 seconds
  - Greet you with "Good evening, [Your Name]!"

**How to test**: Refresh the page (F5)

---

#### 2. **Quick Stats Cards** (Three cards below banner)
**Animation**: Stagger effect
- The three stat cards (Quiz Match, Messages, Partner Status) should:
  - Appear one after another with a 100ms delay between each
  - Each card fades in and slides up from below
  - Total animation takes ~0.6 seconds

**How to test**: Refresh the page (F5)

**Hover effect**:
- Hover your mouse over any card
- Card should lift up 4px with enhanced shadow
- Transition is smooth (200ms)

---

#### 3. **Agent Operations Monitor - Live Indicator**
**Animation**: Pulsing green dot
- Look for "Status: Online" with a green dot
- The green dot should:
  - Pulse continuously (scale + opacity)
  - Scale from 1.0 → 1.2 → 1.0
  - Opacity from 1.0 → 0.7 → 1.0
  - Complete cycle every 2 seconds

**How to test**: Just watch the green dot - it should pulse continuously

---

## 🔍 Troubleshooting

### If animations don't appear:

1. **Check Browser Console** (F12 → Console tab)
   - Look for errors mentioning "framer-motion" or "animations"
   - Common error: "Module not found" → Dependencies not installed

2. **Hard Refresh**
   ```
   Chrome/Firefox: Ctrl + Shift + R (Windows) or Cmd + Shift + R (Mac)
   Safari: Cmd + Option + R
   ```

3. **Check Dependencies in Container**
   ```bash
   docker exec together-frontend npm list framer-motion
   ```
   Should show: `framer-motion@11.x.x`

4. **Check for TypeScript Errors**
   ```bash
   docker exec together-frontend npm run build
   ```
   Should complete without errors

5. **Verify Files Exist**
   ```bash
   ls frontend/src/lib/animations.ts
   ls frontend/src/components/ui/Button.tsx
   ```

---

## 🎥 Animation Performance Test

### Frame Rate Check
1. Open Chrome DevTools (F12)
2. Go to "Performance" tab
3. Click "Record" (circle icon)
4. Refresh the page
5. Stop recording after 3 seconds
6. Look for "FPS" in the timeline
   - **Target**: Steady 60 FPS during animations
   - **Acceptable**: 50-60 FPS
   - **Poor**: < 50 FPS (may indicate performance issue)

### Layout Shift Check
1. Open Chrome DevTools (F12)
2. Run Lighthouse audit (Lighthouse tab → "Analyze page load")
3. Check "Cumulative Layout Shift (CLS)" score
   - **Good**: < 0.1
   - **Needs improvement**: 0.1 - 0.25
   - **Poor**: > 0.25

---

## 📱 Mobile Testing

If testing on mobile browser:
1. Cards should still hover/lift on tap
2. Animations should run smoothly (may be 30fps on low-end devices)
3. Touch targets should be at least 44x44px

---

## 🐛 Common Issues

### Issue: "Cannot find module '@/lib/animations'"
**Cause**: TypeScript path alias not recognized
**Fix**:
```bash
docker-compose restart frontend
```

### Issue: Animations lag or stutter
**Cause**: Heavy rendering or low-end device
**Solutions**:
1. Check if other tabs are using CPU
2. Close unnecessary browser tabs
3. Test in Incognito mode (disables extensions)

### Issue: No hover effect on cards
**Cause**: Using touch device or CSS conflict
**Check**:
- Hover works on desktop but not mobile? → Expected behavior
- Hover doesn't work at all? → Check browser console for errors

### Issue: Green dot doesn't pulse
**Cause**: `agentStreamError` may be set (degraded state)
**Check**: Status should say "Online" not "Degraded"

---

## 🎯 Next Steps

Once you confirm animations work:

1. **Add more animations** to other pages (messages, agent ops)
2. **Replace buttons** with enhanced `<Button>` component
3. **Add skeleton loaders** for loading states
4. **Implement optimistic UI** in messages

See `IMPLEMENTATION_GUIDE.md` for detailed instructions.

---

## ✨ What Makes It "Smooth"

The animations feel professional because:

1. **GPU Acceleration**: Uses `transform` (not `top/left`)
2. **Spring Physics**: Natural-feeling motion (not linear)
3. **Proper Timing**: 200-500ms (not too fast, not too slow)
4. **Easing Curves**: Custom bezier curves matching Apple/Stripe
5. **Stagger Effect**: Sequential appearance feels more premium
6. **Hover Feedback**: Cards respond to user interaction
7. **60 FPS**: Smooth frame rate throughout

---

## 📸 Expected Visual Flow

### On Page Load (2 seconds total):

```
0.0s: Page starts loading
0.1s: Welcome banner fades in from above ▼
0.3s: First stat card (Quiz) appears ▲
0.4s: Second stat card (Messages) appears ▲
0.5s: Third stat card (Partner) appears ▲
0.6s: Agent monitor section visible
0.8s: Green dot starts pulsing 🟢
2.0s: All animations complete, page fully interactive
```

### On Hover:
```
Hover over card → Card lifts 4px + shadow intensifies (200ms)
Move mouse away → Card returns to original position (200ms)
```

### Continuous:
```
Green status dot pulses every 2 seconds indefinitely
```

---

## 🎉 Success Criteria

You'll know it's working when:
- ✅ Welcome banner smoothly fades in from above
- ✅ Three cards appear sequentially (not all at once)
- ✅ Cards lift when you hover over them
- ✅ Green dot pulses continuously
- ✅ No layout jumps or flickering
- ✅ Animation runs at 60 FPS

---

**Need Help?** Check browser console (F12) for error messages or refer to `IMPLEMENTATION_GUIDE.md` for troubleshooting steps.
