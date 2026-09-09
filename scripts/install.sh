#!/usr/bin/env bash
# Build the dedicated venv and put `reddit` on PATH.
# Idempotent: safe to re-run after pulling changes.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="${REDDIT_PLUGIN_VENV:-$HOME/.local/share/reddit-plugin/venv}"
BINDIR="${REDDIT_PLUGIN_BIN:-$HOME/.local/bin}"
PYTHON="${PYTHON:-python3}"

echo "repo:  $REPO"
echo "venv:  $VENV"
echo "bin:   $BINDIR/reddit"
echo

if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating venv..."
  "$PYTHON" -m venv "$VENV"
fi

"$VENV/bin/python" -m pip install --quiet --upgrade pip
"$VENV/bin/python" -m pip install --quiet -e "$REPO"

mkdir -p "$BINDIR"
ln -sf "$REPO/bin/reddit" "$BINDIR/reddit"

echo "Installed. Verifying..."
"$BINDIR/reddit" --version

case ":$PATH:" in
  *":$BINDIR:"*) ;;
  *) echo; echo "NOTE: $BINDIR is not on your PATH. Add it to use \`reddit\` directly." ;;
esac

echo
echo "Next: register a Reddit app, then run \`reddit doctor\`."
