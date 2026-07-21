/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Anime-inspired palette: deep indigo / sakura pink / electric purple.
        ink: {
          50: "#f6f7fb",
          100: "#eceef6",
          200: "#d3d6e6",
          300: "#a8adc7",
          400: "#737ba0",
          500: "#4d5377",
          600: "#383c5b",
          700: "#262944",
          800: "#171932",
          900: "#0c0e1f",
          950: "#06070f",
        },
        sakura: {
          50: "#fff1f7",
          100: "#ffe2ee",
          200: "#ffbed6",
          300: "#ff8fb6",
          400: "#fc5897",
          500: "#f12d7a",
          600: "#d91564",
          700: "#b40a51",
          800: "#960b46",
          900: "#7e0d3f",
        },
        neon: {
          400: "#7df9ff",
          500: "#22d3ee",
          600: "#0891b2",
        },
      },
      fontFamily: {
        sans: [
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        display: [
          "ui-sans-serif",
          "system-ui",
          "Inter",
          "ui-sans-serif",
          "sans-serif",
        ],
      },
      backgroundImage: {
        "hero-gradient":
          "radial-gradient(1200px 600px at 10% -10%, rgba(241,45,122,0.20), transparent 60%), radial-gradient(900px 500px at 110% 0%, rgba(34,211,238,0.18), transparent 55%), linear-gradient(180deg, #06070f 0%, #0c0e1f 100%)",
        "card-gradient":
          "linear-gradient(135deg, rgba(241,45,122,0.10), rgba(34,211,238,0.10))",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(241,45,122,0.25), 0 10px 40px -10px rgba(241,45,122,0.45)",
      },
      animation: {
        "fade-in": "fadeIn 0.4s ease-out both",
        marquee: "marquee 28s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
    },
  },
  plugins: [],
};
