/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "happy-blue": {
          900: "#0E2A3C",
          700: "#1B4868",
          500: "#3B7BA8",
          200: "#BFD8E8",
        },
        cream: {
          50: "#FBF6E8",
          100: "#F4ECD3",
          200: "#E9DBB4",
        },
        coral: "#E08066",
        leaf: "#6E9D74",
        ink: "#1A1816",
      },
      fontFamily: {
        display: ['"Fraunces"', "Georgia", "serif"],
        body: ['"Inter"', "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
