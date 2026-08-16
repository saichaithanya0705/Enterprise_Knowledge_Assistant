/** Design tokens for the Enterprise Knowledge Assistant. */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        canvas: {
          50: "#FFFDF8",
          100: "#F5F0E6",
          200: "#E9E2D5",
          300: "#D3C9B8",
          500: "#8D8578",
        },
        carbon: {
          950: "#151712",
          900: "#1B1E18",
          800: "#242820",
          700: "#33382E",
          500: "#686D62",
        },
        vermilion: {
          400: "#DE6A50",
          500: "#C84F35",
          600: "#A83D28",
        },
        moss: {
          400: "#78907B",
          500: "#5D7863",
        },
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
          400: "#EF8B82",
          500: "#E2645A",
        },
      },
      fontFamily: {
        display: ["Iowan Old Style", "Baskerville", "Palatino Linotype", "Book Antiqua", "Georgia", "serif"],
        sans: ["Aptos", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["Cascadia Code", "IBM Plex Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        card: "0 1px 0 rgba(255,255,255,0.04) inset, 0 8px 24px rgba(0,0,0,0.35)",
        paper: "0 1px 0 rgba(255,255,255,0.9) inset, 0 18px 45px rgba(62,49,31,0.10)",
        lift: "0 12px 30px rgba(27,30,24,0.14)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
    },
  },
  plugins: [],
};
