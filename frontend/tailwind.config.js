/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        gold: {
          400: "#fbbf24",
          500: "#f59e0b",
          600: "#d97706",
        },
        premium: {
          900: "#0a0a0f",
          800: "#12121a",
          700: "#1a1a24",
          600: "#242430",
        }
      },
      backgroundImage: {
        "gold-gradient": "linear-gradient(135deg, #fbbf24 0%, #d97706 100%)",
        "card-gradient": "linear-gradient(145deg, rgba(26,26,36,0.9) 0%, rgba(18,18,26,0.95) 100%)",
      },
      boxShadow: {
        gold: "0 0 20px rgba(251, 191, 36, 0.15)",
        "gold-lg": "0 0 40px rgba(251, 191, 36, 0.25)",
      }
    },
  },
  plugins: [],
}
