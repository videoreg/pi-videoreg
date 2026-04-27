---
name: videoreg-architecture
description: videoreg architecture rules — three-layer request flow (HTTP handler → api_client → ApiMethod), method-to-plugin assignment, naming conventions (HTTP route ↔ handler ↔ api-method), videoreg-api response format {status, data/error}, plugin pattern, command pattern, HTTP layer structure. Trigger when planning a videoreg feature, deciding where a method should live, reviewing a handler/method, or any architectural question about plugins, services, or videoreg-api.
---

# videoreg architecture conventions

These rules are the source of truth for how the videoreg codebase is organised. Apply them when planning a feature, deciding where a method belongs, or reviewing a handler/method/module.

**Important:** Never read `plugins/org_vrg_http/static/vue.global.js` — it is huge.

System overview, plugin/service list and event-bus layers are described in the project `CLAUDE.md`.

---

## Request architecture

The system has two entry paths into a plugin's logic — both end in the same place (a videoreg-api method):

**HTTP request flow** (web UI):
```
HTTP request
    ↓
handle_*(request)         ← transport: parsing, auth, response
    ↓
api_client.exec(...)      ← videoreg-api method call
    ↓
MethodXxx.exec(args)      ← all business logic here
```

**User-command flow** (interfaces — bot, sms, …):
```
User input in interface (bot/sms/…)
    ↓
Interface plugin → api_client.exec("<plugin>.command", {command, interface, payload, args})
    ↓
InterfaceCommandMethod (in the target plugin)
    ↓
Command<Name>.exec(interface, payload, args)   ← business logic; replies via interface.send_*
```

**Rules:**
- HTTP handlers are a thin transport layer — no business logic.
- Commands are the user-facing counterpart of api-methods: same plugin ownership rules apply (logic lives where the state lives), but commands reply asynchronously through `interface.send_*` instead of returning data.
- Both paths converge on the same plugin — never duplicate logic between a method and a command; have the command call the method (or share a helper inside the plugin).

See the **Interfaces and commands** section below for details.

---

## Method-to-plugin assignment

The default plugin → logic mapping is in `CLAUDE.md` (camera, net, gps, bot, stat, power, sms, http, core, bus).

**Rule:** a method must live in the plugin that owns the state and dependencies it accesses.

To list existing methods of a plugin, read `plugins/<plugin>/plugin_builder.py` — all registered methods are there.

---

## API naming conventions

| Layer | Style | Example |
|-------|-------|---------|
| HTTP route | `kebab-case` | `GET /api/net/modem_info` |
| handler function | `handle_<verb>_<resource>` | `handle_modem_info` |
| videoreg-api method | `snake_case`, no prefix | `modem_info` |
| Call | `"<plugin>.<method>"` | `"net.modem_info"` |

Names must match semantically: `modem_info` → `/api/net/modem_info` → `net.modem_info`.

---

## videoreg-api data format

All methods return strictly one of two formats:

```python
# Success
{"status": "ok", "data": { ... }}

# Error
{"status": "error", "error": "error description"}
```

Working with responses in handlers:
```python
response = await api_client.exec("plugin.method", args)
if response.is_ok():
    data = response.get_data()   # → dict from the "data" field
else:
    err = response.get_error()   # → string from the "error" field
```

---

## Plugin pattern

Each plugin has:

```
plugins/<plugin>/
  plugin.py              — main <Name>Plugin class
  plugin_builder.py      — plugin assembly, method registration
  method/                — one file per method
    <method_name>.py     — class Method<MethodName>(ApiMethod)
```

Method is registered in `plugin_builder.py`:
```python
from plugins.<plugin>.method.<method_name> import Method<MethodName>

# in init_api_server(methods={...}):
"<method_key>": Method<MethodName>(plugin),
```

---

## HTTP layer structure

```
plugins/org_vrg_http/
├── plugin.py              — route registration in _start_server()
└── handlers/
    ├── <resource>_handlers.py          — system handlers (auth, media, static, dashboard)
    └── plugins/
        └── <plugin_id>/
            └── <resource>_handlers.py  — handlers for a specific plugin
```

- **System handlers** — do not use videoreg-api: `handlers/<resource>_handlers.py`
- **Plugin handlers** — interact with other plugins via videoreg-api: `handlers/plugins/<plugin_id>/<resource>_handlers.py`

Public paths: `/`, `/api/auth/*`, `/static/*`. All other `/api/*` paths are protected by middleware automatically.

---

## Interfaces and commands

In addition to videoreg-api, plugins can handle user commands from interfaces (bot, sms, etc.).

**Call flow:**
```
Interface (bot/sms) → api_client.exec("<plugin>.command", {command, interface, payload, args})
    ↓
InterfaceCommandMethod → command.exec(interface, payload, args)
    ↓
InterfaceCommand → interface.send_text/send_image/... (reply to user)
```

**Rules:**
- A command lives in the plugin whose logic it implements
- Commands are registered via `InterfaceCommandMethod` in `plugin_builder.py`
- Commands reply to the user asynchronously via `interface.send_*`, not via return value
- "Entry" commands (invoked directly by the user) are registered in the manifest; internal commands — only in `plugin_builder.py`

**Where to look:** `plugins/<plugin>/commands/`, `sdk/interface.py`, `videoreg.manifest.json`.

---

## Review checklist

When reviewing code, check:

1. **Is the handler thin?** — only body parsing, `api_client.exec` call, response formation
2. **Is the method in the right plugin?** — per the assignment table
3. **Does the response format match the convention?** — `{"status": "ok", "data": ...}` / `{"status": "error", "error": ...}`
4. **Are names consistent?** — HTTP ↔ handler ↔ api-method names match semantically
5. **No duplication?** — if a similar method already exists, prefer extending it
6. **Parallel calls?** — if a handler aggregates multiple plugins, uses `asyncio.gather`
7. **Command follows the pattern?** — inherits `InterfaceCommand`, replies via `interface.send_*`, lives in `commands/`

---

## Algorithm for planning a new feature

1. Determine what data the frontend needs and in what format
2. Determine which plugin owns that data → create the videoreg-api method there
3. Describe the HTTP endpoint: method, path, request/response schema
4. Split tasks: backend implements the method + handler, frontend implements the component

---

## Documenting new logic in CLAUDE.md

When new non-obvious logic is introduced — especially in `sdk/` — document it in `CLAUDE.md` in a brief format: class/function name, purpose, usage pattern. Omit obvious details; focus on what a developer needs to know before using it.
