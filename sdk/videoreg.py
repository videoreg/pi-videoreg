from dataclasses import dataclass
from pathlib import Path


@dataclass
class Manifest:
  """Parsed content of videoreg.manifest.yaml."""

  path: dict
  services: list[str]
  plugins: list[dict]
  interfaces: list[dict]
  locale: str = "ru"


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
