import type { Config } from "tailwindcss";

// Palette "salle de contrôle" : fond quasi-noir, un seul accent (violet
// nébuleuse, en clin d'œil au thème Deepspace du jeu), statuts de job
// codés par couleur plutôt que par icône.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0E0F14",
        surface: "#171922",
        surface2: "#1D202B",
        border: "#2A2D3A",
        ink: "#ECEAE3",
        dim: "#9A9BA8",
        accent: "#8B7CF6",
        "accent-soft": "#3A335E",
        success: "#4FA98C",
        danger: "#D1495B",
        warn: "#D7A65C",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
