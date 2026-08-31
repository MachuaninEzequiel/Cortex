/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Catppuccin Mocha (alineado con el resto de Cortex UI; ver
        // cortex-companion/src/screens/hud_screen.rs y theme del TUI).
        mocha: {
          base: "#1e1e2e",
          surface: "#313244",
          surface2: "#585b70",
          text: "#cdd6f4",
          subtext0: "#a6adc8",
          mauve: "#cba6f7",
          lavender: "#b4befe",
          sky: "#89dceb",
          sapphire: "#04a5e5",
        },
        // Marca voxel viva del mark (solo el isotipo usa verde;
        // chrome desciende a Mauve/Sky según doc 17).
        cortex: {
          forest: "#03522E",
          mint: "#8FDCB0",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: [
          "JetBrains Mono",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};
