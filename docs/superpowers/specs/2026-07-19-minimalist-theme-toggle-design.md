# Design Specification: Minimalist Theme Toggle & Typography

**Date**: 2026-07-19  
**Status**: Proposal  
**Topic**: Theme Switching & Swiss Typography Styling for SupplyMind

---

## 1. Goal Description

This specification outlines the changes required to transform the SupplyMind dashboard's UI/UX to match the minimalist, professional aesthetic of `augen.pro`. This includes:
* Implementing a theme system that supports switching between a **Crisp Light Theme** (off-white base `#F5F5F7` / white cards `#FFFFFF`) and an **Obsidian Dark Theme** (pitch black base `#000000` / obsidian cards `#0A0A0C`).
* Modernizing typography with tighter tracking on large display text and wider tracking on uppercase labels.
* Eliminating shadows and glass reflections in favor of flat container boundaries and thin `1px` hairlines (`#E5E5E7` in light mode, `#1C1C1E` in dark mode).
* Adding a theme toggle to the Topbar next to the user logout action.

---

## 2. Architectural Design

```mermaid
graph TD
    A[App.tsx / Providers] --> B[ThemeProvider]
    B --> C[ThemeContext]
    C -->|Reads/Writes| D[LocalStorage: supplymind_theme]
    C -->|Sets attribute| E[html[data-theme='light/dark']]
    F[Topbar.tsx] -->|Triggers toggle| C
    G[index.css] -->|CSS Variables react to html[data-theme]| H[Tailwind v4 Theme Configuration]
```

### A. Dynamic Theme Switching Mechanics
1. A new `ThemeContext` will manage the theme state (`light` or `dark`).
2. The user's preference will persist in `localStorage` as `supplymind_theme`.
3. The provider will apply or modify the `data-theme` attribute on the root document element: `document.documentElement.setAttribute('data-theme', theme)`.
4. Theme changes will propagate instantly.

### B. Global CSS Variables (`src/index.css`)
We will rewrite the Tailwind v4 color mapping to use CSS variables that change depending on the root element `data-theme` attribute:

```css
:root {
  /* Light mode tokens */
  --canvas: #f5f5f7;
  --surface: #ffffff;
  --surface-elevated: #f9f9fb;
  --hairline: #e5e5e7;
  --ink: #1d1d1f;
  --body: #6e6e73;
  --muted: #86868b;
  --accent: #0066cc;
  --accent-hover: #0071e3;
  
  --risk-low: #10b981;
  --risk-medium: #f59e0b;
  --risk-high: #f43f5e;
}

:root[data-theme="dark"] {
  /* Dark mode tokens */
  --canvas: #000000;
  --surface: #0a0a0c;
  --surface-elevated: #121214;
  --hairline: #1c1c1e;
  --ink: #ffffff;
  --body: #a1a1a6;
  --muted: #6e6e73;
  --accent: #0071e3;
  --accent-hover: #0088ff;
}
```

---

## 3. Proposed Changes

We will modify or create the following files:

### A. Context & Hooks

#### [NEW] `src/context/ThemeContext.tsx`
Create a provider managing state:
```typescript
import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';

type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('supplymind_theme') as Theme;
    if (saved === 'light' || saved === 'dark') return saved;
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  useEffect(() => {
    localStorage.setItem('supplymind_theme', theme);
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
```

#### [MODIFY] `src/App.tsx`
Wrap the main component tree with the new `ThemeProvider`.

---

### B. Global Styles

#### [MODIFY] `src/index.css`
* Replace static hex codes under `@theme` with native CSS variables.
* Remove complex backdrop filters and heavy hover translations on `.glass-card` (rename or rewrite it as `.flat-card` / `.glass-card` to match flat minimalism: zero shadows, simple `1px` borders).
* Style primary/secondary buttons as flat widgets with small border-radius (`6px` to `8px`) and clean hover background overlays.
* Add transition utility classes so color scheme shifts are smooth:
  ```css
  * {
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  }
  ```

---

### C. Layout & Core Components

#### [MODIFY] `src/components/Topbar.tsx`
* Import `useTheme` and Lucide icons `Sun` and `Moon`.
* Add a theme toggle button to the top-right header next to the User section:
  ```tsx
  const { theme, toggleTheme } = useTheme();
  
  // Render:
  <button
    onClick={toggleTheme}
    title="Toggle color theme"
    className="p-2 rounded-full text-muted hover:text-ink transition-colors focus:ring-1 focus:ring-accent-indigo focus:outline-none"
  >
    {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
  </button>
  ```

#### [MODIFY] `src/components/Sidebar.tsx`
* Clean up slate background (`bg-slate-950/90`) to use dynamic theme variables (`bg-surface` or a subtle hybrid tone).
* Ensure nav items utilize dynamic border/hairline variables instead of static slate borders.

#### [MODIFY] `src/components/ui/GlassCard.tsx`
* Retain the name `GlassCard` (to avoid breaking consumers) but update its implementation to represent the minimal flat container design.

---

## 4. Verification Plan

### Automated Tests
Verify that the `vitest` suite passes:
```bash
npm run test
```

### Manual Verification
1. Open the application locally using `npm run dev`.
2. Observe layout colors on default loading: light theme (light off-white background, black text, clean borders).
3. Click the theme switch button in the header.
4. Verify layout switches cleanly to obsidian dark theme (pure black background, dark panels, white text).
5. Refresh the page to verify that the selected theme persists in `localStorage`.
