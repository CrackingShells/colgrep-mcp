#!/bin/sh
# Launcher for the colgrep MCP server, shared by every plugin manifest.
#
# Why a script: plugin ecosystems expand only their own placeholders
# (${CLAUDE_PLUGIN_ROOT}, ${PLUGIN_ROOT}, ...) inside mcp.json, never $HOME or
# $PATH. GUI-launched clients often start with a minimal PATH that lacks uv and
# colgrep, so this script rebuilds a sane PATH from the invoking user's home
# and then hands over to `uv run`, which creates/syncs the server's virtualenv.
#
# Environment honoured:
#   UV_PROJECT_ENVIRONMENT  where uv keeps the venv (plugins point it at their data dir)
#   COLGREP_MCP_*           passed through untouched to the server
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(dirname -- "$here")

PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:${PATH:-/usr/bin:/bin}"
export PATH

if ! command -v uv >/dev/null 2>&1; then
  echo "colgrep-mcp: 'uv' not found on PATH ($PATH). Install: https://docs.astral.sh/uv/" >&2
  exit 127
fi

exec uv run --quiet --directory "$root/server" colgrep-mcp "$@"
