/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class', // enable dark mode by default
  theme: {
    extend: {
      colors: {
        background: '#0B0F19',
        surface: '#1A202C',
        primary: '#3B82F6',
        accent: '#10B981',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
