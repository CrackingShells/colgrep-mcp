# dirtree-rdm Grammar Gotchas

`managing-roadmaps` owns `dirtree-rdm` itself and its full BNF grammar; this file only lists
the traps that matter in this repository. Before writing any leaf file or roadmap README by
hand, run:

```bash
bash ~/.claude/skills/managing-roadmaps/scripts/dirtree-rdm.sh grammar leaf
```

Read what it prints — do not guess the shape from another campaign's file and hand-edit a new
one to match; the grammar is strict and a mismatch fails validation without necessarily saying
which line is wrong.

## Traps (KT-C §Pain Points)

- **`## Reference Documents` bullets must start `[R<nn> …]`.** A bullet phrased any other way
  (e.g. starting with the document title instead of the tag) is rejected.
- **Nothing may follow `(expected: PASS)` on a Consistency Checks line.** No trailing note, no
  second sentence, no parenthetical after it — put any caveat before the `(expected: PASS)`
  marker or drop it.
- **Step headings are exactly `## Step 1`, `## Step 2`, … `## Step N`.** No alternate wording,
  no combined steps, no zero-indexing.
- **Status tables are written only by `dirtree-rdm`.** The Mermaid graph, the Nodes table, and
  the Progress table in a roadmap README are tool output — never hand-edit them, even to fix a
  typo or record a merge a moment early; run the tool's update command instead.

## Why this matters for a lead

A grammar failure caught at `dirtree-rdm validate` time is cheap. A grammar failure caught
after three implementers have already been dispatched against a malformed roadmap is a wasted
cycle. Run the grammar check and `dirtree-rdm validate` before committing specs, not after.
