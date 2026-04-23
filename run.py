import asyncio

from sdk.service import ServiceRunner

if __name__ == "__main__":
  runner = ServiceRunner()
  asyncio.run(runner.run())
