"""Configuration loading for the reddit CLI.

Resolution order, highest wins: environment variables, then config.toml, then
defaults. A 1Password reference is consulted only when the direct value is absent,
so a working config never blocks on the op CLI (which has hung on approval before).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("REDDIT_PLUGIN_HOME", Path.home() / ".config" / "reddit-plugin"))
CONFIG_PATH = CONFIG_DIR / "config.toml"
CACHE_DIR = CONFIG_DIR / "cache"

DEFAULT_USER_AGENT = "reddit-plugin/0.1.0 (VOC research; +https://github.com/juliandickie)"

READ_SCOPES = ["identity", "read", "history"]
WRITE_SCOPES = ["submit", "edit"]


class ConfigError(RuntimeError):
    """Raised when configuration is missing or unusable. Message is user-facing."""


@dataclass
class Config:
    client_id: str | None = None
    client_secret: str | None = None
    refresh_token: str | None = None
    user_agent: str = DEFAULT_USER_AGENT
    allow_write: bool = False
    cache_enabled: bool = True
    cache_ttl_hours: int = 24
    granted_scopes: list[str] = field(default_factory=list)

    def require_auth(self) -> None:
        missing = [
            name
            for name, value in (
                ("client_id", self.client_id),
                ("client_secret", self.client_secret),
                ("refresh_token", self.refresh_token),
            )
            if not value
        ]
        if not missing:
            return
        if missing == ["refresh_token"]:
            raise ConfigError(
                "Not authorised yet. Run `reddit auth` to authorise in a browser once."
            )
        raise ConfigError(
            f"Missing credentials: {', '.join(missing)}.\n"
            f"Register a Reddit app at https://www.reddit.com/prefs/apps as type "
            f"'web app' with redirect http://localhost:8250/callback, then put the id "
            f"and secret in {CONFIG_PATH}. See `reddit doctor`."
        )

    def can_write(self) -> tuple[bool, str]:
        """Return (allowed, reason_if_not). Checks the token and config layers only.

        The per-call --i-am-sure flag is the third layer and is enforced at the
        command level, deliberately not here, so no single call site can satisfy
        all three gates by itself.
        """
        if not self.allow_write:
            return False, (
                f"Write is disabled. Set allow_write = true under [reddit] in "
                f"{CONFIG_PATH} to enable it."
            )
        if self.granted_scopes and not any(s in self.granted_scopes for s in WRITE_SCOPES):
            return False, (
                "The stored token is read-only. Re-authorise with "
                "`reddit auth --with-write` to grant write scopes."
            )
        return True, ""


def _resolve_op_ref(ref: str, account: str | None) -> str | None:
    """Read a secret from 1Password. Returns None rather than raising, so a broken
    op setup degrades to 'credential not found' instead of taking the CLI down."""
    if not shutil.which("op"):
        return None
    cmd = ["op", "read", ref]
    if account:
        cmd += ["--account", account]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (subprocess.TimeoutExpired, OSError):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.strip() or None


def _read_toml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("rb") as handle:
            return tomllib.load(handle)
    except (tomllib.TOMLDecodeError, OSError) as exc:
        raise ConfigError(f"Could not read {path}: {exc}") from exc


def load(path: Path | None = None) -> Config:
    path = path or CONFIG_PATH
    raw = _read_toml(path)
    reddit = raw.get("reddit", {})
    cache = raw.get("cache", {})
    op = reddit.get("op", {})

    client_id = os.environ.get("REDDIT_CLIENT_ID") or reddit.get("client_id")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET") or reddit.get("client_secret")
    refresh_token = os.environ.get("REDDIT_REFRESH_TOKEN") or reddit.get("refresh_token")

    account = op.get("account")
    if not client_secret and op.get("client_secret_ref"):
        client_secret = _resolve_op_ref(op["client_secret_ref"], account)
    if not refresh_token and op.get("refresh_token_ref"):
        refresh_token = _resolve_op_ref(op["refresh_token_ref"], account)

    return Config(
        client_id=client_id,
        client_secret=client_secret,
        refresh_token=refresh_token,
        user_agent=os.environ.get("REDDIT_USER_AGENT") or reddit.get("user_agent", DEFAULT_USER_AGENT),
        allow_write=bool(reddit.get("allow_write", False)),
        cache_enabled=bool(cache.get("enabled", True)),
        cache_ttl_hours=int(cache.get("ttl_hours", 24)),
        granted_scopes=list(reddit.get("granted_scopes", [])),
    )


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def save_tokens(refresh_token: str, granted_scopes: list[str], path: Path | None = None) -> Path:
    """Write the refresh token back into config.toml, preserving other settings.

    Rewrites the file rather than appending, because a duplicated key in TOML is a
    parse error and would brick the config on a second `reddit auth`.
    """
    path = path or CONFIG_PATH
    raw = _read_toml(path)
    reddit = dict(raw.get("reddit", {}))
    cache = dict(raw.get("cache", {}))
    op = dict(reddit.pop("op", {}))

    reddit["refresh_token"] = refresh_token
    reddit["granted_scopes"] = granted_scopes

    lines = ["# reddit-plugin configuration.", "# Written by `reddit auth`. Safe to edit by hand.", "", "[reddit]"]
    for key in ("client_id", "client_secret", "refresh_token", "user_agent"):
        if reddit.get(key):
            lines.append(f'{key} = "{_toml_escape(str(reddit[key]))}"')
    lines.append(f"allow_write = {'true' if reddit.get('allow_write') else 'false'}")
    scopes = ", ".join(f'"{_toml_escape(s)}"' for s in granted_scopes)
    lines.append(f"granted_scopes = [{scopes}]")
    if op:
        lines += ["", "[reddit.op]"]
        for key, value in op.items():
            lines.append(f'{key} = "{_toml_escape(str(value))}"')
    lines += ["", "[cache]"]
    lines.append(f"enabled = {'true' if cache.get('enabled', True) else 'false'}")
    lines.append(f"ttl_hours = {int(cache.get('ttl_hours', 24))}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o600)
    return path
