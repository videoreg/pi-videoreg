---
name: videoreg-frontend
description: videoreg frontend conventions — Vue 3 SPA without Vue Router (history.pushState navigation), page component template with fetch + credentials same-origin, settings sub-page registration (back button, settingsPages arrays, SettingsComponent card), Icon component (Material Symbols inline SVG), i18n via $t/$p, reusable components and design system rules. Trigger when creating or modifying Vue components in plugins/org_vrg_http/static/js/, adding a new page or settings sub-page, or working on the videoreg web UI.
---

# videoreg frontend conventions

The videoreg frontend lives in `plugins/org_vrg_http/static/` — a Vue 3 SPA with URL-based navigation (History API, no Vue Router).

For visual styling rules see the `videoreg-design-system` skill.

**Important:** Never read `plugins/org_vrg_http/static/vue.global.js` — it is huge. Vue 3 is already included.

For overall frontend structure, read `plugins/org_vrg_http/README.md`.

---

## Navigation (URL routing)

The SPA uses `history.pushState`. Page switching is done via `navigate(page)` in `app.js`, which updates `currentPage` and the URL. URL scheme:

- `/` → `media-feed` (photo and video feed, start page)
- `/<page>` → top-level page (e.g. `/stat`, `/gps-tracks`)
- `/settings` → settings section list
- `/settings/<name>` → specific settings page (e.g. `/settings/camera`)

Components switch pages via emit:
```javascript
$emit('navigate', 'settings')
```

---

## Status bar

A fixed `status-bar` is displayed at the top of all pages (for authenticated users). It is implemented in `index.html` and `app.js` — not as a separate component. The status bar shows key system statuses: network, GPS, power, etc., updated via `GET /api/status`. When developing pages, do not modify or duplicate the status bar.

---

## Menu structure and settings

The left sidebar contains top-level pages (media, GPS, statistics, etc.) and the **Settings** section.

**Settings** (`/settings`) is a separate list page (`SettingsComponent`) that links to sub-pages: camera, WiFi, modem, WireGuard, Telegram, power, SMS, storage, system, users.

**Rules for settings sub-pages:**
- File: `plugins/org_vrg_http/static/js/components/pages/<Name>SettingsComponent.js`
- The `page-header` must include a Back button:
  ```html
  <button class="btn-back" @click="$emit('navigate', 'settings')" title="Back">
    <icon name="chevron-left" :size="28"></icon>
  </button>
  ```
- Register the page in `app.js`: add to `settingsPages` (in `pageToPath`, `pathToPage`, `isSettingsActive` methods) and in `currentComponent` (in `computed`).
- Add a card to `SettingsComponent.js` (in the `items` array).

**Content pages** (non-settings) are added to the top-level menu in `app.js` in the `navItems` array.

---

## Icons (Icon component)

All icons in the project are SVG paths from the Material Symbols font (Google). They are inlined via the `Icon` component (`js/components/Icon.js`).

The list of available icons is in the `switch` inside `Icon.js` (dashboard, camera, wifi, settings, chevron-left, etc.).

**If a new icon is needed:**
1. Ask the user for the SVG `<path d="...">` for the required icon (viewBox `0 -960 960 960`, Material Symbols).
2. Add a new `case` to `Icon.js`.
3. Use the icon via `<icon name="new-name" :size="24"></icon>`.

Do not use third-party icon fonts or external SVG files.

---

## Vue page component pattern

**File:** `plugins/org_vrg_http/static/js/components/pages/<PageName>Component.js`

```javascript
const ExampleComponent = {
  components: { ToggleSwitch, TabSwitch },  // only if used

  template: `
    <div>
      <div class="page-header">
        <h1 class="page-title">Page Title</h1>
        <div style="display: flex; gap: var(--spacing-sm);">
          <div v-if="loading" class="spinner spinner-sm"></div>
          <button v-else class="btn btn-icon" @click="load" title="Refresh">↻</button>
        </div>
      </div>

      <div v-if="error" class="alert alert-error">{{ error }}</div>
      <div v-if="success" class="alert alert-success">{{ success }}</div>

      <div class="section-title">Section</div>

      <div class="form-group">
        <label class="form-label">Field</label>
        <input class="form-input" v-model="field" :disabled="loading" />
      </div>

      <button class="btn btn-primary" @click="save" :disabled="loading">
        {{ loading ? 'Saving...' : 'Save' }}
      </button>
    </div>
  `,

  data() {
    return {
      field: '',
      error: '',
      success: '',
      loading: false
    };
  },

  methods: {
    async load() {
      this.loading = true;
      try {
        const response = await fetch('/api/example', { credentials: 'same-origin' });
        const data = await response.json();
        if (!response.ok) { this.error = data.error || 'Load error'; return; }
        this.field = data.field;
      } catch (err) {
        this.error = 'Connection error';
      } finally {
        this.loading = false;
      }
    },

    async save() {
      this.error = '';
      this.success = '';
      this.loading = true;
      try {
        const response = await fetch('/api/example', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify({ field: this.field })
        });
        const data = await response.json();
        if (!response.ok) { this.error = data.error || 'Error'; return; }
        this.success = 'Saved';
      } catch (err) {
        this.error = 'Connection error';
      } finally {
        this.loading = false;
      }
    }
  },

  async mounted() { await this.load(); }
};
```

**Rules:**
- `credentials: 'same-origin'` is required in all `fetch` calls
- Reset `error`/`success` before each new operation
- `loading = false` always in `finally`
- Disable fields and buttons via `:disabled="loading"`

---

## i18n (JS)

The app has a built-in i18n engine (`js/i18n.js`). Translations load before Vue mounts via `GET /api/i18n`.

**Global properties** — available in all components:

```javascript
{{ $t('camera.start_recording') }}                      // simple string
{{ $p('camera.video_count', count) }}                   // plural form
{{ $t('bot.command_error', { status: 404 }) }}          // with variable substitution
```

**Do not hardcode user-facing strings** — always use `$t`/`$p` for new text in components.

For key format, plural rules, translation file layout and how to add new keys → `videoreg-i18n`.

---

## Reusable components

Documentation: `docs/Vue-components.md`

Include in `components: { ... }` only the ones used on the page.

**Rule:** Always use existing components. If a new reusable component is needed — create it in `js/components/`, include it in `index.html` (before `app.js`), and add a description to `docs/Vue-components.md`.

---

## Design system (style.css)

Documentation: `docs/CSS.md`

**Rule:** Always use existing classes and CSS variables from `plugins/org_vrg_http/static/style.css`. Do not write new styles on your own — the `videoreg-design-system` skill describes when and how to introduce them.

---

## Registering a new page component

### 1. Create the component file

`plugins/org_vrg_http/static/js/components/pages/<PageName>Component.js`

### 2. Include in index.html

Add a `<script>` **before** `app.js`, **after** ToggleSwitch and TabSwitch:
```html
<script src="/static/js/components/ExampleComponent.js"></script>
```

### 3. Add to app.js

In `computed.currentComponent` — page-to-component mapping:
```javascript
currentComponent() {
  const map = {
    // ...
    example: ExampleComponent,  // ← add here
  };
  return map[this.currentPage] || MediaFeedComponent;
}
```

For top-level pages — add an entry to `navItems`:
```javascript
navItems: [
  // ...
  { id: 'example', label: 'Example', icon: 'icon-name' }
]
```

For settings sub-pages — add `'example'` to the `settingsPages` arrays in `pageToPath`, `pathToPage`, `isSettingsActive` methods and a card to `SettingsComponent.js`.

---

## If a new HTTP endpoint is needed

The frontend layer does **not** implement HTTP handlers — that lives in the backend. If a component needs data not available in the existing API:

1. Describe the endpoint requirement: method (`GET`/`POST`), path, request/response schema
2. Use a stub or `console.warn` in the component until the endpoint exists
3. Implement the backend side using the `videoreg-api` and `videoreg-http-backend` skills (or delegate to `videoreg-agent-backender` for non-trivial work)

To find existing methods: read `plugins/<plugin>/plugin_builder.py` — all registered methods are listed there.

---

## Task execution algorithm

1. **New top-level page** → create JS file, include in `index.html`, add to `app.js` (`currentComponent` + `navItems`)
2. **New settings sub-page** → create JS file with back button, include in `index.html`, add to `app.js` (`currentComponent` + `settingsPages`), add card to `SettingsComponent.js`
3. **Editing existing code** → find and read the file before modifying
4. **New icon needed** → ask user for SVG `<path d="...">`, add to `Icon.js`
5. **New API needed** → describe the requirement (method, path, schema), implement via `videoreg-api` + `videoreg-http-backend` or delegate to the backender agent
6. **New style needed** → use the `videoreg-design-system` skill (or delegate to `videoreg-agent-designer`); after the new class exists, use it in the component
7. **New reusable component created** → add a description of it to `docs/Vue-components.md` (name, purpose, props, usage example)
8. **No specific task** → explore the current `static/js/` structure and ask what needs to be done

Follow conventions: no CDN, reuse existing styles and components.
