from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class Manifest:
  """Parsed content of videoreg.manifest.yaml.

  Each service is a dict with `name: str` and `plugins: list[str]` (plugin ids).
  Each plugin is a dict keyed by `id`; the service is determined by the services list.
  """

  path: dict
  services: list[dict]
  plugins: list[dict]
  gateways: list[dict]
  locale: str = "ru"


def load_manifest(project_home: Path, env: str = "prod") -> Manifest:
  """Load the manifest for the given environment from the project home.

  For `prod` the file is `videoreg.manifest.yaml`; otherwise it is
  `videoreg.manifest.<env>.yaml`. `extends` references are resolved and merged.
  """
  if env == "prod":
    manifest_file_name = "videoreg.manifest.yaml"
  else:
    manifest_file_name = f"videoreg.manifest.{env}.yaml"

  manifest_dict = _load_manifest_dict(project_home / manifest_file_name)
  return Manifest(**manifest_dict)


def _load_manifest_dict(manifest_path: Path) -> dict:
  """Load a manifest yaml, resolving `extends` recursively and merging.

  Merge rules (child overrides parent):
  - `plugins`: merged by `id` (shallow per-field override; new ids appended).
  - `services`: merged by `name` (child entry replaces parent entry; new names appended).
    A plugin id can appear in at most one service — if a child-defined service
    references a plugin, it is removed from any parent-inherited service.
  - `gateways`: merged by `name` (child entry replaces parent entry; new names appended).
  - `path`, `locale`: child replaces parent entirely.
  """
  with open(manifest_path) as f:
    data = yaml.safe_load(f) or {}

  parent_ref = data.pop("extends", None)
  if parent_ref is None:
    return data

  parent_path = (manifest_path.parent / parent_ref).resolve()
  parent = _load_manifest_dict(parent_path)

  merged = dict(parent)

  if "locale" in data:
    merged["locale"] = data["locale"]
  if "path" in data:
    merged["path"] = data["path"]

  merged["plugins"] = _merge_by_key(parent.get("plugins", []), data.get("plugins", []), "id")
  merged["services"] = _merge_services(parent.get("services", []), data.get("services", []))
  merged["gateways"] = _merge_by_key(
    parent.get("gateways", []), data.get("gateways", []), "name", replace=True
  )

  return merged


def _merge_services(parent: list[dict], child: list[dict]) -> list[dict]:
  """Merge service lists with child-priority deduplication of plugin ids.

  - Service entries are merged by `name`; a child entry replaces the parent entry whole.
  - A plugin id may appear in at most one service. Plugins listed in any
    child-defined service (overridden or new) are removed from parent-inherited services.
  """
  child_names = {entry.get("name") for entry in child}
  child_plugin_ids: set[str] = set()
  for entry in child:
    for pid in entry.get("plugins", []) or []:
      child_plugin_ids.add(pid)

  result: list[dict] = []
  index: dict[str, int] = {}

  for entry in parent:
    name = entry.get("name")
    if name in child_names:
      result.append(dict(entry))
    else:
      filtered = dict(entry)
      filtered["plugins"] = [
        pid for pid in (entry.get("plugins", []) or []) if pid not in child_plugin_ids
      ]
      result.append(filtered)
    index[name] = len(result) - 1

  for entry in child:
    name = entry.get("name")
    if name in index:
      result[index[name]] = dict(entry)
    else:
      index[name] = len(result)
      result.append(dict(entry))

  return result


def _merge_by_key(parent: list[dict], child: list[dict], key: str, replace: bool = False) -> list[dict]:
  """Merge two lists of dicts using `key` as identity.

  When `replace=True`, a matching child entry replaces the parent entry as-is.
  When `replace=False`, child fields are merged on top of parent fields (shallow).
  New entries are appended in the order they appear in child.
  """
  result: list[dict] = []
  index: dict[str, int] = {}
  for entry in parent:
    k = entry.get(key)
    index[k] = len(result)
    result.append(dict(entry))

  for entry in child:
    k = entry.get(key)
    if k in index:
      if replace:
        result[index[k]] = dict(entry)
      else:
        result[index[k]] = {**result[index[k]], **entry}
    else:
      index[k] = len(result)
      result.append(dict(entry))

  return result


class Videoreg:
  """Provides filesystem path helpers for the project home and private (.videoreg) data directory."""

  home: Path
  manifest: Manifest

  def __init__(self, home: Path, manifest: Manifest):
    self.home = home
    self.manifest = manifest
    (home / ".videoreg").mkdir(parents=True, exist_ok=True)

  def app_path(self, internal_relative_path: str = None) -> Path:
    if not internal_relative_path:
      return self.home
    return (self.home / internal_relative_path).resolve()

  def private_path(self, internal_relative_path: str) -> Path:
    return (self.home / ".videoreg" / internal_relative_path).resolve()

  def plugin_private_path(self, plugin_name: str, internal_relative_path: str) -> Path:
    return (
      self.home / ".videoreg" / "data" / "plugins" / plugin_name / internal_relative_path
    ).resolve()

  def jpeg_path(self, internal_relative_path: str = None) -> Path:
    config_value = self.manifest.path.get("jpeg", None)
    if config_value:
      path = Path(config_value)
    else:
      path = self.private_path("jpeg")
    path.mkdir(parents=True, exist_ok=True)
    if internal_relative_path:
      path = path / internal_relative_path
    return path.resolve()

  def h264_path(self, internal_relative_path: str = None) -> Path:
    config_value = self.manifest.path.get("h264", None)
    if config_value:
      path = Path(config_value)
    else:
      path = self.private_path("h264")
    path.mkdir(parents=True, exist_ok=True)
    if internal_relative_path:
      path = path / internal_relative_path
    return path.resolve()

  def mp4_path(self, internal_relative_path: str = None) -> Path:
    config_value = self.manifest.path.get("mp4", None)
    if config_value:
      path = Path(config_value)
    else:
      path = self.private_path("mp4")
    path.mkdir(parents=True, exist_ok=True)
    if internal_relative_path:
      path = path / internal_relative_path
    return path.resolve()

  def sms_path(self, internal_relative_path: str = None) -> Path:
    config_value = self.manifest.path.get("sms", None)
    if config_value:
      path = Path(config_value)
    else:
      path = self.private_path("sms")
    path.mkdir(parents=True, exist_ok=True)
    if internal_relative_path:
      path = path / internal_relative_path
    return path.resolve()

  def gps_path(self, internal_relative_path: str = None) -> Path:
    config_value = self.manifest.path.get("gps", None)
    if config_value:
      path = Path(config_value)
    else:
      path = self.private_path("gps")
    path.mkdir(parents=True, exist_ok=True)
    if internal_relative_path:
      path = path / internal_relative_path
    return path.resolve()

  def jpeg_fave_path(self, internal_relative_path: str = None) -> Path:
    config_value = self.manifest.path.get("jpeg_fave", None)
    if config_value:
      path = Path(config_value)
    else:
      path = self.private_path("jpeg_fave")
    path.mkdir(parents=True, exist_ok=True)
    if internal_relative_path:
      path = path / internal_relative_path
    return path.resolve()

  def h264_fave_path(self, internal_relative_path: str = None) -> Path:
    config_value = self.manifest.path.get("h264_fave", None)
    if config_value:
      path = Path(config_value)
    else:
      path = self.private_path("h264_fave")
    path.mkdir(parents=True, exist_ok=True)
    if internal_relative_path:
      path = path / internal_relative_path
    return path.resolve()
