"""The plugin's hooks: behaviour of `hooks/colgrep_policy.py` and drift guards on `hooks/*.json`.

The script is driven the way a harness drives it — one JSON object on
stdin, JSON or nothing on stdout, exit 0 — through the interpreter running
the tests, so the Windows CI job is the portability oracle for it as it is
for `fake_colgrep.py` (harness_wiring R01 §Validation). The drift guards pin
what no ecosystem's loader checks for us: that the portable file names only
events every hook-capable harness understands (R01 §C1), that the Claude-only
file is disjoint from it and named by the Claude Code manifest alone (R01
§C2), that every command launches the one script through the one launcher
(R01 §C3), and that the injected policy stays under Codex's context cap
(R01 §C4).
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / "hooks"
SCRIPT = HOOKS_DIR / "colgrep_policy.py"
PORTABLE_FILE = HOOKS_DIR / "hooks.json"
CLAUDE_ONLY_FILE = HOOKS_DIR / "claude-code.json"

#: Events documented by all three hook-capable ecosystems: Claude Code's hooks
#: reference, Codex's "Hooks" doc (§Hooks) and Cursor's third-party-hooks
#: mapping table (R01 §C1). Anything outside this set belongs in the
#: Claude-only file.
PORTABLE_EVENTS = {
    "SessionStart",
    "SessionEnd",
    "SubagentStart",
    "SubagentStop",
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "PreCompact",
    "Stop",
}

LAUNCHER = 'uv run --no-project --quiet python "${CLAUDE_PLUGIN_ROOT}/hooks/'

#: Codex spills `additionalContext` above ~2 500 tokens per handler; the policy
#: is kept well under that so it never competes with the guide (R01 §C4).
POLICY_CHAR_CAP = 2000


def _load_module():
    spec = importlib.util.spec_from_file_location("colgrep_policy", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def run_hook(payload, *, env: dict[str, str] | None = None, stdin: str | None = None) -> tuple[int, str, str]:
    """Drive the script exactly as a harness does: JSON on stdin, capture both streams."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload) if stdin is None else stdin,
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, **(env or {})},
    )
    return proc.returncode, proc.stdout, proc.stderr


def _hook_output(stdout: str) -> dict:
    return json.loads(stdout)["hookSpecificOutput"]


@pytest.fixture
def corpus(tmp_path: Path) -> Path:
    """A git work tree: the one thing that makes any path a source corpus.

    `tmp_path` lives under the system temp directory, which the gate treats
    as machine state, so without `git init` every deny below would be a pass.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    return repo


# --- SessionStart / SubagentStart --------------------------------------------------


@pytest.mark.parametrize("event", ["SessionStart", "SubagentStart"])
def test_context_events_echo_the_event_and_carry_the_policy(event: str):
    rc, out, _err = run_hook({"hook_event_name": event, "source": "startup", "cwd": "/"})

    assert rc == 0
    output = _hook_output(out)
    assert output["hookEventName"] == event
    policy = output["additionalContext"]
    assert "`search`" in policy and "`expand`" in policy
    assert "COLGREP_BYPASS=1" in policy
    assert "colgrep -" not in policy, "the policy names MCP tools, never CLI flags"


def test_policy_stays_under_the_codex_context_cap():
    module = _load_module()
    assert len(module.POLICY) <= POLICY_CHAR_CAP


# --- PreToolUse: Grep tool -------------------------------------------------------------


def test_grep_tool_is_denied_inside_a_source_corpus(corpus: Path):
    rc, out, _err = run_hook(
        {"hook_event_name": "PreToolUse", "tool_name": "Grep", "tool_input": {"pattern": "x"}, "cwd": str(corpus)}
    )

    assert rc == 0
    output = _hook_output(out)
    assert output["permissionDecision"] == "deny"
    assert "`search`" in output["permissionDecisionReason"]


def test_grep_tool_passes_at_machine_state(tmp_path: Path):
    rc, out, _err = run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Grep",
            "tool_input": {"pattern": "x", "path": str(tmp_path)},
            "cwd": str(tmp_path),
        }
    )
    assert (rc, out) == (0, "")


# --- PreToolUse: Bash ----------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    [
        "grep -rn foo src",
        "grep -R 'foo' .",
        "rg foo",
        "rg -n 'foo bar' src",
        "find . -name '*.py' -exec grep foo {} +",
        "find . -type f | xargs grep foo",
        "grep -rc foo .",  # -c with -r is still a corpus search
        "grep --recursive foo .",
    ],
)
def test_corpus_searches_are_denied(corpus: Path, command: str):
    rc, out, _err = run_hook(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(corpus)}
    )

    assert rc == 0
    output = _hook_output(out)
    assert output["permissionDecision"] == "deny"
    assert "`search`" in output["permissionDecisionReason"]
    assert "COLGREP_BYPASS=1" in output["permissionDecisionReason"]


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "git log --oneline | grep fix",
        "cat file.txt | rg todo",
        "grep foo file.txt",
        "grep -c foo file.txt",
        "grep -v foo file.txt",
        "grep -o 'pat' file.txt",
        'grep -n "Anti-patterns" guide.md',  # a hyphenated word is not a -r flag
        "grep 'foo-r' file.txt",
        "rg --files",
        "COLGREP_BYPASS=1 grep -rn foo .",
        "COLGREP_BYPASS=1 rg foo",
    ],
)
def test_allowed_shell_commands_pass_silently(corpus: Path, command: str):
    rc, out, _err = run_hook(
        {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(corpus)}
    )
    assert (rc, out) == (0, "")


def test_corpus_search_at_machine_state_passes(tmp_path: Path):
    """The source-corpus gate: a tmp directory is application state, not a corpus."""
    rc, out, _err = run_hook(
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": f"grep -rn foo {tmp_path}"},
            "cwd": str(tmp_path),
        }
    )
    assert (rc, out) == (0, "")


def test_system_temp_and_platform_state_trees_are_never_a_corpus(tmp_path: Path):
    """On Windows the temp directory is `%LOCALAPPDATA%\\Temp`: under the home
    directory, no dot-prefixed component. The first Windows CI run of these
    hooks read a pytest `tmp_path` as a source corpus and denied a grep there
    (PR #7); this pins the temp directory, `Library` and `AppData` as machine
    state on every platform, independent of where the runner's temp lives."""
    module = _load_module()
    home = os.path.realpath(os.path.expanduser("~"))

    assert module.is_source_corpus(os.path.realpath(tempfile.gettempdir())) is False
    assert module.is_source_corpus(str(tmp_path.resolve())) is False
    for tree in ("Library", "AppData"):
        assert module.is_source_corpus(os.path.join(home, tree, "Caches", "x")) is False


def test_shell_alias_and_top_level_command_are_accepted(corpus: Path):
    """Cursor's Claude-Code import maps Bash to Shell and may carry `command` at the top level."""
    rc, out, _err = run_hook(
        {"hook_event_name": "PreToolUse", "tool_name": "Shell", "command": "grep -rn foo .", "cwd": str(corpus)}
    )
    assert rc == 0
    assert _hook_output(out)["permissionDecision"] == "deny"


def test_non_search_bash_spawns_no_subprocess(monkeypatch):
    """The common path is regex-only: `git rev-parse` runs only after a pattern matched (R01 risk 3)."""
    module = _load_module()

    def boom(*_args, **_kwargs):
        raise AssertionError("subprocess spawned for a non-search command")

    monkeypatch.setattr(module.subprocess, "run", boom)
    assert module.decide_bash("ls -la && git status", "/") is None
    assert module.decide_bash("git log | grep fix", "/") is None


# --- fail-open ---------------------------------------------------------------------------


def test_unparsable_stdin_and_unknown_events_exit_zero_silently():
    rc, out, _err = run_hook({}, stdin="not json at all")
    assert (rc, out) == (0, "")

    rc, out, _err = run_hook({"hook_event_name": "Notification", "cwd": "/"})
    assert (rc, out) == (0, "")

    rc, out, _err = run_hook({"hook_event_name": "PreToolUse", "tool_name": "Write", "tool_input": {}, "cwd": "/"})
    assert (rc, out) == (0, "")


# --- WorktreeRemove ---------------------------------------------------------------------


def _reap(fake_colgrep_bin: str, tmp_path: Path, worktree: Path, extra_env: dict[str, str]) -> list[str]:
    """Run the WorktreeRemove branch against the fake and return the last colgrep argv it ran."""
    argv_file = tmp_path / "argv.json"
    rc, out, _err = run_hook(
        {"hook_event_name": "WorktreeRemove", "worktree_path": str(worktree), "cwd": str(tmp_path)},
        env={"COLGREP_MCP_BINARY": fake_colgrep_bin, "FAKE_COLGREP_ARGV_FILE": str(argv_file), **extra_env},
    )
    assert (rc, out) == (0, "")
    return json.loads(argv_file.read_text()) if argv_file.exists() else []


def test_worktree_remove_clears_an_index_the_worktree_owns(fake_colgrep_bin, tmp_path):
    worktree = tmp_path / "wt"
    worktree.mkdir()

    last_argv = _reap(fake_colgrep_bin, tmp_path, worktree, {})

    assert last_argv[:2] == ["clear", str(worktree.resolve())]
    assert last_argv[2:] == ["--color", "never"], "global flags after the subcommand (stack-traps flag-order)"


def test_worktree_remove_never_clears_a_folded_ancestor_project(fake_colgrep_bin, tmp_path):
    worktree = tmp_path / "wt"
    worktree.mkdir()

    last_argv = _reap(fake_colgrep_bin, tmp_path, worktree, {"FAKE_COLGREP_STATUS_PROJECT": str(tmp_path)})

    assert last_argv[0] == "status", f"expected only a status probe, got {last_argv}"


def test_worktree_remove_does_nothing_without_an_index(fake_colgrep_bin, tmp_path):
    worktree = tmp_path / "wt"
    worktree.mkdir()

    last_argv = _reap(fake_colgrep_bin, tmp_path, worktree, {"FAKE_COLGREP_INDEXED": "0"})

    assert last_argv[0] == "status"


def test_worktree_remove_without_a_binary_is_a_silent_no_op(tmp_path, monkeypatch):
    module = _load_module()
    monkeypatch.delenv("COLGREP_MCP_BINARY", raising=False)
    monkeypatch.setattr(module.shutil, "which", lambda _name: None)
    monkeypatch.setattr(module.os.path, "isfile", lambda _p: False)

    assert module.reap_worktree_index(str(tmp_path)) is False


# --- drift guards on the hook manifests ---------------------------------------------------


def _load(path: Path) -> dict:
    return json.loads(path.read_text())


def _commands(config: dict):
    for groups in config["hooks"].values():
        for group in groups:
            yield from group["hooks"]


def test_portable_file_names_only_events_every_harness_understands():
    events = set(_load(PORTABLE_FILE)["hooks"])
    assert events <= PORTABLE_EVENTS, f"non-portable events in hooks.json: {events - PORTABLE_EVENTS}"
    assert {"SessionStart", "SubagentStart", "PreToolUse"} <= events


def test_claude_only_file_is_disjoint_from_the_portable_file():
    portable = set(_load(PORTABLE_FILE)["hooks"])
    claude_only = set(_load(CLAUDE_ONLY_FILE)["hooks"])
    assert claude_only, "the Claude-only file exists to hold at least one event"
    assert not (claude_only & portable)
    assert not (claude_only & PORTABLE_EVENTS), "a portable event belongs in hooks.json"


def test_pre_tool_use_matches_grep_and_bash_only():
    groups = _load(PORTABLE_FILE)["hooks"]["PreToolUse"]
    assert [g["matcher"] for g in groups] == ["Grep|Bash"]


def test_every_handler_launches_the_one_script_through_the_one_launcher():
    for path in (PORTABLE_FILE, CLAUDE_ONLY_FILE):
        for handler in _commands(_load(path)):
            assert handler["type"] == "command", path.name
            command = handler["command"]
            assert command.startswith(LAUNCHER), (path.name, command)
            script = command[len(LAUNCHER) :].split('"', 1)[0]
            assert (HOOKS_DIR / script).is_file(), (path.name, script)
            assert command.count("${") == 1, "the plugin root is the only placeholder in a hook command"
            assert isinstance(handler["timeout"], int) and handler["timeout"] > 0


def test_manifests_name_the_hook_files_per_ecosystem():
    claude = _load(REPO_ROOT / ".claude-plugin" / "plugin.json")
    codex = _load(REPO_ROOT / ".codex-plugin" / "plugin.json")
    agent = _load(REPO_ROOT / "plugin.json")

    assert claude["hooks"] == ["./hooks/hooks.json", "./hooks/claude-code.json"]
    assert codex["hooks"] == "./hooks/hooks.json", "Codex must never be pointed at the Claude-only file"
    assert "hooks" not in agent, "Agent Plugins 1.0 defines no hooks component"


def test_hook_script_is_stdlib_only_and_never_imports_the_server():
    """`uv run --no-project python` installs nothing: only the standard library may be imported."""
    tree = ast.parse(SCRIPT.read_text())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module.split(".")[0])
    foreign = imported - set(sys.stdlib_module_names)
    assert not foreign, f"non-stdlib imports in the hook: {foreign}"
