---
name: ui-ux-guidelines
description: Use when designing or reviewing user interfaces — visual hierarchy, color systems, spacing, interaction patterns, forms, accessibility, responsive design, dark mode, and common UI component patterns.
version: 0.1.0
---

# UI/UX Guidelines

## Core Principles

1. **User-Centered Design** — base decisions on user needs and data, not assumptions
2. **Accessibility is Mandatory** — WCAG 2.1 AA minimum for all interfaces
3. **Consistency** — same component behaves the same everywhere
4. **Feedback** — users always know what's happening
5. **Error Prevention** — prevent mistakes rather than just recovering from them

## Visual Hierarchy

- **Size** — larger elements draw more attention; use intentionally
- **Contrast** — high contrast for primary actions, lower for secondary
- **Whitespace** — don't fear empty space; it improves readability
- **Typography scale** — use a consistent scale (e.g., 12, 14, 16, 20, 24, 32, 48px)

## Color System

```css
/* Semantic colors */
--color-success: #10B981;    /* green */
--color-error: #EF4444;      /* red */
--color-warning: #F59E0B;    /* amber */
--color-info: #3B82F6;       /* blue */

/* Contrast requirements (WCAG AA) */
/* Normal text:  4.5:1 minimum */
/* Large text:   3:1 minimum */
/* UI components: 3:1 minimum */
```

## Spacing System (8px base)

```
4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px, 96px, 128px
```
Use consistently across components; avoid arbitrary values.

## Component Standards

- **Buttons**: consistent padding, border-radius, and all states (hover, active, disabled, focus)
- **Input fields**: uniform height, padding, border styling
- **Cards**: consistent shadow, border-radius, internal spacing
- **Icons**: single icon library, consistent sizes (16, 20, 24px)

## Interaction Design

### Feedback Timing
- **< 100ms** — immediate visual response to user action
- **100ms – 1s** — no loader needed, but show state change
- **> 1s** — show spinner or progress bar
- **> 3s** — show skeleton screen + progress indication

### Micro-interactions
- Transitions: 200–300ms for most animations
- Use `prefers-reduced-motion` to disable for users who prefer it

### Navigation
- Users should always know where they are
- Breadcrumbs for hierarchies deeper than 2 levels
- Primary nav in expected locations (top or left sidebar)
- Highlight active page/section clearly

## Forms

- **Labels** above inputs (best scannability)
- **Validation**: real-time for complex fields, on-submit for simple
- **Error messages**: specific, helpful, next to the relevant field
- **Required fields**: mark clearly with asterisk or "(required)"
- **Related fields**: visually group them together

```tsx
// Good form field pattern
<div className="field">
  <label htmlFor="email">Email address *</label>
  <input id="email" type="email" aria-describedby="email-error" />
  {error && <span id="email-error" role="alert">{error}</span>}
</div>
```

## Responsive Design

```
Mobile:        0–640px
Tablet:        641–1024px
Desktop:       1025–1440px
Large desktop: 1441px+
```

### Mobile Best Practices
- **Touch targets**: minimum 44×44px
- **Body text**: minimum 16px (prevents iOS zoom)
- **Thumb zones**: primary actions within easy reach
- **Navigation**: hamburger menu or bottom nav

## Accessibility (A11y)

### Must-Haves
- **Keyboard navigation**: all interactive elements reachable via Tab/Enter/Space
- **Focus indicators**: visible focus states — never remove outline without replacement
- **Alt text**: meaningful descriptions for all images
- **ARIA labels**: for icon-only buttons and complex components
- **Color independence**: don't rely solely on color to convey meaning
- **Semantic HTML**: `<button>` for buttons, `<a>` for links, `<nav>`, `<main>`, etc.

```tsx
// Icon-only button needs aria-label
<button onClick={close} aria-label="Close dialog">
  <XIcon />
</button>

// Color alone is not enough — also use text/icon
<span className="error-icon" aria-label="Error">⚠</span>
<span>Required field missing</span>
```

## Common UI Patterns

### Data Tables
- Sortable columns for > 10 rows
- Pagination or infinite scroll for large datasets
- Row selection: checkboxes in first column
- Row actions: icon buttons or dropdown in last column
- On mobile: consider card view

### Modals / Dialogs
- Always provide X close button (top-right)
- Escape key closes the modal
- Click outside backdrop to close (optional but common)
- Trap keyboard focus inside modal while open
- Lock body scroll when modal is open

### Search
- Autocomplete if feasible
- Clear button to reset input
- Helpful "No results" state with suggestions
- Debounce search input (300ms)

### Empty States
- Explain what this area is for
- Clear call-to-action to add the first item
- Use an icon or illustration to avoid blank whitespace

## Performance & UX

- **Skeleton screens** instead of blank space during loading
- **Optimistic updates** for fast-feeling mutations
- **Progressive loading**: show content as it arrives
- **Image optimization**: WebP/AVIF, lazy loading, correct sizes
- **First Contentful Paint** target: < 1.8s
- **Time to Interactive** target: < 3.8s

## Dark Mode

- Don't just invert colors — reduce saturation and brightness
- Avoid pure white on pure black (harsh contrast)
- Elevated surfaces should be slightly lighter
- Test semantic colors — they behave differently in dark mode

```css
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1a1a;
    --fg: #e5e5e5;      /* Not pure white */
    --surface: #2a2a2a; /* Slightly lighter than bg */
  }
}
```

## Implementation Checklist

Before shipping any UI:
- [ ] All interactive elements are keyboard accessible
- [ ] Color contrast meets WCAG AA (4.5:1 normal, 3:1 large text)
- [ ] Focus indicators are visible
- [ ] Touch targets are minimum 44×44px on mobile
- [ ] Loading states exist for all async operations
- [ ] Error states handled gracefully with helpful messages
- [ ] Form validation is clear and specific
- [ ] Empty states provide guidance and CTA
- [ ] Responsive design works across all breakpoints
- [ ] Animations respect `prefers-reduced-motion`

## Tools

- **Figma / Sketch**: Design and prototyping
- **Tailwind CSS**: Utility-first, consistent spacing/colors
- **shadcn/ui or Radix UI**: Accessible component primitives
- **axe DevTools**: Browser extension for a11y testing
- **Lighthouse**: Automated performance + a11y audits

## When to Use This Skill

- Designing new UI components or pages
- Reviewing existing interfaces for quality issues
- Building or extending a component library
- Making accessibility improvements
- Design reviews before feature launch
- Deciding on patterns for new interaction types
