/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Brand - Sky Blue (matching interlinking style)
        brand: {
          1: '#38BDF8',  // Primary sky blue
          2: '#7DD3FC',  // Lighter sky blue
          3: '#BAE6FD',  // Lightest sky blue
        },
        // Page backgrounds (dark theme)
        page: '#030303',
        card: '#0A0A0A',
        surface: '#111111',
        input: '#1A1A1A',
        // Borders
        border: {
          DEFAULT: '#222222',
          dim: '#1A1A1A',
          bright: '#333333',
        },
        // Text
        text: {
          DEFAULT: '#FFFFFF',
          secondary: '#A3A3A3',
          muted: '#666666',
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
          DEFAULT: '#030303',
          secondary: '#0A0A0A',
          tertiary: '#111111',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
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
