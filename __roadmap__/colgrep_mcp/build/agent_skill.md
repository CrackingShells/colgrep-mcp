# Agent Usage Skill

**Goal**: Ship the plugin's `skills/colgrep-search/SKILL.md` — the progressive-disclosure guidance that teaches an agent *when* and *how* to use the colgrep MCP tools (and the shared `guide.md` resource text the server serves at `colgrep://guide`), so the tool descriptions can stay short.
**Pre-conditions**:
- [ ] `scaffold_package` merged
**Success Gates**:
- ⬜ [static] `skills/colgrep-search/SKILL.md` has YAML frontmatter with `name: colgrep-search` and a `description` that names concrete triggers (questions about where/how code does something, mapping a codebase, finding call sites, before refactoring) and states the anti-pattern (shell grep/rg for meaning-based questions)
- ⬜ [static] `server/colgrep_mcp/guide.md` exists, ≤ 250 lines, and `SKILL.md` links to it via the resource URI `colgrep://guide` and by relative path
- ⬜ [run] `cd server && uv run python -c "import importlib.resources as r; print(len(r.files('colgrep_mcp').joinpath('guide.md').read_text()))"` prints a number > 1000
**References**: [R01 §Tools](../../../__reports__/colgrep_mcp/00-architecture_v0.md) — the exact tool names and arguments to teach; [R01 §Prompts](../../../__reports__/colgrep_mcp/00-architecture_v0.md) — the explore/locate/impact workflows the skill should describe in prose; the user's existing session-start policy hook `/Users/hacker/.claude/hooks/colgrep_session_context.py` — read it to reuse the hard-won guidance about `-k`, `-e`, exhaustive vs exploratory, and translate CLI flags into tool arguments

## Step 1: Write guide.md and SKILL.md
**Goal**: Give agents a short, correct mental model of hybrid semantic search through MCP tools.
**Implementation Logic**:
`guide.md` (served as `colgrep://guide` and packaged via hatch `[tool.hatch.build.targets.wheel] include`/`force-include` so `importlib.resources` finds it): sections — What colgrep indexes (code units: functions, classes, methods, markdown sections; 27 languages); Choosing a tool (`search` vs `find_files` vs `expand`; `index_status`/`index_build` for cold repos); Writing queries (natural language describing behaviour, not identifiers; when you know an identifier add `pattern`; `fixed_string` for literal strings with regex metacharacters; `whole_word`); Scoping (`paths`, `include` globs like `*.py`, `exclude_dir` like `node_modules`); Result size (`limit` 10–25 exploring; omit for exhaustive; `snippet_lines`; `include_code` off by default; `expand` for the few hits that matter); Reading results (`hit_id` format, score is relative not absolute, `truncated` flag); Anti-patterns (grep for "where is X handled", reading whole files after a search, re-running identical searches). Keep it dense and imperative; ≤ 250 lines.
`SKILL.md`: frontmatter `name`, `description` (trigger-rich, ≤ 1024 chars); body ≤ 120 lines: a decision table (question type → tool + arguments), the three workflows from R01 §Prompts in prose, one worked example per workflow showing tool calls as JSON arguments, and a pointer to `colgrep://guide` for details. Do not restate the whole guide.
**References**: [R01 §Token-budget invariant](../../../__reports__/colgrep_mcp/00-architecture_v0.md) — explain truncation and expand to the agent
**Deliverables**: `skills/colgrep-search/SKILL.md`, `server/colgrep_mcp/guide.md`, `server/pyproject.toml` (hatch include for `guide.md`)
**Consistency Checks**: `cd server && uv run python -c "import importlib.resources as r; assert len(r.files('colgrep_mcp').joinpath('guide.md').read_text())>1000"` (expected: PASS)
**Commit**: `docs(skill): add colgrep-search skill and agent guide resource text`
