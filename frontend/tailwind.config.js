import typography from "@tailwindcss/typography";

export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"Source Serif 4"', '"Source Serif Pro"', 'Georgia', 'serif'],
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Pulled directly from the green & beige mockup — no renaming, no drift
        paper: {
          50:  '#fdfaf0',  // fresh-page cream (editor inner surface)
          100: '#f5efdc',  // panel / card background
          200: '#f0ead8',  // page background
          300: '#ebe2c4',  // header & sidebar background (toasted parchment)
          400: '#d8c9a3',  // border (aged paper edge)
        },
        forest: {
          DEFAULT: '#2d4a2f',  // primary green — buttons, brand, tab bar, ink
          deep:    '#2d4a2f',
          dark:    '#1f3a21',
        },
        sage: {
          50:  '#e6dfc4',  // heatmap empty
          100: '#d4e2c2',  // selected-row background tint
          200: '#c8d4a8',  // heatmap tier 1 (pale sage)
          400: '#8aa56e',  // heatmap tier 2 (sage)
          600: '#5a7a4a',  // heatmap tier 3 (forest), legend bar
          700: '#2d4a2f',  // heatmap tier 4 (deep forest)
        },
        ink: {
          900: '#2d2820',  // entry body text (warm near-black)
          700: '#4a5d44',  // ink-on-paper for non-selected sidebar text
          500: '#5a6b4a',  // muted moss (secondary text, "less"/"more" labels)
          400: '#7a8770',  // tertiary text (sage gray, placeholders)
        },
      },
      typography: ({ theme }) => ({
        DEFAULT: {
          css: {
            color: theme('colors.ink.900'),
            '--tw-prose-bold': theme('colors.forest.DEFAULT'),
            '--tw-prose-headings': theme('colors.forest.DEFAULT'),
          },
        },
      }),
    },
  },
  plugins: [typography],
};