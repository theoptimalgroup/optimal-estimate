import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        optimal: {
          bg: "var(--optimal-bg)",
          elevated: "var(--optimal-bg-elevated)",
          panel: "var(--optimal-panel)",
          surface: "var(--optimal-surface)",
          orange: "var(--optimal-orange)",
          "orange-dark": "var(--optimal-orange-dark)",
          field: "var(--optimal-field)",
          "field-text": "var(--optimal-field-text)",
          muted: "var(--optimal-muted)",
          text: "var(--optimal-text)",
        },
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.35s ease-out",
        "pulse-soft": "pulse-soft 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
