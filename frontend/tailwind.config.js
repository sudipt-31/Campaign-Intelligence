/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Syne"', 'sans-serif'],
        body:    ['"DM Sans"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        ink:    '#F8FAFC',
        panel:  '#FFFFFF',
        card:   '#FFFFFF',
        border: '#E2E8F0',
        muted:  '#F1F5F9',
        text:   '#0F172A',
        dim:    '#475569',
        accent: '#1E3A8A',
        gold:   '#D97706',
        rose:   '#E11D48',
        sage:   '#7C3AED',
      },
      backgroundImage: {
        'grid-pattern': `
          linear-gradient(rgba(30, 58, 138, 0.05) 1px, transparent 1px),
          linear-gradient(90deg, rgba(30, 58, 138, 0.05) 1px, transparent 1px)
        `,
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      animation: {
        'fade-up':    'fadeUp 0.5s ease forwards',
        'fade-in':    'fadeIn 0.4s ease forwards',
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'scan':       'scan 2s linear infinite',
        'blink':      'blink 1s step-end infinite',
        'slide-in':   'slideIn 0.4s cubic-bezier(0.16,1,0.3,1) forwards',
      },
      keyframes: {
        fadeUp:  { from: { opacity: 0, transform: 'translateY(16px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        fadeIn:  { from: { opacity: 0 }, to: { opacity: 1 } },
        scan:    { from: { transform: 'translateY(-100%)' }, to: { transform: 'translateY(400%)' } },
        blink:   { '0%,100%': { opacity: 1 }, '50%': { opacity: 0 } },
        slideIn: { from: { opacity: 0, transform: 'translateX(-12px)' }, to: { opacity: 1, transform: 'translateX(0)' } },
      },
      boxShadow: {
        'accent':  '0 0 20px rgba(30, 58, 138, 0.15)',
        'gold':    '0 0 20px rgba(217, 119, 6, 0.15)',
        'card':    '0 4px 24px rgba(0, 0, 0, 0.05)',
        'inset':   'inset 0 1px 0 rgba(0, 0, 0, 0.05)',
      },
    },
  },
  plugins: [],
}  