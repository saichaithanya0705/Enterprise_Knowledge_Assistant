/** Design tokens for the Enterprise Knowledge Assistant. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0B0F1A",
          900: "#0F1420",
          800: "#161C2C",
          700: "#1D2438",
          600: "#2A3348",
          500: "#3A4560",
        },
        paper: {
          100: "#EDEFF5",
          300: "#B7BDCC",
          500: "#8B93A7",
        },
        amber: {
          400: "#F0B860",
          500: "#E8A33D",
          600: "#C9862A",
        },
        teal: {
          400: "#7BC9B8",
          500: "#5FB4A2",
        },
        coral: {
          500: "#E2645A",
        },
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px rgba(0,0,0,0.35)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
    },
  },
  plugins: [],
};
