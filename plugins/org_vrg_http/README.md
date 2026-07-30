# HTTP server

HTTPS on port `8443`, self-signed certificate.

Frontend SPA on Vue 3 without a router, backend — aiohttp.

Authorization via HTTP-only JWT cookies.

**External resources via CDN are prohibited** — everything is local.

## Structure

```
plugins/org_vrg_http/
├── plugin.py                   # aiohttp: port, SSL, manifest read, route registration
├── manifest_reader.py          # Scan plugins/*/manifest.yaml http blocks
├── bundle.py                   # Assemble static/js/bundle.js
├── handlers/                   # Route handlers (one file per group)
│   ├── __init__.py             # Export all handler functions
│   ├── static_handlers.py      # Static files, index.html bootstrap injection
│   ├── generic_api_handler.py  # make_api_handler — manifest api → videoreg-api
│   └── <group>_handlers.py
└── static/
    ├── index.html              # Mounts Vue, loads scripts, VRG_BOOTSTRAP marker
    ├── style.css               # Global CSS design system
    └── js/
        ├── app.js              # Vue root: navigation, currentComponent
        ├── icon-registry.js    # Global IconRegistry (loaded before bundle.js)
        ├── bundle.js           # Generated, git-ignored — all Vue components
        └── components/         # org_vrg_http's own UI primitives
            └── pages/          # org_vrg_http's own page components
```

**Frontend:**
- reusable components are documented in `docs/Vue-components.md`;
- navigation via `$emit('navigate', 'page')`;
- `fetch` with `credentials: 'same-origin'` is required everywhere.

## Plugin HTTP manifests

Web assets are owned by their plugin, not by `org_vrg_http`. Each plugin may
declare an `http:` block in `plugins/<id>/manifest.yaml`. Since the http plugin
runs in its own service, at `start()` it scans **every** `plugins/*/manifest.yaml`
(`manifest_reader.read_plugin_http_configs`), caches the result on the plugin and
exposes it via `app["http_manifests"]`.

The `http:` block keys:

- **`api`** — endpoints. Each entry: `url`, `method`, `plugin` (the videoreg-api
  method to call), optional `timeout`. Registered generically as `/api/<url>` via
  `generic_api_handler.make_api_handler`, which reads args from the query
  (GET/DELETE) or JSON body (POST/PUT/PATCH) and forwards them to the method.
  Routes already registered in `plugin.py` are skipped (hardcoded wins —
  transitional).
- **`menu`** / **`menu_settings`** — sidebar / settings-grid entries. Each entry:
  `url`, `title` (an `$<id>.…` i18n token), `icon`, `component`. Not fetched at
  runtime — injected server-side (see Bootstrap injection).
- **`components`** — JS filenames in `plugins/<id>/http/components/` (Vue
  components and icon-registration modules) that go into `bundle.js`.

## bundle.js

`bundle.py::build_bundle` concatenates into a single `static/js/bundle.js`:

1. `org_vrg_http`'s own `static/js/components` — base UI primitives first, then
   `pages/` (order matters: components reference `Icon` and other primitives at
   definition time);
2. every plugin's manifest `components`, in plugin order.

It is **generated, git-ignored, and root-owned at runtime**. Rebuilt on every
plugin start, so a deploy that changes a component never keeps serving the
previously generated bundle (the `?v=<git hash>` cache-buster invalidates the
browser copy, but the file on disk would stay stale). Also built on demand: on a
cold start when the file is missing (`static_handlers`), or explicitly via
`POST /api/http/bundle/rebuild` (the *Rebuild Vue components* button on the
settings page), which additionally re-reads the plugin manifests.

`bundle.js` and `vue.global.js` are served with on-the-fly gzip compression.

## Bootstrap injection

`static_handlers.handle_index` replaces the `<!-- VRG_BOOTSTRAP -->` marker (after
`bundle.js`, before `app.js`) with an inline script built from
`app["http_manifests"]`:

- `window.__vrgMenu` — `menu` / `menu_settings` data;
- `window.__vrgComponents` — a name→object bridge written with literal Vue
  component identifiers resolved from `bundle.js`.

`app.js` and `SettingsComponent.js` merge these with their hardcoded entries, so
manifest-driven and not-yet-migrated plugins coexist.

## Icons & i18n

- **Icons:** a global `IconRegistry` (`icon-registry.js`, loaded before
  `bundle.js`). Plugin icon modules register their SVGs into it; `<icon name>`
  checks the registry, then built-ins. Only plugin-exclusive icons live in the
  plugin.
- **i18n:** the http plugin loads **all** plugins' translations at start (not just
  its own service's). Plugin tokens are namespaced `$<plugin_id>.…`.
