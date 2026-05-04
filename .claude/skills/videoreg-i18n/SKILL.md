---
name: videoreg-i18n
description: videoreg internationalization conventions — engine in sdk/i18n.py (class I18n, accessible as runner.i18n), translation files in sdk/translations/ and plugins/<id>/translations/ (ru.yaml / en.yaml, plugin strings merged on top of global), flat dot-namespaced keys (camera.start_recording), CLDR plural forms (one/few/many/other), Python API plugin.runner.i18n.t/p with {{var}} substitution, JS API VrgI18n / $t / $p loaded via GET /api/i18n, locale set in videoreg.manifest.yaml, fallback to en then to the key itself. Trigger when adding or modifying translation keys in any translations/*.yaml, using $t/$p in Vue components, using i18n.t/p in Python, or setting up i18n in a new plugin.
---

# videoreg internationalization (i18n)

Single i18n stack covers Python (api-methods, commands, errors) and JS (Vue components). One yaml schema, two consumers.

For details on where each consumer lives:
- Python usage in api-methods / commands → `videoreg-api`, `videoreg-command`.
- JS usage in Vue components → `videoreg-frontend`.

This skill is the source of truth for the i18n engine itself: keys, plural forms, file layout, loader.

---

## Engine

- File: `sdk/i18n.py`, class `I18n`.
- Constructed by `ServiceRunner` at startup; accessible from any plugin as `plugin.runner.i18n`.
- **Locale** is set in `videoreg.manifest.yaml` (`locale: ru`). Default: `"ru"`.

---

## Translation file layout

```
sdk/translations/                ← global strings (common.*)
  ru.yaml
  en.yaml
plugins/<plugin_id>/translations/   ← plugin strings, merged on top of global
  ru.yaml
  en.yaml
```

A new plugin that needs strings creates its own `translations/` folder with `ru.yaml` and `en.yaml`. Don't add plugin-specific strings to `sdk/translations/` — keep `sdk/translations/` for cross-cutting `common.*`.

---

## Key format

Flat keys, namespaced with dots:

```yaml
common.error: "Error"
camera.start_recording: "Start recording"
bot.command_error: "Command failed: {{status}}"
```

- **Namespace prefix matches the plugin name** (`camera.*`, `bot.*`, `net.*`, …) or `common.*` for cross-cutting strings.
- Snake_case for the suffix.
- One key per line; nested yaml maps are reserved for plural forms (see below).

---

## Variable substitution

Mustache-style `{{var}}` placeholders:

```yaml
bot.command_error: "Command failed: {{status}}"
```

```python
plugin.runner.i18n.t("bot.command_error", status=404)
# → "Command failed: 404"
```

```javascript
$t('bot.command_error', { status: 404 })
```

---

## Plural forms (CLDR)

Value is a dict keyed by CLDR plural categories: `one`, `few`, `many`, `other`. Pick the categories the locale needs (Russian uses `one / few / many / other`; English uses `one / other`).

```yaml
camera.video_count:
  one: "{{n}} video"
  other: "{{n}} videos"
```

Use `p()` (Python) or `$p()` (JS) — pass the count as a positional integer:

```python
plugin.runner.i18n.p("camera.video_count", 5)   # → "5 videos"
```

```javascript
$p('camera.video_count', 5)
```

The count is also injected as `{{n}}` into the chosen variant.

---

## Python API

```python
plugin.runner.i18n.t("camera.start_recording")            # → "Start recording"
plugin.runner.i18n.t("bot.command_error", status=404)     # variable substitution
plugin.runner.i18n.p("camera.video_count", 5)             # plural form
```

In api-methods and commands the plugin reference is `self._plugin`, so:

```python
self._plugin.runner.i18n.t(...)
```

---

## JS API

A global object `VrgI18n` is exposed; in Vue components use the global properties `$t` / `$p`:

```html
{{ $t('camera.start_recording') }}
{{ $p('camera.video_count', 5) }}
```

Translations are loaded by the frontend at startup via `GET /api/i18n`, which returns the merged dict from all plugins (global `common.*` + each plugin's `<plugin>.*`).

---

## Fallback chain

If a key is missing in the current locale:

1. Look up the key in `en` (the canonical source locale).
2. If still missing → return the key itself (`"camera.foo.bar"`).

Returning the key makes missing translations visible without crashing — but it's a bug, not a feature. Keep `en.yaml` complete.

---

## Rules

- **Both `ru.yaml` and `en.yaml` get every new key.** Don't add to one without the other.
- **Don't concatenate translated fragments in code.** Compose at the yaml level (`{{var}}` substitution) — concatenation breaks word order in other languages.
- **Don't translate identifiers, log messages, or commit messages.** i18n is for user-facing text only. Internal logs and code remain in English.
- **No HTML in values.** If markup is needed, keep it in the component template and pass plain text via i18n.
- **Plural keys live under a dict** with CLDR categories — don't simulate plurals with `{{n}} item(s)`.

---

## Adding a string

1. Pick a key: `<plugin>.<snake_case>` or `common.<snake_case>`.
2. Add the value to **both** `ru.yaml` and `en.yaml` in the right `translations/` folder.
3. Use `t` / `p` (Python) or `$t` / `$p` (JS) at the consumption site.
4. Plural? Use a dict with CLDR categories and `p` / `$p`.

## Adding a new plugin's strings

1. Create `plugins/<plugin_id>/translations/ru.yaml` and `en.yaml`.
2. Use the `<plugin>.*` namespace for all keys.
3. No registration step is needed — the engine picks up plugin folders automatically and merges them on top of `sdk/translations/`.

---

## Examples

See `sdk/translations/en.yaml` for the canonical reference of style and the `common.*` namespace. Each plugin's `translations/` folder demonstrates plugin-scoped keys and plural forms.
