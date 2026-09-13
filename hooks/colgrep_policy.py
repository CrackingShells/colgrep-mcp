#!/usr/bin/env python3
"""The colgrep-mcp plugin's hooks, in one script dispatched on `hook_event_name`.

Runs under whatever interpreter `uv run --no-project python` resolves, so
it is stdlib-only and Python >= 3.8 syntax; it must cost a bare interpreter
start and nothing more, because the `PreToolUse` branch runs on every Bash
call (harness_wiring R01 §C3: `uv run` 0.09 s vs `uvx colgrep-mcp` 0.68 s).

Events (R01 §C4):
  SessionStart, SubagentStart  -> a short search policy as `additionalContext`
  PreToolUse Grep|Bash         -> deny the built-in Grep tool and shell corpus
                                  searches, naming the MCP tools to call instead
  WorktreeRemove               -> `colgrep clear` a removed worktree's own index

Every branch fails open: unparsable stdin, an unknown event, a missing
colgrep binary or any exception exits 0 with no output. The deny is the
JSON `permissionDecision` form because Claude Code, Codex and Cursor all
carry its reason to the model; exit code 2 would reach the model on only
two of the three (R01 D3).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

# --- SessionStart / SubagentStart --------------------------------------------

#: Under 2 000 characters (R01 §C4): Codex truncates `additionalContext` at
#: about 2 500 tokens per handler, and the *how* already lives in the
#: server's instructions, tool descriptions and `colgrep://guide`; this text
#: carries only the rule, the tool names and the escape hatch.
POLICY = """\
SEARCH POLICY (colgrep-mcp plugin hook)

Denied in this session: the built-in Grep tool, and shell CORPUS searches
(grep -r, rg, find -exec grep, xargs grep). Nothing else is blocked.

Search a corpus with the colgrep MCP server instead: `search` (a
natural-language `query`; add `pattern` when you know an identifier, omit
`limit` for every match), `find_files` for a file list, then `expand` on
the hit_ids that matter instead of opening whole files. If the tool list
is deferred, look up the `colgrep` server before your first search. Read
the `colgrep://guide` resource once before a non-trivial query.

Still allowed -- reach for these when they fit:
  a known file's contents      -> read it
  files by name                -> the file-glob tool (colgrep cannot)
  one pattern in ONE file      -> plain grep, it is not blocked
  filter a command's output    -> cmd | grep, it is not blocked
Prefix COLGREP_BYPASS=1 only to a shell command that would otherwise be
denied and that colgrep cannot serve (extensionless or lock files, grep -rv).
"""

# --- PreToolUse deny messages ------------------------------------------------

GREP_TOOL_DENIED = (
    "The built-in Grep tool is disabled by the colgrep-mcp plugin. Call the colgrep MCP "
    "server's `search` tool (natural-language `query`; add `pattern` for an identifier you "
    "know) or `find_files` for a file list, then `expand` the hits that matter. Looking files "
    "up by name is not blocked."
)

BASH_DENIED = (
    "Shell corpus search (grep -r / rg / find -exec grep / xargs grep) is disabled by the "
    "colgrep-mcp plugin. Call the colgrep MCP server's `search` tool with `pattern` set to "
    "the text you were grepping for and `query` describing what you want; omit `limit` to get "
    "every match, or `find_files` for the file list. To count or extract matches, run the "
    "search and post-process its structured hits. For files colgrep cannot index "
    "(extensionless or lock files) or an inverted match, prefix the command with "
    "COLGREP_BYPASS=1 and retry."
)

# --- corpus-search detection (carried verbatim from the machine hook, R01 §C5)

XARGS_GREP = re.compile(r"\bxargs\s+(grep|rg|egrep|fgrep)\b")
FIND_EXEC = re.compile(r"\bfind\b.*-exec\s+(grep|rg|egrep|fgrep)\b")
RG_CMD = re.compile(r"(?<![a-zA-Z0-9_])rg\b")
RG_FILES = re.compile(r"\brg\s+(--files|-l)\b")
GREP_CMD = re.compile(r"\b(grep|egrep|fgrep)\b")
# A flag is a dash *after whitespace*: the machine hook's `-[a-zA-Z]*[rR]`
# also matched the `-patterns` inside `grep -n "Anti-patterns" file.md` and
# denied a single-file grep (found while writing these hooks; pinned by tests).
RECURSIVE = re.compile(r"\b(grep|egrep|fgrep)\b[^\n|;&]*\s-{1,2}[a-zA-Z]*[rR]")
# -c (count), -v (invert), -o (only-matching): colgrep has no equivalent, so a
# single-file use of them passes; combined with -r it is still a corpus search.
ALLOW_FLAGS = re.compile(r"\b(grep|egrep|fgrep)\b[^\n|;&]*\s-{1,2}[a-zA-Z]*[cvo]")
PATH_TOKEN = re.compile(r"(?<![\w=])(?:~/|\.{1,2}/|/)[^\s'\"|;&<>]*")


def is_pipe_grep(cmd: str) -> bool:
    """True when grep/rg appears only after a pipe: stream filtering, not a corpus search."""
    segments = re.split(r"(?<!\|)\|(?!\|)", cmd)
    if len(segments) < 2:
        return False
    if GREP_CMD.search(segments[0]) or RG_CMD.search(segments[0]):
        return False
    return any(GREP_CMD.search(s) or RG_CMD.search(s) for s in segments[1:])


def is_corpus_search(cmd: str) -> bool:
    """Does this shell command search a corpus in a way colgrep replaces?"""
    if "COLGREP_BYPASS=1" in cmd:
        return False
    if XARGS_GREP.search(cmd) or FIND_EXEC.search(cmd):
        return True
    # Stream filtering of another command's output is never a corpus search,
    # for rg as much as for grep (the machine hook checked this only for grep,
    # so `cmd | rg pat` used to be denied; the tests pin the fix).
    if is_pipe_grep(cmd):
        return False
    if RG_CMD.search(cmd):
        # `rg --files` / `rg -l` with no pattern enumerates files: allowed.
        if RG_FILES.search(cmd) and not re.search(r"\brg\b\s+[\"']", cmd):
            return False
        return True
    if GREP_CMD.search(cmd):
        if ALLOW_FLAGS.search(cmd) and not RECURSIVE.search(cmd):
            return False
        return bool(RECURSIVE.search(cmd))
    return False


# --- source-corpus gate ---------------------------------------------------------
# colgrep serves authored material (code, docs, drafts), not application state.
# Denying grep at a target like ~/.claude or ~/Library would leave a semantic
# index build over cached third-party files as the only compliant route, which
# is worse than the grep it replaces. Convention-based so it needs no list:
# a git work tree is always a corpus; otherwise only a non-hidden path under
# the home directory is.


def in_work_tree(path: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return r.stdout.strip() == "true"
    except (subprocess.SubprocessError, OSError):
        return False


def is_source_corpus(path: str) -> bool:
    if in_work_tree(path):
        return True
    home = os.path.realpath(os.path.expanduser("~"))
    if path != home and not path.startswith(home + os.sep):
        return False
    if path.startswith(os.path.join(home, "Library")):
        return False
    inner = path[len(home) :]
    return not any(part.startswith(".") for part in inner.split(os.sep) if part)


def resolve_targets(cmd: str, cwd: str) -> list:
    """The paths a command searches; the cwd when it names none."""
    toks = [t for t in PATH_TOKEN.findall(cmd) if t != "/"]
    base = cwd or os.getcwd()
    if not toks:
        return [os.path.realpath(base)]
    return [os.path.realpath(os.path.join(base, os.path.expanduser(t))) for t in toks]


def serves_corpus(cmd: str, cwd: str) -> bool:
    """False when any target is application state: fails open by design."""
    return all(is_source_corpus(p) for p in resolve_targets(cmd, cwd))


def decide_bash(cmd: str, cwd: str) -> str | None:
    """The deny reason for a Bash command, or None to let it through.

    The regex tests run first and the `git` subprocess in `serves_corpus`
    only after one of them matched, so the common (non-search) path spawns
    nothing (R01 risk 3).
    """
    if cmd and is_corpus_search(cmd) and serves_corpus(cmd, cwd):
        return BASH_DENIED
    return None


def decide_grep(tool_input: dict, cwd: str) -> str | None:
    base = cwd or os.getcwd()
    target = tool_input.get("path") or base
    resolved = os.path.realpath(os.path.join(base, os.path.expanduser(target)))
    return GREP_TOOL_DENIED if is_source_corpus(resolved) else None


# --- WorktreeRemove ----------------------------------------------------------------

PROJECT_LINE = re.compile(r"^Project:\s*(?P<project>.+?)\s*$", re.MULTILINE)


def find_colgrep() -> str | None:
    """`COLGREP_MCP_BINARY` if set (the server's own knob), else PATH, else cargo's default."""
    configured = os.environ.get("COLGREP_MCP_BINARY")
    if configured:
        return configured
    found = shutil.which("colgrep")
    if found:
        return found
    fallback = os.path.expanduser("~/.cargo/bin/colgrep")
    return fallback if os.path.isfile(fallback) and os.access(fallback, os.X_OK) else None


def reap_worktree_index(worktree_path: str) -> bool:
    """Clear the index a removed worktree owned; never one it was folded into.

    colgrep folds a path into the nearest already-indexed ancestor project and
    `clear` is project-wide (colgrep_mcp R05 D3), so the index is cleared
    only when `colgrep status` names the worktree itself as the project —
    the same rule `index_clear` applies. Returns whether a clear ran.
    """
    binary = find_colgrep()
    if not binary or not worktree_path:
        return False
    path = os.path.realpath(os.path.expanduser(worktree_path))
    try:
        # Subcommand first, global flags after: clap reads a leading flag as
        # a search query (stack-traps `colgrep.md#flag-order`).
        status = subprocess.run(
            [binary, "status", path, "--color", "never"], capture_output=True, text=True, timeout=20
        )
    except (subprocess.SubprocessError, OSError):
        return False
    match = PROJECT_LINE.search(status.stdout)
    if not match or os.path.realpath(match.group("project")) != path:
        return False
    try:
        subprocess.run([binary, "clear", path, "--color", "never"], capture_output=True, timeout=60)
    except (subprocess.SubprocessError, OSError):
        return False
    return True


# --- dispatch -----------------------------------------------------------------------

CONTEXT_EVENTS = ("SessionStart", "SubagentStart")


def emit(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload))
    sys.stdout.write("\n")


def handle(data: dict) -> None:
    event = data.get("hook_event_name", "")
    cwd = data.get("cwd", "") or ""

    if event in CONTEXT_EVENTS:
        emit({"hookSpecificOutput": {"hookEventName": event, "additionalContext": POLICY}})
        return

    if event == "PreToolUse":
        tool = data.get("tool_name", "")
        tool_input = data.get("tool_input") or {}
        if tool == "Grep":
            reason = decide_grep(tool_input, cwd)
        elif tool in ("Bash", "Shell"):
            # Cursor's import maps Bash to Shell and may carry the command at
            # the top level; Claude Code and Codex put it in tool_input.command.
            cmd = tool_input.get("command") or data.get("command") or ""
            reason = decide_bash(cmd, cwd)
        else:
            reason = None
        if reason:
            emit(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        return

    if event == "WorktreeRemove":
        reap_worktree_index(data.get("worktree_path") or "")
        return


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    if not isinstance(data, dict):
        return
    try:
        handle(data)
    except Exception:  # noqa: BLE001 - a hook must never take the session down with it
        return


if __name__ == "__main__":
    main()
    sys.exit(0)
