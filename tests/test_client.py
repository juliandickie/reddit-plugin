"""Comment-tree walking and thread-id parsing.

Tree walking is the piece that fails silently if it is wrong, so it is tested against
a hand-built nested forest rather than trusting PRAW's own depth attribute.
"""

import unittest

from reddit_cli.client import parse_thread_id, walk_comments
from reddit_cli.client import RedditError


class Fake:
    """Duck-types enough of a PRAW comment for the walker."""

    def __init__(self, cid, body="text", replies=None):
        self.id = cid
        self.body = body
        self.replies = replies or []


class Stub:
    """A MoreComments stub: no body attribute."""

    def __init__(self):
        self.count = 5


class TestWalk(unittest.TestCase):
    def test_depth_is_computed_from_structure(self):
        forest = [
            Fake("a", replies=[Fake("b", replies=[Fake("c")])]),
            Fake("d"),
        ]
        walked = [(c.id, depth) for c, depth in walk_comments(forest)]
        self.assertEqual(walked, [("a", 0), ("b", 1), ("c", 2), ("d", 0)])

    def test_unexpanded_stubs_are_skipped_not_crashed_on(self):
        forest = [Fake("a"), Stub(), Fake("b")]
        walked = [c.id for c, _ in walk_comments(forest)]
        self.assertEqual(walked, ["a", "b"])

    def test_deep_nesting_is_not_truncated(self):
        node = Fake("leaf")
        for i in range(30):
            node = Fake(f"n{i}", replies=[node])
        walked = list(walk_comments([node]))
        self.assertEqual(len(walked), 31)
        self.assertEqual(walked[-1][1], 30)


class TestThreadId(unittest.TestCase):
    def test_full_url(self):
        url = "https://www.reddit.com/r/Dentistry/comments/18asj3l/is_a_scanner_worth_it/"
        self.assertEqual(parse_thread_id(url), "18asj3l")

    def test_url_without_slug(self):
        self.assertEqual(parse_thread_id("https://redd.it/comments/abc123"), "abc123")

    def test_bare_id(self):
        self.assertEqual(parse_thread_id("18asj3l"), "18asj3l")

    def test_garbage_is_refused(self):
        with self.assertRaises(RedditError):
            parse_thread_id("https://example.com/not/a/thread/!!")


if __name__ == "__main__":
    unittest.main()
