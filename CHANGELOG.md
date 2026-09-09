# Changelog

## 0.1.0 - 2026-09-09

Initial build.

- `reddit` CLI on PATH: `search`, `thread`, `browse`, `user`, `post`, `comment`,
  `auth`, `doctor`, `cache`.
- OAuth refresh-token flow on port 8250, chosen over Reddit's password grant so the
  account password never reaches disk. Port 8250 rather than 8000 because 8000 is
  contended by Scribe's OAuth callback in parallel sessions.
- Full comment-tree expansion via PRAW `replace_more`, with depth computed by walking
  the tree rather than read off the object, since that attribute is not always
  populated and a missing value would silently flatten the thread.
- Three output formats: `json`, `markdown`, `voc`.
- `voc` shapes records for the Ultimate Message Map. Mechanical prefilter only, with a
  per-reason audit of every drop. The sticky-VOC filter is deliberately not
  implemented, because it is an eyes-closed human judgement.
- UMM slot legend emitted once per payload rather than per record, which cut a
  200-comment payload to roughly a third of its first size.
- Write gated three independent ways: token scope, config flag, per-call flag.
- 24-hour disk cache keyed by request signature.
- 27 tests, no network.
