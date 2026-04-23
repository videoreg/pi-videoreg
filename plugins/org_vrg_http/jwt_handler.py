import secrets
from datetime import datetime, timedelta
from pathlib import Path

import jwt


class JwtHandler:
  """JWT token handler"""

  ACCESS_TOKEN_EXPIRE_MINUTES = 720
  REFRESH_TOKEN_EXPIRE_DAYS = 30
  ALGORITHM = "HS256"

  def __init__(self, secret_key_path: Path):
    """
    Args:
      secret_key_path: Path to the secret key file
    """
    self.secret_key_path = secret_key_path
    self._secret_key = self._load_or_create_secret_key()

  def _load_or_create_secret_key(self) -> str:
    """Loads or creates a new secret key"""
    if self.secret_key_path.exists():
      with open(self.secret_key_path) as f:
        return f.read().strip()
    else:
      # Create new secret key
      secret_key = secrets.token_urlsafe(32)
      self.secret_key_path.parent.mkdir(parents=True, exist_ok=True)
      with open(self.secret_key_path, "w") as f:
        f.write(secret_key)
      return secret_key

  def create_access_token(self, username: str) -> str:
    """
    Creates an access token

    Args:
      username: Username

    Returns:
      JWT access token
    """
    expire = datetime.utcnow() + timedelta(minutes=self.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire, "type": "access"}
    return jwt.encode(payload, self._secret_key, algorithm=self.ALGORITHM)

  def create_refresh_token(self, username: str) -> str:
    """
    Creates a refresh token

    Args:
      username: Username

    Returns:
      JWT refresh token
    """
    expire = datetime.utcnow() + timedelta(days=self.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": username, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, self._secret_key, algorithm=self.ALGORITHM)

  def verify_token(self, token: str, token_type: str = "access") -> str | None:
    """
    Verifies a token and returns the username

    Args:
      token: JWT token
      token_type: Token type ("access" or "refresh")

    Returns:
      Username if token is valid, None if invalid
    """
    try:
      payload = jwt.decode(token, self._secret_key, algorithms=[self.ALGORITHM])

      # Verify token type
      if payload.get("type") != token_type:
        return None

      username: str = payload.get("sub")
      if username is None:
        return None

      return username
    except jwt.ExpiredSignatureError:
      # Token expired
      return None
    except jwt.JWTError:
      # Invalid token
      return None
