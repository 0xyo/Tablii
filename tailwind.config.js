/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/templates/**/*.html"],
  theme: {
    extend: {
      colors: {
        // ── Midnight Amber palette ──────────────────
        amber: {
          50: "#FFF9F0",
          100: "#FFF0DB",
          200: "#FFE0B8",
          300: "#F5CFA0",
          400: "#D4A574",
          500: "#C4956A",
          600: "#A87B55",
          700: "#8C6340",
          800: "#6B4A2E",
          900: "#4A3220",
        },
        cream: {
          50: "#FDFCFA",
          100: "#FAF8F5",
          200: "#F5F0EB",
          300: "#EDE6DD",
          400: "#DDD3C7",
        },
        charcoal: {
          50: "#F5F4F3",
          100: "#E8E6E3",
          200: "#D1CCC6",
          300: "#A69E95",
          400: "#7A7168",
          500: "#5A524A",
          600: "#3D3731",
          700: "#2D2926",
          800: "#1A1714",
          900: "#0F0D0B",
        },
        burgundy: {
          50: "#FDF2F5",
          100: "#FCE5EC",
          200: "#F5C6D0",
          300: "#E89AAD",
          400: "#C46B82",
          500: "#8B2252",
          600: "#731C44",
          700: "#5B1636",
          800: "#431028",
          900: "#2B0A1A",
        },
        // Jewel-tone status colors
        emerald: {
          400: "#4ADE80",
          500: "#22C55E",
          600: "#16A34A",
        },
        sapphire: {
          400: "#60A5FA",
          500: "#3B82F6",
          600: "#2563EB",
        },
        ruby: {
          400: "#FB7185",
          500: "#F43F5E",
          600: "#E11D48",
        },
        topaz: {
          400: "#FBBF24",
          500: "#F59E0B",
          600: "#D97706",
        },
      },
      fontFamily: {
        display: ['"Playfair Display"', "serif"],
        body: ['"DM Sans"', "sans-serif"],
        arabic: ['"Cairo"', "sans-serif"],
        mono: ['"JetBrains Mono"', "monospace"],
      },
      borderRadius: {
        "4xl": "2rem",
      },
      boxShadow: {
        gold: "0 4px 24px -4px rgba(196, 149, 106, 0.25)",
        "gold-lg": "0 8px 40px -6px rgba(196, 149, 106, 0.35)",
        dark: "0 4px 24px -4px rgba(15, 13, 11, 0.3)",
        "inner-glow": "inset 0 1px 0 0 rgba(255,255,255,0.08)",
      },
      backgroundImage: {
        grain:
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E\")",
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "deco-pattern":
          "url(\"data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23C4956A' fill-opacity='0.06'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E\")",
      },
      animation: {
        "fade-up": "fadeUp 0.6s cubic-bezier(0.16,1,0.3,1) both",
        "fade-up-2": "fadeUp 0.6s 0.1s cubic-bezier(0.16,1,0.3,1) both",
        "fade-up-3": "fadeUp 0.6s 0.2s cubic-bezier(0.16,1,0.3,1) both",
        "fade-up-4": "fadeUp 0.6s 0.3s cubic-bezier(0.16,1,0.3,1) both",
        float: "float 5s ease-in-out infinite",
        shimmer: "shimmer 2s ease-in-out infinite",
        "glow-pulse": "glowPulse 2s ease-in-out infinite",
        "slide-in-right": "slideInRight 0.5s cubic-bezier(0.16,1,0.3,1) both",
      },
      keyframes: {
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-14px)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        glowPulse: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(196,149,106,0.15)" },
          "50%": { boxShadow: "0 0 40px rgba(196,149,106,0.35)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(24px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
      },
    },
  },
  plugins: [],
};
