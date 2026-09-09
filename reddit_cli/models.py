"""Normalized records.

PRAW objects are lazy and network-backed. Everything crossing out of client.py is
converted to these plain dataclasses first, so formatters and tests never trigger a
surprise HTTP call by touching an attribute.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

REDDIT_BASE = "https://www.reddit.com"


def _iso(created_utc: float | None) -> str | None:
    if created_utc is None:
        return None
    return datetime.fromtimestamp(float(created_utc), tz=timezone.utc).isoformat()


def _permalink(path: str | None) -> str | None:
    if not path:
        return None
    return path if path.startswith("http") else f"{REDDIT_BASE}{path}"


@dataclass
class Comment:
    id: str
    author: str | None
    body: str
    score: int
    created: str | None
    permalink: str | None
    depth: int
    parent_id: str | None
    is_submitter: bool = False
    edited: bool = False

    @classmethod
    def from_praw(cls, raw, depth: int) -> "Comment":
        return cls(
            id=getattr(raw, "id", ""),
            author=str(raw.author) if getattr(raw, "author", None) else None,
            body=getattr(raw, "body", "") or "",
            score=int(getattr(raw, "score", 0) or 0),
            created=_iso(getattr(raw, "created_utc", None)),
            permalink=_permalink(getattr(raw, "permalink", None)),
            depth=depth,
            parent_id=getattr(raw, "parent_id", None),
            is_submitter=bool(getattr(raw, "is_submitter", False)),
            edited=bool(getattr(raw, "edited", False)),
        )

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Post:
    id: str
    title: str
    author: str | None
    subreddit: str | None
    selftext: str
    score: int
    upvote_ratio: float | None
    num_comments: int
    created: str | None
    permalink: str | None
    url: str | None
    link_flair: str | None = None
    over_18: bool = False
    comments: list[Comment] = field(default_factory=list)

    @classmethod
    def from_praw(cls, raw) -> "Post":
        return cls(
            id=getattr(raw, "id", ""),
            title=getattr(raw, "title", "") or "",
            author=str(raw.author) if getattr(raw, "author", None) else None,
            subreddit=str(raw.subreddit) if getattr(raw, "subreddit", None) else None,
            selftext=getattr(raw, "selftext", "") or "",
            score=int(getattr(raw, "score", 0) or 0),
            upvote_ratio=getattr(raw, "upvote_ratio", None),
            num_comments=int(getattr(raw, "num_comments", 0) or 0),
            created=_iso(getattr(raw, "created_utc", None)),
            permalink=_permalink(getattr(raw, "permalink", None)),
            url=getattr(raw, "url", None),
            link_flair=getattr(raw, "link_flair_text", None),
            over_18=bool(getattr(raw, "over_18", False)),
        )

    def to_dict(self) -> dict:
        data = asdict(self)
        data["comments"] = [c.to_dict() for c in self.comments]
        return data
