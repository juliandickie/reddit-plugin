"""Renderers. json for machines, markdown for reading, voc for the message map."""

from __future__ import annotations

import json
from typing import Any

from . import voc as voc_module
from .models import Post

FORMATS = ("json", "markdown", "voc")


def render(data: Any, fmt: str, **voc_kwargs) -> str:
    if fmt == "json":
        return _json(data)
    if fmt == "voc":
        return _json(_voc(data, **voc_kwargs))
    if fmt == "markdown":
        return _markdown(data)
    raise ValueError(f"Unknown format {fmt!r}. Choose from {', '.join(FORMATS)}.")


def _json(data: Any) -> str:
    def default(obj):
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        raise TypeError(f"not serializable: {type(obj)}")

    return json.dumps(data, indent=2, ensure_ascii=False, default=default)


def _voc(data: Any, **kwargs) -> dict:
    if isinstance(data, Post):
        return voc_module.shape(data, **kwargs)
    if isinstance(data, list) and data and isinstance(data[0], Post):
        return voc_module.shape_many(data, **kwargs)
    if isinstance(data, dict) and "comments" in data:
        # user history: wrap the loose comments in a synthetic source
        return {
            "sources": [{"kind": "reddit_user", "name": data.get("name")}],
            "records": [
                {
                    "id": c["id"],
                    "text": c["body"],
                    "permalink": c["permalink"],
                    "source_tag": f"Reddit u/{data.get('name')}",
                    "author": data.get("name"),
                    "score": c["score"],
                    "created": c["created"],
                    "umm": {"big_picture_tag": None, "granular_tag": None, "slot": None},
                }
                for c in data.get("comments", [])
            ],
            "umm_slots": voc_module.UMM_SLOTS,
            "audit": {
                "note": "User history is emitted unfiltered. No prefilter applied.",
                "considered": len(data.get("comments", [])),
                "kept": len(data.get("comments", [])),
                "dropped": {},
                "dropped_total": 0,
            },
        }
    raise ValueError("The voc format needs a thread, a list of threads, or user history.")


def _markdown(data: Any) -> str:
    if isinstance(data, Post):
        return _post_markdown(data)
    if isinstance(data, list):
        return "\n".join(_post_summary(p) for p in data)
    if isinstance(data, dict) and "name" in data:
        lines = [f"# u/{data['name']}", ""]
        if data.get("submissions"):
            lines += ["## Submissions", ""] + [_post_summary(_as_post(s)) for s in data["submissions"]]
        if data.get("comments"):
            lines += ["", "## Comments", ""]
            for c in data["comments"]:
                lines.append(f"**{c['score']} points** - {c['created']} - {c['permalink']}")
                lines.append("")
                lines.append(c["body"])
                lines.append("")
        return "\n".join(lines)
    return _json(data)


def _as_post(data: dict) -> Post:
    fields = {k: v for k, v in data.items() if k != "comments"}
    return Post(**fields)


def _post_summary(post: Post) -> str:
    sub = f"r/{post.subreddit}" if post.subreddit else ""
    return f"- **{post.title}** ({sub}, {post.score} points, {post.num_comments} comments)\n  {post.permalink}"


def _post_markdown(post: Post) -> str:
    lines = [
        f"# {post.title}",
        "",
        f"r/{post.subreddit} - u/{post.author} - {post.score} points "
        f"({post.num_comments} comments) - {post.created}",
        f"{post.permalink}",
        "",
    ]
    if post.selftext.strip():
        lines += [post.selftext, ""]
    lines += ["---", ""]
    for comment in post.comments:
        indent = "  " * comment.depth
        marker = " [OP]" if comment.is_submitter else ""
        lines.append(f"{indent}**u/{comment.author}**{marker} - {comment.score} points")
        for line in comment.body.splitlines() or [""]:
            lines.append(f"{indent}{line}")
        lines.append("")
    return "\n".join(lines)
