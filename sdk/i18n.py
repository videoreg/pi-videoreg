import re
from pathlib import Path

import yaml


def _plural_form(n: int, locale: str) -> str:
  if locale == "ru":
    if n % 10 == 1 and n % 100 != 11:
      return "one"
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
      return "few"
    return "many"
  return "one" if n == 1 else "other"


def _interpolate(template: str, vars: dict) -> str:
  return re.sub(r"\{\{(\w+)\}\}", lambda m: str(vars.get(m.group(1), m.group(0))), template)


class I18n:
  """Loads YAML translation files and resolves keys with variable substitution and pluralization."""

  def __init__(self, locale: str = "ru"):
    self._locale = locale
    self._data: dict = {}
    self._fallback: dict = {}

  def load_global(self, sdk_path: Path):
    self._load_into(sdk_path / "translations" / f"{self._locale}.yaml", self._data)
    if self._locale != "en":
      self._load_into(sdk_path / "translations" / "en.yaml", self._fallback)

  def load_plugin(self, plugin_path: Path):
    self._load_into(plugin_path / "translations" / f"{self._locale}.yaml", self._data)
    if self._locale != "en":
      self._load_into(plugin_path / "translations" / "en.yaml", self._fallback)

  def _load_into(self, path: Path, target: dict):
    if path.exists():
      with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
      if data:
        target.update(data)

  def t(self, key: str, **kwargs) -> str:
    val = self._data.get(key) or self._fallback.get(key) or key
    if isinstance(val, dict):
      val = val.get("other") or key
    return _interpolate(str(val), kwargs)

  def p(self, key: str, n: int, **kwargs) -> str:
    val = self._data.get(key) or self._fallback.get(key)
    if not isinstance(val, dict):
      return _interpolate(str(val or key), {"n": n, **kwargs})
    form = _plural_form(n, self._locale)
    template = val.get(form) or val.get("other") or key
    return _interpolate(template, {"n": n, **kwargs})

  def all(self) -> dict:
    result = dict(self._fallback)
    result.update(self._data)
    return result

  @property
  def locale(self) -> str:
    return self._locale
