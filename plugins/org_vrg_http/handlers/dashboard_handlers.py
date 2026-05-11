"""Dashboard summary status handler"""

import asyncio

from aiohttp import web


async def handle_get_dashboard_status(request: web.Request):
  """System summary status for the main page"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  (
    connections_response,
    modem_response,
    wg_response,
    camera_response,
    power_response,
    last_media_response,
    location_response,
    trip_response,
  ) = await asyncio.gather(
    api_client.exec("net.connections", None),
    api_client.exec("net.modem_info", {}),
    api_client.exec("net.wg_show", {}),
    api_client.exec("camera.get_info", {}),
    api_client.exec("power.get_status", {}),
    api_client.exec("camera.get_last_media", {}),
    api_client.exec("gps.get_location", {}),
    api_client.exec("core.get_trip_state", {}),
    # api_client.exec("stat.storage_info", {}),
    return_exceptions=True,
  )

  result = {
    "connections": None,
    "modem": None,
    "wireguard": None,
    "camera": None,
    "power": None,
    "storage": None,
    "last_media": None,
    "location": None,
    "trip": None,
  }

  if isinstance(connections_response, Exception):
    logger.warning(f"Dashboard: connections error: {connections_response}")
  elif connections_response.is_ok():
    result["connections"] = connections_response.get_data()

  if isinstance(modem_response, Exception):
    logger.warning(f"Dashboard: modem info error: {modem_response}")
  elif modem_response.is_ok():
    result["modem"] = modem_response.get_data()

  if isinstance(wg_response, Exception):
    logger.warning(f"Dashboard: wg_show error: {wg_response}")
  elif wg_response.is_ok():
    result["wireguard"] = wg_response.response.body.get("wg_info")

  if isinstance(camera_response, Exception):
    logger.warning(f"Dashboard: camera info error: {camera_response}")
  elif camera_response.is_ok():
    result["camera"] = camera_response.get_data()

  if isinstance(power_response, Exception):
    logger.warning(f"Dashboard: power status error: {power_response}")
  elif power_response.is_ok():
    result["power"] = power_response.get_data()

  if isinstance(last_media_response, Exception):
    logger.warning(f"Dashboard: last media error: {last_media_response}")
  elif last_media_response.is_ok():
    result["last_media"] = last_media_response.get_data()

  if isinstance(location_response, Exception):
    logger.warning(f"Dashboard: location error: {location_response}")
  elif location_response.is_ok():
    result["location"] = location_response.get_data()

  if isinstance(trip_response, Exception):
    logger.warning(f"Dashboard: trip state error: {trip_response}")
  elif trip_response.is_ok():
    result["trip"] = trip_response.get_data()

  # if isinstance(storage_response, Exception):
  #   logger.warning(f"Dashboard: storage info error: {storage_response}")
  # elif storage_response.is_ok():
  #   data = storage_response.get_data()
  #   partitions = data.get("partitions", [])
  #   data_partition = next(
  #     (p for p in partitions if p["mountpoint"] == "/mnt/data"),
  #     None
  #   )
  #   if data_partition:
  #     result["storage"] = {"data_use_percent": data_partition["use_percent"]}

  return web.json_response(result)


async def handle_get_statusbar_status(request: web.Request):
  """Minimal status for the global status bar (camera + power only)"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  (
    camera_response,
    power_response,
    last_media_response,
  ) = await asyncio.gather(
    api_client.exec("camera.get_info", {}),
    api_client.exec("power.get_status", {}),
    api_client.exec("camera.get_last_media", {}),
    return_exceptions=True,
  )

  result = {
    "camera": None,
    "power": None,
    "last_media": None,
  }

  if isinstance(camera_response, Exception):
    logger.warning(f"Statusbar: camera info error: {camera_response}")
  elif camera_response.is_ok():
    result["camera"] = camera_response.get_data()

  if isinstance(power_response, Exception):
    logger.warning(f"Statusbar: power status error: {power_response}")
  elif power_response.is_ok():
    result["power"] = power_response.get_data()

  if isinstance(last_media_response, Exception):
    logger.warning(f"Statusbar: last media error: {last_media_response}")
  elif last_media_response.is_ok():
    result["last_media"] = last_media_response.get_data()

  return web.json_response(result)
