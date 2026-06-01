"""Generic HTTP handler that proxies a request to a videoreg-api method.

Plugins declare their HTTP endpoints in `plugins/<id>/manifest.yaml` under
`http.api`. Each entry maps an URL + method to a videoreg-api method. Instead of
a bespoke handler per endpoint, a single factory builds a handler that forwards
the request arguments to the api-method and returns its response.
"""

from aiohttp import web

from sdk.socket.requests import RequestTimeoutError


def make_api_handler(method_name: str, timeout: float | None = None):
  """Build an aiohttp handler that calls `method_name` and returns its response.

  Arguments are taken from the query string for GET/DELETE and from the JSON body
  for POST/PUT/PATCH, then passed as-is to the videoreg-api method.
  """

  async def handler(request: web.Request):
    logger = request.app["logger"]
    api_client = request.app["api_client"]

    # Read args from the JSON body when one is present (POST/PUT/PATCH and also
    # DELETE-with-body, e.g. camera/fave); otherwise from the query string (GET).
    if request.can_read_body:
      try:
        args = await request.json()
      except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)
    else:
      args = dict(request.query)

    try:
      response = await api_client.exec(method_name, args, timeout=timeout)
      if not response.is_ok():
        return web.json_response({"error": response.get_error()}, status=500)
      return web.json_response(response.get_data())
    except RequestTimeoutError:
      return web.json_response({"error": "timeout"}, status=504)
    except Exception as e:
      logger.error(f"Error in api handler for '{method_name}': {e}", exc_info=True)
      return web.json_response({"error": str(e)}, status=500)

  return handler
