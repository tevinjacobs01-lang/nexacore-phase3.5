/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef4ff",
          500: "#3b5bdb",
          600: "#2f4bc0",
          700: "#26399a",
        },
      },
    },
  },
  plugins: [],
};
