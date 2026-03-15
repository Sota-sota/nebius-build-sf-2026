/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ["'SF Mono'", "'Monaco'", "'Cascadia Code'", "'Fira Code'", "'DejaVu Sans Mono'", "'Liberation Mono'", "monospace"],
      },
      colors: {
        wm: {
          bg: "#0a0a0a",
          secondary: "#111",
          surface: "#141414",
          "surface-hover": "#1e1e1e",
          border: "#2a2a2a",
          "border-strong": "#444",
          text: "#e8e8e8",
          "text-dim": "#888",
          "text-muted": "#666",
          "text-faint": "#555",
        },
        risk: {
          low: "#44aa44",
          medium: "#ffaa00",
          high: "#ff4444",
        },
        step: {
          perceiving: "#3388ff",
          searching: "#ff8800",
          planning: "#aa55ff",
          executing: "#44ff88",
          awaiting: "#ffaa00",
        },
        status: {
          live: "#44ff88",
          cached: "#ffaa00",
          unavailable: "#ff4444",
        },
      },
      keyframes: {
        "pulse-dot": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.5" },
        },
      },
      animation: {
        "pulse-dot": "pulse-dot 2s infinite",
      },
    },
  },
  plugins: [],
}
