import json
from pathlib import Path
from typing import Any


class State:
  """Persistent JSON key-value store backed by a file."""

  _file_path: Path
  _state: dict[str, Any]

  def __init__(self, file_path: Path):
    self._file_path = file_path

    mode = "r" if file_path.exists() else "w+"
    with open(file_path, mode) as f:
      try:
        self._state = json.load(f)
      except:
        self._state = {}

  def set_defaults(self, defaults: dict[str, Any]):
    for key, value in defaults.items():
      if key not in self._state:
        self._state[key] = value

  def reload(self):
    if self._file_path.exists():
      with open(self._file_path) as f:
        try:
          self._state = json.load(f)
        except:
          self._state = {}

  def get(self, key: str, default: Any = None):
    return self._state.get(key, default)

  def save(self, patch: dict[str, Any]):
    self._state = {**self._state, **patch}
    with open(self._file_path, "w") as f:
      json.dump(self._state, f, indent=2)
