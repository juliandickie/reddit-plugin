# reddit-plugin

Read Reddit through the official API, from a CLI any session, script, or plugin can
call. Built for voice-of-customer research, where Reddit is a triangulation source.

No MCP server by design: nothing loads into a session's context until a command runs.

## Why this exists

Every unauthenticated route to Reddit thread content is blocked from this machine
(verified 2026-09-09: the Reddit MCP connector returns 403, both `.json` endpoints are
blocked, Firecrawl refuses the domain by policy, the in-app browser blocks it by
policy). Reddit's own API is free, supported, and allows 100 requests a minute with
credentials you control, so that is what this uses.

## Install

As a Claude Code plugin, from either of Julian's catalogs:

```
/plugin marketplace add juliandickie/outfit
/plugin install reddit@outfit
```

Or straight from the repo, which is also how the plugin's own scripts set up the CLI:

```bash
bash scripts/install.sh
```

Creates a venv at `~/.local/share/reddit-plugin/venv`, installs the package, and links
`reddit` into `~/.local/bin`. Re-run it after pulling changes. Idempotent.

## Set up credentials

1. Go to https://www.reddit.com/prefs/apps and create an app.
2. Choose type **web app**.
3. Set the redirect URI to exactly `http://localhost:8250/callback`.
4. Copy the client id (under the app name) and the secret into
   `~/.config/reddit-plugin/config.toml`:

```toml
[reddit]
client_id = "..."
client_secret = "..."
allow_write = false
```

5. Authorise once:

```bash
reddit auth
```

A browser opens, you approve, and a refresh token is written back to the config. Your
Reddit password is never stored. Revoke access any time from Reddit's app settings
without changing your password.

`reddit doctor` tells you exactly what is missing at any point.

## Use

```bash
reddit search "intraoral scanner worth it" --sub Dentistry --limit 25
reddit thread <url> --format markdown
reddit browse Dentistry --sort top --time month
reddit user <name> --kind comments
reddit doctor
reddit cache info | reddit cache clear
```

Formats: `json` (default, for scripts), `markdown` (for reading), `voc` (for research
capture). Results cache for 24 hours; `--no-cache` bypasses it.

## The voc format

Emits one record per comment shaped for the Ultimate Message Map, carrying the
verbatim text plus permalink, author, score, date, thread and depth.

**It does not apply the sticky-VOC filter.** That filter is an eyes-closed human
judgement and code cannot make it. The CLI removes unambiguous noise only: deleted
bodies, bots, comments under 80 characters, exact duplicates. Every drop is counted by
reason in an `audit` block, `--keep-all` disables the prefilter, `--min-length`
changes the threshold. Applying the real filter is the reader's job, using the
`voc-research` skill.

Text is copied, never rewritten. Paraphrasing a captured line is how strong VOC gets
destroyed.

## Writing

`reddit post` and `reddit comment` exist and are gated three independent ways, all of
which must be open:

1. the token must carry write scopes, granted only by `reddit auth --with-write`
2. `allow_write = true` must be set in config
3. `--i-am-sure` must be passed on every call

The default state is read-only on all three. The gates prevent an accident; they are
not a substitute for asking a human first.

## Development

```bash
~/.local/share/reddit-plugin/venv/bin/python -m unittest discover -s tests
```

27 tests, no network. Coverage concentrates on comment-tree walking (the piece that
fails silently if wrong), prefilter audit accounting, the write gate, and config
precedence.

Design record: `docs/superpowers/specs/2026-09-09-reddit-cli-design.md`.

## Conduct

Uses the sanctioned API at its published rate limit. No scraping fallback, no proxy
workaround, nothing that defeats a block. A private subreddit or a removed thread is
an answer, not an obstacle to route around.
