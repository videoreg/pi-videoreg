# Vue Components — Videoreg

Reusable components are registered globally via `index.html` before `app.js`, so they are available as global variables in all component files.

---

## Using a component on a new page

To use a reusable component, declare it in your component's `components` option:

```js
const MyComponent = {
  components: { ToggleSwitch, TabSwitch },
  // ...
};
```

No need to register them in `app.js` — they are already loaded as global variables.

---

## ToggleSwitch

An iOS-style toggle switch.
File: [js/components/ToggleSwitch.js](../src/http/static/js/components/ToggleSwitch.js)

### Props

| Prop | Type | Default | Description |
|---|---|---|---|
| `modelValue` | Boolean | `false` | Toggle state |
| `label` | String | `''` | Text to the right of the toggle (hidden when empty) |
| `disabled` | Boolean | `false` | Disables interaction |

### Emits

`update:modelValue` — new boolean value on toggle.

### Examples

**Basic with `v-model`:**

```html
<toggle-switch v-model="enabled"></toggle-switch>
```

**With a label:**

```html
<toggle-switch v-model="enabled" label="Enable feature"></toggle-switch>
```

**Disabled during loading:**

```html
<toggle-switch v-model="enabled" :disabled="loading" label="Auto-connect"></toggle-switch>
```

**With a change handler (in addition to `v-model`):**

```html
<toggle-switch
  v-model="enabled"
  :disabled="loading"
  label="Enable WiFi"
  @update:modelValue="onToggle"
></toggle-switch>
```

```js
methods: {
  async onToggle(value) {
    // value — new boolean value
    await this.applyChange(value);
  }
}
```

**Without a label, with a separate description alongside:**

```html
<div style="display: flex; align-items: center; gap: var(--spacing-md);">
  <toggle-switch v-model="ap.enabled" :disabled="loading" @update:modelValue="onApToggle"></toggle-switch>
  <div>
    <div style="font-weight: 500;">📡 Access Point</div>
    <div style="font-size: 0.875rem; color: var(--color-text-secondary);">Device creates a WiFi network</div>
  </div>
</div>
```

---

## TabSwitch

A tab switcher. Renders a row of buttons; the active one is highlighted in blue.
File: [js/components/TabSwitch.js](../src/http/static/js/components/TabSwitch.js)

### Props

| Prop | Type | Required | Description |
|---|---|---|---|
| `modelValue` | String | yes | `value` of the active tab |
| `tabs` | Array | yes | Array of tabs: `[{ value, label }]` |
| `disabled` | Boolean | no | Disables all buttons |

### Emits

`update:modelValue` — `value` string of the selected tab.

### Usage example

```js
data() {
  return {
    activeTab: 'status',
    tabs: [
      { value: 'status',   label: 'Status' },
      { value: 'settings', label: 'Settings' },
    ]
  };
}
```

```html
<tab-switch
  v-model="activeTab"
  :tabs="tabs"
  style="margin-bottom: var(--spacing-lg);"
></tab-switch>

<div v-if="activeTab === 'status'">
  <!-- Status tab content -->
</div>

<div v-if="activeTab === 'settings'">
  <!-- Settings tab content -->
</div>
```

**Disabled:**

```html
<tab-switch v-model="activeTab" :tabs="tabs" :disabled="loading"></tab-switch>
```

---

## Tooltip

A floating menu positioned relative to an anchor element.
File: `js/components/Tooltip.js`

Automatically picks its position (below the anchor if there is enough space, otherwise above), centers horizontally relative to the anchor without going off-screen. Closes on click outside.

### Slots

| Slot | Description |
|---|---|
| `anchor` | Anchor element. Receives `{ open }` — a function to open/close the tooltip |
| `default` | Content of the floating block |

### Methods (via `ref`)

| Method | Description |
|---|---|
| `close()` | Closes the tooltip programmatically |

### Usage example

```html
<tooltip ref="myTooltip">
  <template #anchor="{ open }">
    <span class="status-item" @click="open">Anchor</span>
  </template>
  <!-- tooltip content -->
  <div>Info line</div>
  <button class="tooltip-btn" @click="doAction(); $refs.myTooltip.close();">
    Action
  </button>
</tooltip>
```

### Buttons inside a tooltip

Use CSS design system classes for menu-item buttons inside a tooltip:

```html
<!-- Regular menu-item button -->
<button class="tooltip-btn" @click="...">Menu item</button>

<!-- Small button (in a row) -->
<div style="display: flex; gap: var(--spacing-xs);">
  <button class="tooltip-btn tooltip-btn-sm" style="flex: 1;">Start</button>
  <button class="tooltip-btn tooltip-btn-sm" style="flex: 1;">Pause</button>
</div>
```

See `docs/CSS.md` for details on `.tooltip-btn` and `.tooltip-btn-sm` styles.
