# Commitizen gotchas

The validator and bump machinery in `server/pyproject.toml`
`[tool.commitizen]` / `[tool.commitizen.customize]` behave slightly
differently from what their flags suggest. Each row below was found by
deliberately probing the validator with an invalid input, not by reading
valid history — `cz check --rev-range` only ever sees commits that already
passed, so it cannot show you a rejection. (`KT-H` §Pain Points, `OBS-H`
findings 1-3.)

| Symptom | Cause | What to do |
|:--|:--|:--|
| The incremental changelog duplicates or garbles old entries after `cz bump --changelog` | `changelog_incremental = true` cannot parse hand-written Keep-a-Changelog headings (`## [0.1.0] - 2026-...`) the way it parses its own generated ones | Never hand-edit a released section of `CHANGELOG.md`; `tests/test_changelog.py` pins the parseable shape — if it goes red, the file was edited by hand, fix the file |
| `cz bump --changelog --dry-run` gives no file list | The dry-run only prints the version bump and the changelog diff, not which files `version_files` will touch | After a real bump, read `git status --porcelain` to see what changed, or trust the `version_files` list in `[tool.commitizen]` directly |
| `feat(search)!: rename x` is accepted by `cz check` but the next `cz bump` still computes a MINOR release | `bump_map` keys on `^.+!$` against the *change type prefix*, and the customize `schema_pattern` allows the trailing `!`, but nothing here inspects a footer — only a `BREAKING CHANGE:` footer line trips the `MAJOR` bump | For a breaking change, add a `BREAKING CHANGE:` footer; do not rely on the `!` alone to bump major |
| A subject with a trailing period (`chore(repo): tidy.`) is accepted somewhere it shouldn't be | `schema_pattern` needs its `$` end-anchor for the "no trailing period" rule to actually reject; a pattern missing the anchor lets a period slip through because the message group can match a prefix | Trust `probe_cz_check.sh`'s reject list over reading the regex by eye; if a probe subject that should reject now passes, the pattern regressed |
| A deliberately malformed subject seems to pass when checked against branch history | `cz check --rev-range <a>..<b>` only ever sees commits that were already accepted onto the branch — it cannot demonstrate a rejection | Probe with `cz check --message "<subject>"` (see `scripts/probe_cz_check.sh`), never with `--rev-range`, when you want to confirm the validator actually rejects something |
