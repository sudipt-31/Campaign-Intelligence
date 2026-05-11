/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"Outfit"', 'sans-serif'],
        body:    ['"Plus Jakarta Sans"', 'sans-serif'],
        mono:    ['"JetBrains Mono"', 'monospace'],
      },
      colors: {
        ink:    '#FAF9F6',
        panel:  '#FFFFFF',
        card:   '#FFFFFF',
        border: '#EDE9E6',
        muted:  '#F3F1EF',
        text:   '#332D2D',
        dim:    '#7C726A',
        accent: '#F59E0B',
        gold:   '#D97706',
        rose:   '#EF4444',
        sage:   '#10B981',
        indigo: '#6366F1',
      },
      backgroundImage: {
        'soft-glow': 'radial-gradient(circle at top, rgba(245, 158, 11, 0.05) 0%, transparent 70%)',
      },
      backgroundSize: {
        'grid': '40px 40px',
      },
      animation: {
        'fade-up':    'fadeUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards',
        'fade-in':    'fadeIn 0.5s ease-out forwards',
        'pulse-slow': 'pulse 4s cubic-bezier(0.4,0,0.6,1) infinite',
        'bounce-soft': 'bounceSoft 2s ease-in-out infinite',
      },
      keyframes: {
        fadeUp:  { from: { opacity: 0, transform: 'translateY(20px)' }, to: { opacity: 1, transform: 'translateY(0)' } },
        fadeIn:  { from: { opacity: 0 }, to: { opacity: 1 } },
        bounceSoft: { '0%, 100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-4px)' } },
      },
      boxShadow: {
        'soft':    '0 4px 20px -2px rgba(45, 40, 37, 0.05), 0 2px 8px -2px rgba(45, 40, 37, 0.03)',
        'card':    '0 10px 30px -5px rgba(45, 40, 37, 0.08), 0 4px 12px -4px rgba(45, 40, 37, 0.04)',
        'accent':  '0 0 20px rgba(245, 158, 11, 0.15)',
        'inset-soft': 'inset 0 2px 4px 0 rgba(45, 40, 37, 0.02)',
      },
    },
  },
  plugins: [],
}  