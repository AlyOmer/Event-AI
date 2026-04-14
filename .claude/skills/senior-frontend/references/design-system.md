# Design System Reference

## Color Palette

### Brand Colors
```
indigo-500  #6366f1   primary interactive
indigo-600  #4f46e5   primary hover / CTA
indigo-700  #4338ca   active / pressed
purple-600  #9333ea   gradient end (logo, accents)
blue-500    #3b82f6   secondary brand (frontend package)
blue-600    #2563eb   secondary hover
```

### Semantic Colors
```
green-500   #22c55e   success
green-50    #f0fdf4   success background
red-500     #ef4444   error / destructive
red-50      #fef2f2   error background
yellow-500  #eab308   warning
yellow-50   #fefce8   warning background
```

### Neutral Scale
```
gray-50   #f9fafb   page background
gray-100  #f3f4f6   subtle background, skeleton
gray-200  #e5e7eb   borders, dividers
gray-300  #d1d5db   input borders
gray-400  #9ca3af   placeholder, muted icons
gray-500  #6b7280   secondary text
gray-600  #4b5563   body text
gray-700  #374151   label text
gray-800  #1f2937   strong text
gray-900  #111827   headings
```

## Gradient Recipes

### Hero Background
```css
bg-gradient-to-b from-blue-50 to-white
/* or */
bg-gradient-to-br from-indigo-50 via-white to-purple-50
```

### Logo / Icon Background
```css
bg-gradient-to-br from-indigo-500 to-purple-600
```

### CTA Section Background
```css
bg-gradient-to-r from-indigo-600 to-purple-600
```

### Card Accent
```css
bg-gradient-to-br from-indigo-50 to-purple-50
```

## Shadow Scale

```
shadow-sm    subtle card lift
shadow       default card
shadow-md    hover state, dropdowns
shadow-lg    modals, popovers
shadow-xl    full-screen overlays
```

Custom glow (for featured cards):
```css
shadow-[0_0_0_1px_rgba(99,102,241,0.1),0_4px_24px_rgba(99,102,241,0.12)]
```

## Border Radius Scale

```
rounded-md    inputs, small buttons (6px)
rounded-lg    buttons, cards (8px)
rounded-xl    large cards (12px)
rounded-2xl   hero cards, feature blocks (16px)
rounded-full  pills, avatars, badges
```

## Spacing Scale (Tailwind 4px grid)

| Token | px  | Use |
|-------|-----|-----|
| 1     | 4   | icon gap, tight spacing |
| 2     | 8   | compact padding |
| 3     | 12  | small gap |
| 4     | 16  | standard gap |
| 5     | 20  | card inner gap |
| 6     | 24  | card padding |
| 8     | 32  | section gap |
| 10    | 40  | large gap |
| 12    | 48  | section padding |
| 16    | 64  | large section |
| 20    | 80  | hero padding |
| 24    | 96  | xl section |

## Typography Scale

| Class | Size | Weight | Use |
|-------|------|--------|-----|
| text-xs | 12px | — | captions, badges |
| text-sm | 14px | medium | labels, secondary |
| text-base | 16px | — | body |
| text-lg | 18px | semibold | card titles |
| text-xl | 20px | semibold | section subtitles |
| text-2xl | 24px | bold | page titles |
| text-3xl | 30px | bold | section headings |
| text-4xl | 36px | bold | hero subheadings |
| text-5xl | 48px | bold | hero headings |
| text-6xl | 60px | bold | landing hero |

## Z-Index Scale

```
z-0    base content
z-10   sticky elements (cards on hover)
z-20   dropdowns, tooltips
z-30   sticky headers
z-40   drawers, sidebars
z-50   modals, overlays
```

## Breakpoints

```
sm   640px   tablet portrait
md   768px   tablet landscape
lg   1024px  desktop
xl   1280px  wide desktop
2xl  1536px  ultra-wide
```
