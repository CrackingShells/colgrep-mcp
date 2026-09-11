# MCP Feature Matrix Study

**Goal**: Produce a systematic matrix of every MCP server-side and client-side feature (spec revisions 2025-06-18, 2025-11-25, 2026-07-28) with its Python SDK v2.2 support status, its Claude Code / Codex / Cursor client support status, and an adopt / defer / reject decision for colgrep-mcp with a one-line rationale each.
**Pre-conditions**:
- [ ] context7 MCP server reachable (library id `/websites/py_sdk_modelcontextprotocol_io_v2`)
- [ ] Web access to modelcontextprotocol.io specification pages
**Success Gates**:
- ✅ [static] Report exists at `__reports__/colgrep_mcp/01-findings_mcp_feature_matrix_v0.md` following the `findings` report type (front matter, Headline Result, Results Tables, Observations, Steering Questions, Pointers)
- ✅ [static] Matrix rows cover at minimum: tools (annotations, title, icons, structured output/outputSchema, input-required/elicitation-in-result), resources (static, templates, subscriptions, list_changed, mime types, embedded resources in tool results), prompts (arguments, completions, embedded resources), logging (setLevel, notifications), progress, cancellation, pagination, ping, roots, sampling (incl. sampling.tools), elicitation (form + url), tasks (experimental, removed in SDK v2), server instructions, capability negotiation, protocol-version behaviour, transports (stdio, streamable-http, stateless), auth
- ✅ [static] Every row has an explicit Decision column value in {adopt-now, adopt-guarded, defer, reject} and a rationale that names the agent-facing benefit or the blocker
**References**: [R01 §Contracts](../../__reports__/colgrep_mcp/00-architecture_v0.md) — the feature set the architecture already assumes; confirm or challenge it

## Step 1: Build and write the feature matrix
**Goal**: Give the team a single authoritative table so every implementation leaf can cite a row instead of re-deriving what MCP offers.
**Implementation Logic**:
1. Query context7 (`/websites/py_sdk_modelcontextprotocol_io_v2`) for each feature family listed in the gates; record the exact SDK v2 API (decorator, `Context` method, type name) that exposes it, and any deprecation note (e.g. roots deprecated 2026-07-28; server-initiated requests raise `NoBackChannelError` on the 2026-07-28 protocol; experimental tasks removed in v2).
2. Fetch the MCP specification pages for 2025-11-25 and 2026-07-28 changelogs to confirm what changed between revisions.
3. For client support, check Claude Code docs (`https://code.claude.com/docs/en/mcp`) for: roots, sampling, elicitation, resources (`@`-mention), prompts (slash commands), tool annotations display, progress display, logging display. Record "documented yes / documented no / unknown" — never guess.
4. Decide per row with colgrep-mcp's purpose in mind: a search server for coding agents, stdio-first, run under Claude Code. Guarded adoption means: use it only after checking `ctx.session.client_params.capabilities` (or equivalent) and degrade gracefully.
5. Write the report with the `writing-reports` skill's `findings` template. Keep tables ≤ 20 rows each (split by family). End with ≤ 5 steering questions for the team lead.
**References**: [R01 §Alternatives Considered](../../__reports__/colgrep_mcp/00-architecture_v0.md) — decisions already taken that the matrix should confirm or contest
**Deliverables**: `__reports__/colgrep_mcp/01-findings_mcp_feature_matrix_v0.md` (sections: Headline Result, Tools table, Resources table, Prompts+Completions table, Client-initiated-by-server table [sampling/elicitation/roots], Transport+Lifecycle table, Observations, Steering Questions, Pointers); `__reports__/colgrep_mcp/README.md` updated with the new round-01 entry
**Consistency Checks**: `grep -c "adopt-now\|adopt-guarded\|defer\|reject" __reports__/colgrep_mcp/01-findings_mcp_feature_matrix_v0.md` (expected: PASS)
**Commit**: `docs(reports): add MCP feature matrix study for colgrep-mcp scope`
