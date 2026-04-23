from collections.abc import Callable
from urllib.parse import quote

from aiohttp import web

from plugins.org_vrg_http.jwt_handler import JwtHandler
from sdk.user_manager import UserManager


def create_auth_middleware(jwt_handler: JwtHandler, user_manager: UserManager):
  """
  Creates authorization middleware

  Args:
    jwt_handler: JWT token handler
    user_manager: User manager

  Returns:
    Middleware function
  """

  def _try_refresh(request: web.Request) -> tuple[str, str] | None:
    """Tries to refresh the access token using the refresh token from cookie.

    Returns:
      (username, new_access_token) or None if refresh is not possible
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
      return None
    username = jwt_handler.verify_token(refresh_token, token_type="refresh")
    if not username or not user_manager.user_exists(username):
      return None
    new_access_token = jwt_handler.create_access_token(username)
    return username, new_access_token

  def _media_login_redirect(request: web.Request) -> web.Response:
    encoded_path = quote(request.path_qs, safe="")
    raise web.HTTPFound(location=f"/?redirect={encoded_path}")

  @web.middleware
  async def auth_middleware(request: web.Request, handler: Callable):
    # Public API endpoints (no authorization required)
    public_api_paths = ["/api/auth/login", "/api/auth/logout", "/api/auth/refresh"]

    if request.path in public_api_paths:
      return await handler(request)

    # Static files and SPA pages are public — authorization is handled on the frontend
    if request.path.startswith("/static/"):
      return await handler(request)

    if (
      not request.path.startswith("/api/")
      and not request.path.startswith("/video/")
      and not request.path.startswith("/photo/")
      and not request.path.startswith("/fave_photo/")
    ):
      return await handler(request)

    # For media files (/video, /photo, /fave_photo) redirect when not authorized
    is_media_request = (
      request.path.startswith("/video/")
      or request.path.startswith("/photo/")
      or request.path.startswith("/fave_photo/")
    )

    # For all other paths check authorization
    authorization = request.headers.get("Authorization")

    # If no Authorization header, check cookies
    if not authorization:
      access_token_cookie = request.cookies.get("access_token")
      if access_token_cookie:
        authorization = f"Bearer {access_token_cookie}"

    if not authorization:
      if is_media_request:
        # Try to refresh via refresh token to avoid showing an HTML page
        refreshed = _try_refresh(request)
        if refreshed:
          username, new_access_token = refreshed
          request["user"] = username
          response = await handler(request)
          response.set_cookie(
            "access_token",
            new_access_token,
            max_age=7 * 24 * 60 * 60,
            httponly=True,
            secure=True,
            samesite="Strict",
          )
          return response
        _media_login_redirect(request)
      else:
        raise web.HTTPUnauthorized(
          text='{"error": "Missing authorization header"}', content_type="application/json"
        )

    # Verify header format
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
      raise web.HTTPUnauthorized(
        text='{"error": "Invalid authorization header format"}', content_type="application/json"
      )

    token = parts[1]

    # Verify token
    username = jwt_handler.verify_token(token, token_type="access")

    if username is None:
      # Token is invalid or expired
      if is_media_request:
        # For media try refresh token to avoid showing an HTML page
        refreshed = _try_refresh(request)
        if refreshed:
          username, new_access_token = refreshed
          request["user"] = username
          response = await handler(request)
          response.set_cookie(
            "access_token",
            new_access_token,
            max_age=7 * 24 * 60 * 60,
            httponly=True,
            secure=True,
            samesite="Strict",
          )
          return response
        _media_login_redirect(request)
      else:
        raise web.HTTPUnauthorized(
          text='{"error": "Invalid or expired token"}', content_type="application/json"
        )

    # Check that the user exists
    if not user_manager.user_exists(username):
      raise web.HTTPUnauthorized(
        text='{"error": "User not found"}', content_type="application/json"
      )

    # Attach user info to the request
    request["user"] = username

    return await handler(request)

  return auth_middleware
