# HTTP server

HTTPS on port `8443`, self-signed certificate.

Frontend SPA on Vue 3 without a router, backend — aiohttp.

Authorization via HTTP-only JWT cookies.

**External resources via CDN are prohibited** — everything is local.

## Structure

```
plugins/org_vrg_http/
├── plugin.py               # aiohttp: port, SSL, route registration
├── handlers/               # Route handlers (one file per group)
│   ├── __init__.py         # Export all handler functions
│   └── <group>_handlers.py
└── static/
    ├── index.html          # Mounts Vue, loads scripts
    ├── style.css           # Global CSS design system
    └── js/
        ├── app.js          # Vue root: navigation, currentComponent
        └── components/     # UI primitives
            └── pages/      # Page components
```

**Frontend:**
- reusable components are documented in `docs/Vue-components.md`;
- navigation via `$emit('navigate', 'page')`;
- `fetch` with `credentials: 'same-origin'` is required everywhere.
