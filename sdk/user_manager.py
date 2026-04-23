import json
from datetime import datetime
from pathlib import Path
from typing import Any

import bcrypt


class UserManager:
  """Manages system users."""

  DEFAULT_USERNAME = "admin"
  DEFAULT_PASSWORD = "videoreg"

  def __init__(self, users_file_path: Path):
    """
    Args:
      users_file_path: Path to the users file
    """
    self.users_file_path = users_file_path
    self._users: dict[str, dict[str, Any]] = self._load_or_create_users()

  def _load_or_create_users(self) -> dict[str, dict[str, Any]]:
    """Loads the users file or creates it with a default admin user."""
    if self.users_file_path.exists():
      with open(self.users_file_path) as f:
        return json.load(f)
    else:
      users = {}
      password_hash = self._hash_password(self.DEFAULT_PASSWORD)
      users[self.DEFAULT_USERNAME] = {
        "password_hash": password_hash,
        "password_changed": False,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
      }
      self._save_users(users)
      return users

  def _save_users(self, users: dict[str, dict[str, Any]]) -> None:
    """Saves users to file."""
    self.users_file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.users_file_path, "w") as f:
      json.dump(users, f, indent=2)

  def _hash_password(self, password: str) -> str:
    salt = bcrypt.gensalt()
    password_hash = bcrypt.hashpw(password.encode("utf-8"), salt)
    return password_hash.decode("utf-8")

  def _verify_password(self, password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

  def authenticate(self, username: str, password: str) -> bool:
    user = self._users.get(username)
    if user is None:
      return False
    password_hash = user.get("password_hash")
    if password_hash is None:
      return False
    return self._verify_password(password, password_hash)

  def user_exists(self, username: str) -> bool:
    return username in self._users

  def change_password(self, username: str, old_password: str, new_password: str) -> bool:
    if not self.authenticate(username, old_password):
      return False
    password_hash = self._hash_password(new_password)
    self._users[username]["password_hash"] = password_hash
    self._users[username]["password_changed"] = True
    self._users[username]["updated_at"] = datetime.utcnow().isoformat()
    self._save_users(self._users)
    return True

  def get_user_info(self, username: str) -> dict[str, Any] | None:
    user = self._users.get(username)
    if user is None:
      return None
    return {
      "username": username,
      "password_changed": user.get("password_changed", True),
      "created_at": user.get("created_at"),
      "updated_at": user.get("updated_at"),
    }

  def get_all_users(self) -> list:
    """Returns all users with plugin_fields, without password_hash."""
    result = []
    for username, user in self._users.items():
      result.append(
        {
          "username": username,
          "created_at": user.get("created_at"),
          "updated_at": user.get("updated_at"),
          "plugin_fields": user.get("plugin_fields", {}),
        }
      )
    return result

  def add_user(self, username: str, password: str) -> bool:
    if username in self._users:
      return False
    password_hash = self._hash_password(password)
    self._users[username] = {
      "password_hash": password_hash,
      "created_at": datetime.utcnow().isoformat(),
      "updated_at": datetime.utcnow().isoformat(),
    }
    self._save_users(self._users)
    return True

  def delete_user(self, username: str) -> bool:
    if username == self.DEFAULT_USERNAME:
      raise ValueError("Cannot delete admin user")
    if username not in self._users:
      return False
    del self._users[username]
    self._save_users(self._users)
    return True

  def get_plugin_fields(self, username: str, plugin: str) -> dict[str, Any]:
    """Returns plugin fields for the given user."""
    user = self._users.get(username)
    if user is None:
      return {}
    return user.get("plugin_fields", {}).get(plugin, {})

  def set_plugin_fields(self, username: str, plugin: str, fields: dict[str, Any]) -> bool:
    """
    Overwrites plugin fields for the given user.
    Fields with empty values are removed. If all fields are empty, the entire plugin namespace is removed.

    Returns:
      True if the user was found, False otherwise
    """
    user = self._users.get(username)
    if user is None:
      return False

    filtered = {k: v for k, v in fields.items() if v != "" and v is not None}

    if "plugin_fields" not in user:
      user["plugin_fields"] = {}

    if filtered:
      user["plugin_fields"][plugin] = filtered
    else:
      user["plugin_fields"].pop(plugin, None)

    self._save_users(self._users)
    return True
