/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: 'var(--canvas)',
        surface: 'var(--surface)',
        'surface-elevated': 'var(--surface-elevated)',
        ink: 'var(--ink)',
        body: 'var(--body)',
        muted: 'var(--muted)',
        hairline: 'var(--hairline)',
        primary: 'var(--accent)',
        risk: { low: 'var(--risk-low)', medium: 'var(--risk-medium)', high: 'var(--risk-high)' },
        accent: { indigo: 'var(--accent)', cyan: 'var(--accent)', violet: 'var(--accent-hover)' },
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
