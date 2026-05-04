---
name: videoreg-plugin
description: videoreg plugin conventions — plugin id vs short name, plugin folder layout (plugin.py, plugin_builder.py, methods/, commands/, translations/), assembly order in plugin_builder.py (init_logger / init_socket / init_journal_client / init_api_client / init_api_servier), plugin lifecycle (start/stop), service-to-plugin mapping in videoreg.manifest.yaml. Trigger when creating a new plugin, modifying plugin.py or plugin_builder.py skeleton, or registering a plugin in the manifest. Excludes api-method and command bodies — see videoreg-api and videoreg-command.
---

# videoreg plugin conventions

Templates and rules for plugin-level work: plugin file structure, assembly in `plugin_builder.py`, lifecycle, service/manifest registration. Bodies of api-methods and interface commands are covered by the dedicated `videoreg-api` and `videoreg-command` skills.

For higher-level architectural rules (where a plugin's logic should live, request flow, naming) see the `videoreg-architecture` skill.

**Important:** Never read `plugins/org_vrg_http/static/vue.global.js` — it is huge.

---

## Plugin id and short name

Each plugin has two identifiers (declared in `videoreg.manifest.yaml`):

- **id** — e.g. `org_vrg_camera`. Used for system-level separation: log folder, data folder, Python package path. Must be globally unique.
- **name** (short name) — e.g. `camera`. Used as the api-method prefix (`camera.get_info`) and the default socket channel name. Keeps identifiers short.

Both are passed to the plugin constructor in `plugin_builder.py`:

```python
id = plugin_manifest.get("id")
name = plugin_manifest.get("name")
plugin = <Name>Plugin(id, name, runner)
```

Default plugin → logic mapping is in `CLAUDE.md` (camera, net, gps, bot, stat, power, sms, http, core, bus).

---

## Folder layout

```
plugins/<plugin_id>/
  plugin.py              — main <Name>Plugin class (state, lifecycle, helpers)
  plugin_builder.py      — async build_plugin(runner, args, plugin_manifest) — assembly + registration
  methods/               — one file per videoreg-api method   → see videoreg-api skill
  commands/              — one file per interface command     → see videoreg-command skill
  translations/          — ru.yaml / en.yaml (plugin-scoped i18n strings)
  README.md              — plugin-specific docs
```

Anything else (e.g. `prod/`, `dev/`, helper modules) is plugin-specific.

---

## `plugin.py` — the plugin class

```python
from sdk.service import Plugin, ServiceRunner


class <Name>Plugin(Plugin):
    def __init__(self, id: str, name: str, runner: ServiceRunner):
        super().__init__(id, name, runner)
        # plugin-specific state: managers, watchers, queues, …

    async def start(self):
        await super().start()
        # start long-running resources: FolderWatcher.start(), background tasks, …

    async def stop(self):
        # stop in reverse order of start
        await super().stop()
```

**Rules:**
- The plugin owns state and dependencies — methods and commands access them via `self._plugin`.
- `self.logger` is available after `init_logger` runs in `plugin_builder.py`.
- `self.runner.i18n` gives access to the i18n engine (`t` / `p`) — see `videoreg-i18n` for the engine, and `videoreg-api` / `videoreg-command` for usage in methods and commands.
- Long-running resources (watchers, tasks) start in `start()` and stop in `stop()`.

---

## `plugin_builder.py` — assembly

Every plugin exposes `async def build_plugin(runner, args, plugin_manifest) -> <Name>Plugin`. The runner imports and calls it.

Standard assembly order:

```python
from argparse import Namespace
from sdk.service import ServiceRunner
from sdk.interface import Interface, InterfaceCommand, InterfaceCommandMethod
from plugins.<plugin_id>.plugin import <Name>Plugin
# import methods and commands here — see videoreg-api / videoreg-command


async def build_plugin(
    runner: ServiceRunner, args: Namespace, plugin_manifest: dict
) -> <Name>Plugin:
    id = plugin_manifest.get("id")
    name = plugin_manifest.get("name")

    plugin = <Name>Plugin(id, name, runner)

    # 1. Logger — must be first so subsequent helpers can log.
    plugin.init_logger(args.log_level)

    # 2. Socket / event bus connection (channels the plugin listens on).
    plugin.init_socket(
        client_id=name,
        channels=[name],          # by default, listen on the channel named after the plugin
        socket_path=None,
    )

    # 3. Optional: journal client for business events.
    plugin.init_journal_client()

    # 4. Optional: api-client to call other plugins' methods.
    plugin.init_api_client()

    # 5. Optional: api-server with this plugin's methods + interface commands.
    interfaces = Interface.parse_interfaces(
        runner.videoreg.manifest.interfaces, plugin.logger, plugin.api_client
    )
    commands: dict[str, InterfaceCommand] = {
        # "<command_key>": Command<Name>(plugin),   ← see videoreg-command skill
    }

    plugin.init_api_servier(methods={
        "command": InterfaceCommandMethod(interfaces, commands),  # only if the plugin handles commands
        # "<method_key>": Method<Name>(plugin),                    ← see videoreg-api skill
    })

    return plugin
```

**Rules:**
- Order matters: `init_logger` before anything that may log; `init_api_client` before `init_api_servier` if any method needs to call other plugins.
- Skip helpers the plugin doesn't need (e.g. an internal-only plugin may have no api-server, no commands, no journal).
- Heavy or env-dependent dependencies (e.g. `prod/` vs `dev/` implementations) are constructed inside `build_plugin` based on `args.env` and injected into the plugin via dedicated setters (e.g. `plugin.init_camera_controls(...)`).

**Custom socket listener.** If the plugin needs to react to data on its channels, pass a `connection_listener_factory` to `init_socket`:

```python
from sdk.service import PluginConnectionListener, ConnectionListenerFactory

class <Name>ConnectionListener(PluginConnectionListener):
    plugin: <Name>Plugin
    async def on_data(self, data, to, from_=None):
        await super().on_data(data, to, from_)
        # handle data for specific channels

class <Name>ConnectionListenerFactory(ConnectionListenerFactory):
    def create(self, plugin):
        return <Name>ConnectionListener(plugin)

# in build_plugin:
plugin.init_socket(
    client_id=name,
    channels=[name, "extra_channel"],
    socket_path=None,
    connection_listener_factory=<Name>ConnectionListenerFactory(),
)
```

---

## Manifest registration

Plugins are declared in `videoreg.manifest.yaml` (and `videoreg.manifest.dev.yaml`) under the relevant service. Multiple plugins may run inside one service.

```yaml
services:
  - name: vrg-camera
    plugins:
      - id: org_vrg_camera
        name: camera
```

**Rules:**
- The service name (e.g. `vrg-camera`) is the systemd unit and matches `task/service/`.
- A plugin's `id` and `name` here are the values that arrive in `plugin_manifest` inside `build_plugin`.
- Default service ↔ plugin mapping is in `CLAUDE.md` §"Default plugins and method-to-plugin assignment rules".

---

## Lifecycle resources (FolderWatcher, background tasks)

Long-running resources must be started in `start()` and stopped in `stop()`:

```python
async def start(self):
    await super().start()
    self._h264_watcher.start()

async def stop(self):
    await self._h264_watcher.stop()
    await super().stop()
```

For folder-watching subclasses (template, inotify rules, lifecycle wiring) → `videoreg-folder-watcher`.
For business events emitted from the plugin (`init_journal_client()`, `JournalRecord`, event names) → `videoreg-journal`.

---

## Where api-methods and commands live

This skill stops at plugin assembly. For:

- the contents of `methods/` and how api-methods are written/registered → **`videoreg-api` skill**
- the contents of `commands/`, `InterfaceCommandMethod`, replying via `interface.send_*` → **`videoreg-command` skill**
- HTTP handlers (these live in `org_vrg_http`, not in the plugin) → **`videoreg-http-backend` skill**

---

## Task execution algorithm

1. **New plugin?** → create `plugins/<id>/{plugin.py, plugin_builder.py}`, declare it in `videoreg.manifest.yaml` under the right service, add a `README.md`.
2. **Adding a helper / lifecycle resource?** → add to `plugin.py`; wire start/stop in `start()` / `stop()`.
3. **Adding a method or command?** → defer to the dedicated skill; only the registration line touches `plugin_builder.py`.
4. **Editing existing assembly?** → read `plugin_builder.py` first; preserve the helper init order.
