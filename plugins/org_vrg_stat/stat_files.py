"""Helpers for reading and parsing statistics data files.

Moved here from the http plugin's stat handlers: file reading and formatting is
business logic that belongs to the stat plugin, so the http layer can stay a
thin transport over the generic api handler.
"""

import os
from datetime import datetime as _dt


def list_stat_files(dir_path: str) -> list[str]:
  """Return sorted absolute paths of all files in `dir_path` (empty if missing)."""
  if not os.path.exists(dir_path):
    return []
  return sorted(
    os.path.join(dir_path, f)
    for f in os.listdir(dir_path)
    if os.path.isfile(os.path.join(dir_path, f))
  )


def parse_stat_file(file_path: str):
  """Read a scalar stat file and return (data, date).

  Line format: timestamp,datetime,value
  """
  date = os.path.splitext(os.path.basename(file_path))[0]
  data = []
  with open(file_path) as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      parts = line.split(",")
      if len(parts) >= 3:
        try:
          data.append({"ts": int(parts[0]), "dt": parts[1], "value": float(parts[2])})
        except (ValueError, IndexError):
          pass
  return data, date


def parse_traffic_hourly_file(file_path: str):
  """Read an hourly traffic file and return (series, interfaces, date).

  Line format: timestamp,<iface>:<upload_mb>:<download_mb>,...
  """
  date = os.path.splitext(os.path.basename(file_path))[0]
  series = {}
  with open(file_path) as f:
    for line in f:
      line = line.strip()
      if not line:
        continue
      parts = line.split(",")
      if len(parts) < 2:
        continue
      try:
        ts = int(parts[0])
        dt = _dt.fromtimestamp(ts).strftime("%Y-%m-%d_%H:%M:%S")
        for iface_part in parts[1:]:
          fields = iface_part.split(":")
          if len(fields) == 3:
            iface, upload, download = fields[0], float(fields[1]), float(fields[2])
            if iface not in series:
              series[iface] = []
            series[iface].append({"ts": ts, "dt": dt, "upload": upload, "download": download})
      except (ValueError, IndexError):
        pass
  interfaces = sorted(series.keys())
  return series, interfaces, date
