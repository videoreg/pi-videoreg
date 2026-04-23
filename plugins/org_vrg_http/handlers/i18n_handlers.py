from aiohttp import web


async def handle_get_i18n(request: web.Request):
  i18n = request.app["i18n"]
  return web.json_response(
    {
      "locale": i18n.locale,
      "translations": i18n.all(),
    }
  )
