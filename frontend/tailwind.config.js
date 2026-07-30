/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#FBF7F0',
          secondary: '#FFF9F0',
          tertiary: '#F5EEE0',
        },
        primary: {
          DEFAULT: '#C9622A',
          dark: '#A04A1E',
          light: '#EFA882',
          muted: '#D4A484',
        },
        foreground: {
          DEFAULT: '#2C1810',
          secondary: '#5A4032',
          tertiary: '#8B7355',
          disabled: '#BFA98F',
        },
        border: {
          DEFAULT: '#D4C5B0',
          light: '#E8DFD0',
          dark: '#8B7355',
        },
        success: '#6B8E6B',
        warning: '#C9A227',
        error: '#B85450',
        info: '#7A8B99',
      },
      fontFamily: {
        display: ['Georgia', 'Times New Roman', 'Noto Serif SC', 'Songti SC', 'serif'],
        body: ['-apple-system', 'BlinkMacSystemFont', 'PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        mono: ['SF Mono', 'Consolas', 'Monaco', 'Courier New', 'monospace'],
      },
      borderRadius: {
        'sm': '4px',
        'md': '8px',
        'lg': '16px',
      },
      animation: {
        'stamp-drop': 'stampDrop 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards',
        'float': 'float 3s infinite ease-in-out',
      },
      keyframes: {
        stampDrop: {
          '0%': { opacity: '0', transform: 'scale(3) rotate(-45deg)', filter: 'blur(4px)' },
          '70%': { opacity: '0.9', transform: 'scale(0.9) rotate(-12deg)', filter: 'blur(0px)' },
          '85%': { transform: 'scale(1.1) rotate(-17deg)' },
          '100%': { opacity: '0.85', transform: 'scale(1) rotate(-15deg)' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-8px)' },
        },
      },
    },
  },
  plugins: [],
}