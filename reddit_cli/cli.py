"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import sys

from . import auth as auth_module
from . import config as config_module
from . import formats
from .client import Client, RedditError
from .config import CONFIG_PATH, ConfigError

VERSION = "0.1.0"

WRITE_REFUSAL = (
    "Refusing to write without --i-am-sure. Write is gated three ways: a token with "
    "write scopes (reddit auth --with-write), allow_write = true in config, and this "
    "flag on every call."
)


def _add_common(parser: argparse.ArgumentParser, *, voc_opts: bool = True) -> None:
    parser.add_argument(
        "--format", choices=formats.FORMATS, default="json", help="output format (default json)"
    )
    parser.add_argument("--no-cache", action="store_true", help="bypass the disk cache")
    if voc_opts:
        parser.add_argument(
            "--min-length",
            type=int,
            default=None,
            help="voc format: minimum comment length to keep (default 80)",
        )
        parser.add_argument(
            "--keep-all",
            action="store_true",
            help="voc format: disable the mechanical prefilter entirely",
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="reddit",
        description="Read Reddit for VOC research. Official API, no scraping.",
    )
    parser.add_argument("--version", action="version", version=f"reddit-plugin {VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_auth = sub.add_parser("auth", help="authorise once in a browser")
    p_auth.add_argument("--with-write", action="store_true", help="also request write scopes")
    p_auth.add_argument("--port", type=int, default=auth_module.DEFAULT_PORT)

    p_search = sub.add_parser("search", help="search Reddit or named subreddits")
    p_search.add_argument("query")
    p_search.add_argument("--sub", help="comma separated subreddits, omit for all of Reddit")
    p_search.add_argument(
        "--sort", default="relevance", choices=["relevance", "hot", "top", "new", "comments"]
    )
    p_search.add_argument(
        "--time", dest="time_filter", default="all",
        choices=["hour", "day", "week", "month", "year", "all"],
    )
    p_search.add_argument("--limit", type=int, default=25)
    p_search.add_argument(
        "--with-comments", action="store_true",
        help="fetch the full comment tree for every hit (slow, but what voc needs)",
    )
    _add_common(p_search)

    p_thread = sub.add_parser("thread", help="one thread with its full comment tree")
    p_thread.add_argument("ref", help="URL or submission id")
    p_thread.add_argument("--limit-comments", type=int, default=None)
    _add_common(p_thread)

    p_browse = sub.add_parser("browse", help="browse a subreddit")
    p_browse.add_argument("subreddit")
    p_browse.add_argument(
        "--sort", default="hot", choices=["hot", "new", "top", "rising", "controversial"]
    )
    p_browse.add_argument(
        "--time", dest="time_filter", default="day",
        choices=["hour", "day", "week", "month", "year", "all"],
    )
    p_browse.add_argument("--limit", type=int, default=25)
    _add_common(p_browse)

    p_user = sub.add_parser("user", help="one account's post and comment history")
    p_user.add_argument("name")
    p_user.add_argument("--kind", default="all", choices=["all", "submissions", "comments"])
    p_user.add_argument("--limit", type=int, default=50)
    _add_common(p_user)

    p_post = sub.add_parser("post", help="submit a post (write)")
    p_post.add_argument("subreddit")
    p_post.add_argument("--title", required=True)
    p_post.add_argument("--text", required=True)
    p_post.add_argument("--i-am-sure", action="store_true", dest="i_am_sure")

    p_comment = sub.add_parser("comment", help="reply to a post or comment (write)")
    p_comment.add_argument("parent", help="submission URL/id, or t1_xxxx for a comment")
    p_comment.add_argument("--text", required=True)
    p_comment.add_argument("--i-am-sure", action="store_true", dest="i_am_sure")

    sub.add_parser("doctor", help="diagnose config, auth and cache")

    p_cache = sub.add_parser("cache", help="inspect or clear the disk cache")
    p_cache.add_argument("action", choices=["info", "clear"])

    return parser


def _voc_kwargs(args) -> dict:
    if getattr(args, "format", None) != "voc":
        return {}
    out = {}
    if getattr(args, "min_length", None) is not None:
        out["min_length"] = args.min_length
    if getattr(args, "keep_all", False):
        out["keep_all"] = True
    return out


def _emit(data, args) -> int:
    print(formats.render(data, args.format, **_voc_kwargs(args)))
    return 0


def cmd_auth(args, cfg) -> int:
    print(json.dumps(auth_module.authorise(cfg, with_write=args.with_write, port=args.port), indent=2))
    return 0


def cmd_search(args, cfg) -> int:
    client = Client(cfg)
    subs = [s.strip() for s in args.sub.split(",")] if args.sub else None
    posts = client.search(
        args.query, subreddits=subs, sort=args.sort, time_filter=args.time_filter,
        limit=args.limit, use_cache=not args.no_cache,
    )
    if args.with_comments or args.format == "voc":
        posts = [
            client.thread(p.permalink or p.id, use_cache=not args.no_cache) for p in posts
        ]
    return _emit(posts, args)


def cmd_thread(args, cfg) -> int:
    client = Client(cfg)
    post = client.thread(args.ref, comment_limit=args.limit_comments, use_cache=not args.no_cache)
    return _emit(post, args)


def cmd_browse(args, cfg) -> int:
    client = Client(cfg)
    posts = client.browse(
        args.subreddit, sort=args.sort, time_filter=args.time_filter,
        limit=args.limit, use_cache=not args.no_cache,
    )
    if args.format == "voc":
        posts = [client.thread(p.permalink or p.id, use_cache=not args.no_cache) for p in posts]
    return _emit(posts, args)


def cmd_user(args, cfg) -> int:
    data = Client(cfg).user(args.name, kind=args.kind, limit=args.limit, use_cache=not args.no_cache)
    return _emit(data, args)


def cmd_post(args, cfg) -> int:
    if not args.i_am_sure:
        raise ConfigError(WRITE_REFUSAL)
    result = Client(cfg).submit_post(args.subreddit, args.title, args.text)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_comment(args, cfg) -> int:
    if not args.i_am_sure:
        raise ConfigError(WRITE_REFUSAL)
    result = Client(cfg).submit_comment(args.parent, args.text)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_doctor(args, cfg) -> int:
    write_ok, write_reason = cfg.can_write()
    report = {
        "version": VERSION,
        "config_path": str(CONFIG_PATH),
        "config_exists": CONFIG_PATH.exists(),
        "client_id": bool(cfg.client_id),
        "client_secret": bool(cfg.client_secret),
        "refresh_token": bool(cfg.refresh_token),
        "granted_scopes": cfg.granted_scopes,
        "write_enabled": write_ok,
        "write_blocked_because": write_reason or None,
        "cache": Client(cfg).cache.info(),
    }
    problems = []
    if not (cfg.client_id and cfg.client_secret):
        problems.append(
            "Register an app at https://www.reddit.com/prefs/apps (type: web app, "
            f"redirect http://localhost:{auth_module.DEFAULT_PORT}/callback), then add "
            f"client_id and client_secret to {CONFIG_PATH}."
        )
    elif not cfg.refresh_token:
        problems.append("Run `reddit auth` to authorise.")
    report["ok"] = not problems
    report["next_steps"] = problems
    print(json.dumps(report, indent=2))
    return 0 if not problems else 1


def cmd_cache(args, cfg) -> int:
    cache = Client(cfg).cache
    if args.action == "info":
        print(json.dumps(cache.info(), indent=2))
    else:
        print(json.dumps({"cleared_entries": cache.clear()}, indent=2))
    return 0


HANDLERS = {
    "auth": cmd_auth, "search": cmd_search, "thread": cmd_thread, "browse": cmd_browse,
    "user": cmd_user, "post": cmd_post, "comment": cmd_comment, "doctor": cmd_doctor,
    "cache": cmd_cache,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return HANDLERS[args.command](args, config_module.load())
    except (ConfigError, RedditError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
