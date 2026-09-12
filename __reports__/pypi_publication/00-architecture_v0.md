# pypi_publication — Architecture Analysis (v0)

Date: 2026-09-12

Report id in this campaign: **R01 (pypi_publication)**. Earlier campaigns' reports are cited by the ids in `AGENTS.md` §Report ids.

## Executive Summary
- **Problem**: every manifest launches `uv run --quiet --directory <ROOT>/server colgrep-mcp` with the ecosystem's root placeholder in `args`. Claude Code expands `${CLAUDE_PLUGIN_ROOT}` (verified, repo_health `04-findings_remote_install_v0.md`); Codex reads the same file and its expansion is unverified; Agent Plugins 1.0 clients are unverified too. Where the placeholder stays literal, `uv` is told to run in a directory named `${CLAUDE_PLUGIN_ROOT}/server` and the server never starts — the PI reports exactly this. Three retrospectives carried "publish to PyPI so manifests become `uvx colgrep-mcp`" without doing it (colgrep_mcp `03-knowledge_transfer_v0.md` §32, repo_health `02-…` §32, dev_plugin `03-…` §36); the blocker was credentials, which PyPI trusted publishing removes.
- **Proposed change**: (1) a `publish.yml` workflow that builds and uploads to PyPI through trusted publishing when the `cz bump` tag is pushed — the human's last release step already; (2) complete the package metadata so the PyPI page is usable (`server/README.md`, `[project.urls]`, `LICENSE` in the wheel); (3) every manifest launches `uvx colgrep-mcp==<version>`, pinned by `cz bump`, with no placeholder in `args`; (4) the README makes the clone path first class with `uv tool install` (no per-start resolution) and `uvx --from <clone>/server`, next to the PyPI path.
- **Non-goals**: no change to the tool surface; no TestPyPI stage (one account, one publisher — the dry-run oracle is `uv build` + `twine check --strict` on every PR instead); no server-side tolerance for literal `${…}` in `COLGREP_MCP_ROOT` (rejected in D6); no Codex end-to-end verification (still no Codex CLI here).
- **Biggest risks**: R1 the trusted publisher on PyPI is misconfigured and the first tag push fails after the tag exists; R2 the plugin loaded from a clone runs the PyPI version, not the tree, and a maintainer trusts the wrong gate; R3 a pinned version that is not on PyPI yet (a tag pushed but publish failed) makes the plugin unlaunchable until fixed.
- **Validation**: the existing gates; new drift tests (manifest argv, pinned version = pyproject, `server/LICENSE` = `LICENSE`, both READMEs' tool tables); a scratch-clone `cz bump` run diffed before trusting the new `version_files`; the `build` CI job.

## Current State
```mermaid
graph LR
    subgraph manifests
        CM[.claude-plugin/mcp.json<br/>uv run --directory ${CLAUDE_PLUGIN_ROOT}/server]
        AM[mcp.json<br/>uv run --directory ${PLUGIN_ROOT}/server]
    end
    CC[Claude Code] -->|expands| CM
    CX[Codex] -.unverified.-> CM
    AP[Agent Plugins clients] -.unverified.-> AM
    CM --> UV[uv run … colgrep-mcp]
    AM --> UV
    UV -->|placeholder literal| X((server never starts))
    REL[cz bump → git push main vX.Y.Z] --> GH[(GitHub tag)]
    GH -.nothing listens.-> N((no artefact anywhere))
```

## Proposed State
```mermaid
graph LR
    subgraph release["release (human, unchanged recipe)"]
        B[cz bump --changelog] --> P[git push origin main vX.Y.Z]
    end
    P -->|push tags v*| W[publish.yml]
    subgraph W[publish.yml]
        J1[build: tag == pyproject, on main, uv build, twine check] --> J2[publish: environment pypi, id-token, pypa/gh-action-pypi-publish]
        J2 --> J3[github-release: notes from CHANGELOG section, dist attached]
    end
    J2 --> PYPI[(PyPI colgrep-mcp)]
    subgraph manifests["manifests (one argv, no placeholder in args)"]
        CM[.claude-plugin/mcp.json<br/>uvx colgrep-mcp==X.Y.Z<br/>env COLGREP_MCP_ROOT=${CLAUDE_PROJECT_DIR}]
        XM[.codex-plugin/mcp.json<br/>uvx colgrep-mcp==X.Y.Z]
        AM[mcp.json<br/>uvx colgrep-mcp==X.Y.Z]
    end
    PYPI --> CM & XM & AM
    subgraph clone["from a clone (first class)"]
        TI[uv tool install ./server → colgrep-mcp on PATH]
        UF[uvx --from ./server colgrep-mcp]
        UR[uv run --directory ./server colgrep-mcp]
    end
```

## Key Flow: a release reaches a user
```mermaid
sequenceDiagram
    participant H as human
    participant G as GitHub
    participant W as publish.yml
    participant P as PyPI
    participant C as client (any ecosystem)
    H->>H: cd server && uv run cz bump --changelog
    Note over H: rewrites pyproject, uv.lock, 4 plugin.json, 3 mcp.json pins, CHANGELOG
    H->>G: git push origin main vX.Y.Z
    G->>W: push tags v*
    W->>W: build: refuse unless tag == v<pyproject version> and commit ∈ main
    W->>W: uv build server; twine check --strict
    W->>P: OIDC token (environment pypi) → upload sdist + wheel (+ attestations)
    W->>G: gh release create vX.Y.Z dist/* --notes-file <CHANGELOG section>
    C->>C: plugin update → manifest says uvx colgrep-mcp==X.Y.Z
    C->>P: uvx resolves the pin once, caches the environment
    C->>C: colgrep-mcp starts; no placeholder involved
```

## Contracts

### C1 — publish trigger
`on: push: tags: ["v[0-9]+.[0-9]+.[0-9]+"]`. The tag is the one `cz bump` writes (`tag_format = "v$version"`), and pushing it is already the deliberate, manual, never-scripted last step of the release recipe (`landing-and-release` §Release, `release.sh` refuses to push). No `workflow_dispatch`: a dispatch on `main` would either re-upload an existing version (PyPI rejects, harmless) or upload an unreleased tree under a released number (PyPI rejects too, but only because the number exists) — it adds a knob with no successful path.

### C2 — build job guards
Before building, the job fails unless `v<pyproject version> == $GITHUB_REF_NAME` and `git merge-base --is-ancestor $GITHUB_SHA origin/main`. A tag on the wrong commit, or on a branch, is the one way a wrong version ships, and PyPI file names are burned forever; failing before upload costs nothing.

### C3 — trusted publishing
`pypa/gh-action-pypi-publish@release/v1` in a job with `environment: pypi` and `permissions: id-token: write`, downloading `dist/` from the build job — the split PyPI's own guide prescribes so the OIDC-privileged job runs no build code. Attestations are on by default. The trusted publisher the PI registers on PyPI is exactly: owner `CrackingShells`, repository `colgrep-mcp`, workflow `publish.yml`, environment `pypi`.

### C4 — GitHub Release
After a successful upload, `gh release create <tag> dist/* --notes-file` with the tag's own `## vX.Y.Z (date)` section of `CHANGELOG.md`. Ceremony-test verdict: borderline — it shortens no agent command (agents read `CHANGELOG.md`), but it is where humans look for a version, the artefacts attached are the ones on PyPI, and the release page is the only place the PyPI-attested files and the changelog meet. Separate job, `contents: write` only there; drop the job and nothing else changes.

### C5 — package metadata
`[project.urls]` (Homepage, Repository, Changelog, Issues); `server/LICENSE` is a byte copy of `LICENSE` (hatchling ignores a `../LICENSE` glob without error — probed on 2026-09-12: no `License-File` in METADATA), guarded by a drift test; `server/README.md` becomes the PyPI page (quick start, the tools table in the same `### Tools` shape as the root README so `test_readme.py` guards both).

### C6 — manifests
Every manifest: `"command": "uvx"`, `"args": ["colgrep-mcp==<version>"]`. The pin is a `version_files` target so `cz bump` moves it; the plugin version and the server version are the same number by construction, and a plugin update changes uvx's cache key so a stale environment is never reused. Placeholders survive only in `env`, only in the Claude Code manifest (`COLGREP_MCP_ROOT=${CLAUDE_PROJECT_DIR}`), because Codex now has its own `.codex-plugin/mcp.json` with no `env` at all. `UV_PROJECT_ENVIRONMENT` goes: uvx manages its own tool cache.

### C7 — the clone path
`uv tool install /path/to/clone/server` puts a `colgrep-mcp` executable on `PATH` with no per-start resolution — the answer for anyone who will not pay uvx's startup; `uvx --from /path/to/clone/server colgrep-mcp` for a one-off; `uv run --quiet --directory /path/to/clone/server colgrep-mcp` for development (editable, picks up edits). `claude --plugin-dir <clone>` launches the PyPI pin, not the tree — the gate in `AGENTS.md` says so.

## Decision Table

| Decision | Options | Chosen | Why |
|:--|:--|:--|:--|
| D1 trigger | tag push; `release: published`; push to `main` filtered on `release(…)` subject; `workflow_dispatch` | **tag push** | The tag push is already the manual last step; a GitHub Release as trigger would add a step to the recipe and duplicate the changelog; subject filtering is fragile; dispatch has no successful path (C1) |
| D2 uploader | `pypa/gh-action-pypi-publish`; `uv publish --trusted-publishing always` | **pypa action** | What PyPI's trusted-publisher docs name; attestations by default; `uv publish` would save one action but its attestation support is not something to verify on a first release |
| D3 TestPyPI stage | yes; no | **no** | Second publisher and account for one maintainer; `uv build` + `twine check --strict` on every PR catches metadata before a tag exists (the failure TestPyPI would catch) |
| D4 pin the version in manifests | `uvx colgrep-mcp`; `uvx colgrep-mcp==X` | **pinned** | Unpinned, uvx never upgrades a cached tool environment: the plugin would update and keep running the old server. Pinned, plugin version = server version and the cache key moves with it |
| D5 Claude Code manifest | keep `uv run --directory ${CLAUDE_PLUGIN_ROOT}/server` (runs the plugin's own tree); `uvx` like the others | **uvx** | One launch argv is the invariant `test_manifests.py` already pins; the PI's failure is the placeholder; the tree-running path stays available by hand (C7) and is named in the AGENTS gate |
| D6 tolerate literal `${…}` in `COLGREP_MCP_ROOT` | yes; no | **no** | After C6 only the Claude Code manifest carries a placeholder, in a client that expands it; the current failure text already names the literal root (`Default root ${…} (from env) does not exist`) |
| D7 GitHub Release | yes; no | **yes, separate job** | C4 |
| D8 build check in `ci.yml` | yes; no | **yes** | Removes the failure "tag pushed, publish fails on metadata, version burned" |
| D9 `server/LICENSE` | copy + drift test; `force-include` gymnastics; nothing | **copy + drift test** | AGPL requires the text to travel with the distribution; hatchling cannot reach above the project root |

## Risks & Mitigations

| # | Risk | Likelihood | Impact | Mitigation |
|:--|:--|:--|:--|:--|
| R1 | Trusted publisher misconfigured; first `v0.3.0` push fails at upload | medium | the tag exists, PyPI has nothing; re-run the workflow after fixing PyPI — no version is burned because nothing uploaded | C3 names the exact quadruple; the `pypi` environment is created on first run; the build job's guards run before any upload |
| R2 | A maintainer runs `claude --plugin-dir . mcp list` and reads "Connected" as a verdict on the tree | high | wrong gate trusted | AGENTS.md gate line rewritten; `stack-traps` gets a symptom row |
| R3 | Pin points at a version not on PyPI (publish failed, tag exists) | low | plugin unlaunchable until publish succeeds | R1's re-run; the pin is correct by construction the moment upload succeeds |
| R4 | `version_files` regex for the pin rewrites nothing or too much | medium | manifests drift from pyproject | scratch-clone `cz bump` run diffed before landing (this cycle); `test_version.py` pins the three mcp.json versions |
| R5 | uvx first start downloads the package on a machine without network | low | slow/failed first start | README: `uv tool install colgrep-mcp` once, then `command: colgrep-mcp` |

## What the PI does by hand (once)
1. PyPI → account → Publishing → "Add a new pending publisher": PyPI project name `colgrep-mcp`, owner `CrackingShells`, repository `colgrep-mcp`, workflow name `publish.yml`, environment name `pypi`.
2. Optionally protect the `pypi` GitHub environment (Settings → Environments → `pypi` → required reviewers) — the workflow creates it unprotected on first run otherwise.
3. Merge this branch, then the usual `release.sh --run` and `git push origin main v0.3.0` from the main checkout. The push publishes.

## Pointers
- Prior decision this reverses: colgrep_mcp `00-architecture_v0.md` §Decision table "Distribution: dir + `uv run` now, PyPI later".
- Placeholder rules per ecosystem: repo_health `00-findings_launch_placeholders_v0.md`.
- Release recipe and why the push is manual: `dev/skills/landing-and-release/SKILL.md` §Release.
