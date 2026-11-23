/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      // Restrained, government-agency-style palette.
      colors: {
        brand: {
          50: '#eef4fb',
          100: '#d8e6f7',
          500: '#1d5b96',
          600: '#174a7c',
          700: '#12395f',
          900: '#0c2338',
        },
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
