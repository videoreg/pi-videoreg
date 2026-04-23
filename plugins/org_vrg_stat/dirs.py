from sdk.videoreg import Videoreg


class Dirs:
  videoreg: Videoreg = None
  plugin_id: str = None

  def __init__(self, videoreg: Videoreg, plugin_id: str):
    self.videoreg = videoreg
    self.plugin_id = plugin_id
    self.cpu.mkdir(parents=True, exist_ok=True)
    self.pisugar.mkdir(parents=True, exist_ok=True)
    self.traffic_kbps.mkdir(parents=True, exist_ok=True)
    self.traffic_hourly.mkdir(parents=True, exist_ok=True)
    self.temp.mkdir(parents=True, exist_ok=True)

  @property
  def cpu(self):
    if not self.videoreg:
      raise Exception("Set videoreg first")
    return self.videoreg.plugin_private_path(self.plugin_id, "cpu")

  @property
  def pisugar(self):
    if not self.videoreg:
      raise Exception("Set videoreg first")
    return self.videoreg.plugin_private_path(self.plugin_id, "pisugar")

  @property
  def traffic_kbps(self):
    if not self.videoreg:
      raise Exception("Set videoreg first")
    return self.videoreg.plugin_private_path(self.plugin_id, "traffic_kbps")

  @property
  def traffic_hourly(self):
    if not self.videoreg:
      raise Exception("Set videoreg first")
    return self.videoreg.plugin_private_path(self.plugin_id, "traffic_hourly")

  @property
  def temp(self):
    if not self.videoreg:
      raise Exception("Set videoreg first")
    return self.videoreg.plugin_private_path(self.plugin_id, "temp")
