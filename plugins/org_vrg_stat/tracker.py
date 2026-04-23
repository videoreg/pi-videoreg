class Tracker:
  async def start_loop(self):
    raise NotImplementedError()

  def stop_loop(self):
    raise NotImplementedError()
