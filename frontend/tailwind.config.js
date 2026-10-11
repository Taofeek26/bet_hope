// rgb(var(--<name>-rgb) / <alpha-value>) — see globals.css
const tok = (name) => `rgb(var(--${name}-rgb) / <alpha-value>)`;

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    screens: {
      'xs': '480px',
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
    },
    extend: {
      colors: {
        // Every theme colour is rgb(var(--x-rgb) / <alpha-value>) (Phase 4,
        // UI-01/02): the CSS variables let Settings > Appearance > Theme
        // flip colours at runtime, and the channel form lets Tailwind apply
        // opacity (bg-brand/10, bg-surface/50). Plain var(--x) values made
        // Tailwind silently drop every /NN class.
        brand: {
          DEFAULT: tok('brand1'), // bg-brand, text-brand, border-brand/40 ...
          1: tok('brand1'),
          2: tok('brand2'),
          3: tok('brand3'),
        },
        brand1: tok('brand1'),    // legacy name used in a few components
        bg: tok('page'),          // text-bg = text in page colour (on brand fills)
        page: tok('page'),
        card: tok('card'),
        'card-hover': tok('input'),
        surface: { DEFAULT: tok('surface'), alt: tok('input') },
        input: tok('input'),
        // Borders
        border: {
          DEFAULT: tok('border'),
          dim: tok('border-dim'),
          bright: tok('border-bright'),
        },
        // Text (sec / primary are aliases already used across the pages)
        text: {
          DEFAULT: tok('text'),
          primary: tok('text'),
          secondary: tok('text-sec'),
          sec: tok('text-sec'),
          muted: tok('text-muted'),
        },
        // Primary - Sky Blue
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
          950: '#082f49',
        },
        // Accent - Also Sky Blue (lighter shade)
        accent: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Result colors
        win: '#38BDF8',
        draw: '#94A3B8',
        loss: '#ef4444',
        // Status colors
        success: '#38BDF8',
        error: '#dc2626',
        warning: '#f59e0b',
        info: '#7DD3FC',
        // Background
        background: {
          DEFAULT: tok('page'),
          secondary: tok('card'),
          tertiary: tok('surface'),
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains-mono)', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-in-out',
        'slide-up': 'slideUp 0.5s ease-out',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { transform: 'translateY(20px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
