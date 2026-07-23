import os
import socket


def sd_notify(state: str) -> bool:
  """Send a notification to systemd via $NOTIFY_SOCKET.

  No-op (returns False) when NOTIFY_SOCKET is unset, so it is safe to call from
  services that are not Type=notify.
  """
  addr = os.environ.get("NOTIFY_SOCKET")
  if not addr:
    return False

  # Abstract namespace socket (starts with '@' or a null byte)
  if addr.startswith("@"):
    addr = "\0" + addr[1:]

  with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_CLOEXEC) as sock:
    sock.connect(addr)
    sock.sendall(state.encode())

  return True


def sd_notify_ready() -> bool:
  """Tell systemd the service has finished starting up (READY=1)."""
  return sd_notify("READY=1")
