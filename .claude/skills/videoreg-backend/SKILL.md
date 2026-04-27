---
name: videoreg-backend
description: videoreg backend conventions — how to write a videoreg-api method (Method<Name>(ApiMethod) template, plugin registration in plugin_builder.py), HTTP handler templates (system vs plugin handler, parallel aggregation via asyncio.gather), interface command pattern (InterfaceCommand, InterfaceCommandMethod), i18n usage from Python (plugin.runner.i18n.t/p). Trigger when implementing or modifying a videoreg-api method, an HTTP handler in plugins/org_vrg_http/handlers/, or a plugin command in plugins/<plugin>/commands/.
---

# videoreg backend conventions

Templates and step-by-step rules for backend work: videoreg-api methods, HTTP handlers, interface commands, i18n.

For higher-level architectural rules (layer separation, naming, response format, plugin assignment) see the `videoreg-architecture` skill.

**Important:** Never read `plugins/org_vrg_http/static/vue.global.js` — it is huge.

---

## Part 1: videoreg-api methods

### Method structure

**File:** `plugins/<plugin>/methods/<method_name>.py`

```python
from sdk.socket.api import ApiMethod
from plugins.<plugin>.plugin import <plugin>Plugin


class Method<MethodName>(ApiMethod):
    """Brief method description"""

    _plugin: <plugin>Plugin

    def __init__(self, plugin: <Service>Service):
        super().__init__()
        self._plugin = plugin

    async def exec(self, args):
        try:
            # ... logic via self._plugin ...
            return {
                "status": "ok",
                "data": { ... }
            }
        except Exception as e:
            self._plugin.logger.error(f"Error in <method_name>: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e)
            }
```

**Rules:**
- Method lives in the plugin that owns the state it accesses (camera, net, gps, stat, power...)
- Always return `{"status": "ok", "data": ...}` or `{"status": "error", "error": ...}`
- Use only `self._plugin` to access plugin dependencies
- Log errors via `self._plugin.logger.error(..., exc_info=True)`

### Registering a method

**File:** `plugins/<plugin>/plugin_builder.py`

```python
from plugins.<plugin>.method.<method_name> import Method<MethodName>

# In init_api_server(methods={...}):
"<method_key>": Method<MethodName>(plugin),
```

Call from another plugin: `api_client.exec("<plugin>.<method_key>", args)`

### Finding existing methods

Read `plugins/<plugin>/plugin_builder.py` — all registered methods are listed there.

---

## Part 2: HTTP handlers

### Handler file locations

- **System handlers** (auth, media, static, users, dashboard) — do not interact with other plugins via videoreg-api:
  `plugins/org_vrg_http/handlers/<resource>_handlers.py`

- **Plugin handlers** (camera, net, gps, power, etc.) — interact with other plugins via videoreg-api:
  `plugins/org_vrg_http/handlers/plugins/<plugin_id>/<resource>_handlers.py`

### Handler file structure

**File:** `plugins/org_vrg_http/handlers/plugins/<plugin_id>/<resource>_handlers.py`

```python
from aiohttp import web
from sdk.socket.requests import RequestTimeoutError

async def handle_get_<resource>(request: web.Request):
    logger = request.app["logger"]
    api_client = request.app["api_client"]

    try:
        response = await api_client.exec("plugin.method", {})
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
        response = await api_client.exec("plugin.method", {"field": body.get("field")})
        if not response.is_ok():
            return web.json_response({"error": response.get_error()}, status=500)
        return web.json_response({"status": "ok"})
    except RequestTimeoutError:
        return web.json_response({"error": "timeout"}, status=504)
    except Exception as e:
        logger.error(f"Error in handle_set_<resource>: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)
```

**Available dependencies from `request.app`:**
- `api_client` — call videoreg-api methods
- `logger` — logger
- `videoreg` — system config
- `jwt_handler`, `user_manager` — authorization
- `request.get("user")` — authenticated username (middleware)

### Parallel aggregation (multiple plugins)

```python
import asyncio

async def handle_get_dashboard_status(request: web.Request):
    logger = request.app["logger"]
    api_client = request.app["api_client"]

    r1, r2 = await asyncio.gather(
        api_client.exec("plugin1.method", {}),
        api_client.exec("plugin2.method", {}),
        return_exceptions=True
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

### Registering a handler

Register the route in `plugins/org_vrg_http/plugin.py` in the `_start_server()` method:

```python
# For a plugin handler:
from plugins.org_vrg_http.handlers.plugins.<plugin_id>.<resource>_handlers import handle_get_<resource>, handle_set_<resource>

# For a system handler:
from plugins.org_vrg_http.handlers.<resource>_handlers import handle_get_<resource>, handle_set_<resource>

# ...
app.router.add_get("/api/<resource>", handle_get_<resource>)
app.router.add_post("/api/<resource>", handle_set_<resource>)
```

**Authorization:** public paths — only `/`, `/api/auth/*`, `/static/*`. All other `/api/*` paths are protected by middleware automatically.

---

## Part 3: interface commands

Commands are how a plugin reacts to user actions via an interface (bot, sms, etc.). Unlike videoreg-api methods, commands do not return data directly — they asynchronously reply to the user via `interface.send_*`.

### Command structure

**File:** `plugins/<plugin>/commands/<command_name>.py`

```python
from sdk.interface import Interface, InterfaceCommand, InterfaceInteractions

class Command<Name>(InterfaceCommand):
    _plugin: <Plugin>

    def __init__(self, plugin: <Plugin>):
        super().__init__()
        self._plugin = plugin

    async def exec(self, interface: Interface, payload, args):
        # ... logic ...
        await interface.send_text(payload, "result text")
        # or: send_image(payload, path), send_video(payload, path, w, h), send_document(payload, path)
        # check support: interface.support(InterfaceInteractions.VIDEO.value)
```

### Registration in plugin_builder.py

```python
from sdk.interface import Interface, InterfaceCommand, InterfaceCommandMethod

interfaces = Interface.parse_interfaces(runner.videoreg.manifest.interfaces, plugin.logger, plugin.api_client)
commands: dict[str, InterfaceCommand] = {
    "<command_key>": Command<Name>(plugin),
}

plugin.init_api_servier(methods={
    "command": InterfaceCommandMethod(interfaces, commands),
    ...
})
```

Call from the interface side: `api_client.exec("<plugin>.command", {"command": "<command_key>", "interface": "bot", "payload": ..., "args": ...})`

### Algorithm for adding a command

1. Create `plugins/<plugin>/commands/<command_name>.py`, class `Command<Name>(InterfaceCommand)`
2. Implement `async def exec(self, interface, payload, args)`
3. Register in `plugin_builder.py` in the `commands` dict
4. If needed, add an "entry" command to `videoreg.manifest.json` (under `commands`)

---

## i18n (Python)

The system has a built-in i18n engine. Use it for any user-facing strings — bot replies, command responses, error messages.

**Access:** `plugin.runner.i18n` (instance of `sdk.i18n.I18n`)

```python
# Simple string
text = plugin.runner.i18n.t("camera.start_recording")

# With variable substitution
text = plugin.runner.i18n.t("bot.command_error", status=404)

# Plural form
text = plugin.runner.i18n.p("camera.video_count", n)
```

**Adding new strings:** add the key to `plugins/<id>/translations/ru.yaml` and `en.yaml`. Format: flat key, namespaced with dot (`camera.*`, `bot.*`, `common.*`). See `sdk/translations/en.yaml` for examples.

---

## Task execution algorithm

1. **Business logic needed?** → create a videoreg-api method in the correct plugin (see `videoreg-architecture` for plugin assignment)
2. **HTTP endpoint needed?** → create/extend a handler file in the correct folder (`handlers/` or `handlers/plugins/<plugin_id>/`), register route in `plugin.py`
3. **Editing existing code** → find and read the file before modifying
4. **No task** → explore `plugins/org_vrg_http/handlers/` and `plugins/<plugin>/plugin_builder.py`, ask what needs to be done
