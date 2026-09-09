"""The prefilter must account for every record and must never alter text."""

import unittest

from reddit_cli.models import Comment, Post
from reddit_cli.voc import DEFAULT_MIN_LENGTH, shape, shape_many

LONG = "I bought the scanner in March and the interproximal contacts were a nightmare for weeks."
assert len(LONG) >= DEFAULT_MIN_LENGTH


def comment(body, cid="c1", author="dentist", depth=0, score=1):
    return Comment(
        id=cid, author=author, body=body, score=score, created="2026-01-01T00:00:00+00:00",
        permalink=f"https://www.reddit.com/comments/x/_/{cid}", depth=depth, parent_id="t3_x",
    )


def post(comments):
    p = Post(
        id="x", title="Is a scanner worth it", author="op", subreddit="Dentistry", selftext="",
        score=10, upvote_ratio=0.9, num_comments=len(comments),
        created="2026-01-01T00:00:00+00:00",
        permalink="https://www.reddit.com/r/Dentistry/comments/x/", url=None,
    )
    p.comments = comments
    return p


class TestPrefilter(unittest.TestCase):
    def test_audit_accounts_for_every_record(self):
        comments = [
            comment(LONG, "keep1"),
            comment("Great video", "short"),
            comment("[deleted]", "gone"),
            comment(LONG, "dupe"),
            comment(LONG, "bot1", author="AutoModerator"),
        ]
        out = shape(post(comments))
        audit = out["audit"]
        self.assertEqual(audit["considered"], 5)
        self.assertEqual(audit["kept"] + audit["dropped_total"], audit["considered"])
        self.assertEqual(audit["kept"], 1)
        self.assertEqual(audit["dropped"]["below_min_length"], 1)
        self.assertEqual(audit["dropped"]["deleted_or_removed"], 1)
        self.assertEqual(audit["dropped"]["duplicate"], 1)
        self.assertEqual(audit["dropped"]["bot_or_automod"], 1)

    def test_text_is_never_modified(self):
        messy = "  I said:   'it never fits'\n\nand nobody listened.  " + "x" * 80
        out = shape(post([comment(messy)]))
        self.assertEqual(out["records"][0]["text"], messy)

    def test_keep_all_disables_the_filter(self):
        comments = [comment(LONG, "a"), comment("no", "b"), comment("[removed]", "c")]
        out = shape(post(comments), keep_all=True)
        self.assertEqual(len(out["records"]), 3)
        self.assertEqual(out["audit"]["dropped_total"], 0)
        # the reason is still surfaced so the caller can see what would have gone
        self.assertEqual(out["records"][1]["prefilter"]["reason"], "below_min_length")

    def test_bot_suffix_authors_are_dropped(self):
        out = shape(post([comment(LONG, "a", author="helpful_bot")]))
        self.assertEqual(out["audit"]["dropped"]["bot_or_automod"], 1)

    def test_min_length_is_configurable(self):
        out = shape(post([comment("short but wanted", "a")]), min_length=5)
        self.assertEqual(out["audit"]["kept"], 1)

    def test_never_claims_the_sticky_filter(self):
        out = shape(post([comment(LONG)]))
        self.assertIn("has NOT been applied", out["audit"]["note"])

    def test_records_carry_provenance(self):
        record = shape(post([comment(LONG)]))["records"][0]
        self.assertTrue(record["permalink"])
        self.assertEqual(record["source_tag"], "Reddit r/Dentistry")
        self.assertEqual(record["thread"]["permalink"], "https://www.reddit.com/r/Dentistry/comments/x/")
        self.assertIsNone(record["umm"]["granular_tag"])

    def test_slot_legend_is_listed_once_not_per_record(self):
        many = [comment(LONG + str(i), f"c{i}") for i in range(20)]
        out = shape(post(many))
        self.assertEqual(len(out["records"]), 20)
        self.assertIn("umm_slots", out)
        for record in out["records"]:
            self.assertNotIn("candidate_slots", record["umm"])

    def test_shape_many_merges_audits(self):
        out = shape_many([post([comment(LONG, "a")]), post([comment("no", "b")])])
        self.assertEqual(out["audit"]["considered"], 2)
        self.assertEqual(out["audit"]["kept"], 1)
        self.assertEqual(len(out["sources"]), 2)


if __name__ == "__main__":
    unittest.main()
