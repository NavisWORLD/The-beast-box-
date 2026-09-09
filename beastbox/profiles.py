"""Isolated local profiles. Not a public multi-tenant internet service.

Each profile owns a private data directory. Sessions bind a token to exactly
one profile. A request that names another profile's files is denied. Authority
and credentials remain outside every profile store.

Default Beast Box remains a single-owner local runtime. Enable this gateway
only with an explicit multi-user launch.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

INDEX_NAME = "index.json"
PROFILE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 _.-]{0,63}$")
TOKEN_BYTES = 32


class ProfileError(ValueError):
    """Fail-closed profile or isolation error."""


@dataclass(frozen=True)
class Profile:
    profile_id: str
    name: str
    root: Path

    def to_public(self) -> dict[str, str]:
        return {"profile_id": self.profile_id, "name": self.name, "root": str(self.root)}


def default_home() -> Path:
    return Path.home() / ".beastbox"


class ProfileRegistry:
    """Owns ``<home>/profiles/<id>/`` directories and a public index with no secrets."""

    def __init__(self, home: str | Path | None = None) -> None:
        base = Path(home).expanduser() if home is not None else default_home()
        if base.is_symlink() or ".." in base.parts:
            raise ProfileError("profile home must not be a symlink or parent-traversing path")
        self.home = base.absolute()
        self.root = self.home / "profiles"
        self.root.mkdir(parents=True, exist_ok=True)
        self.root.chmod(0o700)
        if not self._index_path().exists():
            self._write_index([])

    def _index_path(self) -> Path:
        return self.root / INDEX_NAME

    def _write_index(self, profiles: list[Profile]) -> None:
        payload = {
            "schema": "beastbox-profiles-v1",
            "profiles": [profile.to_public() for profile in profiles],
        }
        path = self._index_path()
        tmp = path.with_name(".index.tmp")
        tmp.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
        tmp.chmod(0o600)
        os.replace(tmp, path)
        path.chmod(0o600)

    def list(self) -> list[Profile]:
        raw = json.loads(self._index_path().read_text())
        if not isinstance(raw, dict) or raw.get("schema") != "beastbox-profiles-v1":
            raise ProfileError("unsupported profile index")
        rows = raw.get("profiles")
        if not isinstance(rows, list):
            raise ProfileError("invalid profile index")
        profiles: list[Profile] = []
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"profile_id", "name", "root"}:
                raise ProfileError("invalid profile record")
            profile = Profile(str(row["profile_id"]), str(row["name"]), Path(str(row["root"])))
            expected = self.root / profile.profile_id
            if profile.root.resolve() != expected.resolve():
                raise ProfileError("profile root escaped the registry")
            profiles.append(profile)
        return profiles

    def get(self, profile_id: str) -> Profile:
        for profile in self.list():
            if profile.profile_id == profile_id:
                return profile
        raise ProfileError("unknown profile")

    def by_name(self, name: str) -> Profile:
        matches = [profile for profile in self.list() if profile.name == name]
        if len(matches) != 1:
            raise ProfileError("profile name must match exactly one profile")
        return matches[0]

    def create(self, name: str) -> Profile:
        if not isinstance(name, str) or PROFILE_NAME_RE.fullmatch(name) is None:
            raise ProfileError("profile name must be 1..64 letters, digits, space, _ . -")
        if any(profile.name == name for profile in self.list()):
            raise ProfileError("profile name already exists")
        profile_id = uuid.uuid4().hex
        root = self.root / profile_id
        if root.exists():
            raise ProfileError("profile directory collision")
        root.mkdir(mode=0o700)
        profile = Profile(profile_id, name, root)
        self._write_index([*self.list(), profile])
        return profile


class MultiUserGateway:
    """Loopback multi-profile isolation. Bind remains loopback-only at the HTTP layer."""

    def __init__(self, registry: ProfileRegistry) -> None:
        self.registry = registry
        self._apps: dict[str, Any] = {}
        self._sessions: dict[str, str] = {}
        self._lock = threading.RLock()

    def login(self, *, profile_id: str | None = None, name: str | None = None) -> dict[str, Any]:
        if (profile_id is None) == (name is None):
            raise ProfileError("login requires exactly one of profile_id or name")
        profile = self.registry.get(profile_id) if profile_id else self.registry.by_name(str(name))
        from .cosmic_web import CosmicApp

        with self._lock:
            app = self._apps.get(profile.profile_id)
            if app is None:
                app = CosmicApp(profile.root)
                self._apps[profile.profile_id] = app
            token = secrets.token_urlsafe(TOKEN_BYTES)
            self._sessions[token] = profile.profile_id
        return {"token": token, "profile": profile.to_public(), "authority": "SESSION_LOCAL"}

    def logout(self, token: str) -> dict[str, Any]:
        with self._lock:
            profile_id = self._sessions.pop(token, None)
            if profile_id is None:
                raise ProfileError("invalid session")
            remaining = [sid for sid, pid in self._sessions.items() if pid == profile_id]
            app = self._apps.get(profile_id)
            if app is not None and not remaining:
                app.authority.revoke_all()
                del self._apps[profile_id]
        return {"logged_out": True, "authority": "REVOKED"}

    def _profile_for(self, token: str) -> tuple[Profile, Any]:
        with self._lock:
            profile_id = self._sessions.get(token)
            if profile_id is None:
                raise PermissionError("invalid session")
            app = self._apps[profile_id]
            profile = self.registry.get(profile_id)
        return profile, app

    def deny_foreign_paths(self, profile: Profile, value: Any) -> None:
        if isinstance(value, dict):
            for item in value.values():
                self.deny_foreign_paths(profile, item)
            return
        if isinstance(value, list):
            for item in value:
                self.deny_foreign_paths(profile, item)
            return
        if not isinstance(value, str) or not value:
            return
        candidate = Path(value)
        if not candidate.is_absolute() and not value.startswith(("~", "/", "\\")):
            return
        try:
            resolved = candidate.expanduser().resolve()
        except OSError:
            return
        own = profile.root.resolve()
        try:
            resolved.relative_to(own)
            return
        except ValueError:
            pass
        for other in self.registry.list():
            if other.profile_id == profile.profile_id:
                continue
            try:
                resolved.relative_to(other.root.resolve())
            except ValueError:
                continue
            raise PermissionError("cross-profile path access denied")

    def dispatch(self, token: str, method: str, path: str, body: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
        try:
            profile, app = self._profile_for(token)
        except PermissionError as exc:
            return 401, {"error": str(exc)}
        payload = body or {}
        try:
            self.deny_foreign_paths(profile, payload)
            status, result = app.dispatch(method, path, payload)
        except PermissionError as exc:
            return 403, {"error": str(exc)}
        return status, result
