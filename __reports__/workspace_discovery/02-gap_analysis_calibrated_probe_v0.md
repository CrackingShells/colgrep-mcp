# Gap Analysis: workspace_discovery - probe records cannot be trusted

## Problem Statement

The probe instrumentation shipped at `ca3cb40` cannot distinguish a
record the harness actually produced from a record the test harness's
`colgrep` stub fabricated. Every leg of the level-2 evidence plan (the
harness × signal matrix, the batch-01 findings rung picks) rests on
probe records *provably* being harness-sent. The adversarial verifier
finding at `02-findings_probe_verifier_v0.md` (this session, layered verdict
UNSOUND) proves they need not be, and one of the four levers actively breaks
the leaf's own law ("a probe must never break a tool call"). The structure
of the defect collection is what matters: three independent places where
the probe can lead the campaign astray exactly on the columns the campaign
exists to fill (`init_capabilities`, `request_meta`, `roots_list`).

## Evidence

Dumped severity leads (full verbose trace at `02-findings_probe_verifier_v0.md`,
not repeated here):

1. **Stub impersonation (silent falsification, exploitable).**
   `server/tests/e2e/probe_workspace.py`'s `_STUB_SCRIPT` (`:51-70`) writes fully
   R01-shaped JSONL records hardcoded with `"init_capabilities": None`,
   `"request_meta": None`, `"roots_list": {"static": "empty"}`. The
   `doctor` tool resolves its root locally in `tools_index.py:331-339` (bypassing
   `resolve_target_paths`), so **no server-side record is ever written** — the
   stub's synthetic lines *are* the whole ledger, and `validate()` (`:158-183`)
   passes them on key-presence alone. The repro, if executed, is a
   single-stub run producing a complete-looking R01 record with no harness
   having spoken. That directly falsifies the R03 matrix columns.

2. **Tool-name fabrication (silent falsification, exploitable).**
   `server/colgrep_mcp/probe.py`'s `_probe_tool_name()` frame scan resolves to
   the `record` function itself every time, so each ledger line claims
   `"tool": "record"` — a factually false value in the column that tells the
   matrix which observation fired.

3. **Non-`OSError` escape (law break, exploitable).**
   `capture_pure(record_obj)` at `probe.py:132` sits *outside* the `try`/`except
   OSError` that claims "never raises"; a non-`model_dump`, non-serializable
   snapshot key turns into a `TypeError` that travels up through the
   `resolve_target_paths` call site (`paths.py:113`) — a tool call corrupting
   the very resolve path the module docstring promises never to touch.

4. **Blind dump-only oracle (regression honesty, exploitable).**
   `test_no_probe_side_effects` deletes `COLGREP_MCP_PROBE` first
   (`test_probe.py:229`), so `record()` early-returns nothing observable;
   its sole post-call assertion re-checks an environment variable
   (`:247-251`), never reading a ledger or comparing a value. Its background
   filesystem assertions probe filenames (`probe.jsonl`, `~/colgrep_probe.jsonl`)
   that the implementation never writes (the real one is `colgrep_probe.jsonl`).
   A probe that fabricates `init_capabilities` passes the whole test.

5. **Gap-record crash (driver hygiene).** `_validate_record` (`:167-172`) keys
   on `snap["ts"]`, so the driver's own `{"error": ...}` gap record
   (`:112-118`) raises rather than reports — the driver cannot use its own
   gap signalling.

6. **Roots classification loses the `error` case (format assertion).**
   `probe.record` maps "no pin and `client_roots` returned `None`" and "`client_roots`
   dereferenced an exception" to the *same* `"empty"` value, so the matrix has
   no way to tell "the harness sent nothing" from "the round-trip failed".

## Root Cause

The leaf was authored against a dump-only contract (`R01` §Contracts & Invariants)
but its implementation was given no truth-source oracle to prove the contract:
no fixture exists that fabricates a record from *known* ground truth and
checks an independent differ catches the issued-with-barrier. The first two verifier
dispatch rounds died before delivering any output, so the defect reached
merge approval on the implementer's self-report alone. Root cause is not "the code was written
sloppily" — it is "the campaign shipped an *accreditation-based* probe
implementer without a *commissioning* artefact to build trust. A gap analysis
whose success criteria are 'the ledger correctly separates known
fabrication' would have caught lever 1 at authoring time.

## Impact Assessment

- **In scope**: the full probe chain — `probe.py` truth-source columns,
  the never-raise boundary, `test_probe.py`'s oracle fixture, `probe_workspace.py`'s
  stub-vs-server provenance and gap-record tolerance.
- **Out of scope**: `paths.py` precedence behaviour (unchanged and separately
  guarded by pre-existing resolve tests), the harness fleet run itself, any
  report already published (`00-architecture_v0.md`, `01-findings_protocol_survey_v0.md`).
- **Risk if unaddressed**: every R03 matrix cell backed by a probe run is
  unfalsifiable; a gap in the snapshot of the `_meta` station could be a stub
  default carried all the way to the milestone `02-architecture_v1.md`'s
  lowest-level decisions — the exact failure mode the earlier sponsor-called
  loud-fail+guidance discussion existed to prevent.

## Proposed Solution

A hardening leaf, `probe_hardening`, at level 1 (sibling of `probe_instrumentation`,
before `evidence/`), composed of four steps:
1. Truth-source repair of the ledger columns (`tool`, `roots_list`'s `error`
   class distinct from `empty`).
2. Non-raise hardening: make every code path in `record` total for arbitrary
   inputs (no `TypeError` can escape past `resolve_target_paths`).
3. Calibration oracle fixture (`forge_record` / `diff_record`) — a ground-truth
   record builder and an independent differ whose disagreement test must
   whistle when given the stub's exact fabrication (a committed proof the
   harness can catch a liar).
4. Provenance + gap-record hygiene in `probe_workspace.py` (stub-authored
   records marked; `{"error": ...}` gaps reported, not crashed over).
Completion requires (a) the calibration test failing against the shipped
faulty state then passing after; (b) the rebuilt dump-only oracle reading the
real ledger record and asserting verbatim equality against constructed truth;
(c) a re-run of the existing suite green; (d) a fresh adversarial verifier
signature replacing the UNSOUND one before any evidence-level dispatch.

## Recommendations

1. **Hold level 2 (`evidence/`) until this leaf lands and is adversarially
   re-verified.** A signature superseding the UNSOUND verdict is the
   pre-condition recorded in the campaign's roadmap Gotchas.
2. **Each future leaf pair (implementer + adversary) must ship a calibration
   or truth-source omelette-sized artefact alongside its feature** — briefs
   and gates verify code can be *run*; only a fixture tied to ground truth
   verifies code can be *trusted*.
3. **`forge_record` / `diff_record` are generic probe utilities, retained under
   `probe.py` (not test-only) so the evidence leaf's own matrix validator can
   reuse them** rather than hand-rolling a second, drifting differ.
