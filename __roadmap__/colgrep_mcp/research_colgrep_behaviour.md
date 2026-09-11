# colgrep CLI Behaviour Probe

**Goal**: Empirically characterise colgrep 1.6.x as a subprocess — exit codes, stdout/stderr formats, JSON schema edge cases, indexing progress output, timing — so the adapter is built on observed behaviour rather than on `--help` text.
**Pre-conditions**:
- [ ] `colgrep --version` reports ≥ 1.6.2
- [ ] A small corpus is available to index (use a fresh copy of a ~50–500 file repo under the scratchpad; never index this repository's worktrees)
**Success Gates**:
- ⬜ [static] Report exists at `__reports__/colgrep_mcp/01-findings_colgrep_behaviour_v0.md` following the `findings` report type
- ⬜ [static] Raw captured outputs are saved under `__reports__/colgrep_mcp/evidence/colgrep/` (one file per probe, named `<probe>.stdout.txt` / `.stderr.txt` / `.exit`)
- ⬜ [static] The report contains a JSON Schema (draft 2020-12) for one search hit, derived from ≥ 3 real outputs, marking which fields are nullable
**References**: [R01 §Contracts](../../__reports__/colgrep_mcp/00-architecture_v0.md) — the adapter contract this probe must validate or correct

## Step 1: Run the probe matrix and write the findings
**Goal**: Replace assumptions in the adapter contract with measured facts.
**Implementation Logic**:
Run every probe with `--color never` and capture stdout, stderr and exit code separately (`cmd >out 2>err; echo $? >exit`). Probes, on a fresh scratchpad corpus:
1. Cold `colgrep init -y <dir>` — what goes to stderr during model load and indexing (progress lines? one line per file? spinner escapes even with `--color never`?), wall time, exit code.
2. Warm `colgrep init <dir>` (no changes) and after touching one file — output and time.
3. `colgrep --json -k 3 "<query>" <dir>` — full JSON; also with `-c`, with `-n 2`, with `-l` (does `--json` still apply?), with `-e <regex>` and `-e` alone (no query), with `--include`, `--exclude-dir`, with a query that matches nothing (empty array? exit code?), with a non-existent path, with a file path instead of a dir, with two paths.
4. `--json` with `-k` omitted — how many results; does stderr report truncation?
5. `colgrep status <dir>` (indexed and not indexed), `colgrep --stats`, `colgrep settings` — capture exact text for the text parsers.
6. `colgrep clear <dir>` — does it prompt? exit code; `colgrep status` afterwards.
7. Concurrency: launch two `colgrep --json` searches on the same dir simultaneously right after touching a file — any lock error, corrupted output or crash?
8. Unicode / spaces: query and path containing spaces and non-ASCII.
9. `HOME`/`XDG_DATA_HOME` handling: where the index landed on this macOS (`~/Library/Application Support/colgrep/indices/...`), so the server can report index location.
10. `colgrep` binary absent: run with `PATH=/nonexistent` to capture the failure shape the server must translate.
Write the report: Headline Result (hit JSON schema stability), Results Tables (probe × exit code × stdout kind × stderr kind × time), Observations vs the R01 contract (Baseline = what R01 assumed), Contradictions & Surprises, Steering Questions for the adapter author.
**References**: [R01 §Contracts](../../__reports__/colgrep_mcp/00-architecture_v0.md) — the `SearchHit` and `IndexStatus` models to check against
**Deliverables**: `__reports__/colgrep_mcp/01-findings_colgrep_behaviour_v0.md` (sections: Headline Result, Probe Results table, Hit JSON Schema, Text-format samples for status/stats/settings, Observations, Contradictions & Surprises, Steering Questions, Pointers); `__reports__/colgrep_mcp/evidence/colgrep/*.{stdout.txt,stderr.txt,exit}`; `__reports__/colgrep_mcp/README.md` updated
**Consistency Checks**: `ls __reports__/colgrep_mcp/evidence/colgrep/ | wc -l` (expected: PASS)
**Commit**: `docs(reports): record measured colgrep CLI behaviour for the adapter`
