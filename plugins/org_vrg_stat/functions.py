import os


def read_stat_dir(dir_path):
  """Reads all files from the stats directory, returns lines sorted by file date."""
  rows = []
  dir_path = str(dir_path)
  if not os.path.exists(dir_path):
    return rows
  files = sorted(f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f)))
  for fname in files:
    with open(os.path.join(dir_path, fname)) as f:
      for line in f:
        line = line.strip()
        if line:
          rows.append(line)
  return rows


def read_latest_stat_file(dir_path):
  """Reads only the most recent file from the stats directory.
  Returns (rows, date) where date is the filename without extension (YYYY-MM-DD)."""
  dir_path = str(dir_path)
  if not os.path.exists(dir_path):
    return [], None
  files = sorted(f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f)))
  if not files:
    return [], None
  latest = files[-1]
  date = os.path.splitext(latest)[0]
  rows = []
  with open(os.path.join(dir_path, latest)) as f:
    for line in f:
      line = line.strip()
      if line:
        rows.append(line)
  return rows, date


def get_cpu_temp():
  with open("/sys/class/thermal/thermal_zone0/temp") as f:
    return round(float(f.read()) / 1000.0, 1)


async def get_disk_partitions():
  import asyncio

  proc = await asyncio.create_subprocess_exec(
    "df",
    "-PT",
    "-x",
    "tmpfs",
    "-x",
    "devtmpfs",
    "-x",
    "squashfs",
    "-x",
    "overlay",
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )
  stdout, _ = await proc.communicate()
  lines = stdout.decode().splitlines()
  partitions = []
  for line in lines[1:]:
    parts = line.split()
    if len(parts) < 7:
      continue
    device = parts[0]
    fstype = parts[1]
    total_bytes = int(parts[2]) * 1024
    used_bytes = int(parts[3]) * 1024
    free_bytes = int(parts[4]) * 1024
    use_percent = int(parts[5].rstrip("%"))
    mountpoint = parts[6]
    partitions.append(
      {
        "device": device,
        "fstype": fstype,
        "mountpoint": mountpoint,
        "total_bytes": total_bytes,
        "used_bytes": used_bytes,
        "free_bytes": free_bytes,
        "use_percent": use_percent,
      }
    )
  return partitions
