---
name: nextjs-ui-polish
description: |
  Polishes Next.js/React UI: fixes duplicate navbars, redesigns admin dashboards, and applies modern Tailwind CSS design patterns. This skill should be used when users want to improve the visual quality of their Next.js portals, fix layout issues like double navigation bars, or make admin/user interfaces look professional and modern.
---

# Next.js UI Polish Skill

## What This Skill Does
- Fixes duplicate/double navigation bar issues in Next.js layouts
- Redesigns plain admin dashboards into polished, modern UIs
- Applies consistent design tokens (spacing, color, typography, shadows)
- Improves sidebar navigation with active states, icons, and branding
- Upgrades tables, stat cards, and data displays

## Before Implementation

| Source | Gather |
|--------|--------|
| **Codebase** | `layout.tsx`, `sidebar.tsx`, `navbar.tsx`, page components, `globals.css` |
| **Conversation** | Which portals need fixing, specific pain points |
| **Skill References** | Patterns below |

## Double Navbar Fix Pattern

The most common cause: `layout.tsx` renders `<Navbar />` globally, AND individual pages also render their own nav. Fix by:

1. Check `layout.tsx` — if `<Navbar />` is there, it applies to ALL pages
2. Check each page for its own nav/header rendering
3. For pages that need NO nav (login, register), use a `LayoutShell` pattern:

```tsx
// layout-shell.tsx
const NO_NAV_ROUTES = ['/login', '/register', '/signup'];
export function LayoutShell({ children }) {
  const pathname = usePathname();
  if (NO_NAV_ROUTES.includes(pathname)) return <>{children}</>;
  return (
    <>
      <Navbar />
      <main>{children}</main>
    </>
  );
}
```

4. Move `<Navbar />` OUT of `layout.tsx` and INTO `LayoutShell`
5. Remove any per-page nav renders

## Admin Sidebar Upgrade Pattern

Transform plain gray sidebar into polished design:

```tsx
// Modern sidebar with gradient brand header + active states
<aside className="w-64 h-screen bg-white border-r border-gray-100 flex flex-col shadow-sm">
  {/* Brand */}
  <div className="h-16 flex items-center px-6 border-b border-gray-100">
    <div className="flex items-center gap-3">
      <div className="h-8 w-8 rounded-lg bg-gradient-to-br from-violet-600 to-indigo-600 flex items-center justify-center">
        <Icon className="h-4 w-4 text-white" />
      </div>
      <span className="font-bold text-gray-900">Admin Portal</span>
    </div>
  </div>
  {/* Nav items */}
  <nav className="flex-1 px-3 py-4 space-y-1">
    <Link className={cn(
      "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
      isActive
        ? "bg-violet-50 text-violet-700 shadow-sm"
        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
    )}>
      <Icon className={cn("h-5 w-5", isActive ? "text-violet-600" : "text-gray-400")} />
      {name}
    </Link>
  </nav>
</aside>
```

## Stat Card Pattern

```tsx
<div className="rounded-2xl bg-white border border-gray-100 p-6 shadow-sm hover:shadow-md transition-shadow">
  <div className="flex items-center justify-between mb-4">
    <div className={`h-12 w-12 rounded-xl flex items-center justify-center ${colorClass}`}>
      <Icon className="h-6 w-6" />
    </div>
    <span className="text-xs font-medium text-green-600 bg-green-50 px-2 py-1 rounded-full">
      {trend}
    </span>
  </div>
  <p className="text-2xl font-bold text-gray-900">{value}</p>
  <p className="text-sm text-gray-500 mt-1">{label}</p>
</div>
```

## Table Upgrade Pattern

Replace plain `<table>` with styled version:
- Header: `bg-gray-50` with `text-xs uppercase tracking-wider text-gray-500`
- Rows: `hover:bg-gray-50 transition-colors`
- Status badges: colored `rounded-full px-2.5 py-0.5 text-xs font-medium`
- Action buttons: icon buttons with hover color rings

## Color Palette (Tailwind)

| Use | Classes |
|-----|---------|
| Primary | `violet-600`, `indigo-600` |
| Success | `green-500`, `emerald-500` |
| Warning | `amber-500`, `yellow-500` |
| Danger | `red-500`, `rose-500` |
| Neutral bg | `gray-50`, `gray-100` |
| Card bg | `white` with `border-gray-100` |
| Text primary | `gray-900` |
| Text secondary | `gray-500` |

## Anti-Patterns to Fix

- `bg-gray-900` sidebar → use `bg-white` with border for modern look
- Hardcoded `text-gray-300` nav items → use semantic active/inactive states
- Missing hover transitions → add `transition-all duration-150`
- No border-radius on cards → use `rounded-2xl`
- Missing shadows → use `shadow-sm` on cards, `shadow-lg` on dropdowns
