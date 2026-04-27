---
name: videoreg-design-system
description: videoreg design system rules — editing plugins/org_vrg_http/static/style.css (CSS variables, dark theme, no hardcoded colors/spacing), keeping docs/CSS.md in sync, responsiveness from 320px to desktop, what's allowed (extending classes, new modifiers) vs not allowed (renaming/removing existing classes). Trigger when changing visual appearance, color scheme, typography, spacing, shadows, layout consistency, or responsiveness in the videoreg web UI.
---

# videoreg design system

Rules for changing the visual appearance of the videoreg web interface: design system styles, color scheme, typography, spacing, readability, layout consistency, responsiveness.

This skill covers visual design only. Vue component logic is described in the `videoreg-frontend` skill.

**Important:** Never read `plugins/org_vrg_http/static/vue.global.js` — it is huge.

---

## Key files

- `plugins/org_vrg_http/static/style.css` — the project's single CSS file: variables, classes, components
- `docs/CSS.md` — design system documentation: all variables, classes, patterns with examples

**Always start by reading both files** before making any changes.

---

## Design system principles

Dark theme. Everything via CSS variables — no hardcoded colors or spacing values.

Detailed documentation of variables, classes, and patterns is in `docs/CSS.md`.

---

## Modifying style.css

**Allowed:**
- Adding and modifying CSS variables
- Extending existing classes (colors, shadows, radii, animations, sizes)
- Adding new classes and modifiers
- Improving responsiveness via media queries

**Not allowed:**
- Renaming or deleting existing classes — this will break components
- Using hardcoded values instead of variables

After changes — update `docs/CSS.md`.

---

## Responsiveness

The interface must work correctly from 320px (mobile) to wide desktop screens. When editing layout, account for breakpoints and avoid horizontal scrolling.

---

## Task execution algorithm

1. Read `style.css` and `docs/CSS.md`
2. Make changes to `style.css`
3. Update `docs/CSS.md` — add descriptions of new variables or classes, update changed ones
