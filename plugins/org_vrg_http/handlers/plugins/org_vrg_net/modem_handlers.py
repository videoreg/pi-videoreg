"""Modem configuration handlers"""

import json

from aiohttp import web

import plugins.org_vrg_http.handlers.plugins.org_vrg_net.nm_helpers as nm_helpers


async def handle_net_get_modem_info(request: web.Request):
  """Get connected modem info (requires authorization)"""
  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    # Get modem info via NetService
    response = await api_client.exec("net.modem_info", {})

    if response.is_ok():
      data = response.get_data()
      logger.info(f"Modem info retrieved: connected={data.get('connected', False)}")

      return web.Response(text=json.dumps(data), content_type="application/json")
    else:
      error = response.get_error()
      logger.error(f"Error getting modem info: {error}")
      return web.Response(
        status=500, text=json.dumps({"error": error}), content_type="application/json"
      )

  except Exception as e:
    logger.error(f"Error getting modem info: {e}", exc_info=True)
    return web.Response(
      status=500, text=json.dumps({"error": str(e)}), content_type="application/json"
    )


async def handle_get_modem_apn(request: web.Request):
  """Get current modem configuration (requires authorization)"""
  logger = request.app["logger"]

  try:
    # Get modem connection info
    modem_info = await nm_helpers.get_connection_info(
      "modem", logger, properties_map={"gsm.apn": "apn"}
    )

    logger.info(
      f"Modem config retrieved: APN={modem_info['apn'] if modem_info['apn'] else '(empty)'}, "
      f"enabled={modem_info['enabled']}, autoconnect={modem_info['autoconnect']}, "
      f"ip={modem_info['ip'] if modem_info['ip'] else '(none)'}"
    )

    return web.Response(text=json.dumps(modem_info), content_type="application/json")

  except FileNotFoundError:
    logger.error("nmcli not found")
    return web.Response(
      status=500,
      text='{"error": "NetworkManager tools (nmcli) not installed"}',
      content_type="application/json",
    )
  except Exception as e:
    logger.error(f"Error getting modem APN: {e}")
    return web.Response(
      status=500,
      text=f'{{"error": "Failed to get modem APN: {str(e)}"}}',
      content_type="application/json",
    )


async def handle_set_modem_apn(request: web.Request):
  """Set modem configuration (requires authorization)"""
  logger = request.app["logger"]
  username = request.get("user")  # Set by middleware

  try:
    data = await request.json()
  except json.JSONDecodeError:
    return web.Response(
      status=400, text='{"error": "Invalid JSON"}', content_type="application/json"
    )

  logger.info(f"Updating modem config by user '{username}'")

  try:
    # Update APN if provided
    if "apn" in data:
      apn = data["apn"].strip()
      logger.info(f"Setting modem APN to: {apn if apn else '(empty)'}")
      await nm_helpers.set_connection_property("modem", "gsm.apn", apn, logger)

    # Update autoconnect if provided
    if "autoconnect" in data:
      autoconnect = "yes" if data["autoconnect"] else "no"
      logger.info(f"Setting modem autoconnect to: {autoconnect}")
      await nm_helpers.set_connection_property(
        "modem", "connection.autoconnect", autoconnect, logger
      )

    # Enable or disable connection if provided
    if "enabled" in data:
      if data["enabled"]:
        logger.info("Activating modem connection")
        await nm_helpers.connection_up("modem", logger)
      else:
        logger.info("Deactivating modem connection")
        await nm_helpers.connection_down("modem", logger)

    logger.info("Modem config successfully updated")

    return web.Response(
      text='{"message": "Modem configuration successfully updated"}',
      content_type="application/json",
    )

  except FileNotFoundError:
    logger.error("nmcli not found")
    return web.Response(
      status=500,
      text='{"error": "NetworkManager tools (nmcli) not installed"}',
      content_type="application/json",
    )
  except Exception as e:
    logger.error(f"Error setting modem APN: {e}")
    return web.Response(
      status=500,
      text=f'{{"error": "Failed to set modem APN: {str(e)}"}}',
      content_type="application/json",
    )
