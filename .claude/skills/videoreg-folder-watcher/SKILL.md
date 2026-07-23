---
name: videoreg-folder-watcher
description: videoreg FolderWatcher conventions — abstract class in sdk/folder_watcher.py for monitoring a directory via inotify-simple, subclasses implement async on_file_created(filename), blocking inotify.read runs in run_in_executor with a 500ms timeout and a threading.Event for clean shutdown, lifecycle wiring (watcher.start() in plugin.start(), await watcher.stop() in plugin.stop()), implementation example in plugins/org_vrg_camera/h264_watcher.py. Trigger when creating a new folder watcher, modifying an existing one (e.g. h264_watcher.py / jpeg_watcher.py), or wiring a watcher into a plugin's lifecycle.
---

# videoreg FolderWatcher

`sdk/folder_watcher.py` defines an abstract class for reacting to **new files appearing in a directory**. Use this skill when you need to ingest files dropped into a folder by an external process (e.g. `rpicam-apps` writing H.264 / JPEG files).

For plugin lifecycle context (`start()` / `stop()`) see `videoreg-plugin`. For emitting business events on file creation see `videoreg-journal`.

---

## What `FolderWatcher` does

- Wraps `inotify-simple` to watch a single directory.
- Reacts to **fully-written** files (`CLOSE_WRITE | MOVED_TO`) — never to half-written ones.
- The blocking `inotify.read(timeout=500ms)` runs in `run_in_executor`, so the asyncio event loop stays responsive.
- A `threading.Event` lets the executor thread exit within ≤ 500 ms after `stop()` is called — clean async shutdown.
- Subclasses implement `async on_file_created(filename: str)`.

---

## Subclass template

```python
from pathlib import Path
import logging
from sdk.folder_watcher import FolderWatcher


class <Name>FolderWatcher(FolderWatcher):
    def __init__(self, watch_dir: Path, logger: logging.Logger, ...deps...):
        super().__init__(watch_dir, logger)
        # store deps the subclass needs

    async def on_file_created(self, filename: str):
        # react to a fully-written new file
        ...
```

**Reference implementation:** `plugins/org_vrg_camera/h264_watcher.py`:

```python
class H264FolderWatcher(FolderWatcher):
    async def on_file_created(self, filename: str):
        self._media_manager.append_file(MediaFileType.H264, filename)
        await self._journal_client.write(JournalRecord(
            type="video_h264_created", data={"filename": filename}
        ))
```

---

## Lifecycle wiring

A watcher must be **started in the plugin's `start()`** and **stopped in `stop()`** so it joins the plugin's lifetime. `start()` is non-async, `stop()` is async.

```python
class <Name>Plugin(Plugin):
    def __init__(self, id, name, runner):
        super().__init__(id, name, runner)
        self._watcher: <Name>FolderWatcher | None = None

    def init_watcher(self, watch_dir, ...deps...):
        self._watcher = <Name>FolderWatcher(watch_dir, self.logger, ...deps...)

    async def start(self):
        await super().start()
        if self._watcher:
            self._watcher.start()

    async def stop(self):
        if self._watcher:
            await self._watcher.stop()
        await super().stop()
```

`init_watcher` is typically called from `plugin_builder.py` after `init_journal_client()` (so the watcher can receive the journal client).

---

## Rules

- **One watcher per directory.** If you need to watch several directories, create several watcher instances.
- **`on_file_created` is fired in a fresh `asyncio.create_task`.** Don't assume it runs serially — guard shared state if needed.
- **Don't block in `on_file_created`.** Long work belongs in a background task; the watcher loop should return quickly to keep up with bursts of file events.
- **Stop in reverse order of start.** When the plugin owns multiple resources, stop the watcher before stopping the resources it depends on.

---

## Task execution algorithm

1. **New watcher?** Create `plugins/<plugin>/<name>_watcher.py`, subclass `FolderWatcher`, implement `on_file_created`.
2. **Wire dependencies** (media manager, journal client, …) through the constructor.
3. **Add `init_<name>_watcher` and start/stop calls** to the plugin's `plugin.py`; instantiate from `plugin_builder.py`.
4. **Editing an existing watcher?** Find it via `grep -rl "FolderWatcher" plugins/`. Read the current implementation before changing behaviour.
