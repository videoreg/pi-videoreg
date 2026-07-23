---
name: videoreg-http-backend
description: videoreg HTTP backend conventions — handler template (system handlers without api-client vs plugin handlers using api-client), thin-transport rule, kebab-case route ↔ handle_<verb>_<resource> ↔ api-method naming, dependencies from request.app (api_client / logger / videoreg / jwt_handler / user_manager), parsing api responses (is_ok / get_data / get_error), parallel aggregation via asyncio.gather, route registration in plugins/org_vrg_http/plugin.py, public-path auth rules. Trigger when implementing or modifying an HTTP handler in plugins/org_vrg_http/handlers/.
---

# videoreg HTTP backend conventions

Templates and rules for HTTP handlers in the `org_vrg_http` plugin. For higher-level architectural rules see `videoreg-architecture`. For the videoreg-api methods that handlers call see `videoreg-api`.

**Important:** Never read `plugins/org_vrg_http/static/vue.global.js` — it is huge.

---

## Three-layer flow

```
HTTP request
    ↓
handle_*(request)         ← transport: parsing, auth, response
    ↓
api_client.exec(...)      ← videoreg-api method call
    ↓
MethodXxx.exec(args)      ← all business logic here
```

**Rule:** the handler is a thin transport layer — body parsing, calling `api_client.exec`, mapping errors to HTTP status codes. **No business logic.** Logic lives in the videoreg-api method (`videoreg-api` skill).

---

## Naming convention

| Layer | Style | Example |
|-------|-------|---------|
| HTTP route | `kebab-case` (or `snake_case` matching the api-method) | `GET /api/net/modem_info` |
| Handler function | `handle_<verb>_<resource>` | `handle_get_modem_info` |
| api-method (called) | `<plugin>.<snake_case>` | `net.modem_info` |

Names must match semantically across the layers. If the api-method is `net.modem_info`, the handler is `handle_get_modem_info` and the route is `/api/net/modem_info`.

---

## Handler file locations

- **System handlers** (auth, media, static, users, dashboard) — do not call other plugins via videoreg-api:

  ```
  plugins/org_vrg_http/handlers/<resource>_handlers.py
  ```

- **Plugin handlers** (camera, net, gps, power, etc.) — call other plugins via videoreg-api:

  ```
  plugins/org_vrg_http/handlers/plugins/<plugin_id>/<resource>_handlers.py
  ```

---

## Plugin handler template

**File:** `plugins/org_vrg_http/handlers/plugins/<plugin_id>/<resource>_handlers.py`

```python
from aiohttp import web
from sdk.socket.requests import RequestTimeoutError


async def handle_get_<resource>(request: web.Request):
    logger = request.app["logger"]
    api_client = request.app["api_client"]

    try:
        response = await api_client.exec("<plugin>.<method>", {})
        if not response.is_ok():
            return web.json_response({"error": response.get_error()}, status=500)
        return web.json_response(response.get_data())
    except RequestTimeoutError:
        return web.json_response({"error": "timeout"}, status=504)
    except Exception as e:
        logger.error(f"Error in handle_get_<resource>: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)


async def handle_set_<resource>(request: web.Request):
    logger = request.app["logger"]
    api_client = request.app["api_client"]
    body = await request.json()

    try:
        response = await api_client.exec("<plugin>.<method>", {"field": body.get("field")})
        if not response.is_ok():
            return web.json_response({"error": response.get_error()}, status=500)
        return web.json_response({"status": "ok"})
    except RequestTimeoutError:
        return web.json_response({"error": "timeout"}, status=504)
    except Exception as e:
        logger.error(f"Error in handle_set_<resource>: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)
```

---

## Working with the api response

Methods return `{"status": "ok", "data": ...}` or `{"status": "error", "error": ...}` — see `videoreg-api`. On the consumer side:

```python
response = await api_client.exec("plugin.method", args)
if response.is_ok():
    data = response.get_data()    # → dict from the "data" field
else:
    err = response.get_error()    # → string from the "error" field
```

Map errors to HTTP status:
- `RequestTimeoutError` → `504`
- `not response.is_ok()` → `500` with `{"error": ...}` (or a more specific code if the method's contract guarantees a recognisable error string)
- generic `Exception` → log with `exc_info=True`, return `500`

---

## Available dependencies (from `request.app`)

- `api_client` — call videoreg-api methods (`exec("<plugin>.<method>", args)`)
- `logger` — handler-side logger
- `videoreg` — system config / paths
- `jwt_handler`, `user_manager` — authorization helpers
- `request.get("user")` — authenticated username (set by middleware)

---

## Parallel aggregation (multiple plugins)

When a single endpoint needs data from multiple plugins, fan out with `asyncio.gather(..., return_exceptions=True)` and tolerate partial failures:

```python
import asyncio

async def handle_get_dashboard_status(request: web.Request):
    logger = request.app["logger"]
    api_client = request.app["api_client"]

    r1, r2 = await asyncio.gather(
        api_client.exec("plugin1.method", {}),
        api_client.exec("plugin2.method", {}),
        return_exceptions=True,
    )

    result = {}
    if not isinstance(r1, Exception) and r1.is_ok():
        result["data1"] = r1.get_data()
    else:
        logger.warning(f"Dashboard: data1 error: {r1}")

    if not isinstance(r2, Exception) and r2.is_ok():
        result["data2"] = r2.get_data()

    return web.json_response(result)
```

---

## Route registration

Routes are registered in `plugins/org_vrg_http/plugin.py` inside `_start_server()`:

```python
# Plugin handler:
from plugins.org_vrg_http.handlers.plugins.<plugin_id>.<resource>_handlers import (
    handle_get_<resource>, handle_set_<resource>,
)

# System handler:
from plugins.org_vrg_http.handlers.<resource>_handlers import (
    handle_get_<resource>, handle_set_<resource>,
)

# ...
app.router.add_get("/api/<plugin>/<resource>", handle_get_<resource>)
app.router.add_post("/api/<plugin>/<resource>", handle_set_<resource>)
```

---

## Authorization

Public paths: `/`, `/api/auth/*`, `/static/*`. All other `/api/*` paths are protected automatically by middleware — no per-handler auth code needed. The authenticated username is available as `request.get("user")`.

---

## Task execution algorithm

1. **Need a new endpoint?** First make sure the videoreg-api method exists (or create it — see `videoreg-api`).
2. **System or plugin handler?** No api-client calls → `handlers/<resource>_handlers.py`. Calls one or more plugins → `handlers/plugins/<plugin_id>/<resource>_handlers.py`.
3. **Create / extend the handler file** using the template; map errors to HTTP status codes consistently.
4. **Register the route** in `plugins/org_vrg_http/plugin.py` `_start_server()`.
5. **Aggregating multiple plugins?** Use `asyncio.gather(..., return_exceptions=True)` and degrade gracefully.
