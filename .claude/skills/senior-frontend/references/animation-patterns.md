# Animation Patterns Reference

## CSS Keyframes (add to globals.css)

```css
/* Entrance */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-16px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInLeft {
  from { opacity: 0; transform: translateX(-16px); }
  to   { opacity: 1; transform: translateX(0); }
}
@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to   { opacity: 1; transform: scale(1); }
}

/* Loaders */
@keyframes shimmer {
  from { background-position: -200% 0; }
  to   { background-position: 200% 0; }
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }

/* Attention */
@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-6px); }
}
@keyframes wiggle {
  0%, 100% { transform: rotate(0deg); }
  25%       { transform: rotate(-3deg); }
  75%       { transform: rotate(3deg); }
}

/* Utility classes */
.animate-fadeInUp   { animation: fadeInUp 0.4s ease-out both; }
.animate-fadeInDown { animation: fadeInDown 0.4s ease-out both; }
.animate-scaleIn    { animation: scaleIn 0.3s ease-out both; }
.animate-shimmer    {
  background: linear-gradient(90deg, #f3f4f6 25%, #e5e7eb 50%, #f3f4f6 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
```

## Staggered List Entrance

```tsx
{items.map((item, i) => (
  <div
    key={item.id}
    className="animate-fadeInUp"
    style={{ animationDelay: `${i * 60}ms` }}
  >
    {/* card content */}
  </div>
))}
```

## Tailwind Transition Utilities

### Hover Lift (cards)
```
hover:-translate-y-1 hover:shadow-lg transition-all duration-300
```

### Hover Lift Subtle (list items)
```
hover:-translate-y-0.5 hover:shadow-md transition-all duration-200
```

### Button Press
```
active:scale-[0.97] transition-transform duration-100
```

### Icon Scale on Parent Hover
```tsx
<div className="group ...">
  <Icon className="group-hover:scale-110 transition-transform duration-200" />
</div>
```

### Smooth Color Transition
```
transition-colors duration-150
```

### Smooth All Properties
```
transition-all duration-200 ease-out
```

## Page-Level Transitions

Wrap page content in a fade wrapper:
```tsx
export default function Page() {
  return (
    <div className="animate-fadeInUp">
      {/* page content */}
    </div>
  );
}
```

## Loading States

### Spinner
```tsx
<Loader2 className="h-5 w-5 animate-spin text-indigo-600" />
```

### Skeleton with Shimmer
```tsx
<div className="animate-shimmer rounded-xl h-48 w-full" />
```

### Pulse Skeleton (Tailwind built-in)
```tsx
<div className="animate-pulse space-y-3">
  <div className="h-4 bg-gray-200 rounded-full w-3/4" />
  <div className="h-4 bg-gray-200 rounded-full w-1/2" />
</div>
```

## Framer Motion (install if needed: `pnpm add framer-motion`)

### Fade + Slide Variant
```tsx
import { motion } from "framer-motion";

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: "easeOut" } },
};

<motion.div variants={fadeUp} initial="hidden" animate="visible">
  {/* content */}
</motion.div>
```

### Stagger Container
```tsx
const container = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.06 } },
};

<motion.ul variants={container} initial="hidden" animate="visible">
  {items.map(item => (
    <motion.li key={item.id} variants={fadeUp}>{/* ... */}</motion.li>
  ))}
</motion.ul>
```

### Layout Animation (reordering lists)
```tsx
<motion.div layout layoutId={item.id}>
  {/* content */}
</motion.div>
```

### Presence (mount/unmount)
```tsx
import { AnimatePresence } from "framer-motion";

<AnimatePresence>
  {isOpen && (
    <motion.div
      key="modal"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
    >
      {/* modal */}
    </motion.div>
  )}
</AnimatePresence>
```

## Notification Badge Pulse

```tsx
<div className="relative">
  <Bell className="h-5 w-5" />
  <span className="absolute -top-1 -right-1 flex h-4 w-4">
    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
    <span className="relative inline-flex rounded-full h-4 w-4 bg-red-500 text-[10px] font-bold text-white items-center justify-center">
      3
    </span>
  </span>
</div>
```
