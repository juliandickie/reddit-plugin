# Reddit CLI and Plugin - Design

Date 2026-09-09. Status approved, building.

## Why

Every unauthenticated route to Reddit thread content is blocked from this machine
(verified 2026-09-09: MCP connector 403, both .json endpoints, Firecrawl refuses the
domain by policy, in-app browser blocked by policy). Reddit is the validation and
triangulation source in the `voc-research` methodology, sixth in its source priority.
The supported route is Reddit's own API, which is free at 100 requests per minute with
credentials the user controls.

The tool must be callable from a plain shell, from another plugin's script, and from
any Claude session, without loading anything into context until it is used.

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Surface | CLI on PATH plus a thin skill. No MCP server | Callable from anywhere, costs zero context until invoked |
| Language | Python with PRAW | `replace_more()` solves comment-tree expansion, the one part that fails silently if hand-rolled |
| Auth | OAuth refresh token, not password grant | The Reddit password never touches disk; the token is revocable without a password change |
| Callback port | 8250 | Port 8000 is contended by Scribe OAuth in parallel sessions |
| Credentials | `~/.config/reddit-plugin/config.toml`, optional `op://` ref | Matches vimeo and spiffy; avoids `op read` hanging on approval |
| Write access | Present, gated three ways | User's explicit call, overriding a read-only recommendation |

## Write Safety

Write is gated at three independent layers, all of which must be open:

1. **Token scope.** `reddit auth` requests read-only scopes. Write scopes are granted
   only by `reddit auth --with-write`, a separate deliberate authorisation.
2. **Config.** `allow_write` defaults to `false` in `config.toml`.
3. **Per-call flag.** `--i-am-sure` is required on every write invocation and is never
   implied by any other flag.

A missing layer produces a refusal naming which layer is closed, not a generic error.

## Layout

```
reddit_cli/
  config.py      load config.toml, env overrides, optional op:// resolution
  auth.py        OAuth flow, local callback listener, token storage
  client.py      PRAW wrapper, rate limiting, disk cache
  models.py      normalized Post and Comment records
  formats.py     json / markdown / voc renderers
  voc.py         UMM shaping and the mechanical prefilter
  cli.py         argparse dispatch and the command handlers
bin/reddit       PATH wrapper, execs the venv interpreter
skills/reddit/   thin skill teaching the commands
tests/           fixture-based, no network
```

## Commands

| Command | Purpose |
|---|---|
| `reddit auth [--with-write]` | One-time browser authorisation, stores refresh token |
| `reddit search QUERY [--sub a,b]` | Search Reddit-wide or within named subreddits |
| `reddit thread URL_OR_ID` | Post plus fully expanded comment tree |
| `reddit browse SUB` | hot, new, top, rising, controversial over a time window |
| `reddit user NAME` | Post and comment history |
| `reddit post SUB --title --text --i-am-sure` | Write, triple-gated |
| `reddit comment PARENT --text --i-am-sure` | Write, triple-gated |
| `reddit doctor` | Diagnose config, auth, scopes, rate limit, cache |
| `reddit cache info\|clear` | Inspect and clear the disk cache |

Global flags: `--format json\|markdown\|voc` (default json), `--limit`, `--no-cache`.

## The VOC Format, and What It Honestly Does

The `voc` renderer emits one record per comment shaped for the Ultimate Message Map,
carrying the verbatim text plus everything needed to judge and trace it: permalink,
author, score, created date, thread title, thread permalink, and depth.

**Text is never modified.** Not trimmed for polish, not summarized, not cleaned up.
`references/06-filtering-and-processing.md` names paraphrasing a captured line as the
common way strong VOC is destroyed, so the renderer only ever copies.

**The sticky-VOC filter is not implemented and must not be claimed.** That filter is an
eyes-closed judgement about whether a line creates a picture and could not have been
invented at a desk. Code cannot make that call. What the CLI does instead is a
**mechanical prefilter** that removes only unambiguous noise:

- deleted or removed bodies
- bot and AutoModerator authors
- bodies under a minimum length (default 80 characters, `--min-length` to change)
- exact duplicates within the pull

Every dropped record is counted by reason and reported in an `audit` block. Nothing is
silently discarded, and `--keep-all` disables the prefilter entirely. Tagging against
the UMM taxonomy and the sticky call are left to Claude via the skill.

Each record carries an empty `umm` block with `big_picture_tag`, `granular_tag`, and
`candidate_slots` for the skill to fill, so the CLI never guesses at classification it
has no basis for.

## Caching

Responses cache to `~/.config/reddit-plugin/cache/` keyed by request signature, default
TTL 24 hours, `--no-cache` to bypass. Re-running a VOC pass over a captured thread
costs nothing and does not re-spend rate limit, which matters because analysis usually
runs several times over the same corpus.

## Testing

Fixture-based against recorded API payloads, no network in the suite. Coverage focuses
on comment-tree flattening including `more` stubs, the prefilter's audit accounting,
the three-layer write gate, and config resolution precedence. One live smoke test is
run manually after the user registers the Reddit app.

## Out of Scope

No MCP server. No scheduled or unattended runs in v1. No multi-account support. No
Apify or third-party scraping fallback: the official API is the sanctioned route and a
fallback that scrapes against a block would undercut the reason for using the API.
