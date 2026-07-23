---
name: videoreg-journal
description: videoreg event journal conventions — business-event log separate from technical logging, file format (.videoreg/data/plugins/org_vrg_core/journal/YYYY-MM-DD.txt), JournalRecord/JournalClient/JournalServer in sdk/journal.py, initialization via plugin.init_journal_client() in plugin_builder.py, sending events with self.journal_client.write(JournalRecord(...)), unique event names across plugins. Trigger when adding or modifying business events (start/stop, recording lifecycle, charging events, …), wiring journal_client into a plugin, or working with sdk/journal.py.
---

# videoreg event journal

A mechanism for writing **business events** to a file, intentionally separate from technical logging (`logger.info / .error / …`). Use this skill when emitting domain events ("recording started", "charging on", "video file created") that belong in the day's journal — not for debug or error logs.

For plugin lifecycle and the `plugin_builder.py` skeleton see `videoreg-plugin`.

---

## Files

```
.videoreg/data/plugins/org_vrg_core/journal/YYYY-MM-DD.txt
```

A new file is created each day. Lines have the format:

```
<ISO-date>,<plugin_id>,<event_type>,<JSON-data>
```

---

## Classes (`sdk/journal.py`)

- `JournalRecord(type, data)` — record model. `type` is the event name, `data` is a free-form dict.
- `JournalClient` — sends a record to the `"journal"` bus channel. Initialized via `plugin.init_journal_client()` in `plugin_builder.py`.
- `JournalServer` — receives records from the bus and writes them to file. Lives in the `org_vrg_core` plugin; nothing to do here from a regular plugin.

---

## Wiring into a plugin

1. **In `plugin_builder.py`** — initialize the client (place after `init_socket`, before `init_api_servier`):

   ```python
   plugin.init_journal_client()
   ```

   The full assembly skeleton is in the `videoreg-plugin` skill.

2. **In `plugin.py` (or any code with access to the plugin)** — emit a record. Use `asyncio.create_task` to fire-and-forget so the caller doesn't await the bus round-trip:

   ```python
   from sdk.journal import JournalRecord

   asyncio.create_task(self.journal_client.write(
       JournalRecord(type="my_event", data={"key": "value"})
   ))
   ```

3. **From a `FolderWatcher`** — `journal_client` is typically passed in via constructor:

   ```python
   class H264FolderWatcher(FolderWatcher):
       async def on_file_created(self, filename: str):
           self._media_manager.append_file(MediaFileType.H264, filename)
           await self._journal_client.write(JournalRecord(
               type="video_h264_created", data={"filename": filename}
           ))
   ```

---

## Event names

**Event names are unique across all plugins** — the journal is a single global timeline. Pick names that won't collide.

Existing conventions (examples): `start`, `stop`, `video_start`, `video_stop`, `video_pause`, `charging_on`, `charging_off`, `video_h264_created`. New names should be `snake_case`, descriptive, and verb-oriented (state change, not state itself).

---

## When to journal vs when to log

- **Journal** — business-meaningful event that operators / future analysis would care about: lifecycle transitions, file creation, charging changes, recording starts.
- **Logger** — technical detail: errors with stack traces, debug output, warnings about transient issues. Use `self.logger.info / warning / error(..., exc_info=True)`.

Don't journal errors — log them. Don't log routine events that already produce a journal record.

---

## Task execution algorithm

1. **New event?** Pick a unique `snake_case` name, agree it doesn't collide with existing events (grep `JournalRecord(type=` across `plugins/`).
2. **Plugin doesn't have a journal client yet?** Add `plugin.init_journal_client()` to `plugin_builder.py` (see `videoreg-plugin`).
3. **Emit** via `asyncio.create_task(self.journal_client.write(JournalRecord(type=..., data=...)))`.
4. **Don't await** the write in performance-sensitive paths unless the ordering matters.
