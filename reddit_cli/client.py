"""PRAW wrapper: auth, disk cache, and comment-tree expansion.

The one genuinely dangerous operation here is comment-tree expansion. Reddit does not
return a whole thread in one response; deep branches come back as `more` stubs that
must be re-requested. Getting that wrong yields a thread that looks complete and is
quietly truncated, which is the exact failure the voc-research skill warns about. That
is why PRAW's replace_more carries the load rather than hand-rolled pagination.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Iterator

from .config import CACHE_DIR, Config, ConfigError
from .models import Comment, Post

THREAD_ID_RE = re.compile(r"/comments/([a-z0-9]+)", re.I)
BARE_ID_RE = re.compile(r"^[a-z0-9]{4,10}$", re.I)


class RedditError(RuntimeError):
    """User-facing failure talking to Reddit."""


def parse_thread_id(value: str) -> str:
    """Accept a full URL, a short link, or a bare submission id."""
    match = THREAD_ID_RE.search(value)
    if match:
        return match.group(1)
    candidate = value.rsplit("/", 1)[-1].strip()
    if BARE_ID_RE.match(candidate):
        return candidate
    raise RedditError(f"Could not read a thread id out of {value!r}.")


class Cache:
    def __init__(self, enabled: bool, ttl_hours: int, directory: Path | None = None):
        self.enabled = enabled
        self.ttl = ttl_hours * 3600
        self.dir = directory or CACHE_DIR

    def _path(self, signature: str) -> Path:
        digest = hashlib.sha256(signature.encode("utf-8")).hexdigest()[:32]
        return self.dir / f"{digest}.json"

    def get(self, signature: str) -> Any | None:
        if not self.enabled:
            return None
        path = self._path(signature)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
        if time.time() - payload.get("cached_at", 0) > self.ttl:
            return None
        return payload.get("data")

    def put(self, signature: str, data: Any) -> None:
        if not self.enabled:
            return
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self._path(signature)
        try:
            path.write_text(
                json.dumps({"cached_at": time.time(), "signature": signature, "data": data}),
                encoding="utf-8",
            )
        except OSError:
            pass  # A cache write failure must never fail the command.

    def info(self) -> dict:
        if not self.dir.exists():
            return {"path": str(self.dir), "entries": 0, "bytes": 0}
        files = list(self.dir.glob("*.json"))
        return {
            "path": str(self.dir),
            "entries": len(files),
            "bytes": sum(f.stat().st_size for f in files),
        }

    def clear(self) -> int:
        if not self.dir.exists():
            return 0
        files = list(self.dir.glob("*.json"))
        for f in files:
            f.unlink(missing_ok=True)
        return len(files)


def walk_comments(forest: Any, depth: int = 0) -> Iterator[tuple[Any, int]]:
    """Depth-first walk yielding (comment, depth).

    Depth is computed here rather than read off the object, because a comment's own
    depth attribute is only populated in some access paths and a missing value would
    silently flatten the tree.
    """
    for item in forest:
        if not hasattr(item, "body"):
            continue  # an unexpanded MoreComments stub; replace_more should prevent this
        yield item, depth
        replies = getattr(item, "replies", None)
        if replies:
            yield from walk_comments(replies, depth + 1)


class Client:
    def __init__(self, config: Config):
        self.config = config
        self.cache = Cache(config.cache_enabled, config.cache_ttl_hours)
        self._reddit = None

    @property
    def reddit(self):
        if self._reddit is None:
            self.config.require_auth()
            try:
                import praw
            except ImportError as exc:  # pragma: no cover - install-time problem
                raise RedditError(
                    "praw is not installed. Run scripts/install.sh to build the venv."
                ) from exc
            self._reddit = praw.Reddit(
                client_id=self.config.client_id,
                client_secret=self.config.client_secret,
                refresh_token=self.config.refresh_token,
                user_agent=self.config.user_agent,
            )
            self._reddit.read_only = True
        return self._reddit

    def _cached(self, signature: str, produce, use_cache: bool = True):
        if use_cache:
            hit = self.cache.get(signature)
            if hit is not None:
                return hit
        data = produce()
        self.cache.put(signature, data)
        return data

    def thread(self, ref: str, *, comment_limit: int | None = None, use_cache: bool = True) -> Post:
        thread_id = parse_thread_id(ref)
        signature = f"thread:{thread_id}:{comment_limit}"

        def produce() -> dict:
            submission = self.reddit.submission(id=thread_id)
            try:
                submission.comments.replace_more(limit=None)
            except Exception as exc:  # PRAW raises a family of network errors here
                raise RedditError(f"Could not expand the comment tree: {exc}") from exc
            post = Post.from_praw(submission)
            collected = []
            for raw, depth in walk_comments(submission.comments):
                collected.append(Comment.from_praw(raw, depth))
                if comment_limit and len(collected) >= comment_limit:
                    break
            post.comments = collected
            return post.to_dict()

        return _post_from_dict(self._cached(signature, produce, use_cache))

    def search(
        self,
        query: str,
        *,
        subreddits: list[str] | None = None,
        sort: str = "relevance",
        time_filter: str = "all",
        limit: int = 25,
        use_cache: bool = True,
    ) -> list[Post]:
        target = "+".join(subreddits) if subreddits else "all"
        signature = f"search:{target}:{query}:{sort}:{time_filter}:{limit}"

        def produce() -> list[dict]:
            listing = self.reddit.subreddit(target).search(
                query, sort=sort, time_filter=time_filter, limit=limit
            )
            return [Post.from_praw(item).to_dict() for item in listing]

        return [_post_from_dict(d) for d in self._cached(signature, produce, use_cache)]

    def browse(
        self,
        subreddit: str,
        *,
        sort: str = "hot",
        time_filter: str = "day",
        limit: int = 25,
        use_cache: bool = True,
    ) -> list[Post]:
        signature = f"browse:{subreddit}:{sort}:{time_filter}:{limit}"

        def produce() -> list[dict]:
            sub = self.reddit.subreddit(subreddit)
            if sort in ("top", "controversial"):
                listing = getattr(sub, sort)(time_filter=time_filter, limit=limit)
            else:
                listing = getattr(sub, sort)(limit=limit)
            return [Post.from_praw(item).to_dict() for item in listing]

        return [_post_from_dict(d) for d in self._cached(signature, produce, use_cache)]

    def user(
        self,
        name: str,
        *,
        kind: str = "all",
        limit: int = 50,
        use_cache: bool = True,
    ) -> dict:
        signature = f"user:{name}:{kind}:{limit}"

        def produce() -> dict:
            redditor = self.reddit.redditor(name)
            out: dict = {"name": name, "submissions": [], "comments": []}
            if kind in ("all", "submissions"):
                out["submissions"] = [
                    Post.from_praw(s).to_dict() for s in redditor.submissions.new(limit=limit)
                ]
            if kind in ("all", "comments"):
                out["comments"] = [
                    Comment.from_praw(c, 0).to_dict() for c in redditor.comments.new(limit=limit)
                ]
            return out

        return self._cached(signature, produce, use_cache)

    # -- write path -------------------------------------------------------
    # Reached only after config.can_write() passes AND the command layer has
    # confirmed --i-am-sure. Both checks live outside this class on purpose.

    def _writable(self):
        allowed, reason = self.config.can_write()
        if not allowed:
            raise ConfigError(reason)
        reddit = self.reddit
        reddit.read_only = False
        return reddit

    def submit_post(self, subreddit: str, title: str, body: str) -> dict:
        submission = self._writable().subreddit(subreddit).submit(title=title, selftext=body)
        return Post.from_praw(submission).to_dict()

    def submit_comment(self, parent_id: str, body: str) -> dict:
        reddit = self._writable()
        parent = (
            reddit.comment(id=parent_id[3:])
            if parent_id.startswith("t1_")
            else reddit.submission(id=parse_thread_id(parent_id))
        )
        return Comment.from_praw(parent.reply(body), 0).to_dict()


def _post_from_dict(data: dict) -> Post:
    comments = [Comment(**c) for c in data.get("comments", [])]
    fields = {k: v for k, v in data.items() if k != "comments"}
    post = Post(**fields)
    post.comments = comments
    return post
