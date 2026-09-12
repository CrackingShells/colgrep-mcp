# consistency — Knowledge Transfer (v0)

Date: 2026-09-12

## Executive Summary
- **What changed**: `server/colgrep_mcp/` now has one idiom per concern — module-level tool handlers registered through `server.register_tool`, one path resolver (`paths.resolve_target_paths`, client roots fetched only when they can change the answer), one adapter-error translation (`errors.translate_adapter_errors`, catching the base class), one best-effort notification module (`logging_utils.safe_*`), one adapter shared by every handler including static resources and completions (`server.get_app(ctx=None)`, scoped by a `ContextVar`), one budgeted text renderer. Two handlers stopped doing input-proportional I/O: `find_files` no longer reads or re-locates hit files it never exposes, `expand` reads only the requested span. Per-spawn environment copies, per-lock `resolve()` calls, per-request guide reads and the completion-cache refill race are gone. Tool descriptions ship dedented. Docstrings say why, and `AGENTS.md` resolves the report ids they cite. No tool, argument, schema, code, hint or text-layout change; the intended visible deltas are `doctor.root_source == "roots"` where the README already promised it, whitespace-only description dedent, and a coded `[COLGREP_FAILED]` where the adapter's own guards previously surfaced uncoded.
- **Primary outcomes**: ≈50 min wall time (15:57 → 16:48 CEST) against a 3 h box; one lead (Fable) with three Sonnet implementers at depth 0 and one Sonnet implementer plus one Sonnet reviewer at depth 1; the lead took the adapter leaf, the shared helpers, the description dedent and the OV1 fix. Tests 199 → 208 passing, ruff clean, `cz check` green over 34 branch commits, `claude --plugin-dir . mcp list` connects. Measured (reviewer-reproduced in parentheses): `find_files` file handling 63.4 → 0.65 ms (53.2 → 0.70), `expand` 6.1 → 0.03 ms (3.6 → 0.03) on synthetic corpora; tool-description bytes 1510 → 1395 (1516 → 1401).

## Wins
- **Helpers before dispatch.** Committing C1–C4 as one additive `refactor(server)` before any leaf existed meant four branches consumed one idiom instead of inventing four; zero conflicts at integration, every rebase clean.
- **The oracle was named, not implied.** "Tests change only at private-name call sites; the `list_tools()` JSON diff must be empty" caught real drift within minutes: moving closures to module level changed the docstring indentation the SDK ships verbatim. The implementer preserved bytes as told and flagged it; the lead turned the flag into a measured `perf` commit instead of a silent whitespace change.
- **File ownership in the roadmap README, again.** Same device as `repo_health`, same result: no cross-leaf edit, one accurate "outside my files" note per agent.
- **Lead-sized leaves stayed with the lead.** `adapter_hygiene` took 4 minutes; a dispatch would have cost more in prompt tokens than the leaf.
- **Sonnet implementers finished in 6–15 minutes each** on 1–3-step leaves with exact commit subjects and gate commands; the 17:25 hard stop was never approached, and the whole campaign closed in a third of its budget.
- **The reviewer's "known intentional deltas" list worked both ways**: it stopped re-reporting and let the reviewer prove they were the *only* deltas (word-normalised recursive schema diff).

## Pain Points
- `dirtree-rdm`'s grammar rejects a `## Reference Documents` bullet that does not start with `[R<nn> …]` and any text after `(expected: PASS)` in a consistency check; three leaf files and both READMEs failed validation on first write.
- `git merge -F -` does not read stdin; the first `--no-ff` merge failed inside an `&&` chain and had to be redone with `-m`.
- `pydantic.validate_call` (which the SDK wraps every resource in) rejects a `functools.cache` wrapper; the implementer had to put the cache one level down. Undocumented.
- The SDK ships `__doc__` verbatim as the tool description; nothing pinned that, so 8-space indentation had reached every client since 0.1.0.
- The lead's first regression test for OV1 read `colgrep://errors`, which never touches the app handle, and passed against the broken implementation. Only running the test against the *old* code exposed it; the corrected test reads `colgrep://indexes`.
- One agent reported "196 tests" on a branch that had 206; harmless because the lead re-ran the gates, but agent-reported counts are not evidence.
- **PR #3's first CI run failed on Windows** (macOS/Linux green): the index leaf's new `doctor` test was the first to exercise client roots end to end and found that `client_roots` built `Path(root.uri.path)` from the URI form `/C:/Users/…`, yielding `C:Users\…`; the same code kept percent-encoding. Nothing local could have caught it — no Windows machine, no prior test of that path. Fixed with `url2pathname` (`fix(server)`) plus two tests that had hard-coded POSIX renderings.

## Root Causes
- 0.1.0's three parallel implementers each chose a local idiom for cross-cutting concerns because R01 specified behaviour, not idiom, and no shared helper existed to copy from.
- A "no behaviour change" oracle is only as good as what is dumped; description whitespace was client-visible but never asserted.
- A regression test that passes on first run has proven nothing until it has failed once.
- A refactor that makes an untested path reachable inherits that path's latent bugs; the Windows matrix is the only oracle for path-string portability and it runs only on the PR.

## Next-cycle Changes
- **Instruction changes**: `AGENTS.md` carries the four idiom rules and the report-id legend; every future leaf names the shared helper it consumes and the exact dump-and-diff oracle command, as these did.
- **Workflow changes**: run `dirtree-rdm grammar leaf | grep -A2 consistency` once before writing leaf files and keep `(expected: PASS)` terminal; merge with `--no-ff -m`, never `-F -`; for every `fix` commit, run the new test against the pre-fix code before committing and say so in the body.
- **Review process changes**: when a leaf adds the first test of a previously untested path, name it in the PR body so the Windows job's verdict on it is read, not skimmed; keep the "known intentional deltas" paragraph in the reviewer prompt; keep the word-normalised schema diff as a standing probe; the lead re-runs the gates on every branch rather than trusting reported counts.
- **Product follow-ups**: `find_files` still builds a `SearchHit` (and a `hit_id` from reported lines) per raw hit it then discards — a `FileHit`-only path would skip that; `safe_log` still sends one `notifications/message` per colgrep stderr line during `search` while the logging capability is deprecated upstream — decide whether that traffic stays; carried items: PyPI → `uvx`, `ruff format` sweep (no parallel branch open now), Codex placeholder expansion, Agent Plugins `COLGREP_MCP_ROOT` asymmetry, `list_indexes` text budget.

## Artifacts to Preserve
- `__reports__/consistency/00-architecture_v0.md` — contracts C1–C6 and the ownership table; reusable shape for a consistency pass over any multi-implementer package.
- `__reports__/consistency/01-observation_review_v0.md` — the probe list (schema dump-and-diff against `main`, leftover-idiom greps, roots-call counting, perf reproduction, cancellation re-read) is a reusable post-refactor checklist; its "Traced, No Issue" section is the current statement of what is known good.
- `server/tests/test_smoke.py::test_tool_descriptions_are_dedented` and `::test_overlapping_sessions_keep_their_own_app_handle`, `test_paths.py::test_roots_can_matter_only_without_env_root_and_with_something_relative`, `test_errors.py::test_translate_adapter_errors_catches_the_base_class`, `test_tools_search.py::test_find_files_does_not_read_hit_files`, `test_prompts.py::test_completion_cache_refill_is_serialised`, `test_locks.py::test_lock_key_is_the_path_string`, `test_tools_index.py::test_doctor_reports_client_root_when_env_root_unset` — the guards that make the idioms self-checking.
- `__roadmap__/consistency/` — the BFS tree with per-leaf timings in the Progress tables.

## Open Questions
- Does any shipped transport ever run two lifespans in one process? The reviewer could not find a path outside `asyncio.gather` of two in-memory clients; the `ContextVar` fix makes the question moot for correctness, but if the answer is "never", the docstring could say so.
- `hit_from_raw` still resolves `unit.file` twice per hit (once in `_fill_file_cache`, once in `hit_from_raw`) on the `search` path; worth folding when `find_files` gets its `FileHit`-only path.
- Should `list_indexes`/`--stats` remain machine-global on shared machines (carried from 0.1.0)?
