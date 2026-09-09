"""VOC shaping for the Ultimate Message Map.

Two rules govern this module, both taken from the voc-research skill:

1. Verbatim only. `references/06-filtering-and-processing.md` names paraphrasing a
   captured line as the common way strong VOC is destroyed. Nothing here rewrites,
   trims, summarizes or "cleans up" a body. It copies.

2. The sticky-VOC filter is NOT implemented here and must not be claimed. That filter
   is an eyes-closed judgement about whether a line creates a picture and could not
   have been invented at a writing desk. Code cannot make that call. What follows is
   a mechanical prefilter that removes unambiguous noise only, and it reports every
   drop so nothing disappears silently.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .models import Comment, Post

DEFAULT_MIN_LENGTH = 80

# Authors that are never a human prospect.
BOT_AUTHORS = {"automoderator", "[deleted]", "reddit", "botdefense", "repostsleuthbot"}
BOT_SUFFIXES = ("bot", "_bot", "-bot")

# Bodies Reddit returns for content that no longer exists.
TOMBSTONES = {"[deleted]", "[removed]", ""}

# Every slot in the Ultimate Message Map a Reddit comment could plausibly land in.
# Offered to the skill as candidates; the CLI never picks one.
UMM_SLOTS = [
    "Problems and Motivators",
    "Failed Solutions",
    "Desired Outcome / Dream State",
    "Switching / Habits of the Now",
    "Switching / Worries of the New",
    "Switching / Pushes of the Now",
    "Switching / Pulls of the New",
    "Beliefs and Conversion Precursors",
    "Purchase Criteria",
    "Decision Constraints",
    "Direct Competition - Likes",
    "Direct Competition - Dislikes",
    "All Known Jobs - Functional",
    "All Known Jobs - Personal Emotional",
    "All Known Jobs - Personal Social",
]


@dataclass
class Audit:
    """Accounting for the prefilter. Every input lands in exactly one bucket."""

    considered: int = 0
    kept: int = 0
    dropped: dict[str, int] = field(default_factory=dict)

    def drop(self, reason: str) -> None:
        self.dropped[reason] = self.dropped.get(reason, 0) + 1

    def to_dict(self) -> dict:
        return {
            "considered": self.considered,
            "kept": self.kept,
            "dropped": dict(sorted(self.dropped.items())),
            "dropped_total": sum(self.dropped.values()),
            "note": (
                "Mechanical prefilter only. The sticky-VOC filter is an eyes-closed "
                "human judgement and has NOT been applied. Re-run with --keep-all to "
                "see every dropped record."
            ),
        }


def _is_bot(author: str | None) -> bool:
    if not author:
        return True
    lowered = author.lower()
    return lowered in BOT_AUTHORS or lowered.endswith(BOT_SUFFIXES)


def _drop_reason(comment: Comment, min_length: int, seen: set[str]) -> str | None:
    body = comment.body.strip()
    if body.lower() in TOMBSTONES:
        return "deleted_or_removed"
    if _is_bot(comment.author):
        return "bot_or_automod"
    if len(body) < min_length:
        return "below_min_length"
    if body in seen:
        return "duplicate"
    return None


def shape(
    post: Post,
    *,
    min_length: int = DEFAULT_MIN_LENGTH,
    keep_all: bool = False,
) -> dict:
    """Turn one post and its comments into UMM-shaped VOC records plus an audit."""
    audit = Audit()
    seen: set[str] = set()
    records: list[dict] = []

    source_tag = f"Reddit r/{post.subreddit}" if post.subreddit else "Reddit"

    for comment in post.comments:
        audit.considered += 1
        reason = _drop_reason(comment, min_length, seen)
        if reason and not keep_all:
            audit.drop(reason)
            continue
        seen.add(comment.body.strip())
        audit.kept += 1
        records.append(
            {
                "id": comment.id,
                "text": comment.body,  # verbatim, never modified
                "permalink": comment.permalink,
                "source_tag": source_tag,
                "author": comment.author,
                "score": comment.score,
                "created": comment.created,
                "depth": comment.depth,
                "is_op": comment.is_submitter,
                "thread": {
                    "title": post.title,
                    "permalink": post.permalink,
                    "subreddit": post.subreddit,
                },
                # Slots are listed once at the top level, not repeated per record:
                # a 200-comment thread would otherwise carry 3,000 redundant strings
                # into whatever context reads this.
                "umm": {"big_picture_tag": None, "granular_tag": None, "slot": None},
                "prefilter": {"kept": True, "reason": reason} if keep_all and reason else {"kept": True},
            }
        )

    return {
        "source": {
            "kind": "reddit_thread",
            "title": post.title,
            "permalink": post.permalink,
            "subreddit": post.subreddit,
            "score": post.score,
            "num_comments": post.num_comments,
            "created": post.created,
        },
        "records": records,
        "umm_slots": UMM_SLOTS,
        "audit": audit.to_dict(),
        "next_step": (
            "Apply the sticky-VOC filter from voc-research "
            "references/06-filtering-and-processing.md to these records, then tag "
            "each keeper against the Tag Manager and file it into the Ultimate "
            "Message Map. Expect roughly 3 to 4 sticky lines per 100 records."
        ),
    }


def shape_many(posts: list[Post], **kwargs) -> dict:
    """Combine several threads into one VOC payload with a merged audit."""
    shaped = [shape(p, **kwargs) for p in posts]
    merged = Audit()
    for item in shaped:
        a = item["audit"]
        merged.considered += a["considered"]
        merged.kept += a["kept"]
        for reason, count in a["dropped"].items():
            merged.dropped[reason] = merged.dropped.get(reason, 0) + count
    return {
        "sources": [item["source"] for item in shaped],
        "records": [r for item in shaped for r in item["records"]],
        "umm_slots": UMM_SLOTS,
        "audit": merged.to_dict(),
        "next_step": shaped[0]["next_step"] if shaped else "",
    }
