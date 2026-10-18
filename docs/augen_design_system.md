# Design System Specification: augen.pro

This document details the visual guidelines, typography, color palette, layout mechanics, and UI/UX patterns of the **augen.pro** website. It serves as a reference manual for replicating its professional, minimal, and premium Swiss-style editorial aesthetics in other projects.

---

## 1. Core Design Philosophy
The design language of `augen.pro` is heavily inspired by the **International Typographic Style (Swiss Design)**. Its main tenets are:
* **Asymmetric Grid Layouts**: Mimicking physical editorial prints rather than standard symmetrical bootstrap-like columns.
* **Negative Space (Whitespace) as a Tool**: Heavy reliance on empty spaces to direct user focus, evoke luxury, and signal premium engineering.
* **Extreme Color Contrast**: Transitioning cleanly between sterile light-gray sections and premium solid dark-mode segments.
* **Flat Presentation**: Virtually no gradients or box-shadows. Depth is established through typography scale, color blocks, and thin, high-contrast hairlines.

---

## 2. Color Palette & Tokens

The visual theme functions as a **contextual hybrid theme**. The canvas transitions between a bright editorial light mode and a premium dark mode depending on the content block.

### A. Theme Colors

| Token Name | Light Theme Value | Dark Theme Value | Purpose & Application |
| :--- | :--- | :--- | :--- |
| **Canvas (Background)** | `#F5F5F7` or `#F9F9FB` | `#000000` or `#0B0B0C` | Page base background. |
| **Surface (Cards/Panels)** | `#FFFFFF` | `#0A0A0C` | Input fields, content panels, lists. |
| **Ink Primary** | `#1D1D1F` (Charcoal Black) | `#FFFFFF` (Crisp White) | Main headers, hero titles, body paragraphs. |
| **Ink Secondary** | `#6E6E73` (Cool Gray) | `#A1A1A6` (Muted Gray) | Supporting text, timestamps, labels, descriptions. |
| **Ink Muted** | `#86868B` | `#6E6E73` | Footer text, deactivated menu items, help text. |
| **Hairline (Borders)** | `#E5E5E7` | `#1C1C1E` | Section divider lines, input borders. |
| **Accent / Interactive** | `#0066CC` | `#0071E3` | Hover indicators, links, active tab selectors. |

### B. Contrast Guidelines
* **Light Mode Contrast**: Deep dark charcoal (`#1D1D1F`) on clean off-white (`#F5F5F7`). High readability, clean documentation aesthetic.
* **Dark Mode Contrast**: Bright white (`#FFFFFF`) on pitch black (`#000000`). Used to represent high-tech, hardware products, or focus areas.
* **Divider lines**: Kept extremely faint. Border widths should be exactly `1px`.

---

## 3. Typography & Type Scale

Typography is the most prominent element in this design system. It uses a neutral, high-legibility geometric/grotesque sans-serif typeface.

* **Primary Font Family**: `Inter`, `SF Pro Display`, `SF Pro Text`, or `Neue Haas Grotesk`.
* **Fallback Stack**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`.

### Typography Scale Hierarchy

```
├── Heading Super (Hero Titles) ── 72px - 96px (Bold 700 / Tracking -0.02em / LH 1.05)
│
├── Heading Large (Section Headers) ── 40px - 48px (Semi-bold 600 / Tracking -0.01em / LH 1.15)
│
├── Heading Medium (Widget Titles) ── 20px - 24px (Medium 500 / Tracking -0.01em / LH 1.25)
│
├── Body Regular (Standard Text) ── 16px - 18px (Regular 400 / Tracking 0 / LH 1.5)
│
├── Caption/Small (Helper text) ── 13px - 14px (Regular 400 / Tracking 0 / LH 1.4)
│
└── Uppercase Label (Meta tags/Badges) ── 11px - 12px (Medium 500 / Tracking 0.08em - 0.1em / Uppercase)
```

### Key Rules:
1. **Letter Spacing (Tracking)**: 
   - Tighten spacing for large headings: `tracking-tight` or `tracking-[-0.02em]`. This binds large headers together visually.
   - Expand spacing for uppercase labels: `tracking-widest` or `letter-spacing: 0.1em`. This increases readability for small-caps tags (e.g. `P01`, `RESEARCH`, `MITIGATION`).
2. **Line Height (Leading)**:
   - For titles: extremely tight (`1.05` to `1.15`).
   - For body: comfortable and readable (`1.5`).

---

## 4. UI Elements & Layout Mechanics

### A. Asymmetric Two-Column Grid (Editorial Style)
Instead of standard symmetrical columns (e.g. 50/50 split), layouts use an offset two-column arrangement to mirror high-end fashion or architectural journals:
* **Left Column (width ~30%)**: Houses metadata tags, category markers, section indicators, or small titles.
* **Right Column (width ~70%)**: Houses the main detailed descriptions, body text, or charts.
* **Negative Space**: Massive gutters (padding) separate sections (often utilizing `96px` to `120px` vertical margins).

### B. Headers & Navigation
* **Structure**: A single, clean horizontal strip fixed or absolute-positioned at the top:
  - **Left-aligned**: Minimal text-based or clean vector Logo.
  - **Center-aligned**: Widely-spaced text links (`letter-spacing: 0.05em`) with subtle transitions.
  - **Right-aligned**: Single contact link or call-to-action (`email` or small secondary button).
* **Overlay Menu**: Clicking header categories opens a full-screen or full-height drawer with huge, clean list items (`font-size: 32px`, vertical spacing: `24px`).
* **Zero Drop-Shadows**: The navigation elements are flat against the background, separated only by a clean background color block or a single hairline bottom border (`1px solid var(--hairline)`).

### C. Cards & Containers
* **Sharp Edges**: Grid card boxes utilize sharp corners (`border-radius: 0px` or a tiny `6px` radius) rather than deep rounded borders. This creates a technical, architectural grid layout.
* **Card Separation**: Cards do not float using box-shadows. They are delimited by thin `1px` border lines or distinct background contrast blocks.
* **Flat Design**: Avoid gradients, reflections, or glowing backgrounds.

### D. Interactive Buttons
* **Standard Button**: 
  - Flat solid black background with white text (Dark Mode) or solid white background with black text (Light Mode).
  - Subtle hover transition (`transition: all 0.2s ease-in-out`).
  - Small border radius (`6px` to `8px`).
* **Circular Icon Buttons**:
  - Toggles, page controls, and navigation indicators use circular boundaries (`border-radius: 50%`).
  - Size is kept small (e.g. `32px` to `40px` diameter).
  - Hover states invert colors (e.g. transparent/border to filled accent color).

---

## 5. Micro-Interactions & UX Details

* **Hover Transitions**: Snap-like but smooth transition speed (`150ms` to `200ms`) with `ease-out` timing function.
* **Scroll-to-top**: Minimal trigger (often absolute positioned on the bottom left margin) that fades in after scrolling beyond the viewport fold.
* **Opacity Pulse**: An indicator for active connections or status uses keyframe opacity animation (`opacity: 1` to `opacity: 0.45` over `1.75s`), avoiding glowing blur shadows.
* **Contrast Transitions**: Page elements smoothly interpolate text and border colors when moving between light and dark sections.

---

## 6. Sample Tailwind v4 Implementation Config

Below is a CSS configuration matching these guidelines, configured to support dynamic theme switching via a `data-theme` attribute:

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
  --color-canvas: var(--canvas);
  --color-surface: var(--surface);
  --color-surface-elevated: var(--surface-elevated);
  --color-hairline: var(--hairline);
  --color-ink: var(--ink);
  --color-body: var(--body);
  --color-muted: var(--muted);
  --color-accent-indigo: var(--accent);
  --color-accent-cyan: var(--accent);
  
  --color-risk-low: var(--risk-low);
  --color-risk-medium: var(--risk-medium);
  --color-risk-high: var(--risk-high);
}
```
