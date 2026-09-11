"""Scripted stdio session against the REAL colgrep binary (roadmap leaf `e2e_validation`).

Not a pytest test module (no `test_` prefix, no `__init__.py` in this
directory) -- pytest's default `testpaths = ["tests"]` only collects files
matching `test_*.py`/`*_test.py`, so this script is invisible to `pytest`
even though it lives under `tests/`. Run it directly:

    cd server && uv run python tests/e2e/run_e2e.py --corpus <path>
    cd server && uv run python tests/e2e/run_e2e.py --corpus <path> --dry-run

It spawns the real console entry point (`sys.executable -m colgrep_mcp`,
cwd=server/, exactly what `colgrep-mcp` resolves to -- see
`tests/test_stdio.py`) against the REAL `colgrep` binary on PATH, drives a
fixed sequence of tool/resource/prompt calls over the real stdio transport,
and prints a Markdown results table plus a few derived summary lines.

Never point `--corpus` at this repository, any of its worktrees, or
anything under `/private/tmp` (R05 D3: colgrep folds a path under
`/private/tmp` into whatever project already anchors that prefix on this
machine -- see `__reports__/colgrep_mcp/02-architecture_v1.md` D3). This
script refuses to run against such a path as a defense-in-depth check on top
of operator discipline.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# server/tests/e2e/run_e2e.py -> e2e -> tests -> server
SERVER_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = SERVER_DIR.parent


@dataclass
class CallSpec:
    """One planned call in the fixed e2e sequence."""

    kind: str  # "tool" | "resource" | "prompt"
    name: str  # tool name / resource URI / prompt name
    args: dict[str, Any] = field(default_factory=dict)
    label: str = ""  # short id used to cross-reference later steps (e.g. "search_a")


@dataclass
class CallRecord:
    """What actually happened when a `CallSpec` was executed."""

    step: int
    spec: CallSpec
    wall_ms: int
    is_error: bool
    hits: int | None
    text_chars: int
    truncated: bool | None
    notes: list[str]
    structured_content: Any = None
    error_text: str = ""


def _refuse_unsafe_corpus(corpus: Path) -> None:
    """Defense-in-depth guard on top of operator discipline (R05 D3)."""
    private_tmp = Path("/private/tmp")
    resolved = corpus.resolve()
    for banned, why in (
        (private_tmp, "colgrep folds any /private/tmp path into a pre-existing ancestor project (R05 D3)"),
        (REPO_ROOT, "never run colgrep against this repository or its worktrees"),
    ):
        try:
            resolved.relative_to(banned.resolve())
        except ValueError:
            continue
        except OSError:
            continue
        print(f"REFUSING: --corpus {corpus} is under {banned} -- {why}", file=sys.stderr)
        raise SystemExit(2)


def build_call_plan(corpus: Path, top3_hit_ids: list[str] | None = None) -> list[CallSpec]:
    """The fixed, ordered sequence of calls the roadmap leaf specifies.

    `top3_hit_ids` is only known once search (a) has actually run; for
    `--dry-run` (which never executes anything) it stays `None` and the
    `expand` step's args show a placeholder instead.
    """
    status_path = str(corpus).lstrip("/")
    expand_ids = top3_hit_ids if top3_hit_ids is not None else ["<top 3 hit_ids of search (a)>"]

    return [
        CallSpec("tool", "doctor", {}, "doctor"),
        CallSpec("tool", "index_status", {}, "index_status_1"),
        CallSpec("tool", "index_build", {}, "index_build"),
        CallSpec("tool", "index_status", {}, "index_status_2"),
        CallSpec(
            "tool",
            "search",
            {"query": "how are command line options parsed into values", "limit": 5},
            "search_a",
        ),
        CallSpec(
            "tool",
            "search",
            {
                "query": "decorator that registers a command",
                "pattern": "def command",
                "include": ["*.py"],
                "limit": 3,
            },
            "search_b",
        ),
        CallSpec("tool", "search", {"query": "shell completion", "limit": None}, "search_c"),
        CallSpec(
            "tool",
            "search",
            {"query": "uses of parse_args", "pattern": "parse_args", "limit": None},
            "search_d",
        ),
        CallSpec(
            "tool",
            "search",
            {"query": "context object lifecycle", "include_code": True, "limit": 3},
            "search_e",
        ),
        CallSpec(
            "tool",
            "search",
            {"query": "zzqx nonexistent quantum banana", "pattern": "zzqxzzqx"},
            "search_f",
        ),
        CallSpec("tool", "find_files", {"query": "shell completion", "limit": 5}, "find_files"),
        CallSpec("tool", "expand", {"hit_ids": expand_ids, "max_lines": 40}, "expand"),
        CallSpec("tool", "list_indexes", {}, "list_indexes"),
        CallSpec("resource", "colgrep://guide", {}, "resource_guide"),
        CallSpec("resource", f"colgrep://status/{status_path}", {}, "resource_status"),
        CallSpec(
            "prompt",
            "explore",
            {"question": "how does click parse options?"},
            "prompt_explore",
        ),
        CallSpec("tool", "index_clear", {}, "index_clear_noconfirm"),
    ]


def _short_args(args: dict[str, Any]) -> str:
    text = json.dumps(args, separators=(",", ":"), default=str)
    return text if len(text) <= 90 else text[:87] + "..."


def _print_dry_run(corpus: Path) -> None:
    plan = build_call_plan(corpus)
    print(f"# Planned e2e call list ({len(plan)} calls) -- corpus={corpus}\n")
    print("| # | Kind | Name | Args |")
    print("|--:|:--|:--|:--|")
    for i, spec in enumerate(plan, start=1):
        print(f"| {i} | {spec.kind} | `{spec.name}` | `{_short_args(spec.args)}` |")
    print("\nDRY RUN -- no server was spawned, no colgrep call was made.")


def _extract_metrics(spec: CallSpec, text: str, structured: Any) -> tuple[int | None, bool | None, list[str]]:
    """Derive (hits, truncated, notes) from a tool's `structured_content`, when there is one."""
    if not isinstance(structured, dict):
        return None, None, []

    hits: int | None = None
    if spec.name == "search":
        hits = structured.get("total")
    elif spec.name == "find_files":
        files = structured.get("files")
        hits = len(files) if isinstance(files, list) else None
    elif spec.name == "expand":
        units = structured.get("units")
        hits = len(units) if isinstance(units, list) else None
    elif spec.name == "list_indexes":
        indexes = structured.get("indexes")
        hits = len(indexes) if isinstance(indexes, list) else None

    truncated = structured.get("truncated")
    notes = structured.get("notes") or []
    return hits, truncated, notes


async def _run_tool(client: Any, spec: CallSpec, step: int, progress_sink: list[tuple[float, float | None, str | None]] | None = None) -> CallRecord:
    progress_callback = None
    if progress_sink is not None:

        async def _on_progress(progress: float, total: float | None, message: str | None) -> None:
            progress_sink.append((progress, total, message))

        progress_callback = _on_progress

    start = time.monotonic()
    result = await client.call_tool(spec.name, spec.args, progress_callback=progress_callback)
    wall_ms = int((time.monotonic() - start) * 1000)

    text = result.content[0].text if result.content else ""
    hits, truncated, notes = _extract_metrics(spec, text, result.structured_content)

    return CallRecord(
        step=step,
        spec=spec,
        wall_ms=wall_ms,
        is_error=result.is_error,
        hits=hits,
        text_chars=len(text),
        truncated=truncated,
        notes=notes,
        structured_content=result.structured_content,
        error_text=text if result.is_error else "",
    )


async def _run_resource(client: Any, spec: CallSpec, step: int) -> CallRecord:
    start = time.monotonic()
    result = await client.read_resource(spec.name)
    wall_ms = int((time.monotonic() - start) * 1000)
    texts = [c.text for c in result.contents if hasattr(c, "text")]
    text = "\n".join(texts)
    return CallRecord(
        step=step,
        spec=spec,
        wall_ms=wall_ms,
        is_error=False,
        hits=None,
        text_chars=len(text),
        truncated=None,
        notes=[],
    )


async def _run_prompt(client: Any, spec: CallSpec, step: int) -> CallRecord:
    start = time.monotonic()
    result = await client.get_prompt(spec.name, spec.args)
    wall_ms = int((time.monotonic() - start) * 1000)
    text = "\n".join(
        m.content.text for m in result.messages if getattr(m.content, "type", None) == "text"
    )
    return CallRecord(
        step=step,
        spec=spec,
        wall_ms=wall_ms,
        is_error=False,
        hits=None,
        text_chars=len(text),
        truncated=None,
        notes=[],
    )


def _hit_ids(record: CallRecord, n: int) -> list[str]:
    sc = record.structured_content or {}
    hits = sc.get("hits") or []
    return [h["hit_id"] for h in hits[:n] if isinstance(h, dict) and "hit_id" in h]


def _location_verified_false_count(records: dict[str, CallRecord]) -> tuple[int, int]:
    """Count `location_verified is False` across search (a)-(e)'s hits. Returns (false_count, total_hits)."""
    false_count = 0
    total = 0
    for label in ("search_a", "search_b", "search_c", "search_d", "search_e"):
        rec = records.get(label)
        if rec is None:
            continue
        sc = rec.structured_content or {}
        for hit in sc.get("hits") or []:
            total += 1
            if hit.get("location_verified") is False:
                false_count += 1
    return false_count, total


def _render_table(records: list[CallRecord]) -> str:
    lines = [
        "| # | Call | Args | Wall ms | is_error | Hits | Text chars | Truncated | Notes |",
        "|--:|:--|:--|--:|:--|--:|--:|:--|:--|",
    ]
    for r in records:
        name = f"{r.spec.kind}:{r.spec.name}" if r.spec.kind != "tool" else r.spec.name
        notes = "; ".join(r.notes) if r.notes else ""
        if r.is_error and r.error_text:
            notes = (notes + " " if notes else "") + f"ERROR: {r.error_text[:120]}"
        lines.append(
            f"| {r.step} | `{name}` | `{_short_args(r.spec.args)}` | {r.wall_ms} | {r.is_error} | "
            f"{'-' if r.hits is None else r.hits} | {r.text_chars} | "
            f"{'-' if r.truncated is None else r.truncated} | {notes} |"
        )
    return "\n".join(lines)


async def _main_async(corpus: Path, label: str) -> int:
    # Imported lazily so `--dry-run` never needs the `mcp` package importable
    # from a bare `python` (only `uv run` guarantees that).
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "colgrep_mcp"],
        env={"COLGREP_MCP_ROOT": str(corpus)},
        cwd=str(SERVER_DIR),
    )

    records: list[CallRecord] = []
    by_label: dict[str, CallRecord] = {}
    progress_events: list[tuple[float, float | None, str | None]] = []

    async with Client(params, raise_exceptions=True) as client:
        step = 1
        # doctor, index_status (1)
        plan_head = build_call_plan(corpus)[:2]
        for spec in plan_head:
            rec = await _run_tool(client, spec, step)
            records.append(rec)
            by_label[spec.label] = rec
            step += 1

        # index_build, with progress tracking
        rec = await _run_tool(
            client, CallSpec("tool", "index_build", {}, "index_build"), step, progress_sink=progress_events
        )
        records.append(rec)
        by_label["index_build"] = rec
        step += 1

        # index_status (2)
        rec = await _run_tool(client, CallSpec("tool", "index_status", {}, "index_status_2"), step)
        records.append(rec)
        by_label["index_status_2"] = rec
        step += 1

        # six searches
        for spec in build_call_plan(corpus)[4:10]:
            rec = await _run_tool(client, spec, step)
            records.append(rec)
            by_label[spec.label] = rec
            step += 1

        # find_files
        spec = build_call_plan(corpus)[10]
        rec = await _run_tool(client, spec, step)
        records.append(rec)
        by_label[spec.label] = rec
        step += 1

        # expand on top 3 hit_ids of search (a)
        top3 = _hit_ids(by_label["search_a"], 3)
        spec = CallSpec("tool", "expand", {"hit_ids": top3, "max_lines": 40}, "expand")
        rec = await _run_tool(client, spec, step)
        records.append(rec)
        by_label[spec.label] = rec
        step += 1

        # list_indexes
        rec = await _run_tool(client, CallSpec("tool", "list_indexes", {}, "list_indexes"), step)
        records.append(rec)
        by_label["list_indexes"] = rec
        step += 1

        # resources
        rec = await _run_resource(client, CallSpec("resource", "colgrep://guide", {}, "resource_guide"), step)
        records.append(rec)
        by_label["resource_guide"] = rec
        step += 1

        status_uri = f"colgrep://status/{str(corpus).lstrip('/')}"
        rec = await _run_resource(client, CallSpec("resource", status_uri, {}, "resource_status"), step)
        records.append(rec)
        by_label["resource_status"] = rec
        step += 1

        # prompt
        rec = await _run_prompt(
            client,
            CallSpec("prompt", "explore", {"question": "how does click parse options?"}, "prompt_explore"),
            step,
        )
        records.append(rec)
        by_label["prompt_explore"] = rec
        step += 1

        # index_clear, no confirm -> expect an error result
        rec = await _run_tool(client, CallSpec("tool", "index_clear", {}, "index_clear_noconfirm"), step)
        records.append(rec)
        by_label["index_clear_noconfirm"] = rec
        step += 1

    # --- render ---------------------------------------------------------
    header = f"# colgrep-mcp e2e run{f' ({label})' if label else ''}\n\ncorpus: `{corpus}`\n"
    print(header)
    print(_render_table(records))

    search_labels = ("search_a", "search_b", "search_c", "search_d", "search_e")
    search_wall = [r.wall_ms for r in records if r.spec.label in search_labels]
    if search_wall:
        sorted_wall = sorted(search_wall)
        mid = len(sorted_wall) // 2
        median = (
            sorted_wall[mid] if len(sorted_wall) % 2 else (sorted_wall[mid - 1] + sorted_wall[mid]) / 2
        )
        print(f"\nMedian search (a)-(e) wall time: {median} ms (n={len(sorted_wall)}: {sorted_wall})")

    false_count, total_hits = _location_verified_false_count(by_label)
    print(f"location_verified=false count across search (a)-(e): {false_count}/{total_hits} hits")

    n_events = len(progress_events)
    first_msg = progress_events[0][2] if progress_events else None
    last_msg = progress_events[-1][2] if progress_events else None
    print(
        f"index_build progress notifications observed: {n_events} "
        f"(first={first_msg!r}, last={last_msg!r})"
    )

    n_errors = sum(1 for r in records if r.is_error)
    expected_error_labels = {"index_clear_noconfirm"}
    unexpected_errors = [
        r for r in records if r.is_error and r.spec.label not in expected_error_labels
    ]
    print(f"total is_error=True results: {n_errors} (expected: index_clear_noconfirm only)")
    if unexpected_errors:
        print("UNEXPECTED ERRORS:")
        for r in unexpected_errors:
            print(f"  - step {r.step} {r.spec.label}: {r.error_text}")

    return 1 if unexpected_errors else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, help="Absolute path to the repository to search.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned call list and exit 0 without spawning the server.",
    )
    parser.add_argument(
        "--label",
        default="",
        help="Optional free-text label stamped in the printed header (e.g. 'warm-1', 'cold').",
    )
    args = parser.parse_args(argv)

    corpus = Path(args.corpus).expanduser().resolve()
    _refuse_unsafe_corpus(corpus)

    if args.dry_run:
        _print_dry_run(corpus)
        return 0

    if not corpus.is_dir():
        print(f"--corpus {corpus} is not a directory", file=sys.stderr)
        return 2

    return asyncio.run(_main_async(corpus, args.label))


if __name__ == "__main__":
    raise SystemExit(main())
