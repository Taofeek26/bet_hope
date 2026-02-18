# Bet_Hope Styling Guide

## Overview

Uses Tailwind CSS with a custom design system.

---

## Design System

### Colors

```typescript
// tailwind.config.ts
const colors = {
  // Primary - Green (Success/Wins)
  primary: {
    50: '#f0fdf4',
    100: '#dcfce7',
    200: '#bbf7d0',
    300: '#86efac',
    400: '#4ade80',
    500: '#22c55e',  // Main
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
  },

  // Secondary - Blue (Away/Info)
  secondary: {
    50: '#eff6ff',
    100: '#dbeafe',
    200: '#bfdbfe',
    300: '#93c5fd',
    400: '#60a5fa',
    500: '#3b82f6',  // Main
    600: '#2563eb',
    700: '#1d4ed8',
    800: '#1e40af',
    900: '#1e3a8a',
  },

  // Warning - Yellow (Draws)
  warning: {
    50: '#fefce8',
    100: '#fef9c3',
    200: '#fef08a',
    300: '#fde047',
    400: '#facc15',
    500: '#eab308',  // Main
    600: '#ca8a04',
    700: '#a16207',
    800: '#854d0e',
    900: '#713f12',
  },

  // Danger - Red (Losses/Errors)
  danger: {
    50: '#fef2f2',
    100: '#fee2e2',
    200: '#fecaca',
    300: '#fca5a5',
    400: '#f87171',
    500: '#ef4444',  // Main
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d',
  },

  // Neutral - Gray
  gray: {
    50: '#f9fafb',
    100: '#f3f4f6',
    200: '#e5e7eb',
    300: '#d1d5db',
    400: '#9ca3af',
    500: '#6b7280',
    600: '#4b5563',
    700: '#374151',
    800: '#1f2937',
    900: '#111827',
  },
};
```

### Semantic Colors

```css
/* Match Outcomes */
--color-home-win: theme('colors.primary.500');    /* Green */
--color-draw: theme('colors.warning.400');         /* Yellow */
--color-away-win: theme('colors.secondary.500');   /* Blue */

/* Confidence Levels */
--color-high-confidence: theme('colors.primary.500');
--color-medium-confidence: theme('colors.warning.500');
--color-low-confidence: theme('colors.gray.400');

/* Status */
--color-live: theme('colors.danger.500');
--color-finished: theme('colors.gray.500');
--color-scheduled: theme('colors.secondary.500');
```

---

### Typography

```typescript
// tailwind.config.ts
const typography = {
  fontFamily: {
    sans: ['Inter', 'system-ui', 'sans-serif'],
    mono: ['JetBrains Mono', 'monospace'],
  },

  fontSize: {
    xs: ['0.75rem', { lineHeight: '1rem' }],
    sm: ['0.875rem', { lineHeight: '1.25rem' }],
    base: ['1rem', { lineHeight: '1.5rem' }],
    lg: ['1.125rem', { lineHeight: '1.75rem' }],
    xl: ['1.25rem', { lineHeight: '1.75rem' }],
    '2xl': ['1.5rem', { lineHeight: '2rem' }],
    '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
    '4xl': ['2.25rem', { lineHeight: '2.5rem' }],
    '5xl': ['3rem', { lineHeight: '1' }],
  },
};
```

**Typography Usage:**

```tsx
// Headings
<h1 className="text-3xl font-bold text-gray-900">Page Title</h1>
<h2 className="text-2xl font-semibold text-gray-900">Section Title</h2>
<h3 className="text-xl font-semibold text-gray-900">Card Title</h3>
<h4 className="text-lg font-medium text-gray-900">Subsection</h4>

// Body
<p className="text-base text-gray-600">Regular text</p>
<p className="text-sm text-gray-500">Secondary text</p>
<p className="text-xs text-gray-400">Caption text</p>

// Special
<span className="text-2xl font-bold tabular-nums">2-1</span>  // Scores
<span className="text-sm font-medium uppercase tracking-wide">Label</span>
```

---

### Spacing

```typescript
// Consistent spacing scale
const spacing = {
  px: '1px',
  0: '0',
  0.5: '0.125rem',  // 2px
  1: '0.25rem',     // 4px
  1.5: '0.375rem',  // 6px
  2: '0.5rem',      // 8px
  2.5: '0.625rem',  // 10px
  3: '0.75rem',     // 12px
  3.5: '0.875rem',  // 14px
  4: '1rem',        // 16px
  5: '1.25rem',     // 20px
  6: '1.5rem',      // 24px
  7: '1.75rem',     // 28px
  8: '2rem',        // 32px
  9: '2.25rem',     // 36px
  10: '2.5rem',     // 40px
  11: '2.75rem',    // 44px
  12: '3rem',       // 48px
  14: '3.5rem',     // 56px
  16: '4rem',       // 64px
  20: '5rem',       // 80px
  24: '6rem',       // 96px
};
```

**Spacing Guidelines:**

```css
/* Component internal padding */
.card { @apply p-4 md:p-6; }
.button { @apply px-4 py-2; }
.input { @apply px-3 py-2; }

/* Section spacing */
.section { @apply py-12 md:py-16; }
.page-content { @apply space-y-6; }

/* Grid gaps */
.card-grid { @apply gap-4 md:gap-6; }
.form-fields { @apply space-y-4; }
```

---

### Shadows

```typescript
const boxShadow = {
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  DEFAULT: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
};
```

**Shadow Usage:**

```tsx
// Cards
<div className="shadow-sm hover:shadow-md transition-shadow">Card</div>

// Modals/Dropdowns
<div className="shadow-xl">Modal</div>

// Elevated buttons
<button className="shadow hover:shadow-md">Button</button>
```

---

### Border Radius

```typescript
const borderRadius = {
  none: '0',
  sm: '0.125rem',   // 2px
  DEFAULT: '0.25rem', // 4px
  md: '0.375rem',   // 6px
  lg: '0.5rem',     // 8px
  xl: '0.75rem',    // 12px
  '2xl': '1rem',    // 16px
  '3xl': '1.5rem',  // 24px
  full: '9999px',
};
```

**Border Radius Usage:**

```tsx
// Buttons
<button className="rounded-lg">Button</button>

// Cards
<div className="rounded-xl">Card</div>

// Avatars/Badges
<span className="rounded-full">Badge</span>

// Inputs
<input className="rounded-md" />
```

---

## Tailwind Configuration

```typescript
// tailwind.config.ts
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: { /* see above */ },
        secondary: { /* see above */ },
        warning: { /* see above */ },
        danger: { /* see above */ },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'bounce-slow': 'bounce 2s infinite',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};

export default config;
```

---

## Global Styles

```css
/* app/globals.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 142.1 76.2% 36.3%;
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 142.1 70.6% 45.3%;
  }

  * {
    @apply border-border;
  }

  body {
    @apply bg-background text-foreground antialiased;
  }

  /* Custom scrollbar */
  ::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  ::-webkit-scrollbar-track {
    @apply bg-gray-100;
  }

  ::-webkit-scrollbar-thumb {
    @apply bg-gray-300 rounded-full;
  }

  ::-webkit-scrollbar-thumb:hover {
    @apply bg-gray-400;
  }
}

@layer components {
  /* Card */
  .card {
    @apply bg-white rounded-xl shadow-sm border border-gray-100;
  }

  .card-hover {
    @apply card hover:shadow-md transition-shadow cursor-pointer;
  }

  /* Buttons */
  .btn {
    @apply inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none;
  }

  .btn-primary {
    @apply btn bg-primary-500 text-white hover:bg-primary-600 focus:ring-primary-500;
  }

  .btn-secondary {
    @apply btn bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-500;
  }

  .btn-outline {
    @apply btn border border-gray-300 bg-transparent hover:bg-gray-50 focus:ring-gray-500;
  }

  .btn-ghost {
    @apply btn bg-transparent hover:bg-gray-100 focus:ring-gray-500;
  }

  .btn-sm {
    @apply h-8 px-3 text-sm;
  }

  .btn-md {
    @apply h-10 px-4 text-sm;
  }

  .btn-lg {
    @apply h-12 px-6 text-base;
  }

  /* Inputs */
  .input {
    @apply w-full rounded-md border border-gray-300 px-3 py-2 text-sm placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-50 disabled:cursor-not-allowed;
  }

  .input-error {
    @apply input border-danger-500 focus:ring-danger-500;
  }

  /* Labels */
  .label {
    @apply block text-sm font-medium text-gray-700 mb-1;
  }

  /* Badges */
  .badge {
    @apply inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium;
  }

  .badge-success {
    @apply badge bg-green-100 text-green-800;
  }

  .badge-warning {
    @apply badge bg-yellow-100 text-yellow-800;
  }

  .badge-danger {
    @apply badge bg-red-100 text-red-800;
  }

  .badge-info {
    @apply badge bg-blue-100 text-blue-800;
  }

  /* Links */
  .link {
    @apply text-primary-500 hover:text-primary-600 hover:underline;
  }

  /* Probability Bar Segments */
  .prob-home {
    @apply bg-primary-500;
  }

  .prob-draw {
    @apply bg-warning-400;
  }

  .prob-away {
    @apply bg-secondary-500;
  }

  /* Form indicator */
  .form-w {
    @apply bg-primary-500 text-white;
  }

  .form-d {
    @apply bg-warning-400 text-gray-900;
  }

  .form-l {
    @apply bg-danger-500 text-white;
  }

  /* Live indicator */
  .live-pulse {
    @apply relative flex h-2 w-2;
  }

  .live-pulse::before {
    @apply absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75 animate-ping;
    content: '';
  }

  .live-pulse::after {
    @apply relative inline-flex rounded-full h-2 w-2 bg-red-500;
    content: '';
  }
}

@layer utilities {
  /* Text balance */
  .text-balance {
    text-wrap: balance;
  }

  /* Tabular numbers for scores */
  .tabular-nums {
    font-variant-numeric: tabular-nums;
  }

  /* Hide scrollbar */
  .hide-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }

  .hide-scrollbar::-webkit-scrollbar {
    display: none;
  }

  /* Gradient text */
  .gradient-text {
    @apply bg-clip-text text-transparent bg-gradient-to-r from-primary-500 to-secondary-500;
  }
}
```

---

## Component Patterns

### Card Patterns

```tsx
// Standard Card
<div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
  {/* content */}
</div>

// Hover Card
<div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 hover:shadow-md transition-shadow cursor-pointer">
  {/* content */}
</div>

// Bordered Card (with accent)
<div className="bg-white rounded-xl shadow-sm border-l-4 border-l-primary-500 border border-gray-100 p-6">
  {/* content */}
</div>

// Glass Card (for overlays)
<div className="bg-white/80 backdrop-blur-sm rounded-xl shadow-lg p-6">
  {/* content */}
</div>
```

---

### Form Patterns

```tsx
// Input Group
<div className="space-y-1">
  <label className="block text-sm font-medium text-gray-700">
    Email
  </label>
  <input
    type="email"
    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
    placeholder="you@example.com"
  />
  <p className="text-xs text-gray-500">
    We'll never share your email
  </p>
</div>

// Input with error
<div className="space-y-1">
  <label className="block text-sm font-medium text-gray-700">
    Password
  </label>
  <input
    type="password"
    className="w-full rounded-md border border-danger-500 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-danger-500"
  />
  <p className="text-xs text-danger-500">
    Password is required
  </p>
</div>

// Select
<select className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500">
  <option>Select league</option>
  <option>Premier League</option>
  <option>La Liga</option>
</select>
```

---

### Table Patterns

```tsx
<div className="overflow-x-auto">
  <table className="w-full">
    <thead>
      <tr className="border-b border-gray-200">
        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
          Team
        </th>
        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
          P
        </th>
        <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
          Pts
        </th>
      </tr>
    </thead>
    <tbody className="divide-y divide-gray-100">
      <tr className="hover:bg-gray-50 transition-colors">
        <td className="px-4 py-4 text-sm font-medium text-gray-900">
          Arsenal
        </td>
        <td className="px-4 py-4 text-sm text-gray-500 text-center">
          21
        </td>
        <td className="px-4 py-4 text-sm font-semibold text-gray-900 text-center">
          52
        </td>
      </tr>
    </tbody>
  </table>
</div>
```

---

### Grid Patterns

```tsx
// Card Grid - Responsive
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
  {items.map(item => <Card key={item.id} />)}
</div>

// Dashboard Grid
<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
  <div className="lg:col-span-2">{/* Main content */}</div>
  <div>{/* Sidebar */}</div>
</div>

// Stats Grid
<div className="grid grid-cols-2 md:grid-cols-4 gap-4">
  <StatCard />
  <StatCard />
  <StatCard />
  <StatCard />
</div>
```

---

### Animation Patterns

```tsx
// Fade in
<div className="animate-in fade-in duration-500">
  Content
</div>

// Slide up
<div className="animate-in slide-in-from-bottom duration-300">
  Content
</div>

// Pulse (loading)
<div className="animate-pulse bg-gray-200 rounded h-4 w-full" />

// Spin (loading)
<svg className="animate-spin h-5 w-5 text-primary-500">
  {/* spinner icon */}
</svg>

// Live indicator
<span className="relative flex h-2 w-2">
  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
</span>
```

---

## Dark Mode

```tsx
// Component with dark mode support
<div className="bg-white dark:bg-gray-800 text-gray-900 dark:text-white">
  <h2 className="text-gray-900 dark:text-white">Title</h2>
  <p className="text-gray-600 dark:text-gray-300">Description</p>
</div>

// Card with dark mode
<div className="bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl shadow-sm">
  {/* content */}
</div>

// Button with dark mode
<button className="bg-primary-500 hover:bg-primary-600 dark:bg-primary-600 dark:hover:bg-primary-500 text-white">
  Button
</button>
```

---

## Responsive Design

### Breakpoints

```typescript
const screens = {
  sm: '640px',   // Mobile landscape
  md: '768px',   // Tablet
  lg: '1024px',  // Desktop
  xl: '1280px',  // Large desktop
  '2xl': '1536px', // Extra large
};
```

### Mobile-First Patterns

```tsx
// Hide on mobile, show on desktop
<div className="hidden md:block">Desktop only</div>

// Show on mobile, hide on desktop
<div className="md:hidden">Mobile only</div>

// Responsive padding
<div className="p-4 md:p-6 lg:p-8">Content</div>

// Responsive font size
<h1 className="text-2xl md:text-3xl lg:text-4xl">Title</h1>

// Responsive grid
<div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
  {/* items */}
</div>

// Stack to row
<div className="flex flex-col md:flex-row gap-4">
  <div>Item 1</div>
  <div>Item 2</div>
</div>
```

---

## Best Practices

### 1. Use Utility Classes

```tsx
// ✅ Good - Utility classes
<button className="bg-primary-500 text-white px-4 py-2 rounded-lg hover:bg-primary-600">
  Submit
</button>

// ❌ Avoid - Custom CSS when not needed
<button className="submit-button">
  Submit
</button>
```

### 2. Extract Components, Not Classes

```tsx
// ✅ Good - Create component
function Button({ children }) {
  return (
    <button className="bg-primary-500 text-white px-4 py-2 rounded-lg hover:bg-primary-600">
      {children}
    </button>
  );
}

// ❌ Avoid - @apply for everything
/* .btn { @apply bg-primary-500 text-white px-4 py-2 rounded-lg hover:bg-primary-600; } */
```

### 3. Consistent Spacing

```tsx
// ✅ Good - Consistent spacing
<div className="space-y-6">
  <Section />
  <Section />
  <Section />
</div>

// ❌ Avoid - Arbitrary values
<div>
  <Section className="mb-7" />
  <Section className="mb-5" />
</div>
```

### 4. Semantic Color Usage

```tsx
// ✅ Good - Semantic meaning
<Badge className="bg-primary-100 text-primary-800">Win</Badge>
<Badge className="bg-warning-100 text-warning-800">Draw</Badge>
<Badge className="bg-danger-100 text-danger-800">Loss</Badge>

// ❌ Avoid - Arbitrary colors
<Badge className="bg-green-100 text-green-800">Win</Badge>
<Badge className="bg-amber-100 text-amber-800">Draw</Badge>
```
