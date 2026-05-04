---
name: videoreg-api
description: videoreg-api method conventions — Method<Name>(ApiMethod) template, method-to-plugin assignment (logic lives where state lives), snake_case method keys, response format {status, data} / {status, error}, registration in plugin_builder.py, calling other plugins via api_client.exec and parsing responses (is_ok / get_data / get_error), error handling, i18n for response strings. Trigger when implementing or modifying a videoreg-api method in plugins/<plugin>/methods/.
---

# videoreg-api method conventions

Templates and rules for writing videoreg-api methods (`plugins/<plugin>/methods/`). For higher-level architectural rules see `videoreg-architecture`. For plugin assembly / `plugin_builder.py` skeleton see `videoreg-plugin`. For HTTP handlers that *call* methods see `videoreg-http-backend`.

**Important:** Never read `plugins/org_vrg_http/static/vue.global.js` — it is huge.

---

## Method-to-plugin assignment

A method must live in the **plugin that owns the state and dependencies it accesses**. Default mapping (camera → `org_vrg_camera`, net → `org_vrg_net`, gps → `org_vrg_gps`, stat → `org_vrg_stat`, power → `org_vrg_power`, bot → `org_vrg_bot`, sms → `org_vrg_sms`, http → `org_vrg_http`, core → `org_vrg_core`, bus → `org_vrg_bus`) is in `CLAUDE.md`.

To list existing methods of a plugin, read `plugins/<plugin>/plugin_builder.py` — they're all registered there.

---

## Method file structure

**File:** `plugins/<plugin_id>/methods/<method_name>.py`

```python
from sdk.socket.api import ApiMethod
from plugins.<plugin_id>.plugin import <Name>Plugin


class Method<Name>(ApiMethod):
    """Brief method description."""

    _plugin: <Name>Plugin

    def __init__(self, plugin: <Name>Plugin):
        super().__init__()
        self._plugin = plugin

    async def exec(self, args):
        try:
            # ... logic via self._plugin ...
            return {
                "status": "ok",
                "data": { ... },
            }
        except Exception as e:
            self._plugin.logger.error(f"Error in <method_name>: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }
```

**Rules:**
- Access plugin dependencies only via `self._plugin`.
- Always return one of the two response shapes (see below).
- Log errors via `self._plugin.logger.error(..., exc_info=True)`.
- Do not include the plugin name in the method key — the prefix is added on the call side (`"<plugin>.<method_key>"`).

---

## Response format

All methods return strictly one of two shapes:

```python
# Success
{"status": "ok", "data": { ... }}

# Error
{"status": "error", "error": "error description"}
```

The `data` field is a free-form dict (or `None`/`{}` if the method has no payload). The `error` field is a human-readable string.

Consumer side (handlers / other plugins) — see "Calling a method" below.

---

## Naming convention

| Item | Style | Example |
|------|-------|---------|
| Method file | `snake_case.py` | `methods/modem_info.py` |
| Method class | `Method<Name>` | `MethodModemInfo` |
| Method key (registration) | `snake_case`, no plugin prefix | `"modem_info"` |
| Call | `"<plugin>.<method_key>"` | `await api_client.exec("net.modem_info", args)` |

When the method backs an HTTP endpoint, the api-method name should match the route's resource name (e.g. `GET /api/net/modem_info` ↔ `net.modem_info`). Cross-layer naming details are in `videoreg-http-backend`.

---

## Registration in `plugin_builder.py`

```python
from plugins.<plugin_id>.methods.<method_name> import Method<Name>

# inside init_api_servier(methods={...}):
"<method_key>": Method<Name>(plugin),
```

The full assembly skeleton is in the `videoreg-plugin` skill. Only the import line and the dict entry need to be added when introducing a new method.

---

## Calling a method (consumer side)

From another plugin (the calling plugin must have `init_api_client()` in its builder):

```python
response = await self.api_client.exec("net.modem_info", args)

if response.is_ok():
    data = response.get_data()    # → dict from the "data" field
else:
    err = response.get_error()    # → string from the "error" field
```

`args` is whatever the method's `exec(self, args)` expects — typically a dict, sometimes `None`. Document the expected shape in the method's docstring.

For HTTP-handler-side consumption (timeouts, error mapping to HTTP status codes), see `videoreg-http-backend`.

---

## i18n in responses

Use the i18n engine for any user-facing strings (errors that may surface in the UI/bot, human-readable status text):

```python
text = self._plugin.runner.i18n.t("camera.start_recording")
text = self._plugin.runner.i18n.t("bot.command_error", status=404)   # variable substitution
text = self._plugin.runner.i18n.p("camera.video_count", n)            # plural form
```

For key format, plural rules, translation file layout and how to add new keys → `videoreg-i18n`.

---

## Task execution algorithm

1. **Determine the owning plugin** (state + dependencies → plugin). If unsure, see `CLAUDE.md` table or the `videoreg-architecture` skill.
2. **Create the method file** at `plugins/<plugin_id>/methods/<method_name>.py` using the template above.
3. **Register** in `plugins/<plugin_id>/plugin_builder.py` (import + entry in `init_api_servier(methods={...})`).
4. **Editing existing code?** Read `plugin_builder.py` first to find the method, then the file in `methods/`.
