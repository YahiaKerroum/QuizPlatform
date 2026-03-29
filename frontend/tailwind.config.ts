import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./hooks/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        sand: "#f3ebdc",
        clay: "#d96f3d",
        ink: "#1d1b19",
        pine: "#37514b",
        mist: "#efe7da"
      },
      boxShadow: {
        soft: "0 18px 50px rgba(29, 27, 25, 0.12)"
      },
      fontFamily: {
        heading: ["var(--font-space-grotesk)"],
        body: ["var(--font-source-serif)"]
      }
    }
  },
  plugins: [],
};

export default config;

