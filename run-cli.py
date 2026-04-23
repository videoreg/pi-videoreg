import asyncio

from sdk.cli import CliRunner

if __name__ == "__main__":
  runner = CliRunner()
  asyncio.run(runner.run())
