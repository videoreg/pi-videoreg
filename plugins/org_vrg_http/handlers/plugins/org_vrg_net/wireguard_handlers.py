"""WireGuard configuration handlers"""

import asyncio
import json
import os

import aiofiles
from aiohttp import web


async def handle_net_get_wireguard_status(request: web.Request):
  """WireGuard interface status via net.wg_show"""
  from sdk.socket.requests import RequestTimeoutError

  logger = request.app["logger"]
  api_client = request.app["api_client"]

  try:
    response = await api_client.exec("net.wg_show", {})
    if not response.is_ok():
      return web.json_response({"error": response.get_error()}, status=500)
    wg_info = response.response.body.get("wg_info")
    return web.json_response(wg_info)
  except RequestTimeoutError:
    return web.json_response({"error": "timeout"}, status=504)
  except Exception as e:
    logger.error(f"Error getting WireGuard status: {e}")
    return web.json_response({"error": str(e)}, status=500)


async def handle_net_get_wireguard_config(request: web.Request):
  """Read WireGuard config file contents (requires authorization)"""
  logger = request.app["logger"]
  config_path = "/etc/wireguard/wg0.conf"

  # Check if the file exists
  if not os.path.exists(config_path):
    logger.warning(f"WireGuard config file not found: {config_path}")
    return web.Response(
      status=404, text='{"error": "Configuration file not found"}', content_type="application/json"
    )

  try:
    # Read file contents
    async with aiofiles.open(config_path, encoding="utf-8") as f:
      content = await f.read()

    logger.info("WireGuard config file read successfully")

    return web.Response(text=content, content_type="text/plain", charset="utf-8")
  except PermissionError:
    logger.error(f"Permission denied reading {config_path}")
    return web.Response(
      status=403, text='{"error": "Permission denied"}', content_type="application/json"
    )
  except Exception as e:
    logger.error(f"Error reading WireGuard config: {e}")
    return web.Response(
      status=500,
      text=f'{{"error": "Failed to read configuration file: {str(e)}"}}',
      content_type="application/json",
    )


async def handle_net_set_wireguard_config(request: web.Request):
  """Write contents to WireGuard config file (requires authorization)"""
  logger = request.app["logger"]
  username = request.get("user")  # Set by middleware
  config_path = "/etc/wireguard/wg0.conf"

  try:
    # Get content from request body
    content = await request.text()

    if not content:
      return web.Response(
        status=400,
        text='{"error": "Configuration content is required"}',
        content_type="application/json",
      )

    # Create a backup of the existing file
    backup_path = f"{config_path}.backup"
    if os.path.exists(config_path):
      try:
        async with aiofiles.open(config_path, encoding="utf-8") as f:
          backup_content = await f.read()
        async with aiofiles.open(backup_path, "w", encoding="utf-8") as f:
          await f.write(backup_content)
        logger.info(f"Created backup of WireGuard config at {backup_path}")
      except Exception as e:
        logger.warning(f"Failed to create backup: {e}")

    # Write new content
    async with aiofiles.open(config_path, "w", encoding="utf-8") as f:
      await f.write(content)

    logger.info(f"WireGuard config file updated by user '{username}'")

    return web.Response(
      text='{"message": "Configuration file updated successfully"}', content_type="application/json"
    )

  except PermissionError:
    logger.error(f"Permission denied writing to {config_path}")
    return web.Response(
      status=403, text='{"error": "Permission denied"}', content_type="application/json"
    )
  except Exception as e:
    logger.error(f"Error writing WireGuard config: {e}")
    return web.Response(
      status=500,
      text=f'{{"error": "Failed to write configuration file: {str(e)}"}}',
      content_type="application/json",
    )


async def handle_net_generate_wireguard_key(request: web.Request):
  """Generate a WireGuard key pair (requires authorization)"""
  logger = request.app["logger"]

  try:
    # Generate private key
    process = await asyncio.create_subprocess_exec(
      "wg", "genkey", stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
      error_msg = stderr.decode("utf-8").strip()
      logger.error(f"Failed to generate private key: {error_msg}")
      return web.Response(
        status=500,
        text=f'{{"error": "Failed to generate private key: {error_msg}"}}',
        content_type="application/json",
      )

    private_key = stdout.decode("utf-8").strip()

    # Derive public key from private key
    process = await asyncio.create_subprocess_exec(
      "wg",
      "pubkey",
      stdin=asyncio.subprocess.PIPE,
      stdout=asyncio.subprocess.PIPE,
      stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate(input=private_key.encode("utf-8"))

    if process.returncode != 0:
      error_msg = stderr.decode("utf-8").strip()
      logger.error(f"Failed to generate public key: {error_msg}")
      return web.Response(
        status=500,
        text=f'{{"error": "Failed to generate public key: {error_msg}"}}',
        content_type="application/json",
      )

    public_key = stdout.decode("utf-8").strip()

    logger.info("WireGuard key pair generated successfully")

    response_data = {"private_key": private_key, "public_key": public_key}

    return web.Response(text=json.dumps(response_data), content_type="application/json")

  except FileNotFoundError:
    logger.error("WireGuard tools (wg) not found")
    return web.Response(
      status=500, text='{"error": "WireGuard tools not installed"}', content_type="application/json"
    )
  except Exception as e:
    logger.error(f"Error generating WireGuard keys: {e}")
    return web.Response(
      status=500,
      text=f'{{"error": "Failed to generate keys: {str(e)}"}}',
      content_type="application/json",
    )
