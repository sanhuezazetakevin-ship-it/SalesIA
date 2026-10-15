/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Paleta Vitromorfosis (Glassmorphism cobre / terracota / espresso / crema)
        vitro: {
          bgDark: '#0D0806',
          bgDarkElevated: '#140C08',
          cardDark: '#1A100B',
          cardDarkBorder: 'rgba(217, 120, 67, 0.22)',
          bgLight: '#FAF6F2',
          bgLightElevated: '#F5EBE1',
          cardLight: '#FFFFFF',
          cardLightBorder: 'rgba(217, 120, 67, 0.18)',
          copper: {
            DEFAULT: '#D97843',
            50: '#FDF8F5',
            100: '#F8ECE4',
            200: '#F2D7C7',
            300: '#EABCA3',
            400: '#EE915B',
            500: '#D97843', // Color principal cobre / terracota
            600: '#C66532',
            700: '#A8542A',
            800: '#8A4522',
            900: '#5A2B14',
            950: '#261107',
          },
          espresso: {
            50: '#F6F3F1',
            100: '#ECE6E2',
            200: '#D9CCC4',
            300: '#BAA89E',
            400: '#8C776D',
            500: '#5E4A40',
            600: '#3D2F28',
            700: '#2A1F19',
            800: '#1C130E',
            900: '#140C08',
            950: '#0D0806',
          },
          cream: {
            50: '#FFFCF9',
            100: '#FAF6F2',
            200: '#F5EBE1',
            300: '#EDE0D3',
            400: '#E0CEBE',
            500: '#D1BCAB',
          },
          jade: {
            50: '#F0F7F4',
            100: '#DCEEE7',
            200: '#BCDDD0',
            300: '#91C4B1',
            400: '#5FA68E',
            500: '#3D8972', // Tono verdoso medio elegante de la referencia
            600: '#2E6F5C',
            700: '#235849',
            800: '#1B453A',
            900: '#14342C',
            950: '#0B1F1A',
          },
        },
        surface: {
          DEFAULT: '#FAF6F2',
          dark: '#0D0806',
        },
        card: {
          DEFAULT: '#FFFFFF',
          dark: '#140C08',
        },
        accent: {
          DEFAULT: '#D97843',
          light: '#EE915B',
          dark: '#A8542A',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'vitro-glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'vitro-glass-light': '0 8px 32px 0 rgba(168, 84, 42, 0.08)',
        'vitro-glow': '0 0 20px rgba(217, 120, 67, 0.3)',
        'vitro-glow-lg': '0 0 40px rgba(217, 120, 67, 0.45)',
        'vitro-glow-subtle': '0 0 15px rgba(217, 120, 67, 0.15)',
        glass: '0 8px 32px rgba(0,0,0,0.2)',
        glow: '0 0 15px rgba(217, 120, 67, 0.35)',
        'glow-lg': '0 0 30px rgba(217, 120, 67, 0.45)',
        'glow-blue': '0 0 15px rgba(217, 120, 67, 0.3)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(12px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backdropBlur: {
        '2xl': '40px',
        '3xl': '64px',
      },
    },
  },
  plugins: [],
};
