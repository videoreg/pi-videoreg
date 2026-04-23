"""Statistics handlers (CPU temperature, PiSugar, traffic)"""

import os
from datetime import datetime as _dt

from aiohttp import web


def _parse_stat_file(file_path):
  """Reads a stats file and returns (data, date)."""
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


async def _handle_stat_request(request: web.Request, api_method: str):
  """Common stat request handler with ?date=YYYY-MM-DD support."""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec(api_method, {})
    if not response.is_ok():
      return web.json_response({"error": "Ошибка получения данных"}, status=500)

    files = response.get_data().get("files", [])
    if not files:
      return web.json_response({"data": [], "date": None, "available_dates": []})

    available_dates = sorted(os.path.splitext(os.path.basename(f))[0] for f in files)

    requested_date = request.rel_url.query.get("date")
    if requested_date:
      file_by_date = {os.path.splitext(os.path.basename(f))[0]: f for f in files}
      selected_file = file_by_date.get(requested_date, files[-1])
    else:
      selected_file = files[-1]

    data, date = _parse_stat_file(selected_file)
    return web.json_response({"data": data, "date": date, "available_dates": available_dates})
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_camera_photo: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)


async def handle_get_stat_temp(request: web.Request):
  return await _handle_stat_request(request, "stat.get_temp_history")


async def handle_get_stat_pisugar(request: web.Request):
  return await _handle_stat_request(request, "stat.get_pisugar_history")


def _parse_traffic_hourly_file(file_path):
  """Reads an hourly traffic file and returns (series, interfaces, date).

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


async def handle_get_stat_traffic(request: web.Request):
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("stat.get_traffic_hourly_history", {})
    if not response.is_ok():
      return web.json_response({"error": "Ошибка получения данных"}, status=500)

    files = response.get_data().get("files", [])
    if not files:
      return web.json_response(
        {"series": {}, "interfaces": [], "date": None, "available_dates": []}
      )

    available_dates = sorted(os.path.splitext(os.path.basename(f))[0] for f in files)

    requested_date = request.rel_url.query.get("date")
    if requested_date:
      file_by_date = {os.path.splitext(os.path.basename(f))[0]: f for f in files}
      selected_file = file_by_date.get(requested_date, files[-1])
    else:
      selected_file = files[-1]

    series, interfaces, date = _parse_traffic_hourly_file(selected_file)
    return web.json_response(
      {"series": series, "interfaces": interfaces, "date": date, "available_dates": available_dates}
    )
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error in handle_post_camera_photo: {e}", exc_info=True)
    return web.json_response({"error": str(e)}, status=500)
