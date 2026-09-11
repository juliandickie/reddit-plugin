# reddit-plugin - working notes

A CLI that reads Reddit through the official API. Read `README.md` for usage and
`docs/superpowers/specs/2026-09-09-reddit-cli-design.md` for why it is shaped this way.
Session state and open work live in the sibling repo:
`~/code/youtube-plugin/SESSION-HANDOFF-2026-09-10.md`.

**STATUS 2026-09-11: complete but unusable, access request drafted, not yet filed.**
Reddit's Responsible Builder Policy gates app creation behind an approval ticket, and
the create-app form silently reloads rather than erroring. Every read command correctly
refuses with a pointer to `reddit doctor`. Nothing to fix in code.

The ticket text is ready at `docs/reddit-api-access-request-2026-09-11.md`, with the
live form's three tracks mapped and the policy lines that matter quoted. Julian chose
the developer track with honest answers (a business uses it, read-only, small volume).
When he files it, record the ticket number and date here. Do not draft a second
ticket for the same use case; the policy names duplicates as a breach.

## Rules specific to this repo

**Never add a scraping fallback.** The whole reason this exists is that scraping
routes to Reddit are blocked, and the API is the sanctioned answer. A proxy hack, a
headless browser fallback, or an Apify actor bolted on when the API 403s would undo
the design. A block is an answer.

**Never let the `voc` format claim to apply the sticky-VOC filter.** It applies a
mechanical prefilter and nothing more. The distinction is load-bearing: overstating it
would have a researcher trust an unfiltered pull. The audit note in `voc.py` says so
explicitly and a test asserts the wording.

**Never modify captured text.** `voc.py` copies bodies verbatim. No trimming for
polish, no summarizing, no whitespace cleanup. Paraphrase is how strong VOC dies.

**The write gate has three independent layers and they live in three files on
purpose** (`auth.py` scopes, `config.py` allow_write, `cli.py` the flag). Do not
consolidate them into one check for tidiness; the separation is the safety property.

## Testing

```bash
~/.local/share/reddit-plugin/venv/bin/python -m unittest discover -s tests
```

No network in the suite. If a change touches comment-tree walking, add a case to
`tests/test_client.py` with a deeper or more awkward forest first. That code path
fails silently rather than loudly, so tests are the only thing standing between a bug
and a quietly truncated research corpus.

## Gotchas

- `reddit search --format voc` re-fetches every hit as a full thread, so a limit of 25
  becomes 26 API calls. Cached, but slow on first run.
- Config is rewritten wholesale by `save_tokens`, not appended, because a duplicated
  TOML key is a parse error that would brick the file on a second `reddit auth`.
- `op read` can hang waiting on approval, which is why a 1Password reference is only
  consulted when the direct value is absent, and why it has a 20 second timeout and
  degrades to "not found" rather than raising.
