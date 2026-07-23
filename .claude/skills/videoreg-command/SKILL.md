---
name: videoreg-command
description: videoreg gateway command conventions — Command<Name>(GatewayCommand) template, command-to-plugin assignment (same as api-methods — logic lives where state lives), registration via GatewayCommandMethod in plugin_builder.py, replying via gateway.send_text / send_image / send_video / send_document, capability check via gateway.support, entry vs internal commands declared in the plugin's manifest.yaml (with optional weigh/hidden), i18n for replies. Trigger when creating or modifying a user-facing command in plugins/<plugin>/commands/.
---

# videoreg gateway command conventions

Templates and rules for user-facing commands triggered through gateways (bot, sms, …). For higher-level architectural rules see `videoreg-architecture`. For plugin assembly see `videoreg-plugin`. For pure data api-methods see `videoreg-api`.

**Important:** Never read `plugins/org_vrg_http/static/vue.global.js` — it is huge.

---

## Command flow

```
User input in gateway (bot/sms/…)
    ↓
Gateway plugin → api_client.exec("<plugin>.command", {command, gateway, payload, args})
    ↓
GatewayCommandMethod (in the target plugin)
    ↓
Command<Name>.exec(gateway, payload, args)   ← business logic
    ↓
gateway.send_text / send_image / send_video / send_document   ← reply to the user
```

Unlike api-methods, commands **do not return data directly** — they reply asynchronously through `gateway.send_*`.

---

## Command-to-plugin assignment

A command lives in the **plugin whose state it operates on** — same rule as api-methods. Default mapping is in `CLAUDE.md`.

**Avoid duplicating logic between a method and a command.** If a command needs the same logic that an api-method already implements, have the command call the method (or share a helper inside the plugin) rather than re-implementing it.

---

## Command file structure

**File:** `plugins/<plugin_id>/commands/<command_name>.py`

```python
from sdk.gateway import Gateway, GatewayCommand, GatewayInteractions
from plugins.<plugin_id>.plugin import <Name>Plugin


class Command<Name>(GatewayCommand):
    _plugin: <Name>Plugin

    def __init__(self, plugin: <Name>Plugin):
        super().__init__()
        self._plugin = plugin

    async def exec(self, gateway: Gateway, payload, args):
        # ... logic via self._plugin ...
        await gateway.send_text(payload, "result text")
```

**Rules:**
- Access plugin dependencies only via `self._plugin`.
- Reply through `gateway.send_*` — no return value.
- Log errors via `self._plugin.logger.error(..., exc_info=True)`.

---

## Reply primitives

```python
await gateway.send_text(payload, "text")
await gateway.send_image(payload, path)
await gateway.send_video(payload, path, width, height)
await gateway.send_document(payload, path)
```

**Capability check** — not every gateway supports every interaction. Check before sending media:

```python
if gateway.support(GatewayInteractions.VIDEO.value):
    await gateway.send_video(payload, path, w, h)
else:
    await gateway.send_text(payload, self._plugin.runner.i18n.t("common.video_unsupported"))
```

The supported interaction types are declared in `videoreg.manifest.yaml` under `gateways[].interactions`.

---

## Registration in `plugin_builder.py`

`GatewayCommandMethod` is a special videoreg-api method (`<plugin>.command`) that dispatches to the right `GatewayCommand` based on the request payload.

```python
from sdk.gateway import Gateway, GatewayCommand, GatewayCommandMethod
from plugins.<plugin_id>.commands.<command_name> import Command<Name>

# inside build_plugin(...):
gateways = Gateway.parse_gateways(
    runner.videoreg.manifest.gateways, plugin.logger, plugin.api_client
)
commands: dict[str, GatewayCommand] = {
    "<command_key>": Command<Name>(plugin),
}

plugin.init_api_servier(methods={
    "command": GatewayCommandMethod(gateways, commands),
    # ... other api-methods ...
})
```

The full assembly skeleton is in the `videoreg-plugin` skill.

**Call from the gateway side:**
```python
await api_client.exec(
    "<plugin>.command",
    {"command": "<command_key>", "gateway": "bot", "payload": ..., "args": ...},
)
```

See `plugins/org_vrg_bot/commands/common.py` for an end-to-end example.

---

## Entry commands vs internal commands

- **Entry commands** are invoked directly by the user (e.g. typing `/photo` in the bot). They must be registered in the owning plugin's `plugins/<id>/manifest.yaml` under `commands:` so gateways (bot, sms) know about them. Gateways collect them via `read_plugin_commands` (`sdk/command_reader.py`):

  ```yaml
  commands:
    - name: photo            # invoked as /photo (plugin is implied by file location)
      title: Take photo      # used for hints / bot menus
      weigh: 100             # optional; higher weight sorts earlier in the bot menu (default 0)
      hidden: true           # optional; dispatchable but hidden from the bot menu
  ```

- **Internal commands** are triggered by other commands (e.g. an inline-keyboard callback) and only need to be registered in the plugin's `plugin_builder.py` `commands` dict — not in the manifest.

---

## i18n for replies

All user-facing strings use the i18n engine:

```python
text = self._plugin.runner.i18n.t("camera.start_recording")
text = self._plugin.runner.i18n.t("bot.command_error", status=404)
text = self._plugin.runner.i18n.p("camera.video_count", n)
```

For key format, plural rules, translation file layout and how to add new keys → `videoreg-i18n`.

---

## Task execution algorithm

1. **Determine the owning plugin** (state + dependencies → plugin).
2. **Create the command file** at `plugins/<plugin_id>/commands/<command_name>.py`, class `Command<Name>(GatewayCommand)`.
3. **Implement** `async def exec(self, gateway, payload, args)`; reply via `gateway.send_*`; check capability for media.
4. **Register** in `plugin_builder.py` in the `commands` dict (the `command` api-method via `GatewayCommandMethod` is registered once per plugin).
5. **Entry command?** Add to the owning plugin's `plugins/<id>/manifest.yaml` under `commands:` (optionally with `weigh` for menu ordering). Internal command? Skip the manifest.
6. **Editing existing code?** Read `plugin_builder.py` first to find the command, then the file in `commands/`.
