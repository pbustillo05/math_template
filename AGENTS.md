# Instructions for research agents

## Mission and authority

This repository is a mathematics research workspace.
Read `workflow/CURRENT.md` and the relevant topic README before starting; update them when the frontier changes.
Explicit user instructions take precedence over this template.
Do not invent a project direction from the demonstration theorem.
Preserve unrelated edits, source evidence, and useful failed attempts.
Commit and push only when the user requests them.

## Drafts and notes

LaTeX is the user's interface to the mathematics.
`draft/` must contain rigorous, polished final-form exposition following `writing-style.md`, even while its review status remains unreviewed.
Do not put a sketch, missing argument, agent conversation, task ledger, or optimistic claim into the draft as if it were a completed proof.
Keep incomplete work in `notes/<topic>/`; use a visible `\sorry` only when the user deliberately requests an incomplete manuscript checkpoint.
Claims must not be silently weakened to conceal a gap.

`notes/` is the agents' personal workspace, in Markdown, LaTeX, code or other useful formats.
Organize it by topic, with a README, current status, claim/task ledger, sources and a clear next action.
Distinguish conjectures, attempted proofs, proved-but-unreviewed claims, verified counterexamples, failed candidates, and abandoned approaches.
Retain useful failure evidence; archive superseded notes with an explanation and updated links.
A note is not an accepted premise merely because it is written confidently.
Promote a result to the draft only after completing its argument and polishing the whole unit.

## Literature

Maintain all papers relevant to the project in `references/`, including foundational inputs, alternatives, counterexamples and uncited but relevant literature.
Prefer exact pinned TeX source; otherwise keep the original PDF and record why source was unavailable.
Follow `references/README.md`: exact DOI API metadata, actual alpha-style keys, hashes, and paper-specific `audit/` overlays.
Never invent bibliographic fields or edit retained payloads to compile them.
Record inaccessible/DOI-less candidates in `references/gaps.json`; an acquisition gap remains visible until resolved.
Before relying on a theorem, read the exact statement and relevant proof, check later versions/errata, and match all hypotheses, definitions and conventions.
Cite standard theory precisely rather than recreating it for artificial self-containment.

## LaTeX and semantic structure

Read `agents/SEMANTEX.md` before editing annotations or shared tooling.
For drafts, keep package choices, macros and environments in `preamble/research.sty` and `preamble/semantex.sty`.
Use stable labels, explicit statement/proof attachments, and local logical references at their point of use.
A mention, citation or upstream label alone does not certify a premise.
Run `make check` after structural changes and `make pdf` after draft changes.
Inspect affected rendered pages when layout changes; report missing tools or uninspected layout honestly.
Never call a logical DAG, a successful TeX build, a compiler receipt or a review registry a proof of mathematical truth.

## Reviews and delegation

Default to one agent for routine exploration or maintenance.
When independent draft verification is requested, use `agents/PROTOCOL.md` and the role prompts in `agents/roles/`.
Ask for bounded mathematical verification, counterexample search, source checking and writing assessment as the task requires.
Give each worker a precise scope, current candidate, dependencies, output path and exclusive file ownership; keep integration serial.
Do not create a standing team, duplicate unchanged investigations, or manufacture independent reviewer identities.
A reviewer who changes the argument cannot certify that changed argument independently.
Only record reports actually produced; keep unresolved disagreements visible.
