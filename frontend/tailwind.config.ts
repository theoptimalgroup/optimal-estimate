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
        app: {
          bg: "var(--app-bg)",
          card: "var(--app-card)",
          text: "var(--app-text)",
          muted: "var(--app-text-secondary)",
          border: "var(--app-border)",
          primary: "var(--app-primary)",
          "primary-hover": "var(--app-primary-hover)",
          success: "var(--app-success)",
          warning: "var(--app-warning)",
          error: "var(--app-error)",
        },
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
      maxWidth: {
        content: "1400px",
      },
      fontSize: {
        "page-title": ["1.625rem", { lineHeight: "2rem", fontWeight: "600" }],
        "section-title": ["1rem", { lineHeight: "1.5rem", fontWeight: "600" }],
        body: ["0.875rem", { lineHeight: "1.375rem" }],
        helper: ["0.8125rem", { lineHeight: "1.25rem" }],
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
