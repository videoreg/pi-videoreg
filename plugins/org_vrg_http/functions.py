import plugins.org_vrg_http.const as const
import plugins.org_vrg_net.ip as ip


async def get_link(dir: str, file_name) -> str:
  ip_ = ip.get_current_ip()

  port = f":{const.HTTPS_PORT}" if const.HTTPS_PORT != 80 and const.HTTPS_PORT != 443 else ""

  return f"https://{ip_}{port}/{dir}/{file_name}"
