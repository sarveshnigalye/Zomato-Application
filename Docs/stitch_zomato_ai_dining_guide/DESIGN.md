---
name: Nocturne Gourmet AI
colors:
  surface: '#111317'
  surface-dim: '#111317'
  surface-bright: '#37393e'
  surface-container-lowest: '#0c0e12'
  surface-container-low: '#1a1c20'
  surface-container: '#1e2024'
  surface-container-high: '#282a2e'
  surface-container-highest: '#333539'
  on-surface: '#e2e2e8'
  on-surface-variant: '#e4beb7'
  inverse-surface: '#e2e2e8'
  inverse-on-surface: '#2f3035'
  outline: '#ab8983'
  outline-variant: '#5b403b'
  surface-tint: '#ffb4a6'
  primary: '#ffb4a6'
  on-primary: '#670600'
  primary-container: '#ff553b'
  on-primary-container: '#5a0500'
  inverse-primary: '#b91f0a'
  secondary: '#ffb95f'
  on-secondary: '#472a00'
  secondary-container: '#ee9800'
  on-secondary-container: '#5b3800'
  tertiary: '#4edea3'
  on-tertiary: '#003824'
  tertiary-container: '#00a572'
  on-tertiary-container: '#00311f'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffdad4'
  primary-fixed-dim: '#ffb4a6'
  on-primary-fixed: '#400200'
  on-primary-fixed-variant: '#900c00'
  secondary-fixed: '#ffddb8'
  secondary-fixed-dim: '#ffb95f'
  on-secondary-fixed: '#2a1700'
  on-secondary-fixed-variant: '#653e00'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#111317'
  on-background: '#e2e2e8'
  surface-variant: '#333539'
typography:
  display-hero:
    fontFamily: Plus Jakarta Sans
    fontSize: 56px
    fontWeight: '800'
    lineHeight: 64px
    letterSpacing: -0.03em
  display-hero-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 36px
    fontWeight: '800'
    lineHeight: 44px
    letterSpacing: -0.025em
  headline-xl:
    fontFamily: Plus Jakarta Sans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.02em
  headline-xl-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 22px
    fontWeight: '600'
    lineHeight: 30px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: 0em
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 18px
    letterSpacing: 0.01em
  label-numeric:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: -0.01em
  label-caps:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '700'
    lineHeight: 16px
    letterSpacing: 0.08em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-mobile: 0.75rem
  margin: 3rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style

The design system establishes an atmospheric, hyper-refined culinary concierge experience tailored for late-evening discovery, epicurean decision-making, and seamless reservations. Built for urban gastronomes, experiential diners, and food enthusiasts seeking precision recommendations, the interface pairs cutting-edge machine intelligence with sensory, appetite-inducing sophistication.

The visual direction merges **Dark Glassmorphism** with **Atmospheric Luminescence**. Deep obsidian and layered charcoal grounds form an infinite culinary canvas, allowing dynamic imagery and radiant micro-accents to surface naturally. Rather than flat utility, the aesthetic evokes the intimacy of an upscale, dimly lit cocktail lounge: translucent smoked surfaces, soft rim lighting, ambient chromatic glows, and razor-sharp typographic precision.

## Colors

The palette relies on absolute darkness accented by hyper-vibrant heat maps and culinary tones:

- **Primary Accent (`#FF5238` / `#FF6B4A`)**: A warm, electric vermilion-coral that signals action, appetite, urgency, and core AI suggestions. Accompanied by ambient blur glows (`rgba(255, 82, 56, 0.25)`).
- **Secondary Accent (`#F59E0B`)**: Warm Golden Amber dedicated exclusively to Michelin-tier badges, critic ratings, star indicators, and generative AI highlights.
- **Tertiary Accent (`#10B981`)**: Emerald Green reserved for real-time live seat availability, active kitchen status, and confirmed reservations.
- **Surface Foundations**:
  - `Canvas Base`: Deep Obsidian `#0B0D11`
  - `Surface Tier 1`: Midnight Charcoal `#12161F`
  - `Surface Glass`: Semi-translucent Slate `rgba(26, 32, 44, 0.75)`
- **Borders & Micro-Highlights**: Ghost rims use `rgba(255, 255, 255, 0.08)`, shifting to `rgba(255, 255, 255, 0.16)` upon hover.
- **Text & Content**: Primary text sits at `rgba(255, 255, 255, 0.95)`, secondary descriptive copy at `rgba(255, 255, 255, 0.65)`, and tertiary metadata at `rgba(255, 255, 255, 0.40)`.

## Typography

The typographic hierarchy implements a high-performance dual-font strategy:

- **Display & Headings (Plus Jakarta Sans)**: Delivers geometric warmth, contemporary authority, and sculpted proportions. Used for restaurant names, curated collection headers, conversational AI prompts, and hero banners. Tight negative tracking across larger styles guarantees a compact, editorial presentation.
- **Interface, Numbers & Metadata (Inter)**: Handles computational clarity, long-form editorial reviews, culinary attributes, and data dense feeds.
- **Tabular Figures (`tnum`)**: Critical execution rule—all prices, distances, wait times, and decimal ratings (`4.9`, `$120`, `1.2 km`) must enforce tabular numbers (`font-feature-settings: 'tnum' on, 'cv05' on`) to ensure alignment in high-density dining grids.

## Layout & Spacing

The architecture operates on an 8pt spatial baseline anchored to an adaptable 12-column fluid grid for desktop and an adaptive 4-column system for mobile viewports.

- **Desktop (1200px+)**: 12-column grid with 24px gutters and 48px canvas margin. Max-width content boundary is constrained to 1440px to retain intimate focus. Side panels for AI filters and real-time maps occupy 4 fixed-ratio columns.
- **Tablet (768px - 1199px)**: 8-column layout with 16px gutters and 24px canvas margins. Feed transforms into dual-column card matrices.
- **Mobile (<768px)**: 4 columns with 12px gutters and 16px edge-to-edge margins. Bottom navigation and sticky floating conversational pills float over fluid restaurant cards with peek horizontal scrolls for curated dish carousels.

## Elevation & Depth

Visual hierarchy does not use opaque gray stacks; depth is formed through optical translucency, refractive borders, and colored radiometrics:

- **Level 0 (Canvas Base)**: Solid `#0B0D11` with occasional low-contrast radial background gradients (`rgba(255, 82, 56, 0.04)` centered around focal interaction areas).
- **Level 1 (Sub-surface / Neutral Rail)**: Solid `#12161F` used for static sidebars and nested background troughs.
- **Level 2 (Glassmorphic Card Surfaces)**: `rgba(26, 32, 44, 0.75)` combined with `backdrop-filter: blur(16px)` and a precise `1px solid rgba(255, 255, 255, 0.08)`.
- **Level 3 (Interactive Hover / Active AI Recommendations)**: Surface fills brighten to `rgba(32, 40, 56, 0.85)` with a 1px border shift to `rgba(255, 82, 56, 0.40)`. Outer shadow applies an ambient glow: `box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.8), 0 0 24px -4px rgba(255, 82, 56, 0.15)`.
- **Level 4 (Floating Modals & Curated Trays)**: `rgba(18, 22, 31, 0.90)` backed by `backdrop-filter: blur(28px)`, flanked by a top highlight rim of `1px solid rgba(255, 255, 255, 0.18)` and an ambient drop shadow `0 24px 64px rgba(0, 0, 0, 0.9)`.

## Shapes

The design uses balanced, rounded geometries with progressive scale:

- **Standard Elements (0.5rem / 8px)**: Micro-badges, table count chips, rating indicators, and search dropdown items.
- **Containers & Cards (1rem / 16px)**: Restaurant recommendation cards, reservation time slot matrices, and menu item preview sheets.
- **Modals & Hero Glass Panels (1.5rem / 24px)**: Top-level contextual drawers, conversational AI summary blocks, and dish image viewports.
- **Interactive Triggers (Full Pill / 9999px)**: Quick filter tags, conversational prompt suggestions, floating action triggers, and primary reservation buttons.

## Components

### Buttons
- **Primary Action (Book / Reserve)**: Pill geometry, gradient fill from `#FF5238` to `#FF6B4A`, pure white text with bold weight. Hover creates a subtle scalar bloom (`transform: scale(1.02)`) and activates `box-shadow: 0 0 20px rgba(255, 82, 56, 0.45)`.
- **Secondary (Explore / View Menu)**: Transparent dark glass surface (`rgba(255, 255, 255, 0.05)`), `1px solid rgba(255, 255, 255, 0.12)`, text colored in high-contrast white. Hover states shift the border to `rgba(255, 255, 255, 0.3)`.
- **AI Sparkle Action**: Dark glass surface flanked by a shimmering radial gradient border transitioning through `#F59E0B` and `#FF5238`, triggering ambient glow on hover.

### Chips & Dining Filter Badges
- **Inactive**: Smoked glass background `rgba(26, 32, 44, 0.60)`, subtle text `rgba(255, 255, 255, 0.70)`, and border `rgba(255, 255, 255, 0.08)`.
- **Active / Selected**: Filled with semi-translucent coral tint `rgba(255, 82, 56, 0.15)`, crisp border `1px solid #FF5238`, text rendered in pure `#FFFFFF`.
- **Metric Pill (Amber Rating)**: Compact pill container with `#F59E0B` filled glyph, accompanied by tabular rating text (`4.8`), backed by `rgba(245, 158, 11, 0.12)`.

### Restaurant & Recommendation Cards
- **Base Structure**: Translucent slate backdrop (`rgba(26, 32, 44, 0.75)`), 16px radius, `1px solid rgba(255, 255, 255, 0.08)`, and blurred background content.
- **Image Treatment**: 16:9 or 4:3 high-resolution culinary photography featuring a bottom gradient vignette fading into the card surface (`linear-gradient(to top, rgba(26, 32, 44, 1) 0%, rgba(26, 32, 44, 0) 60%)`).
- **Data Cluster**: Tabular layout for distance, cuisine tags, and price points (`$$$$`). Badges (such as "Chef's Table Available") float in the top-left with frosted glass backing.

### Input Fields & Conversational AI Prompt Bar
- **AI Query Field**: Generous 56px height, pill form, dark slate glass base, inner shadow, and an active neon focus ring: `border-color: #FF5238`, `box-shadow: 0 0 16px rgba(255, 82, 56, 0.25)`.
- **Voice / Sparkle Glyph**: Sits inside the trailing input slot with pulsing amber/vermilion glow animation indicating active engine listening or computation.

### Real-Time Status Ticker
- **Live Seat Indicator**: Compact capsule containing a glowing 6px green LED dot (`#10B981` with infinite soft pulse `0 0 8px #10B981`) next to tabular micro-copy (`3 tables left`).