# VideoReg — context for Claude

## What it is

A dashcam system on Raspberry Pi (Python 3, asyncio). Records video/photos from cameras, GPS tracking, HTTPS API, Telegram bot, network and power management.

## Language

All codebase artifacts must be written in English: markdown files, code comments, docstrings, variable names, commit messages.


## Architecture

Main components: `systemd services` and `plugins`.

**Systemd services** with the `vrg-*` prefix are the main processes that run plugins inside them.

**Plugins** implement specific logic: video recording, networking, power management, etc.

System components communicate via a Unix socket (event bus) implemented in the `org_vrg_bus` plugin.

Plugins have both a unique id (e.g. `org_vrg_bus`) and a shorter name (e.g. `bus`). The id is used for system-level separation (e.g. filesystem folders) and must be strictly unique. The name is suitable for API method prefix naming to avoid long identifiers.

Multiple plugins may run within a single systemd service.

**Entry points**:
- `run.py` — start a single service (service name from the manifest is passed)
- `run-cli.py` — CLI client for sending commands to services
- `videoreg.manifest.json` — list of services and their Python plugins

**Plugin pattern**: every plugin has a `plugin_builder.py` that assembles the plugin (an object inheriting from `Plugin`).

## Folder and file structure

```
.videoreg/    — Configuration and data (created after installation)
  config.json — main project config
  log/        - logs
    services/ - per-service logs
    plugins/  — per-plugin logs
  data/       - data
    plugins/  — internal plugin data
docs/         - documentation
plugins/      — plugins
sdk/          — base classes and utilities used by plugins
  socket/     — Unix-socket client/server for inter-service communication
  service.py  — ServiceRunner, Plugin — foundation for all services and plugins
  videoreg.py — Videoreg — access to config and paths
task/         — one-off tasks, bash scripts
  service/    — bash scripts where systemd vrg-services starts
  camera/     — bash scripts to perform video recording or taking photo with rpicam-apps
tools/        — tooling
  bin/        - developer tools intended to be run from the console, e.g. `vrg-log`
  install/    - files required for installation
```

Media (video, photos, GPS tracks) is stored in `/mnt/data/videoreg`.

### Default plugins and method-to-plugin assignment rules

| Service | Short name | Logic |
|---------|------------|-------|
| `org_vrg_core` | `core` | General purpose logic |
| `org_vrg_bus` | `bus` | Event bus (central event bus), Unix socket |
| `org_vrg_camera` | `camera` | Video, photos, OSD, RTSP |
| `org_vrg_net` | `net` | WiFi, WireGuard, modem, networking |
| `org_vrg_gps` | `gps` | GPS tracking, location |
| `org_vrg_bot` | `bot` | Telegram bot, receiving commands from user, sending text and media (photo, video, documents) |
| `org_vrg_stat` | `stat` | Statistics: CPU temp, disk, traffic |
| `org_vrg_power` | `power` | Power management, battery, PiSugar |
| `org_vrg_sms` | `sms` | SMS, receiving commands from user |
| `org_vrg_http` | `http` | HTTPS server (web-site, http-api) |

See each plugin's `README.md` for its documentation.

## Event bus (Unix socket)

The `org_vrg_bus` plugin implements a bus for inter-plugin communication. There are several "layers" of data exchange.

### Layer 1: channels
Arbitrary JSON data via "channels": a plugin subscribes to specific channels (by default a channel named after the plugin itself), and other plugins can "publish" data to arbitrary channels. This is implemented through the `Connection` base class defined in `sdk/socket/client.py`.

```python
# Initialize Connection in a plugin
plugin.init_socket(
  client_id=name,
  channels=["test"],
  socket_path=None
)

# Send data to a channel
await plugin.connection.send_data(to_channel="test", data={"foo":"bar"})

# Receive data from a channel
class CustomConnectionListener(DefaultConnectionListener):
  async def on_data(self, data, to):
    await super().on_data(data, to)
    if to == "test":
      print(data)
```

### Layer 2: API — request-response (also videoreg-api)
On top of channels, a request/response layer is implemented for conveniently sending requests and awaiting results. Plugins can declare themselves an `ApiServer` with `ApiMethod` methods. Other plugins can call these methods via `ApiClient` and receive an `ApiResponse`.

```python
# Initialize ApiClient in a plugin
plugin.init_api_client()

# Initialize ApiServer in a plugin
plugin.init_api_servier(methods={
  "get_info": MethodGetInfo(plugin)
})

# Example: send a request and await the response
response = await plugin.api_client.exec("camera.get_info", args=None)
print(response.get_data())
```

Plugin methods live in `methods/`.

### Layer 3: Interfaces and user commands
The system accounts for multiple interfaces (UI, entry points) through which users interact with the system. Examples of basic interfaces are the `bot` and `sms` plugins — users can execute "commands" through them.

Command description format in the manifest:

```yaml
interfaces:
  - name: bot
    interactions: # Available interaction types for plugins to respond to users via this interface
      text: bot.send_text
      image: bot.send_image

commands:
  - name: photo # User can invoke this command by typing `/photo`
    plugin: camera # plugin that will handle the command execution
    title: Take photo # Title that can be used for hints, e.g. in the bot menu
```

Plugins may not register commands in the manifest. Only "entry" (primary) commands are registered in the manifest.

How an interface interacts with the plugin that handles a command:
- The interface must invoke commands on the plugin via the videoreg-api method `<plugin>.command`, passing user arguments and `payload` (e.g. the chat id where the message was received). See example at `plugins/org_vrg_bot/commands/common.py`.
- The plugin handles commands using the `InterfaceCommandMethod` method.
- The plugin responds to the user via videoreg-api calls to the interface. Available interaction types are described in the interface manifest. See the short video recording command example at `plugins/org_vrg_camera/commands/video.py`.

Plugin commands live in `commands/`.

## Event journal, FolderWatcher, i18n

Business event journal (`sdk/journal.py`), folder-watching abstraction (`sdk/folder_watcher.py`) and the i18n engine (`sdk/i18n.py`) each have their own skill — see `videoreg-journal`, `videoreg-folder-watcher`, `videoreg-i18n` below for the conventions, templates and wiring rules.

## Skills

The project conventions live in skills under `.claude/skills/`. They auto-load by trigger and let you apply project rules to small edits without spawning a sub-agent:

- `videoreg-architecture` — high-level rules: three-layer request flow, method/command-to-plugin assignment, cross-layer naming, response format convention, planning algorithm, review checklist. Delegates implementation details to the four skills below
- `videoreg-plugin` — plugin folder layout, `plugin_builder.py` assembly order, lifecycle, manifest registration
- `videoreg-api` — `Method<Name>(ApiMethod)` template, response format `{status, data/error}`, registration, calling via `api_client.exec`
- `videoreg-http-backend` — HTTP handler templates (system vs plugin), naming, parsing api responses, parallel aggregation, route registration
- `videoreg-command` — `Command<Name>(InterfaceCommand)` template, registration via `InterfaceCommandMethod`, replying via `interface.send_*`, entry vs internal commands
- `videoreg-journal` — `JournalRecord` / `JournalClient` (`sdk/journal.py`), wiring `init_journal_client()`, business-event names and file format
- `videoreg-folder-watcher` — `FolderWatcher` subclass template (`sdk/folder_watcher.py`), `async on_file_created`, start/stop lifecycle wiring
- `videoreg-i18n` — `sdk/i18n.py` engine, translation file layout (`ru.yaml` / `en.yaml`), key format, CLDR plural forms, Python `t/p` and JS `$t/$p`, fallback chain
- `videoreg-frontend` — Vue 3 SPA navigation, page component template, settings sub-page registration, Icon component, JS i18n
- `videoreg-design-system` — `style.css` rules, allowed/forbidden modifications, responsiveness, keeping `docs/CSS.md` in sync

Skills are the source of truth for conventions. Sub-agents (below) reference the same skills — use sub-agents for large or parallel tasks where an isolated context window helps.

## Agents

For non-trivial tasks, delegate work to specialized agents via the Task tool.

### videoreg-agent-architector

Engage **before starting implementation** when a task spans multiple layers or there are non-obvious architectural questions:

- A new feature that needs to be broken down into backend + frontend tasks
- Determining which plugin a new api-method should live in
- Review: whether a handler, method, or module is structured correctly
- Non-obvious distribution of logic between plugins

### videoreg-agent-backender

Engage for backend implementation:

- New HTTP endpoint (`plugins/org_vrg_http/handlers/`, `plugins/org_vrg_http/service.py`)
- New or modified videoreg-api method (`src/<service>/method/`)
- Bug in a handler or api-method

### videoreg-agent-frontender

Engage for UI work:

- New page or Vue component (`plugins/org_vrg_http/static/js/components/`)
- Modifying an existing component
- UI bug

### Typical scenarios

| Task | Agent(s) |
|------|----------|
| Full new feature (UI + API) | architector → backender + frontender |
| API endpoint only | backender (non-trivial — architector first) |
| UI component only, no new API | frontender |
| Where should logic live? | architector |
| Code review | architector |
