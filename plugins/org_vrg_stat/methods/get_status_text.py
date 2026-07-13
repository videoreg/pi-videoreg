import plugins.org_vrg_stat.functions as functions
from sdk.socket.api import ApiMethod

_GIB = 1024**3


class MethodGetStatusText(ApiMethod):
  """Returns a short human-readable system status for the `/status` bot summary."""

  async def exec(self, args):
    try:
      lines = [f"CPU: {functions.get_cpu_temp()}°C"]

      try:
        partitions = await functions.get_disk_partitions()
        data_partition = max(
          partitions, key=lambda p: p["total_bytes"], default=None
        )
        if data_partition:
          free_gib = data_partition["free_bytes"] / _GIB
          lines.append(
            f"Disk: {free_gib:.1f} GB free ({data_partition['use_percent']}% used)"
          )
      except Exception:
        pass

      return {"status": "ok", "data": {"text": "\n".join(lines)}}
    except Exception as e:
      return {"status": "error", "error": str(e)}
