import asyncio
from asyncio import StreamReader
from asyncio.subprocess import Process
from datetime import datetime
from pathlib import Path
from typing import Any


async def _read_stream(pid, stream: StreamReader, cb):
  while True:
    line = await stream.readline()
    if line:
      cb(pid, line.decode())
    else:
      break


async def stream_subprocess(cmd, start_cb, stdout_cb, stderr_cb) -> Process:
  process = await asyncio.create_subprocess_exec(
    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
  )

  start_cb(process.pid, cmd)

  await asyncio.gather(
    _read_stream(process.pid, process.stdout, stdout_cb),
    _read_stream(process.pid, process.stderr, stderr_cb),
  )

  # except OSError as e:
  #   # the program will hang if we let any exception propagate
  #   return e

  await process.wait()

  return process


class CommandResult:
  """Return value from a subprocess: returncode, stdout, stderr."""

  returncode: int
  stdout: Any
  stderr: Any


async def return_subprocess(cmd) -> CommandResult:
  process: Process = await asyncio.create_subprocess_exec(
    *cmd,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
  )

  stdout, stderr = await process.communicate()

  result = CommandResult()

  result.returncode = process.returncode
  result.stdout = stdout.decode()
  result.stderr = stderr.decode()

  return result


def find_latest_file(folder_path: Path, extension="jpg") -> Path:
  """
  Finds the most recently created file in the given folder.

  Args:
    folder_path: Path - path to the folder to search
    extension: str - file extension (default "jpg")

  Returns:
    Path - path to the latest file, or None if no files found
  """

  if not folder_path.exists() or not folder_path.is_dir():
    return None

  files = list(folder_path.glob(f"*.{extension}"))

  if not files:
    return None

  # Filename format YYYY-MM-DD_HH-MM-SS guarantees correct sort order
  files.sort(key=lambda f: f.name)

  return files[-1]


def get_file_age_seconds(file_path: Path) -> int:
  """
  Returns the difference in seconds between now and the timestamp
  encoded in the filename, expected format: "YYYY-MM-DD_HH-MM-SS.jpg".

  Args:
    file_path: Path - path to the file

  Returns:
    int - difference in seconds, or None if the filename cannot be parsed
  """

  filename = file_path.stem

  try:
    file_datetime = datetime.strptime(filename, "%Y-%m-%d_%H-%M-%S")
    current_datetime = datetime.now()
    time_diff = current_datetime - file_datetime
    return int(time_diff.total_seconds())

  except ValueError:
    return None
