# colgrep-mcp-dev

The maintainer's dev environment for this repository, packaged as a Claude Code
plugin of skills. Human projects say "install the dev environment" in
CONTRIBUTING; here the dev environment is knowledge, and this is how an agent
installs it:

```bash
claude --plugin-dir ./dev                     # from a clone
claude plugin install colgrep-mcp-dev@cracking-shells  # from the repo's own marketplace
```

The product plugin (`colgrep-mcp`, repository root) never ships these skills;
end users of the search tools have no use for them. `AGENTS.md` lists each
skill and when it fires. Each skill follows skill-creator's progressive
disclosure: a short `SKILL.md` whose description says when to load it,
`references/` for depth, `scripts/` for mechanical steps, `evals/` cases
(under `dev/evals/`) for triggering checks.
