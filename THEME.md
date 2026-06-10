# LinkedIn Autopilot — Design Tokens

Pulled directly from the live **AI Models Hub** so the SaaS matches it exactly. Use these tokens in the React/Vite frontend.

## Palette (from the Hub's `:root`)

| Token | Hex | Role |
|---|---|---|
| `navy` | `#121358` | Darkest — hero background start, footers |
| `blue` | `#232F72` | Primary brand blue — headings, links, nav |
| `mid` | `#2F578A` | Secondary blue — gradients, hover states |
| `teal` | `#36ADA3` | **Accent / primary CTA** — buttons, highlights |
| `light` | `#f0f4ff` | Light section backgrounds, subtle cards |
| `muted` | `#6b7280` | Secondary text |
| `text` | `#1a1a2e` | Body text |
| `white` | `#ffffff` | Page background, text on dark |

**Hero / dark band gradient:**
`linear-gradient(135deg, #121358 0%, #232F72 60%, #1a3a6a 100%)`

**Primary button:** solid `#36ADA3` (teal), `border-radius: 6–8px`, white text.
**Secondary button on dark:** `rgba(255,255,255,0.1)`, white text.
**Font:** `"Segoe UI", system-ui, sans-serif`.
**Corner radius:** `6–8px` standard.

## CSS variables (`theme.css`)

```css
:root {
  --navy:  #121358;
  --blue:  #232F72;
  --mid:   #2F578A;
  --teal:  #36ADA3;
  --light: #f0f4ff;
  --muted: #6b7280;
  --text:  #1a1a2e;
  --white: #ffffff;

  --hero-gradient: linear-gradient(135deg, #121358 0%, #232F72 60%, #1a3a6a 100%);
  --radius: 8px;
  --font-sans: "Segoe UI", system-ui, sans-serif;
}

body { background: var(--white); color: var(--text); font-family: var(--font-sans); }
.btn-primary { background: var(--teal); color: #fff; border-radius: var(--radius); }
.btn-secondary { background: var(--light); color: var(--blue); border-radius: var(--radius); }
.hero { background: var(--hero-gradient); color: #fff; }
```

## Tailwind config (`tailwind.config.js` → `theme.extend`)

```js
export default {
  theme: {
    extend: {
      colors: {
        navy:  '#121358',
        blue:  '#232F72',
        mid:   '#2F578A',
        teal:  '#36ADA3',
        light: '#f0f4ff',
        muted: '#6b7280',
        ink:   '#1a1a2e',
      },
      fontFamily: { sans: ['"Segoe UI"', 'system-ui', 'sans-serif'] },
      borderRadius: { DEFAULT: '8px' },
      backgroundImage: {
        hero: 'linear-gradient(135deg, #121358 0%, #232F72 60%, #1a3a6a 100%)',
      },
    },
  },
};
```

Usage: `bg-teal` for CTAs, `text-blue` for headings, `bg-hero` for the dashboard top band, `bg-light` for cards.
