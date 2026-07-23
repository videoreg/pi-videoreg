"""The merged manifest: a single generated view of every manifest, in `.videoreg/`.

Manifest data is split across the repo — one central `videoreg.manifest.yaml`
(services / plugins / gateways / locale / paths) plus a per-plugin
`plugins/<id>/manifest.yaml` carrying that plugin's `http` / `commands` / `bot` /
`power` sections. Rather than have every consumer independently glob
`plugins/*/manifest.yaml` and re-parse the central file, `org_vrg_core` builds a
single merged document under `.videoreg/` at startup and all other consumers read
from it.

The merged document keeps the central manifest's shape and folds each plugin's
per-plugin sections into its entry in the `plugins` list (matched by `id`):

    {
      "path": {...}, "services": [...], "gateways": [...], "locale": "en",
      "plugins": [
        {"id": "org_vrg_power", "name": "power", "enabled": true,
         "http": {...}, "commands": [...], "bot": {...}, "power": {...}},
        ...
      ]
    }

The file is created once when missing (see `ensure_merged_manifest`) and then
edited in place — the runtime `enabled` toggle writes here, never to the repo, so
`videoreg.manifest.yaml` stays pristine. It is *not* regenerated on every boot; to
adopt repo manifest changes after an update, delete the file and let core recreate
it (a rebuild resets `enabled` to repo defaults).

Written as JSON (a generated artifact under the already-gitignored `.videoreg/`)
and atomically (temp sibling + `os.replace`) so cross-process readers never observe
a partial file.
"""

import copy
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
  from sdk.videoreg import Videoreg

# Per-plugin manifest sections folded into each plugin's merged entry.
SECTION_KEYS = ("http", "commands", "bot", "power")


def _merged_filename(env: str) -> str:
  """Env-specific merged-manifest filename, mirroring the manifest naming convention.

  `prod` -> `manifest.merged.json`; any other env -> `manifest.merged.<env>.json`
  (as `videoreg.manifest.yaml` vs `videoreg.manifest.<env>.yaml`). This keeps the
  merged views of different environments from clobbering each other when they share
  the same `.videoreg` directory (e.g. the dev container mounts the host's).
  """
  if env == "prod":
    return "manifest.merged.json"
  return f"manifest.merged.{env}.json"


def _merged_path(videoreg: "Videoreg") -> Path:
  return videoreg.private_path(_merged_filename(videoreg.env))


def build_merged_dict(videoreg: "Videoreg") -> dict:
  """Build the merged manifest dict from the central + per-plugin manifests.

  Starts from `videoreg.manifest` (already `extends`-resolved by `load_manifest`),
  then folds each `plugins/<id>/manifest.yaml`'s `http/commands/bot/power` sections
  into the matching plugin entry (id == plugin directory name). Plugins listed on
  disk but absent from the central `plugins` list are ignored.
  """
  manifest = videoreg.manifest
  plugins = copy.deepcopy(manifest.plugins)
  by_id = {p.get("id"): p for p in plugins}

  plugins_dir = videoreg.app_path("plugins")
  for manifest_path in sorted(plugins_dir.glob("*/manifest.yaml")):
    plugin_id = manifest_path.parent.name
    entry = by_id.get(plugin_id)
    if entry is None:
      continue

    try:
      with open(manifest_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    except Exception:
      continue

    if not isinstance(data, dict):
      continue

    for key in SECTION_KEYS:
      value = data.get(key)
      if value is not None:
        entry[key] = value

  return {
    "path": copy.deepcopy(manifest.path),
    "services": copy.deepcopy(manifest.services),
    "plugins": plugins,
    "gateways": copy.deepcopy(manifest.gateways),
    "locale": manifest.locale,
  }


def write_merged(videoreg: "Videoreg", data: dict) -> Path:
  """Atomically write the merged manifest to `.videoreg/manifest.merged[.<env>].json`."""
  path = _merged_path(videoreg)
  path.parent.mkdir(parents=True, exist_ok=True)
  tmp = path.with_name(path.name + ".tmp")
  with open(tmp, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
  os.replace(tmp, path)
  return path


def ensure_merged_manifest(videoreg: "Videoreg") -> Path:
  """Create the merged manifest if it does not exist yet; return its path.

  Create-if-missing: an existing file is left untouched (it may carry `enabled`
  overrides). Called once from `org_vrg_core`'s build phase so the file is present
  before any other plugin/service reads it.
  """
  path = _merged_path(videoreg)
  if path.exists():
    return path
  return write_merged(videoreg, build_merged_dict(videoreg))


def read_merged(videoreg: "Videoreg") -> dict:
  """Return the merged manifest dict, building it in-memory if the file is absent."""
  path = _merged_path(videoreg)
  try:
    with open(path, encoding="utf-8") as f:
      data = json.load(f)
    if isinstance(data, dict):
      return data
  except FileNotFoundError:
    pass
  except Exception:
    pass
  return build_merged_dict(videoreg)


def set_plugin_enabled(videoreg: "Videoreg", plugin_id: str, enabled: bool) -> bool:
  """Set a plugin's `enabled` flag in the merged manifest in place.

  Returns False if the plugin id is not present. The repo manifest is never touched.
  """
  data = read_merged(videoreg)

  found = False
  for plugin in data.get("plugins", []):
    if plugin.get("id") == plugin_id:
      plugin["enabled"] = bool(enabled)
      found = True
      break

  if not found:
    return False

  write_merged(videoreg, data)
  return True
