---
name: Consensus Enterprise
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3d4947'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6d7a77'
  outline-variant: '#bcc9c6'
  surface-tint: '#006a61'
  primary: '#00685f'
  on-primary: '#ffffff'
  primary-container: '#008378'
  on-primary-container: '#f4fffc'
  inverse-primary: '#6bd8cb'
  secondary: '#0058be'
  on-secondary: '#ffffff'
  secondary-container: '#2170e4'
  on-secondary-container: '#fefcff'
  tertiary: '#6b38d4'
  on-tertiary: '#ffffff'
  tertiary-container: '#8455ef'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#89f5e7'
  primary-fixed-dim: '#6bd8cb'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#005049'
  secondary-fixed: '#d8e2ff'
  secondary-fixed-dim: '#adc6ff'
  on-secondary-fixed: '#001a42'
  on-secondary-fixed-variant: '#004395'
  tertiary-fixed: '#e9ddff'
  tertiary-fixed-dim: '#d0bcff'
  on-tertiary-fixed: '#23005c'
  on-tertiary-fixed-variant: '#5516be'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  title-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  base: 8px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  container-max: 1440px
  gutter: 16px
---

## Brand & Style
The design system is engineered for high-stakes decision-making environments where clarity, precision, and objectivity are paramount. The brand personality is authoritative yet unobtrusive, functioning as a sophisticated "glass pane" through which data is analyzed.

The visual style follows a **Corporate / Modern** aesthetic with a lean toward **Minimalism**. It prioritizes information density without sacrificing legibility. The emotional response should be one of "quiet confidence"—the UI feels stable, predictable, and robust. Every element exists to facilitate consensus and verification, avoiding decorative flourishes in favor of functional excellence.

## Colors
This design system utilizes a structured palette designed for data categorization and semantic clarity.

- **Primary Action:** Deep-teal (#0d9488) is reserved for high-intent actions like "Confirm," "Approve," or "Submit."
- **Status & Logic:** A traffic-light system is used for consensus states: Green for accepted, Red for declined, and Amber for pending or contested items.
- **Source Attribution:** To distinguish between data origins, Violet is used exclusively for AI-deduced insights, while Blue identifies colleague-suggested content.
- **Neutral Framework:** The interface sits on a Slate-50 (#f8fafc) background to reduce eye strain, with pure white surfaces for active workspaces and cards. All borders must maintain a minimum 1px width at #e2e8f0 to ensure structural definition.

## Typography
The system relies exclusively on **Inter** to leverage its exceptional legibility in data-heavy enterprise contexts. 

- **Scale:** A tight typographic scale ensures that large amounts of information can be displayed on a single screen without feeling overwhelming.
- **Hierarchy:** Use `Title-MD` for table headers and card titles. `Body-SM` is the workhorse for data grids and technical descriptions.
- **Emphasis:** FontWeight 600 is used for key data points and headers. Avoid using bold weights for body text to maintain a clean, "uncluttered" texture.
- **Mobile:** For handheld viewports, `Display-LG` should downscale to 24px to prevent excessive line wrapping in headers.

## Layout & Spacing
The design system follows an **8px linear spacing grid**. All layout decisions are driven by the need for high-density information architecture.

- **Grid:** A 12-column fluid grid is used for dashboard layouts, while a fixed max-width of 1440px is applied to content containers to prevent excessive line lengths on ultra-wide monitors.
- **Data Grids:** Tables utilize a "Compact" vertical rhythm (8px cell padding) to maximize the amount of visible data.
- **Breakpoints:**
  - **Desktop (1024px+):** 12-column layout, 24px margins.
  - **Tablet (768px - 1023px):** 8-column layout, 16px margins.
  - **Mobile (Below 768px):** 4-column layout, 12px margins, stacked card components.

## Elevation & Depth
Depth is communicated through **Tonal Layering** rather than heavy shadows. This reinforces the "flat and functional" enterprise feel.

- **Level 0 (Background):** Slate-50 (#f8fafc) provides the base canvas.
- **Level 1 (Surface):** White (#ffffff) is used for cards and main content areas. These use a 1px border (#e2e8f0) to separate from the background.
- **Level 2 (Interaction):** Hover states for cards or rows use a subtle background shift to Slate-100 (#f1f5f9). 
- **Level 3 (Modals/Popovers):** For overlays, a very soft, high-diffusion shadow is used (0px 4px 12px rgba(0,0,0,0.05)) to suggest elevation without breaking the professional aesthetic.

## Shapes
The shape language is **Soft** (4px default), reflecting a disciplined and precise tool. 

- **Standard Elements:** Buttons, input fields, and checkboxes use a 4px (0.25rem) radius.
- **Containers:** Large cards and modals use an 8px (0.5rem) radius to create a distinct container hierarchy.
- **Tags/Chips:** Source and status chips use a 4px radius. Avoid pill shapes (fully rounded) as they appear too casual for this enterprise context.

## Components
Consistent implementation of these core components ensures a unified user experience.

- **Buttons:** Primary buttons use the Teal-600 background with white text. Secondary buttons use a white background with 1px Slate-200 border and Slate-700 text.
- **Source Chips:** 
  - *AI-Deduced:* Violet-100 background, Violet-700 text, no border.
  - *Colleague-Suggested:* Blue-100 background, Blue-700 text, no border.
- **Status Badges:** Small text-only or dot-indicator badges. Use subtle background tints (e.g., Green-50 for "Accepted") with high-contrast text (Green-700) to meet WCAG AA standards.
- **Input Fields:** 1px border (#e2e8f0) that transitions to Teal-600 on focus. Placeholder text uses Slate-400.
- **Data Tables:** Zebra striping is not used; instead, use 1px horizontal dividers. Header rows should have a Slate-50 background to distinguish them from data rows.
- **Consensus Indicator:** A custom component showing a horizontal bar with segmented colors (Green/Amber/Red) to visualize the current collective stance on a specific data point.