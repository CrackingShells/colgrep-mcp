# MCP Feature Matrix — Findings (v0)

Date: 2026-09-11

---
type: findings
topic: colgrep_mcp
date: 2026-09-11
version: v0
prior-version: none
key-metric: feature rows with an explicit decision: 38/38 (100%)
decision-required: confirm
---

## Headline Result

metric: adopt-now / adopt-guarded rows (the two decisions that translate into near-term implementation work)
value: 11 adopt-now + 6 adopt-guarded = 17 of 38
unit: rows
prior: N/A (first run)
direction: new

The single most consequential fact this study turned up is not in any one row: **SEP-2577 (protocol revision 2026-07-28) deprecates Roots, Sampling, and Logging simultaneously**, and the same revision removes `ping`, the `initialize` handshake, `notifications/roots/list_changed`, and the classic server-initiated-request model (replaced by a retry-based "MRTR" pattern). Three of the roadmap gate's explicitly-named feature families (sampling, roots, logging) are therefore reject/defer almost by default for a *new* server — not because they lack value today, but because the spec itself is walking away from them during colgrep-mcp's build window.

## Results Tables

### Tools

| Feature | SDK v2 API | Spec status (2025-06-18 → 2025-11-25 → 2026-07-28) | Claude Code client support | Decision | Rationale |
|---|---|---|---|---|---|
| Human-readable title | `@mcp.tool(title=...)` / `Tool.title` | stable | unknown | adopt-now | Zero-cost hint for any client's tool picker; no downside. |
| Tool annotations (`read_only_hint`, `destructive_hint`, `idempotent_hint`, `open_world_hint`) | `ToolAnnotations` via `@mcp.tool(annotations=...)` | stable | documented partial (Claude Code layers its own `anthropic/requiresUserInteraction` / `maxResultSizeChars` `_meta` on top; standard hints not explicitly confirmed as read) | adopt-now | colgrep's tools (search/status/init) are read-only or idempotent; declaring this is free and correct regardless of whether the current client acts on it. |
| Icons | `icons=[Icon(...)]` on tool/resource/prompt (SEP-973, added 2025-11-25) | new 2025-11-25, unchanged 2026-07-28 | unknown (no rendering surface documented for a CLI-first agent) | defer | Cosmetic; revisit only if a GUI client (Cursor) becomes a priority. |
| Structured output / `outputSchema` | `output_schema` on `Tool`, or Pydantic return type + `structured_content` in `CallToolResult`; `@mcp.tool(structured_output=...)` | stable, loosened 2026-07-28 (SEP-2106: any JSON Schema 2020-12 keyword; `structuredContent` allows any JSON value) | documented yes (Claude Code docs describe schema flattening/validation rules for tool responses) | adopt-now | Directly serves the product goal: an agent parsing typed JSON search hits instead of scraping formatted text saves tokens and avoids re-parsing errors. |
| Tool naming guidance (SEP-986) | none (convention only) | added 2025-11-25 | n/a | adopt-now | Free; align `search_code`/`get_index_status` etc. with the guidance to reduce agent confusion between similarly-named tools. |
| Input-required result / elicitation folded into a tool call (MRTR pattern) | `resultType: "input_required"` / `InputRequiredResult` — not exposed as a distinct SDK v2.2 helper in what we queried | new 2026-07-28 (SEP-2322), replaces the old server-initiated-request model | unknown | defer | SDK v2.2's own `elicit_form`/`create_message` still assume an open back-channel (raise `NoBackChannelError` otherwise) rather than the new retry-based pattern; nothing to build against yet. |

### Resources

| Feature | SDK v2 API | Spec status | Claude Code client support | Decision | Rationale |
|---|---|---|---|---|---|
| Static resources | `@mcp.resource(uri)` | stable | documented **no** on the assigned `code.claude.com/docs/en/mcp` page; documented **yes** on Claude Code's separate slash-commands/`@`-mention docs (`@server:protocol://path`), found via follow-up search | adopt-guarded | Could expose index status/model info as a browsable resource; check `ctx.session.client_params.capabilities.resources` before depending on it, since the page this study was told to check does not confirm the behavior and Codex/Cursor support is unconfirmed. |
| Resource templates | `uriTemplate` via `@mcp.resource("scheme://{var}")` | stable | unknown (same caveat) | defer | No concrete use case beyond what explicit tool arguments already cover; colgrep already takes paths directly. |
| Subscriptions | `resources/subscribe`/`unsubscribe` → replaced wholesale by `subscriptions/listen` in 2026-07-28 (SEP-2575) | mechanism replaced, not just deprecated | unknown | reject | No long-lived resource whose changes need pushing; the underlying wire mechanism is being rebuilt in the next revision, so building on the current one is wasted effort. |
| `notifications/resources/list_changed` | `ResourceListChangedNotification` | may fire spontaneously through 2025-11-25; needs opt-in via `subscriptions/listen` from 2026-07-28 | unknown | reject | colgrep-mcp's resource list (if any) is static per session. |
| Mime types on resources | `mime_type=` on `@mcp.resource` | stable | n/a until resources adopted | adopt-guarded | Trivial correctness item tied 1:1 to the static-resources decision above. |
| Embedded resources in tool/prompt results | `EmbeddedResource` in `CallToolResult`/prompt messages | stable | unknown ("up to the client how best to render") | adopt-guarded | Could attach a full matched-file's content as a distinct resource block instead of inlining it in text, saving tokens in the primary content channel; verify rendering before relying on it exclusively. |
| `ui://` app resources | `APP_MIME_TYPE = "text/html;profile=mcp-app"` | MCP-UI extension convention | n/a | reject | Out of scope — colgrep-mcp has no interactive UI surface, and Claude Code is CLI-first. |

### Prompts + Completions

| Feature | SDK v2 API | Spec status | Claude Code client support | Decision | Rationale |
|---|---|---|---|---|---|
| Prompts with arguments | `@mcp.prompt()` | stable | documented **no** on the assigned page; documented **yes** on Claude Code's general docs (`/mcp__<server>__<prompt>` slash commands), found via follow-up search | adopt-guarded | A `search_recipe`/`explain_result` prompt could package a canned multi-step flow as a slash command; guard because the page-of-record for this study doesn't confirm it — verify empirically before depending on it. |
| Completions | `@mcp.completion()` | stable | unknown | defer | Nice autocomplete UX, no confirmed client surface in a terminal coding agent; low priority next to the core search tool. |
| Embedded resources in prompt messages | `EmbeddedResource` inside `UserMessage` | stable | unknown | defer | Depends on both prompts and resources adoption, both already guarded/deferred; revisit together. |
| Prompts surfaced as slash commands (client behavior) | n/a | n/a | documented yes (general Claude Code docs), documented **no** on the specifically-assigned `/docs/en/mcp` page | adopt-guarded | Real value (one keystroke instead of a hand-written query), but confirm on the actual page-of-record this study was pointed at before shipping messaging that assumes it. |

### Client-initiated-by-server (sampling / elicitation / roots)

| Feature | SDK v2 API | Spec status | Claude Code client support | Decision | Rationale |
|---|---|---|---|---|---|
| `sampling.createMessage` | `ctx.session.create_message(...)` (`@deprecated`) | **deprecated 2026-07-28** (SEP-2577); migration: "integrate directly with LLM provider APIs instead" | documented no (not mentioned anywhere in Claude Code's MCP docs) | reject | Deprecated at the spec level and unconfirmed client-side; colgrep-mcp returns deterministic search results and has no need to call back into the agent's model. |
| `sampling.tools` (tool-augmented sampling) | `tools=`/`tool_choice=` params on `create_message`; gated by `check_sampling_tools_capability` | added 2025-11-25 (SEP-1577), inherits the 2026-07-28 deprecation of sampling itself | documented no | reject | Depends on a feature (sampling) that is already being deprecated; doubly speculative. |
| Elicitation — form mode | `ctx.session.elicit_form(...)` | stable core feature, not in the SEP-2577 deprecation list | documented partial (Claude Code mentions elicitation dialogs blocking background execution, implying support, but doesn't fully describe the UI) | adopt-guarded | Useful for confirming a large index build (>10k units) interactively; check `capabilities.elicitation` first and fall back to an explicit `confirm=True` tool argument when unsupported. |
| Elicitation — URL mode | `ctx.elicit_url(...)` | added 2025-11-25 (SEP-1036); its own completion-notification/id fields are removed again in 2026-07-28 (superseded by the MRTR retry pattern) — churn within one revision's lifetime | unknown | reject | Designed for OAuth/payment/credential hand-off; colgrep-mcp is a local CLI wrapper with nothing out-of-band to hand off to. |
| Roots (`roots/list`) | `ctx.session.list_roots()` (`@deprecated`) | **deprecated 2026-07-28** (SEP-2577); migration: "pass directories or files via tool parameters... instead of Roots" | documented **yes today** — Claude Code answers `roots/list` with the launch directory plus every `--add-dir` | defer | Currently supported and could auto-scope search to the workspace, but the spec's own migration guidance points at exactly what colgrep-mcp's tool arguments already do (explicit paths). Confirm with the team lead whether the (missing) architecture report assumes roots-based or path-argument-based scoping. |
| `notifications/roots/list_changed` | part of `RootsCapability` | present through 2025-11-25; carried only as an empty capability object from 2026-07-28 | documented yes today | defer | Tied to the roots decision above; moot if roots itself is deferred. |
| MRTR pattern (`InputRequiredResult`, unifies sampling/elicitation/roots requests) | not exposed as such in the SDK v2.2 surface queried | new 2026-07-28 (SEP-2322) | unknown | defer | The eventual replacement for every row in this table, but not implemented in the pinned SDK yet — nothing to adopt. |

### Transport + Lifecycle

| Feature | SDK v2 API | Spec status | Claude Code client support | Decision | Rationale |
|---|---|---|---|---|---|
| stdio transport | `mcp.run()` (default `transport="stdio"`) | stable | documented yes (primary local transport) | adopt-now | Matches the product brief exactly: a stdio-first search server for a local coding agent. |
| streamable-http transport | `mcp.run(transport="streamable-http", ...)` | stable; the recommended HTTP transport (SSE reclassified Deprecated in its favor) | documented yes (remote MCP servers, with OAuth) | defer | No remote/shared-service deployment requirement yet; revisit if colgrep-mcp ever runs as a shared process rather than per-agent local. |
| `stateless_http` mode | `mcp.run(..., stateless_http=True)` | fits the 2026-07-28 stateless redesign (no `Mcp-Session-Id`) | unknown | defer | Only relevant once/if streamable-http is adopted. |
| SSE transport | `mcp.run(transport="sse", ...)` | deprecated since 2025-03-26; formally reclassified Deprecated 2026-07-28 (SEP-2596) | unknown | reject | Spec explicitly says migrate away from it; never worth adopting new. |
| Auth / OAuth bearer tokens | `BearerAuthBackend`, `RequireAuthMiddleware`, OAuth2 client flows | stable, hardened (RFC 9207 `iss` check, Client ID Metadata Documents favored over Dynamic Client Registration) | documented yes (for remote MCP servers) | reject | Only applies to HTTP transports; colgrep-mcp is a local stdio child process with no network boundary to authenticate across. |
| Server instructions | `MCPServer(..., instructions=...)` → `InitializeResult.instructions` | present through 2025-11-25; the **entire handshake/`InitializeResult` is removed** in the 2026-07-28 stateless redesign | documented yes (folded into the system prompt) | adopt-now | Free channel to teach the agent when to reach for semantic search vs. grep without spending tool-description tokens on every call — but duplicate the essential guidance into tool descriptions too, since this exact field disappears in the next protocol revision. |
| Capability / protocol-version negotiation | `initialize()` handshake (legacy) or `server/discover` (2026-07-28); `Client(mode="auto"\|"legacy"\|pinned)` | fundamentally restructured 2026-07-28 (handshake removed, per-request `_meta` versioning, new `server/discover`) | unknown which revision Claude Code currently negotiates | adopt-now (SDK default), flag for monitoring | Handled automatically by the SDK; the actionable item is operational — track which protocol version the installed Claude Code client negotiates, since 2026-07-28 changes error codes and removes the handshake outright. |
| Lifespan context manager | `MCPServer(..., lifespan=app_lifespan)`, `ctx.request_context.lifespan_context` | SDK-level, not a wire feature | n/a (server-internal) | adopt-now | Keep the colgrep index/model warm across calls in one process instead of re-initializing per request — direct latency/cost win for a search server. |
| In-memory `Client` testing | `mcp.Client(server_instance)` in-process transport | SDK-level; replaces the removed `create_connected_server_and_client_session` helper | n/a (dev/test only) | adopt-now | Free, fast CI coverage of the tool surface without a subprocess; use `mode="legacy"` for any test exercising a deprecated (roots/sampling/elicitation) path to avoid spurious `NoBackChannelError`. |
| Logging (`logging/setLevel`, `notifications/message`) | `ctx.session.set_logging_level(...)` (`@deprecated`) | **deprecated 2026-07-28** (SEP-2577); `logging/setLevel` removed outright same revision; migration: "log to stderr (stdio) or use OpenTelemetry" | documented no (Claude Code docs don't mention displaying MCP log messages) | reject | Matches the CLI's own convention already — colgrep writes diagnostics (e.g. truncation) to stderr; no need to also implement the deprecated MCP logging capability. |
| Progress notifications (server→client) | `ctx.report_progress(...)` / `send_progress_notification` | stable server→client; client→server progress **removed** 2026-07-28 (server-to-client only from then on) | documented yes — Claude Code aborts a call with no progress after an idle window | adopt-now | colgrep's first-run indexing of a large repo can take a while; progress during `init`/first search prevents Claude Code's idle-timeout from aborting the call — this is load-bearing, not cosmetic. |
| Cancellation (`notifications/cancelled`) | built into the JSON-RPC dispatcher (`PeerCancelMode`) | stable | unknown | adopt-now | Cheap to honor; stops a long index build promptly when cancelled, saving CPU/GPU cycles. |
| Pagination (`PaginatedRequestParams`/cursor) | `list_tools(params=PaginatedRequestParams(cursor=...))` etc. | stable | unknown | defer | colgrep-mcp's tool count is small (search/init/status/settings-class commands); revisit only if the list grows enough to need paging. |
| Ping | `send_ping()` (`@deprecated`) | **removed outright 2026-07-28** | unknown | reject | A keepalive has no value for a stdio child process spawned per client session, and the spec is deleting the method anyway. |
| Experimental tasks (SEP-1686) | removed from SDK v2 (`ctx.experimental.run_task`, `TASK_REQUIRED/OPTIONAL/FORBIDDEN` all gone); replaced by a not-yet-implemented extension (SEP-2663) | moved out of core protocol entirely | unknown / n/a | reject | Not available in the pinned SDK version; colgrep's searches are fast single-shot calls that fit ordinary tool-call latency — progress notifications cover the one case (large index builds) that might otherwise want a task. |

## Observations

| Signal | Baseline / Expected | Observed [source] | Interpretation |
|---|---|---|---|
| Roadmap gate lists sampling, roots, and logging as feature families to evaluate independently | Expected each to land on a distinct adopt/defer verdict based on its own merits | All three are deprecated by the *same* SEP (SEP-2577) in the *same* protocol revision (2026-07-28) [source: `py.sdk.modelcontextprotocol_io_v2` migration doc + `modelcontextprotocol.io/specification/2026-07-28/changelog`] | Treat these three as one governance decision ("do we build on soon-to-be-removed server-initiated-request features?"), not three independent feature bets. |
| Assigned Claude Code doc URL (`code.claude.com/docs/en/mcp`) was expected to cover resources/prompts client support per the roadmap leaf's method step 3 | Expected explicit yes/no on that exact page | That page documents roots, elicitation (partially), tool annotations (via Anthropic-specific `_meta` keys), and OAuth, but says nothing about `@`-mention resources or prompt slash-commands — those are documented on other Claude Code pages instead [source: WebFetch of `code.claude.com/docs/en/mcp`, cross-checked via WebSearch] | The single assigned page is not a complete client-capability reference; any future capability check against "the docs" should specify which Claude Code doc page, not assume `/docs/en/mcp` is exhaustive. |
| Roadmap gate names "protocol-version behaviour" as a family to record | Expected incremental version negotiation changes | 2026-07-28 removes the `initialize`/`notifications/initialized` handshake entirely, replacing it with per-request `_meta` fields and a new `server/discover` RPC [source: `modelcontextprotocol.io/specification/2026-07-28/changelog`] | This is not a minor negotiation tweak — it is a different connection model. Any code that assumes `InitializeResult.instructions` or a one-time handshake needs a compatibility path before 2026-07-28 becomes the negotiated default. |
| Architecture report (`00-architecture_v0.md`) was expected to exist per the roadmap leaf's References | File referenced by the roadmap leaf and by `README.md`'s "(latest)" marker | File is **absent** from `__reports__/colgrep_mcp/` at the time of this study [source: `ls __reports__/colgrep_mcp/`] | This matrix could not be checked against or used to challenge specific architecture decisions (e.g. roots vs. explicit-path scoping); flagged as a steering question below. |

## Contradictions & Surprises

- SEP-2577 deprecates Sampling, Roots, and Logging in one motion on 2026-07-28 — a roadmap that treats them as three separate feature bets will draft three near-identical "reject, it's deprecated" rationales; worth collapsing into one shared caveat in the architecture report.
- The URL-mode elicitation fields introduced in 2025-11-25 (`elicitationId`, the completion notification) are already removed again in 2026-07-28, replaced by the MRTR retry pattern — a feature that didn't survive even one full revision cycle before being redesigned.
- `README.md` for this report topic already marked `00-architecture_v0.md` as "(latest)" even though the file does not exist in this worktree — either it exists on a branch not yet visible here, or the README was written ahead of the file landing.

## Steering Questions

- [now] Does the (still-missing) architecture report assume roots-based workspace scoping or explicit tool-argument paths for search scope? Roots is deprecated in the next protocol revision and the spec's own migration advice points at explicit paths — confirm before any leaf builds on `roots/list`.
- [now] Should the server pin `InitializeResult`/handshake behavior against protocol 2025-11-25 explicitly, given 2026-07-28 removes the handshake, `ping`, `logging/setLevel`, and `roots/list_changed` outright?
- [next run] Which protocol revision does the installed Claude Code MCP client actually negotiate today (2025-06-18, 2025-11-25, or already 2026-07-28)? That answer flips server instructions, ping, and logging from "safe to use" to "already gone" client-side.
- [next run] Is there a concrete near-term use case for elicitation form-mode (e.g. confirming a large index build) worth prototyping, or should colgrep-mcp just keep the CLI's own `-y`/prompt behavior and skip elicitation entirely?
- [later] Once `00-architecture_v0.md` exists, re-run this matrix's cross-check against its §Alternatives Considered, as the roadmap leaf originally intended.

## Pointers

- Roadmap leaf: `__roadmap__/colgrep_mcp/research_mcp_features.md`
- Architecture report referenced by the leaf: `__reports__/colgrep_mcp/00-architecture_v0.md` — **absent in this worktree at authoring time**; not consulted.
- context7 library queried: `/websites/py_sdk_modelcontextprotocol_io_v2` (Python MCP SDK v2 docs)
- Spec changelogs fetched: `https://modelcontextprotocol.io/specification/2025-11-25/changelog`, `https://modelcontextprotocol.io/specification/2026-07-28/changelog`
- Client docs fetched: `https://code.claude.com/docs/en/mcp` (roots, elicitation, tool-result `_meta` annotations, OAuth); resources `@`-mention and prompt slash-command support confirmed via a separate Claude Code docs search, not on this exact page.
- `CONTRIBUTING.md` commit convention followed for this report's commit.
