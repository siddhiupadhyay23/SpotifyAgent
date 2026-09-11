/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        /* Light palette — editorial hero/sections */
        paper:   '#fafaf9',
        canvas:  '#f5f4f2',
        white:   '#ffffff',
        ink:     '#111110',
        ink2:    '#3d3d3a',
        ink3:    '#6b6b67',
        rule:    '#e8e6e1',
        'rule-2':'#d4d0c8',

        /* Dark palette — app workspace */
        void:    '#09090b',
        dark:    '#111115',
        dark2:   '#17171c',
        dark3:   '#1f1f26',
        dgray:   '#2a2a35',
        dline:   'rgba(255,255,255,0.08)',
        dtxt:    '#f4f4f5',
        dtxt2:   '#a1a1aa',
        dtxt3:   '#52525b',

        /* Accent */
        accent: {
          50:  '#eff6ff',
          100: '#dbeafe',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          glow:'rgba(59,130,246,0.3)',
        },

        /* Status */
        go:   { DEFAULT: '#16a34a', bg: '#f0fdf4', text: '#15803d' },
        hold: { DEFAULT: '#d97706', bg: '#fffbeb', text: '#b45309' },
        stop: { DEFAULT: '#dc2626', bg: '#fef2f2', text: '#b91c1c' },
      },
      fontSize: {
        '10': ['10px', '14px'],
        '11': ['11px', '15px'],
        '12': ['12px', '16px'],
        '13': ['13px', '18px'],
        '14': ['14px', '20px'],
        '15': ['15px', '22px'],
        '17': ['17px', '24px'],
        '20': ['20px', '26px'],
        '24': ['24px', '30px'],
        '32': ['32px', '38px'],
        '40': ['40px', '46px'],
        '52': ['52px', '56px'],
        '64': ['64px', '68px'],
        '80': ['80px', '82px'],
        '96': ['96px', '96px'],
      },
      letterSpacing: {
        tightest: '-0.05em',
        tighter:  '-0.035em',
        tight:    '-0.02em',
        caps:     '0.08em',
        widest:   '0.15em',
      },
      boxShadow: {
        'card':   '0 1px 2px rgba(0,0,0,0.06), 0 2px 4px rgba(0,0,0,0.04)',
        'lift':   '0 4px 12px rgba(0,0,0,0.08)',
        'dark-card': '0 1px 3px rgba(0,0,0,0.5), 0 1px 2px rgba(0,0,0,0.3)',
        'glow':   '0 0 24px rgba(59,130,246,0.25)',
        'inner-t':'inset 0 1px 0 rgba(255,255,255,0.07)',
      },
      backgroundImage: {
        'dot-light': "radial-gradient(circle, #d4d0c8 1px, transparent 1px)",
        'dot-dark':  "radial-gradient(circle, rgba(255,255,255,0.06) 1px, transparent 1px)",
        'top-glow':  'radial-gradient(ellipse 70% 35% at 50% 0%, rgba(59,130,246,0.1) 0%, transparent 65%)',
        'noise':     "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E\")",
      },
      backgroundSize: {
        'dot': '20px 20px',
      },
      animation: {
        'in-up':   'in-up 0.4s cubic-bezier(0.23,1,0.32,1) both',
        'shimmer': 'shimmer 2s ease-in-out infinite',
        'ping-slow':'ping 2.5s cubic-bezier(0,0,0.2,1) infinite',
      },
      keyframes: {
        'in-up': {
          '0%':   { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%,100%': { opacity: '1' },
          '50%':     { opacity: '0.3' },
        },
      },
    },
  },
  plugins: [],
}
