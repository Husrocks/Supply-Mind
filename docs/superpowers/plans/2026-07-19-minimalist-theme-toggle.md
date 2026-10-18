# Minimalist Theme Toggle & Swiss Typography Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a theme-switching system (light/dark) and update global styling and typography to match the minimalist, professional aesthetics of augen.pro.

**Architecture:** Use CSS custom properties mapped through TailwindCSS v4 `@theme` variables, controlled globally via a React Context (`ThemeProvider`) that persists preferences in `localStorage` and binds the `data-theme` attribute to the root document.

**Tech Stack:** React 19, TypeScript, TailwindCSS v4, Vitest, React Testing Library.

## Global Constraints
* Keep comments/docstrings intact unless explicitly edited.
* Do not introduce third-party css modules.
* Use `lucide-react` for Sun and Moon icons.

---

### Task 1: Create ThemeContext & Tests

**Files:**
- Create: `frontend-v2/src/context/ThemeContext.tsx`
- Create: `frontend-v2/src/test/theme.test.tsx`

**Interfaces:**
- Produces: `ThemeProvider` component, `useTheme` hook, and `ThemeContextType` context state.

- [ ] **Step 1: Write a failing test for ThemeContext**
  Create `frontend-v2/src/test/theme.test.tsx` with the following contents:
  ```typescript
  import { describe, it, expect } from 'vitest';
  import { render, screen, act } from '@testing-library/react';
  import { ThemeProvider, useTheme } from '../context/ThemeContext';

  function TestComponent() {
    const { theme, toggleTheme } = useTheme();
    return (
      <div>
        <span data-testid="theme-val">{theme}</span>
        <button onClick={toggleTheme}>Toggle</button>
      </div>
    );
  }

  describe('ThemeContext', () => {
    it('provides default theme and toggles correctly', () => {
      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      );
      const valEl = screen.getByTestId('theme-val');
      expect(valEl.textContent).toBeDefined();
    });
  });
  ```

- [ ] **Step 2: Run the test to verify it fails**
  Run: `npm run test` inside `frontend-v2`
  Expected: Compile error because `../context/ThemeContext` does not exist.

- [ ] **Step 3: Implement ThemeContext**
  Create `frontend-v2/src/context/ThemeContext.tsx`:
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

- [ ] **Step 4: Run the test to verify it passes**
  Run: `npm run test` inside `frontend-v2`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add frontend-v2/src/context/ThemeContext.tsx frontend-v2/src/test/theme.test.tsx
  git commit -m "feat: implement ThemeContext and verify with test"
  ```

---

### Task 2: Integrate ThemeProvider & Refactor index.css Theme Variables

**Files:**
- Modify: `frontend-v2/src/App.tsx`
- Modify: `frontend-v2/src/index.css`

**Interfaces:**
- Consumes: `ThemeProvider` from `src/context/ThemeContext.tsx`

- [ ] **Step 1: Wrap App tree with ThemeProvider**
  Modify `frontend-v2/src/App.tsx` to import `ThemeProvider` and wrap `<QueryClientProvider>` contents:
  ```typescript
  // Around line 64:
  import { ThemeProvider } from './context/ThemeContext';

  // Inside App function:
  function App() {
    return (
      <QueryClientProvider client={queryClient}>
        <ThemeProvider>
          <AuthProvider>
            <BrowserRouter>
              ...
            </BrowserRouter>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    );
  }
  ```

- [ ] **Step 2: Update index.css theme variables and styles**
  Modify `frontend-v2/src/index.css` to define root theme custom properties and dynamic colors under `@theme`:
  Replace lines 5-56 in `src/index.css` with the CSS variable rules matching the design spec:
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

  @theme {
    --color-primary: var(--accent);
    --color-cyan: var(--accent);
    --color-emerald: var(--risk-low);
    --color-amber: var(--risk-medium);
    --color-rose: var(--risk-high);
    --color-violet: var(--accent-hover);

    --color-canvas: var(--canvas);
    --color-surface: var(--surface);
    --color-surface-elevated: var(--surface-elevated);
    --color-hairline: var(--hairline);
    --color-ink: var(--ink);
    --color-body: var(--body);
    --color-muted: var(--muted);

    --color-accent-indigo: var(--accent);
    --color-accent-cyan: var(--accent);
    --color-accent-yellow: var(--risk-medium);

    --color-risk-low: var(--risk-low);
    --color-risk-medium: var(--risk-medium);
    --color-risk-high: var(--risk-high);

    --font-sans: 'Inter', -apple-system, system-ui, 'Segoe UI', Roboto, sans-serif;
    --font-mono: 'JetBrains Mono', 'Geist Mono', monospace;

    --radius-xl: 8px;
    --radius-2xl: 8px;
  }

  /* Smooth color scheme transitions globally */
  * {
    transition: background-color 0.2s ease, border-color 0.2s ease, color 0.2s ease;
  }
  ```

- [ ] **Step 3: Verify the application build**
  Run: `npm run build` inside `frontend-v2`
  Expected: Successful compilation without errors.

- [ ] **Step 4: Commit**
  ```bash
  git add frontend-v2/src/App.tsx frontend-v2/src/index.css
  git commit -m "style: wrap application in ThemeProvider and integrate dynamic theme variables in CSS"
  ```

---

### Task 3: Implement Theme Toggle Button in Topbar

**Files:**
- Modify: `frontend-v2/src/components/Topbar.tsx`
- Create: `frontend-v2/src/test/topbar.test.tsx`

**Interfaces:**
- Consumes: `useTheme` from `src/context/ThemeContext.tsx`

- [ ] **Step 1: Write a failing test for Topbar toggle**
  Create `frontend-v2/src/test/topbar.test.tsx` to check that the toggle button changes the theme attribute:
  ```typescript
  import { describe, it, expect } from 'vitest';
  import { render, screen, fireEvent } from '@testing-library/react';
  import { BrowserRouter } from 'react-router-dom';
  import { ThemeProvider } from '../context/ThemeContext';
  import { AuthProvider } from '../context/AuthContext';
  import { Topbar } from '../components/Topbar';

  describe('Topbar Theme Toggle', () => {
    it('toggles the document theme attribute when clicked', () => {
      render(
        <ThemeProvider>
          <AuthProvider>
            <BrowserRouter>
              <Topbar />
            </BrowserRouter>
          </AuthProvider>
        </ThemeProvider>
      );
      const button = screen.getByTitle('Toggle color theme');
      expect(button).toBeInTheDocument();
      
      const initialTheme = document.documentElement.getAttribute('data-theme');
      fireEvent.click(button);
      const newTheme = document.documentElement.getAttribute('data-theme');
      expect(newTheme).not.toBe(initialTheme);
    });
  });
  ```

- [ ] **Step 2: Run the test to verify it fails**
  Run: `npm run test`
  Expected: FAIL (Cannot read property or `Toggle color theme` button not found in Topbar).

- [ ] **Step 3: Implement Theme Toggle in Topbar**
  Modify `frontend-v2/src/components/Topbar.tsx`:
  - Import `useTheme` from `../context/ThemeContext`
  - Import `Sun` and `Moon` from `lucide-react`
  - Render a toggle button inside the header actions block (around line 50):
  ```tsx
  import { useTheme } from '../context/ThemeContext';
  import { LogOut, User, Activity, Menu, Sun, Moon } from 'lucide-react';

  // Inside Topbar component:
  const { theme, toggleTheme } = useTheme();

  // Next to the logout button:
  <button
    type="button"
    onClick={toggleTheme}
    title="Toggle color theme"
    className="p-2 rounded-full text-muted hover:text-ink transition-colors focus:ring-1 focus:ring-accent-indigo focus:outline-none"
  >
    {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
  </button>
  ```

- [ ] **Step 4: Run tests to verify it passes**
  Run: `npm run test`
  Expected: PASS (and all other tests pass).

- [ ] **Step 5: Commit**
  ```bash
  git add frontend-v2/src/components/Topbar.tsx frontend-v2/src/test/topbar.test.tsx
  git commit -m "feat: add theme toggle to topbar and verify with test"
  ```

---

### Task 4: Align Sidebar, GlassCard, and Buttons with Minimalist Aesthetic

**Files:**
- Modify: `frontend-v2/src/components/Sidebar.tsx`
- Modify: `frontend-v2/src/components/ui/GlassCard.tsx`
- Modify: `frontend-v2/src/index.css`

- [ ] **Step 1: Update index.css component selectors for flat minimalism**
  Replace lines 70-170 in `frontend-v2/src/index.css` with flat design declarations, ensuring zero shadows and sharp style adjustments:
  ```css
  /* Flat card design - replacing glassmorphic look */
  .glass-card {
    background: var(--color-surface);
    border: 1px solid var(--color-hairline);
    border-radius: var(--radius-2xl);
    padding: 24px;
    contain: layout style paint;
    transition: transform 0.2s ease, border-color 0.2s ease;
  }

  .glass-card:hover {
    border-color: var(--color-primary);
  }

  /* Remove flashy color shadows on hover */
  .glass-card--emerald:hover,
  .glass-card--amber:hover,
  .glass-card--rose:hover,
  .glass-card--indigo:hover,
  .glass-card--cyan:hover {
    box-shadow: none;
  }

  @media (prefers-reduced-motion: reduce) {
    .glass-card { transition: none; }
    .glass-card:hover { transform: none; }
    .pulse-live { animation: none !important; }
  }

  .pulse-live {
    animation: pulse-opacity 1.75s ease-in-out infinite;
  }

  @keyframes pulse-opacity {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.45; }
  }

  /* Minimal flat primary button */
  .btn-primary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 40px;
    padding: 0 18px;
    background: var(--color-ink);
    color: var(--color-canvas);
    font-size: 13px;
    font-weight: 600;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-primary:hover:not(:disabled) {
    opacity: 0.9;
  }

  /* Minimal flat secondary button */
  .btn-secondary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 40px;
    padding: 0 18px;
    background: transparent;
    color: var(--color-ink);
    font-size: 13px;
    font-weight: 600;
    border-radius: 6px;
    border: 1px solid var(--color-hairline);
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--color-surface-elevated);
    border-color: var(--color-muted);
  }

  ::-webkit-scrollbar { width: 4px; height: 4px; }
  ::-webkit-scrollbar-thumb { background: var(--color-hairline); border-radius: 9999px; }
  ```

- [ ] **Step 2: Clean up Sidebar background style**
  Modify `frontend-v2/src/components/Sidebar.tsx` to replace `bg-slate-950/90` with dynamic surface colors:
  Replace the top of the sidebar render container (around line 24):
  ```tsx
  <aside className="w-60 bg-surface border-r border-hairline flex flex-col h-full shrink-0 relative">
  ```
  Ensure mobile close button uses standard classes (around line 29):
  ```tsx
  className="p-1.5 rounded-full bg-surface-elevated text-muted hover:text-ink transition-colors focus:ring-1 focus:ring-accent-indigo focus:outline-none"
  ```
  Ensure navigation active styles use dynamic classes (around lines 53-57):
  ```tsx
  className={({ isActive }) =>
    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
      isActive ? 'bg-surface-elevated text-ink border-l-2 border-accent-indigo' : 'text-body hover:text-ink hover:bg-surface-elevated/50'
    }`
  }
  ```

- [ ] **Step 3: Run full tests verification**
  Run: `npm run test` inside `frontend-v2`
  Expected: PASS

- [ ] **Step 4: Commit**
  ```bash
  git add frontend-v2/src/components/Sidebar.tsx frontend-v2/src/index.css
  git commit -m "style: restyle sidebar, cards, buttons, and custom scrollbars to meet minimalism specifications"
  ```
