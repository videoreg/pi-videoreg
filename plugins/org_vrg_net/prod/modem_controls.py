import asyncio
import re

from plugins.org_vrg_net.modem_controls import ModemControls


class ModemControlsImpl(ModemControls):
  async def get_modem_info(self) -> dict:
    """Gets modem information via mmcli"""

    # Check whether the modem is connected
    result = await self._run_command(["mmcli", "-L"])

    if result.returncode != 0 or not result.stdout:
      return {"connected": False}

    # Extract the modem path from a line like:
    # "/org/freedesktop/ModemManager1/Modem/7 [QUALCOMM INCORPORATED] SIMCOM_SIM7600G-H"
    modem_path_match = re.search(r"(/org/freedesktop/ModemManager1/Modem/\d+)", result.stdout)
    if not modem_path_match:
      return {"connected": False}
    modem_path = modem_path_match.group(1)

    # Extract modem information
    modem_info = await self._run_command(["mmcli", "-m", modem_path])

    if modem_info.returncode != 0:
      return {"connected": False}

    output = modem_info.stdout

    # Parse mmcli output
    return {
      "connected": True,
      "device": self._extract_field(output, r"\|\s+primary port:\s+(.+)"),
      "manufacturer": self._extract_field(output, r"\|\s+manufacturer:\s+(.+)"),
      "model": self._extract_field(output, r"\|\s+model:\s+(.+)"),
      "operator": self._extract_field(output, r"\|\s+operator name:\s+(.+)"),
      "access_tech": self._extract_access_tech(output),
      "signal_quality": self._extract_signal_quality(output),
    }

  async def _run_command(self, cmd):
    """Runs a command and returns the result"""
    proc = await asyncio.create_subprocess_exec(
      *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await proc.communicate()

    return type(
      "Result",
      (),
      {
        "returncode": proc.returncode,
        "stdout": stdout.decode("utf-8", errors="ignore"),
        "stderr": stderr.decode("utf-8", errors="ignore"),
      },
    )()

  def _extract_field(self, output, pattern):
    """Extracts a field value from mmcli output"""
    match = re.search(pattern, output, re.IGNORECASE)
    return match.group(1).strip() if match else None

  def _extract_access_tech(self, output):
    """Extracts the connection type (2g/3g/4g/lte)"""
    match = re.search(r"\|\s+access tech:\s+(.+)", output, re.IGNORECASE)
    if not match:
      return None

    tech = match.group(1).strip().lower()

    # Convert to a readable format
    if "lte" in tech:
      return "4G LTE"
    elif "4g" in tech or "lte" in tech:
      return "4G"
    elif "umts" in tech or "hspa" in tech or "hsupa" in tech or "hsdpa" in tech or "3g" in tech:
      return "3G"
    elif "edge" in tech or "gprs" in tech or "gsm" in tech or "2g" in tech:
      return "2G"
    elif "5g" in tech or "nr" in tech:
      return "5G"
    else:
      return tech.upper()

  def _extract_signal_quality(self, output):
    """Extracts the signal strength"""
    match = re.search(r"\|\s+signal quality:\s+(\d+)%", output, re.IGNORECASE)
    if match:
      return int(match.group(1))
    return None
