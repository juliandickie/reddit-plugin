"""One-time OAuth authorisation.

Deliberately a refresh-token flow rather than Reddit's password grant. The password
grant would put the account password in config.toml in plaintext; a refresh token is
revocable from Reddit's app settings without a password change, and read-only unless
write scopes were explicitly requested.

The callback listens on 8250, not 8000, because 8000 is contended by Scribe's OAuth
callback when parallel sessions are running.
"""

from __future__ import annotations

import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from .config import READ_SCOPES, WRITE_SCOPES, Config, ConfigError, save_tokens

DEFAULT_PORT = 8250
REDIRECT_TEMPLATE = "http://localhost:{port}/callback"

_PAGE = """<!doctype html><meta charset="utf-8"><title>{title}</title>
<style>body{{font:16px system-ui;margin:4rem auto;max-width:32rem;color:#111}}</style>
<h1>{title}</h1><p>{body}</p>"""


class _Handler(BaseHTTPRequestHandler):
    result: dict = {}

    def do_GET(self):  # noqa: N802 - stdlib naming
        parsed = urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        params = parse_qs(parsed.query)
        _Handler.result = {k: v[0] for k, v in params.items()}
        ok = "code" in _Handler.result
        title = "Authorised" if ok else "Authorisation failed"
        body = (
            "You can close this tab and go back to the terminal."
            if ok
            else f"Reddit returned: {_Handler.result.get('error', 'no code')}"
        )
        payload = _PAGE.format(title=title, body=body).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):  # silence the default stderr logging
        return


def authorise(config: Config, *, with_write: bool = False, port: int = DEFAULT_PORT) -> dict:
    """Run the browser flow and persist the refresh token. Returns a summary."""
    if not config.client_id or not config.client_secret:
        raise ConfigError(
            "client_id and client_secret are required before authorising.\n"
            "Register an app at https://www.reddit.com/prefs/apps as type 'web app' "
            f"with redirect {REDIRECT_TEMPLATE.format(port=port)}"
        )
    try:
        import praw
    except ImportError as exc:  # pragma: no cover
        raise ConfigError("praw is not installed. Run scripts/install.sh first.") from exc

    scopes = list(READ_SCOPES) + (list(WRITE_SCOPES) if with_write else [])
    state = secrets.token_urlsafe(16)

    reddit = praw.Reddit(
        client_id=config.client_id,
        client_secret=config.client_secret,
        redirect_uri=REDIRECT_TEMPLATE.format(port=port),
        user_agent=config.user_agent,
    )
    url = reddit.auth.url(scopes=scopes, state=state, duration="permanent")

    try:
        server = HTTPServer(("localhost", port), _Handler)
    except OSError as exc:
        raise ConfigError(
            f"Port {port} is already in use, so the callback cannot start. "
            f"Close whatever holds it, or pass --port with a free one."
        ) from exc

    _Handler.result = {}
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    print("Opening Reddit for authorisation. If nothing opens, paste this:\n")
    print(url + "\n")
    webbrowser.open(url)

    thread.join(timeout=300)
    server.server_close()

    result = _Handler.result
    if not result:
        raise ConfigError("Timed out after 5 minutes waiting for the Reddit callback.")
    if result.get("state") != state:
        raise ConfigError("State mismatch on the callback. Authorisation refused.")
    if "code" not in result:
        raise ConfigError(f"Reddit refused: {result.get('error', 'unknown error')}")

    refresh_token = reddit.auth.authorize(result["code"])
    if not refresh_token:
        raise ConfigError("Reddit did not return a refresh token.")

    path = save_tokens(refresh_token, scopes)
    return {
        "stored_in": str(path),
        "scopes": scopes,
        "write_granted": with_write,
        "note": (
            "Write scopes granted. Writing still also requires allow_write = true in "
            "config and --i-am-sure on the call."
            if with_write
            else "Read-only token. Re-run with --with-write if you ever need to post."
        ),
    }
