import asyncio

from plugins.org_vrg_net.plugin import NetPlugin
from sdk.socket.api import ApiMethod


class MethodGenerateWireguardKey(ApiMethod):
  """Generates a WireGuard key pair via `wg genkey`/`wg pubkey` (moved from the http handler)."""

  _plugin: NetPlugin

  def __init__(self, plugin: NetPlugin):
    super().__init__()
    self._plugin = plugin

  async def exec(self, args):
    try:
      proc = await asyncio.create_subprocess_exec(
        "wg", "genkey",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
      )
      stdout, stderr = await proc.communicate()
      if proc.returncode != 0:
        error_msg = stderr.decode("utf-8").strip()
        self._plugin.logger.error(f"Failed to generate private key: {error_msg}")
        return {"status": "error", "error": f"Failed to generate private key: {error_msg}"}

      private_key = stdout.decode("utf-8").strip()

      proc = await asyncio.create_subprocess_exec(
        "wg", "pubkey",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
      )
      stdout, stderr = await proc.communicate(input=private_key.encode("utf-8"))
      if proc.returncode != 0:
        error_msg = stderr.decode("utf-8").strip()
        self._plugin.logger.error(f"Failed to generate public key: {error_msg}")
        return {"status": "error", "error": f"Failed to generate public key: {error_msg}"}

      public_key = stdout.decode("utf-8").strip()

      self._plugin.logger.info("WireGuard key pair generated")
      return {"status": "ok", "data": {"private_key": private_key, "public_key": public_key}}

    except FileNotFoundError:
      self._plugin.logger.error("WireGuard tools (wg) not found")
      return {"status": "error", "error": "WireGuard tools not installed"}
    except Exception as e:
      self._plugin.logger.error(f"Error generating WireGuard keys: {e}")
      return {"status": "error", "error": str(e)}
