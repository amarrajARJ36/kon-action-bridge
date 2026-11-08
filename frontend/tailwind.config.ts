import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        careem: {
          green: "#00e575",
          darkgreen: "#00b853",
          forest: "#004724",
          deep: "#09281a",
          mint: "#eefcf4",
          yellow: "#ffb800",
          surface: "#ffffff",
          bg: "#f4f6f8",
          border: "#e5e9ec",
          text: "#111827",
          muted: "#6b7280",
        },
        kon: {
          navy: "#1a1a2e",
          dark: "#16213e",
          blue: "#0f3460",
          red: "#e94560",
          surface: "#1f293d",
          border: "#2a3b5c",
          muted: "#94a3b8",
        },
      },
      animation: {
        "pulse-slow": "pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite",
        "fade-in": "fadeIn 0.3s ease-in-out",
        "slide-up": "slideUp 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideUp: {
          "0%": { transform: "translateY(100%)" },
          "100%": { transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
