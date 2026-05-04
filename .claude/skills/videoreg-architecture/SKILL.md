---
name: videoreg-architecture
description: videoreg high-level architecture — three-layer request flow (HTTP path and command path), planning algorithm for a new feature, review checklist, principle that logic lives in the plugin owning the state, names must match across layers, response format convention {status, data/error}. Trigger when planning a feature, deciding where a method or command should live, reviewing a handler/method/module, or any cross-cutting architectural question. Implementation templates live in videoreg-plugin / videoreg-api / videoreg-http-backend / videoreg-command.
---

# videoreg architecture conventions

The source of truth for how the videoreg codebase is organised at a high level. Apply when planning a feature, deciding where a method or command belongs, or reviewing a handler/method/module.

For implementation templates and step-by-step rules, defer to the specialized skills:

- **`videoreg-plugin`** — plugin folder layout, `plugin_builder.py` assembly, lifecycle, manifest registration
- **`videoreg-api`** — `Method<Name>(ApiMethod)` template, response format, method registration
- **`videoreg-http-backend`** — HTTP handler template, route registration, system vs plugin handlers, naming
- **`videoreg-command`** — `Command<Name>(InterfaceCommand)` template, registration via `InterfaceCommandMethod`, manifest entries

System overview, plugin/service list and event-bus layers are described in the project `CLAUDE.md`.

**Important:** Never read `plugins/org_vrg_http/static/vue.global.js` — it is huge.

---

## Request architecture

The system has two entry paths into a plugin's logic — both end in the same place (a videoreg-api method or an interface command).

**HTTP request flow** (web UI):
```
HTTP request
    ↓
handle_*(request)         ← transport: parsing, auth, response   → videoreg-http-backend
    ↓
api_client.exec(...)      ← videoreg-api method call
    ↓
MethodXxx.exec(args)      ← business logic                       → videoreg-api
```

**User-command flow** (interfaces — bot, sms, …):
```
User input in interface (bot/sms/…)
    ↓
Interface plugin → api_client.exec("<plugin>.command", {command, interface, payload, args})
    ↓
InterfaceCommandMethod (in the target plugin)
    ↓
Command<Name>.exec(interface, payload, args)   ← business logic   → videoreg-command
                                                   reply via interface.send_*
```

**Cross-cutting rules:**
- HTTP handlers are a thin transport layer — no business logic.
- Both paths converge on the same plugin: **never duplicate logic between an api-method and a command**. Have the command call the method, or share a helper inside the plugin.

---

## Method- and command-to-plugin assignment

The default plugin → logic mapping is in `CLAUDE.md` (camera, net, gps, bot, stat, power, sms, http, core, bus).

**Rule (applies to both api-methods and commands):** logic must live in the plugin that owns the state and dependencies it accesses.

To list existing methods or commands of a plugin, read `plugins/<plugin>/plugin_builder.py` — they're all registered there.

---

## Cross-layer naming

Names must match semantically across layers:

```
GET /api/net/modem_info   ↔   handle_get_modem_info   ↔   net.modem_info
```

Per-layer style rules (kebab/snake casing, function naming) live in `videoreg-http-backend` (HTTP route + handler) and `videoreg-api` (method key).

---

## videoreg-api response format

All methods return strictly one of two shapes:

```python
{"status": "ok", "data": { ... }}
{"status": "error", "error": "error description"}
```

Producer details (templates, error logging) → `videoreg-api`.
Consumer details (`is_ok` / `get_data` / `get_error`, mapping to HTTP status) → `videoreg-http-backend`.

---

## Plugin pattern (high level)

Each plugin is a folder under `plugins/<plugin_id>/` with a `plugin.py` (state and lifecycle) and a `plugin_builder.py` (assembly: socket, api-client, api-server, journal, methods, commands).

Detailed structure, helper init order and lifecycle rules → `videoreg-plugin`.

---

## HTTP layer (high level)

Two flavours of handler live under `plugins/org_vrg_http/handlers/`:

- **System handlers** (auth, media, static, dashboard) — no api-client calls.
- **Plugin handlers** under `handlers/plugins/<plugin_id>/` — call other plugins via api-client.

Public paths: `/`, `/api/auth/*`, `/static/*`. All other `/api/*` paths are protected by middleware automatically.

Templates, registration, parallel aggregation, error mapping → `videoreg-http-backend`.

---

## Interfaces and commands (high level)

In addition to videoreg-api, plugins can handle user commands from interfaces (bot, sms, …). A command lives in the plugin whose state it operates on; "entry" commands (typed by the user, e.g. `/photo`) are also registered in `videoreg.manifest.yaml`, internal commands are not.

Templates, reply primitives (`interface.send_*`), capability check → `videoreg-command`.

---

## Review checklist

When reviewing code, check:

1. **Is the handler thin?** — only body parsing, `api_client.exec` call, response formation. (See `videoreg-http-backend`.)
2. **Is the method or command in the right plugin?** — per the assignment table in `CLAUDE.md`.
3. **Does the response format match the convention?** — `{"status": "ok", "data": ...}` / `{"status": "error", "error": ...}`. (See `videoreg-api`.)
4. **Are names consistent across layers?** — HTTP ↔ handler ↔ api-method names match semantically.
5. **No duplication?** — if a similar method exists, prefer extending it; if a command and a method need the same logic, the command calls the method (or a shared helper).
6. **Parallel calls?** — if a handler aggregates multiple plugins, uses `asyncio.gather(..., return_exceptions=True)`. (See `videoreg-http-backend`.)
7. **Command follows the pattern?** — inherits `InterfaceCommand`, replies via `interface.send_*`, lives in `commands/`. (See `videoreg-command`.)

---

## Algorithm for planning a new feature

1. Determine what data the frontend (or user) needs and in what format.
2. Determine which plugin owns that data → create the videoreg-api method there (`videoreg-api`).
3. Describe the HTTP endpoint (or command): method/path/schema for HTTP (`videoreg-http-backend`); command name and entry registration for interfaces (`videoreg-command`).
4. Split tasks: backend implements the method + handler/command, frontend implements the component.

---

## Documenting new logic in CLAUDE.md

When new non-obvious logic is introduced — especially in `sdk/` — document it in `CLAUDE.md` in a brief format: class/function name, purpose, usage pattern. Omit obvious details; focus on what a developer needs to know before using it.
