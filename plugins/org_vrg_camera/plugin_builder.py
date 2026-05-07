from argparse import Namespace

from plugins.org_vrg_camera.commands.get_commands import CommandGetCommands
from plugins.org_vrg_camera.commands.list_photos import CommandListPhotos
from plugins.org_vrg_camera.commands.list_videos import CommandListVideos
from plugins.org_vrg_camera.commands.photo import CommandPhoto
from plugins.org_vrg_camera.commands.send_photo import CommandSendPhoto
from plugins.org_vrg_camera.commands.send_photo_link import CommandSendPhotoLink
from plugins.org_vrg_camera.commands.send_video import CommandSendVideo
from plugins.org_vrg_camera.commands.send_video_link import CommandSendVideoLink
from plugins.org_vrg_camera.commands.video import CommandVideo
from plugins.org_vrg_camera.commands.video_pause import CommandVideoPause
from plugins.org_vrg_camera.commands.video_start import CommandVideoStart
from plugins.org_vrg_camera.methods.add_to_fave import MethodAddToFave
from plugins.org_vrg_camera.methods.check_video_ready import MethodCheckVideoReady
from plugins.org_vrg_camera.methods.convert_video import MethodConvertVideo
from plugins.org_vrg_camera.methods.get_camera_modes import MethodGetCameraModes
from plugins.org_vrg_camera.methods.get_info import MethodGetInfo
from plugins.org_vrg_camera.methods.get_last_media import MethodGetLastMedia
from plugins.org_vrg_camera.methods.is_ready_to_die import MethodIsReadyToDie
from plugins.org_vrg_camera.methods.list_media import MethodListMedia
from plugins.org_vrg_camera.methods.photo import MethodPhoto
from plugins.org_vrg_camera.methods.remove_from_fave import MethodRemoveFromFave
from plugins.org_vrg_camera.methods.set_stream_settings import MethodSetStreamSettings
from plugins.org_vrg_camera.methods.set_video_settings import MethodSetVideoSettings
from plugins.org_vrg_camera.methods.stream_start import MethodStreamStart
from plugins.org_vrg_camera.methods.stream_status import MethodStreamStatus
from plugins.org_vrg_camera.methods.stream_stop import MethodStreamStop
from plugins.org_vrg_camera.methods.video import MethodVideo
from plugins.org_vrg_camera.methods.video_pause import MethodVideoPause
from plugins.org_vrg_camera.methods.video_start import MethodVideoStart
from plugins.org_vrg_camera.methods.video_stop import MethodVideoStop
from plugins.org_vrg_camera.plugin import CameraPlugin
from sdk.interface import Interface, InterfaceCommand, InterfaceCommandMethod
from sdk.service import ConnectionListenerFactory, PluginConnectionListener, ServiceRunner


class CameraServiceConnectionListener(PluginConnectionListener):
  plugin: CameraPlugin

  async def on_data(self, data, to, from_=None):
    await super().on_data(data, to, from_)
    try:
      if to == "osd":
        await self.plugin.handle_osd_update(data)
    except Exception as e:
      self.plugin.logger.warning(f"connection listener on_data error {type(e).__name__}: {e}")


class CameraServiceConnectionListenerFactory(ConnectionListenerFactory):
  def create(self, plugin):
    return CameraServiceConnectionListener(plugin)


async def build_plugin(
  runner: ServiceRunner, args: Namespace, plugin_manifest: dict
) -> CameraPlugin:
  id = plugin_manifest.get("id")
  name = plugin_manifest.get("name")

  plugin = CameraPlugin(id, name, runner)
  plugin.init_logger(args.log_level)
  plugin.init_socket(
    client_id=name,
    channels=["osd"],
    socket_path=None,
    connection_listener_factory=CameraServiceConnectionListenerFactory(),
  )
  plugin.init_journal_client()

  if args.env == "dev":
    from plugins.org_vrg_camera.dev.camera_controls import CameraControlsImpl

    camera_controls = CameraControlsImpl()
  else:
    from plugins.org_vrg_camera.prod.camera_controls import CameraControlsImpl

    camera_controls = CameraControlsImpl(plugin.logger, runner.videoreg)

  plugin.init_camera_controls(camera_controls)

  plugin.init_api_client()

  interfaces = Interface.parse_interfaces(
    runner.videoreg.manifest.interfaces, plugin.logger, plugin.api_client
  )
  commands: dict[str, InterfaceCommand] = {
    "camera": CommandGetCommands(plugin),
    "list_photos": CommandListPhotos(plugin),
    "list_videos": CommandListVideos(plugin),
    "pause": CommandVideoPause(plugin),
    "start": CommandVideoStart(plugin),
    "photo": CommandPhoto(plugin),
    "video": CommandVideo(plugin),
    "send_photo": CommandSendPhoto(plugin),
    "send_photo_link": CommandSendPhotoLink(plugin),
    "send_video": CommandSendVideo(plugin),
    "send_video_link": CommandSendVideoLink(plugin),
  }

  plugin.init_api_servier(
    methods={
      "command": InterfaceCommandMethod(interfaces, commands),
      "get_info": MethodGetInfo(plugin),
      # "get_commands": MethodGetCommands(plugin),
      "video_start": MethodVideoStart(plugin),
      "video_stop": MethodVideoStop(plugin),
      "video_pause": MethodVideoPause(plugin),
      "photo": MethodPhoto(plugin),
      "video": MethodVideo(plugin),
      "is_ready_to_die": MethodIsReadyToDie(plugin),
      "list_media": MethodListMedia(plugin),
      "get_last_media": MethodGetLastMedia(plugin),
      "convert_video": MethodConvertVideo(plugin),
      "check_video_ready": MethodCheckVideoReady(plugin),
      "get_camera_modes": MethodGetCameraModes(plugin),
      "set_video_settings": MethodSetVideoSettings(plugin),
      "set_stream_settings": MethodSetStreamSettings(plugin),
      "stream_start": MethodStreamStart(plugin),
      "stream_stop": MethodStreamStop(plugin),
      "stream_status": MethodStreamStatus(plugin),
      "add_to_fave": MethodAddToFave(plugin),
      "remove_from_fave": MethodRemoveFromFave(plugin),
    }
  )

  return plugin
