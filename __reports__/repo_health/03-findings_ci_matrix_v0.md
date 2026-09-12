# repo_health — Findings (v0): first CI matrix runs

Date: 2026-09-12

---
type: findings
topic: repo_health
date: 2026-09-12
version: v0
prior-version: none
key-metric: windows-test-failures: 0 (prior: N/A, delta: N/A)
decision-required: none
---

## Headline Result

metric: pytest failures on windows-latest
value: 0
unit: tests (of 197)
prior: N/A (first run: 73; after fixture wrapper: 19)
direction: new

## Results Tables

### CI runs on `CrackingShells/colgrep-mcp`, 2026-09-12 (UTC times)

| Run | Trigger | ubuntu | macos | windows | What changed before it |
|:--|:--|:--|:--|:--|:--|
| 34688701410 | push main (first) | ✅ 23 s | ✅ 20 s | ❌ 73 failed | first push of the repository |
| 34689028245 | push main | ❌ set-up | ❌ set-up | ❌ set-up | `setup-uv@v10` (no such moving tag) |
| 34689083161 | push main | ✅ | ✅ | ❌ 73 failed | `setup-uv@v10.1.0` |
| 34689095476 | PR #1, push 1 | — | ✅ | ❌ 19 failed | `.cmd` wrapper for the fake binary |
| 34689816367 | PR #1, push 2 | ✅ | ✅ | ✅ 62 s | UTF-8/LF stdio in the fake, drive-rooted fixture paths, guarded `_normalize_status_path` |
| 34689923102 | push main (merge) | ✅ 17 s | ✅ 18 s | ✅ 62 s | PR #1 integrated as c51c8aa |

### Windows failure causes

| Cause | Tests affected | Layer | Fix |
|:--|:--|:--|:--|
| `CreateProcess` cannot spawn a `.py` file (`WinError 193`) | 73 (everything downstream of the fake) | test fixture | `.cmd` wrapper under `tmp_path`, `win32` only |
| Console codepage cannot encode the fake's emoji; `\n`→`\r\n` breaks the stats regex | 2 direct, more indirect | test fake | `sys.stdout.reconfigure(encoding="utf-8", newline="\n")` |
| `/tmp/...` literals are not absolute and render with backslashes | ≈14 | test data | `tests/fixture_paths.py` OS-aware constants; compare as `Path` |
| `_normalize_status_path` prepends `/` to an already drive-rooted path | 3 (`colgrep://status/{+path}`) | **server** | guarded `win32` branch recognising `[A-Za-z]:[/\\]` |

## Observations

| Signal | Baseline / Expected | Observed [source] | Interpretation |
|:--|:--|:--|:--|
| Server code on Windows | unknown (R01 Risk 3; 0.1.1 retrospective open question) | one guarded fix in `resources.py`; adapter, locks, paths needed nothing [PR #1 diff] | the launcher claim holds: the server is portable, the *fake* was not |
| `setup-uv` versioning | moving major tags track releases | tags stop at `v7`, releases reach `v10.1.0` [gh api] | pin exact release tags for this action |
| Windows job duration | comparable to POSIX | 62 s vs 17–20 s [runs above] | acceptable; no action |
| Merge vs PR state | PR auto-closes on merge | stayed OPEN after a rebase-then-merge [gh pr view] | rebasing rewrites the PR's SHAs; close manually with a pointer, or merge the PR's own SHAs |

## Steering Questions
- [later] Run the real-binary e2e driver on a Windows machine with `colgrep.exe` once one is available; CI only exercises the fake.
- [later] Decide whether the `commits` job should also run on pushes to `main` (today it runs on pull requests only, so a direct push is never linted in CI).

## Pointers
- Runs: https://github.com/CrackingShells/colgrep-mcp/actions
- PR #1: https://github.com/CrackingShells/colgrep-mcp/pull/1 — integrated as `c51c8aa`
- `.github/workflows/ci.yml`; `server/tests/conftest.py`, `server/tests/fixture_paths.py`, `server/colgrep_mcp/resources.py`
- Prior: `02-knowledge_transfer_v0.md` §Open Questions ("Does the Windows matrix job pass?")
