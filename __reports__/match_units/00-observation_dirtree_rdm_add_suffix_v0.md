# Match Units — Observation: `dirtree-rdm add` without `.md` writes a row its validator rejects (v0)

Date: 2026-11-01

---
type: observation
topic: match_units
spotted-during: authoring the match_units roadmap (Phase 0) with dirtree-rdm 1.2.0
date: 2026-11-01
domain: code
confidence: confirmed
urgency: low
deferred-because: the tool lives in the managing-roadmaps plugin, not in this repository; passing `.md` works around it
---

## What Was Noticed
- `dirtree-rdm add __roadmap__/<campaign>/<leaf> --title "…"` (no `.md`) creates `<leaf>.md`. Post-write validation of the parent README then fails, so the README is not updated.
- The result is an orphan leaf file that no Nodes row lists.
- The error points at the next table, not at the row that was written:

  ```
  line 29: got: "| `unit_pipeline` | 📄 Leaf Task | ⬜ Planned |"
           expected form: | ID | Date | Source | Nodes Added | Rationale |
  ```

- The same command with `<leaf>.md` succeeds, and the row reads `` `unit_pipeline.md` ``.

## Context
- The aim was to bootstrap `__roadmap__/match_units/` with `init`, then `add` for three nodes.
- The first two attempts failed this way. Filling the README prose in between made no difference.
- Passing the suffix fixed it.

## Location Map
- managing-roadmaps plugin 1.2.0: `skills/managing-roadmaps/scripts/dirtree-rdm.sh` (wrapper) and the compiled binary it dispatches to.
- The CLI doc's `add` examples pass `.md` (`references/dirtree-cli.md`, "add — Create a new node"). Its synopsis is `add <node-path> [--type leaf|dir]`.
- Grammar productions: `<table-header-amendment>`, `<table-header-progress>`, and the Nodes row production (`dirtree-rdm grammar`).

## Evidence
- Failing row: `` | `unit_pipeline` | 📄 Leaf Task | ⬜ Planned | ``. Accepted rows in other campaigns: `` | `regenerate_manifests.md` | 📄 Leaf Task | ✅ Done | ``.
- After each failure the leaf file existed on disk and the README was unchanged (atomic commit skipped). Deleting the orphan and retrying with `.md` worked.

## Re-observation Steps
1. `dirtree-rdm init __roadmap__/demo` in a scratch repo with an `__roadmap__/` directory.
2. `dirtree-rdm add __roadmap__/demo/task_a --title "Task A"`: validation fails, and `task_a.md` is left behind.
3. `dirtree-rdm add __roadmap__/demo/task_b.md --title "Task B"`: succeeds.

## Hand-off Questions
Working theory: `add` derives the file name with `.md` appended for leaves, but writes the Nodes cell from the raw argument. The Nodes row grammar requires a `.md` (leaf) or `/` (directory) suffix, so a bare name breaks out of the table, and the parser reports it at the next header.
- Should `add` normalise a bare leaf path to `<name>.md` everywhere, or refuse it before creating the file?
- Should a failed post-write validation remove the file it just created, so nothing is orphaned?
- Can the validator report "unrecognised Nodes row" at the row, instead of a header mismatch at the next table?

## Scope Boundary
This report does not authorise changes to this repository's roadmaps or to the managing-roadmaps plugin's other commands. A fix belongs in the plugin's own repository, with its own tests.
