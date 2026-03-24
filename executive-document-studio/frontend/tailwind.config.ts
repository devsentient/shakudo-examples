import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './lib/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: '#adc6ff',
        'primary-strong': '#357df1',
        secondary: '#4edea3',
        'secondary-deep': '#00a572',
        ghost: '#45464d',
        studio: {
          950: '#050b18',
          900: '#0b1326',
          850: '#131b2e',
          820: '#182236',
          800: '#1d2740',
          780: '#202b40',
          760: '#060e20',
          720: '#253147',
          680: '#31405d',
          300: '#d8deea',
          200: '#c6c6cd',
          100: '#eef3ff',
        },
        accent: {
          blue: '#adc6ff',
          cyan: '#357df1',
          violet: '#6f7fe8',
          green: '#4edea3',
          amber: '#f5c978',
        },
      },
      boxShadow: {
        chrome: '0 32px 90px rgba(0, 67, 149, 0.18)',
        panel: '0 24px 56px rgba(0, 67, 149, 0.10)',
        float: '0 24px 48px rgba(0, 67, 149, 0.08)',
        glow: '0 18px 48px rgba(53, 125, 241, 0.22), inset 0 0 0 1px rgba(173, 198, 255, 0.12)',
      },
      backgroundImage: {
        grid: 'linear-gradient(rgba(198,198,205,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(198,198,205,0.03) 1px, transparent 1px)',
        noise: 'radial-gradient(circle at top left, rgba(173,198,255,0.16), transparent 30%), radial-gradient(circle at bottom right, rgba(78,222,163,0.08), transparent 22%), radial-gradient(circle at 80% 10%, rgba(53,125,241,0.12), transparent 24%)',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      fontFamily: {
        sans: ['var(--font-inter)'],
        mono: ['var(--font-mono)'],
      },
    },
  },
  plugins: [],
}

export default config
