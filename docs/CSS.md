# CSS Design System — Videoreg

Dark-theme design system. All styles are defined in `src/http/static/style.css`.

---

## CSS Variables

Use variables instead of hardcoded colors and spacing values.

### Colors

```css
/* Primary accent */
--color-primary: #c8ccd6        /* light grey — primary buttons and focus */
--color-primary-hover: #b0b5c2
--color-primary-light: #dde1ea

/* Backgrounds (dark to light) */
--color-bg-main: #12141a       /* main page background — near-black with a subtle blue tint */
--color-bg-secondary: #1c1e25  /* card and sidebar backgrounds */
--color-bg-tertiary: #272a33   /* input backgrounds, hover states, disabled */

/* Input */
--color-bg-input: #161820      /* input field background */

/* Text */
--color-text-primary: #f1f5f9      /* primary text */
--color-text-secondary: #8b92a5   /* secondary text, labels */
--color-text-placeholder: #4e5568 /* placeholder in input fields */

/* Borders */
--color-border: #2e3040
--color-border-light: #3d4052

/* Accent */
--color-accent: #5b7fc4        /* blue — used in toggle-switch and background glow */

/* Status */
--color-success: #10b981
--color-error: #ef4444
--color-warning: #f59e0b

/* Background glow */
--bg-glow: radial-gradient(...)  /* two radial gradients with low-opacity rgba(--color-accent) */
```

#### `--bg-glow`

The variable contains two radial gradients that create a visible blue glow on the page background:

- large ellipse (90vw × 70vh) in the top-right corner — 13% opacity
- smaller ellipse (70vw × 60vh) in the bottom-left corner — 9% opacity

Applied via `background-image` on `body` together with `background-attachment: fixed` — the gradient does not scroll with the content. `background-color` on `body` remains `--color-bg-main`.

### Spacing

```css
--spacing-xs: 4px
--spacing-sm: 8px
--spacing-md: 16px
--spacing-lg: 24px
--spacing-xl: 32px
```

### Border radius

```css
--radius-sm: 4px
--radius-md: 6px
--radius-lg: 8px
```

---

## Typography

### `page-header` — page title row

Wrapper for the page heading. Always use it around `h1.page-title` — it provides bottom spacing and aligns content horizontally, allowing buttons to sit next to the title without inline styles.

```html
<!-- Title only -->
<div class="page-header">
  <h1 class="page-title">Page Title</h1>
</div>

<!-- Title with a button -->
<div class="page-header">
  <h1 class="page-title">Page Title</h1>
  <button class="btn btn-icon" @click="refresh" title="Refresh">↻</button>
</div>
```

| Property | Value |
|---|---|
| `display` | `flex` |
| `align-items` | `center` |
| `gap` | `--spacing-sm` |
| `margin-bottom` | `--spacing-lg` |

### Typography classes

```html
<p class="page-subtitle">Page subtitle or description</p>

<div class="section-title">Section heading</div>
```

| Class | Size | Usage |
|---|---|---|
| `page-title` | 1.875rem, bold | Main page heading; always inside `.page-header` |
| `page-subtitle` | 1rem, secondary | Page description/subtitle |
| `section-title` | 1.25rem, bold | Block heading within a page |

---

## Buttons

```html
<!-- Primary button -->
<button class="btn btn-primary">Save</button>

<!-- Destructive / danger button -->
<button class="btn btn-danger">Delete</button>

<!-- Full width -->
<button class="btn btn-primary btn-block">Sign in</button>

<!-- Disabled during loading -->
<button class="btn btn-primary" :disabled="loading">
  {{ loading ? 'Loading...' : 'Save' }}
</button>
```

Modifiers: `btn-primary`, `btn-danger`, `btn-block`.
`:disabled` automatically applies `opacity: 0.5` and `cursor: not-allowed`.

### btn-icon — icon button without background

Used next to headings or in rows for actions that don't need an accent button (refresh, copy, etc.). Transparent background; hover — subtle darkening; active — darker background.

```html
<button class="btn btn-icon" @click="refresh" :disabled="loading" title="Refresh">
  ↻
</button>
```

| Class | Description |
|---|---|
| `.btn-icon` | Transparent background, `color: --color-text-secondary`, `padding: 8px 10px`, `font-size: 1.125rem` |
| `.btn-icon:hover` | `background: --color-bg-tertiary`, `color: --color-text-primary` |
| `.btn-icon:active` | `background: --color-border-light` |
| `.btn-icon:disabled` | `opacity: 0.4`, `cursor: not-allowed` |

---

## Forms

```html
<div class="form-group">
  <label class="form-label" for="field-id">Field name</label>
  <input
    type="text"
    id="field-id"
    class="form-input"
    v-model="value"
    :disabled="loading"
    placeholder="Enter value"
  />
  <span class="form-hint">Hint below the field</span>
</div>
```

For `textarea` — same class `form-input`:

```html
<textarea
  class="form-input"
  v-model="config"
  rows="10"
  style="font-family: monospace; font-size: 0.875rem; resize: vertical;"
></textarea>
```

For `select` — same class `form-input`. The native browser appearance is reset via `appearance: none`; a custom arrow is added on the right so that `select` looks consistent with `input`:

```html
<select class="form-input" v-model="value">
  <option value="a">Option A</option>
  <option value="b">Option B</option>
</select>
```

The placeholder color is defined by `--color-text-placeholder` (`#4e5568`) — noticeably darker than the primary text to visually distinguish it from entered values. Applied via `::placeholder` on `.form-input`.

For a read-only field (e.g. keys):

```html
<div style="display: flex; gap: var(--spacing-sm);">
  <input type="text" class="form-input" :value="key" readonly style="flex: 1; font-family: monospace;" />
  <button class="btn btn-primary">Copy</button>
</div>
```

---

## Alerts

```html
<div v-if="error" class="alert alert-error">{{ error }}</div>
<div v-if="success" class="alert alert-success">{{ success }}</div>
<div v-if="info" class="alert alert-info">{{ info }}</div>
```

Typically declared in `data()` as empty strings and shown via `v-if`:

```js
data() {
  return {
    error: '',
    success: '',
    loading: false
  }
}
```

---

## Status indicator

Used to display connection/activity state.

```html
<!-- Inactive -->
<span class="status-indicator">
  <span class="status-dot"></span>
  <span>inactive</span>
</span>

<!-- Active (green dot with pulse animation) -->
<span class="status-indicator">
  <span class="status-dot active"></span>
  <span>active</span>
</span>

<!-- Reactive variant -->
<span class="status-indicator">
  <span class="status-dot" :class="{ active: isActive }"></span>
  <span>{{ isActive ? 'active' : 'inactive' }}</span>
</span>

<!-- Compact (less padding) -->
<span class="status-indicator" style="padding: 3px 8px;">
  <span class="status-dot" :class="{ active: enabled }"></span>
  <span>{{ enabled ? 'on' : 'off' }}</span>
</span>
```

---

## Content sections

### `content-section`

Structural container for dividing a page into logical blocks. Adds bottom spacing between sections.

```html
<div class="content-section">
  <div class="section-title">Block heading</div>
  <!-- content -->
</div>

<div class="content-section">
  <!-- next block -->
</div>
```

### `info-block`

Card with background and border. Used to display data, summaries, and results.

```html
<div class="info-block">
  <div class="section-title">Card heading</div>
  <!-- content -->
</div>
```

### `info-rows` / `info-row` / `info-label` — key-value rows

Unified pattern for displaying key–value pairs inside `info-block`.

```html
<div class="info-block">
  <div class="section-title">Information</div>
  <div class="info-rows">
    <div class="info-row">
      <span class="info-label">IP address</span>
      <code class="code-inline">192.168.1.1</code>
    </div>
    <div class="info-row">
      <span class="info-label">Status</span>
      <span>active</span>
    </div>
  </div>
</div>
```

| Class | Description |
|---|---|
| `.info-rows` | Grid container for rows, `gap: --spacing-sm` |
| `.info-row` | Flex row: key on the left, value on the right; `border-bottom: --color-border`; last row has no border |
| `.info-label` | Key label: `color: --color-text-secondary` |

### `info-table` — table inside info-block

Alternative to `info-rows` when data has a tabular structure with column headers. Row vertical padding (`var(--spacing-sm) 0`) matches `.info-row`, so tables and info-rows look consistent inside the same `info-block`.

```html
<div class="info-block">
  <div class="section-title">Routes</div>
  <table class="info-table">
    <thead>
      <tr>
        <th>Network</th>
        <th>Gateway</th>
        <th>Interface</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>192.168.1.0/24</td>
        <td>—</td>
        <td>eth0</td>
      </tr>
      <tr>
        <td>0.0.0.0/0</td>
        <td>192.168.1.1</td>
        <td>eth0</td>
      </tr>
    </tbody>
  </table>
</div>
```

| Class | Description |
|---|---|
| `.info-table` | `width: 100%`, `border-collapse: collapse`, `font-size: 0.875rem` |
| `.info-table th` | Column header: `text-align: left`, `padding: --spacing-sm 0`, `border-bottom: --color-border`, `color: --color-text-secondary`, `font-weight: 500`, `white-space: nowrap` |
| `.info-table td` | Cell: `padding: --spacing-sm 0`, `border-bottom: --color-border` |
| `.info-table tbody tr:last-child td` | Last body row has no bottom border |

### `loading-state` — loading state

Centered block with a spinner and text. Use instead of inline styles.

```html
<div class="loading-state">
  <div class="spinner"></div>
  <p>Loading...</p>
</div>
```

| Class | Description |
|---|---|
| `.loading-state` | `text-align: center`, `padding: --spacing-xl 0` |
| `.loading-state p` | `margin-top: --spacing-md`, `color: --color-text-secondary` |

### `code-inline` — inline code

For displaying IP addresses, keys, and commands.

```html
<code class="code-inline">192.168.1.1</code>
```

| Class | Description |
|---|---|
| `.code-inline` | `background: --color-bg-tertiary`, `padding: 2px 6px`, `border-radius: --radius-sm` |

---

## Progress bar

Reusable component for displaying numeric values as a filled bar: battery level, signal strength, disk usage.

### Structure

```html
<!-- With text (percentage on the right) -->
<div class="progress-bar">
  <div class="progress-track">
    <div class="progress-fill" :style="{ width: value + '%' }"></div>
  </div>
  <span class="progress-label">{{ value }}%</span>
</div>

<!-- Track only, no text -->
<div class="progress-track">
  <div class="progress-fill" :style="{ width: value + '%' }"></div>
</div>
```

### Fill color modifiers

| Class | Variable | Usage |
|---|---|---|
| `.progress-fill` (base) | `--color-success` | Normal state |
| `.progress-fill--warning` | `--color-warning` | Warning |
| `.progress-fill--critical` | `--color-error` | Critical state |

### Reactive color modifier (Vue)

Typical pattern — computed class based on value:

```html
<div class="progress-bar">
  <div class="progress-track">
    <div
      class="progress-fill"
      :class="{
        'progress-fill--warning':  value >= 70 && value < 90,
        'progress-fill--critical': value >= 90
      }"
      :style="{ width: value + '%' }"
    ></div>
  </div>
  <span class="progress-label">{{ value }}%</span>
</div>
```

For battery the logic is reversed (low charge = bad):

```html
<div
  class="progress-fill"
  :class="{
    'progress-fill--warning':  value < 50 && value >= 20,
    'progress-fill--critical': value < 20
  }"
  :style="{ width: value + '%' }"
></div>
```

### Classes

| Class | Description |
|---|---|
| `.progress-bar` | Wrapper: flex row, track + optional text, `gap: --spacing-sm` |
| `.progress-track` | Background track: `height: 8px`, background `--color-bg-tertiary`, radius `--radius-sm` |
| `.progress-fill` | Fill: `background: --color-success`, transition `width 0.3s ease` |
| `.progress-fill--warning` | Modifier: `background: --color-warning` |
| `.progress-fill--critical` | Modifier: `background: --color-error` |
| `.progress-label` | Text to the right of the track: `font-size: 0.875rem`, `font-weight: 500`, `min-width: 36px` |

---

## Spinner

Loading indicator.

```html
<div style="text-align: center; padding: var(--spacing-xl) 0;">
  <div class="spinner"></div>
  <p style="margin-top: var(--spacing-md); color: var(--color-text-secondary);">Loading...</p>
</div>
```

---

## Mobile menu (drawer/sidebar overlay)

On mobile (up to 768px) the sidebar is hidden by default and slides in over the content. On desktop these classes have no effect.

### Burger button

Fixed-position button in the top-left corner. Visible on mobile only.

```html
<button class="sidebar-burger" @click="toggleSidebar" aria-label="Open menu">
  <span class="sidebar-burger-line"></span>
  <span class="sidebar-burger-line"></span>
  <span class="sidebar-burger-line"></span>
</button>
```

### Overlay (background dimming)

Semi-transparent overlay shown when the menu is open. Closes the menu on click.

```html
<div v-if="sidebarOpen" class="sidebar-overlay" @click="closeSidebar"></div>
```

### Open sidebar modifier

```html
<aside class="sidebar" :class="{ 'sidebar--open': sidebarOpen }">
```

### Classes

| Class | Description |
|---|---|
| `.sidebar-burger` | Burger button, `display: none` on desktop, `display: flex` on mobile |
| `.sidebar-burger-line` | Single horizontal bar of the burger |
| `.sidebar-overlay` | Background dimming (`rgba(0,0,0,0.6)`), `z-index: 150` |
| `.sidebar--open` | Sidebar modifier: shifts it into the visible area (`translateX(0)`) |

### `.sidebar` behavior by breakpoint

| Breakpoint | Background | Border | Shadow | Note |
|---|---|---|---|---|
| `≤ 768px` (mobile) | `--color-bg-secondary` | `1px solid --color-border` on the right | `2px 0 8px rgba(0,0,0,0.3)` | Drawer above content — visual layer separation is required |
| `≥ 769px` (desktop) | `transparent` | none | none | Fixed sidebar is part of the layout; no extra highlighting needed |

---

## Tooltip

Styles for the `Tooltip.js` component.

### Tooltip container

| Class | Description |
|---|---|
| `.tooltip-anchor` | Anchor wrapper: `position: relative`, `display: inline-flex` |
| `.tooltip-popup` | Floating block: `position: fixed`, `z-index: 2000`, background `--color-bg-secondary`, border `--color-border-light`, `border-radius: --radius-lg`, shadow `0 8px 24px rgba(0,0,0,0.5)`, `padding: --spacing-md` |

### Buttons inside a tooltip

Menu-item button style — transparent background, hover highlight. Visually similar to sidebar navigation items.

```html
<!-- Regular menu-item button -->
<button class="tooltip-btn">Settings</button>

<!-- Small button for placement in a row -->
<button class="tooltip-btn tooltip-btn-sm">Start</button>
```

| Class | Description |
|---|---|
| `.tooltip-btn` | Transparent background, `color: --color-text-secondary`, `padding: --spacing-sm`, `border-radius: --radius-md`, `width: 100%`, `text-align: left` |
| `.tooltip-btn:hover` | `background: --color-bg-tertiary`, `color: --color-text-primary` |
| `.tooltip-btn:disabled` | `opacity: 0.4`, `cursor: not-allowed` |
| `.tooltip-btn-sm` | Modifier: reduced padding (`5px --spacing-sm`), `font-size: 0.875rem` |
| `.tooltip-btn--danger` | Modifier: `color: --color-error`, hover with red background. For destructive actions. |
| `.tooltip-btn--success` | Modifier: `color: --color-success`, hover with green background. For confirming a successful action. |
