/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#0a0a0b',
        surface: 'rgba(255, 255, 255, 0.02)',
        ink: '#ffffff',
        body: '#a1a1aa',
        muted: '#71717a',
        hairline: 'rgba(255, 255, 255, 0.08)',
        risk: { low: '#10b981', medium: '#f59e0b', high: '#f43f5e' },
        accent: { indigo: '#6366f1', cyan: '#22d3ee', violet: '#8b5cf6' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Geist Mono', 'monospace'],
      },
      maxWidth: { content: '1200px' },
      spacing: { section: '96px' },
    },
  },
  plugins: [],
};
