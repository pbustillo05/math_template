# Instructions for research agents

## Mission and authority

This repository is a mathematics research workspace.
Read `workflow/CURRENT.md` and the relevant topic README before starting; update them when the frontier changes.
Use the bounded research cycle below for substantive mathematical work.
Explicit user instructions take precedence over this template.
Do not invent a project direction from the demonstration theorem.
Preserve unrelated edits, source evidence, and useful failed attempts.
Commit and push only when the user requests them.

## Repository map

| Path | Material |
| --- | --- |
| `workflow/` | Problem statement, current frontier, route registry, optional task queue, reviews, and version links |
| `draft/` | Polished manuscript assembled from `draft/main.tex` |
| `notes/<topic>/` | Active SemanTeX units alongside Markdown research history and ledgers |
| `notebook/` | Optional LaTeX notebook for mathematical milestones |
| `references/KEY/` | Hash-locked original sources and editable `audit/` annotations |
| `preamble/` | Shared LaTeX environments and SemanTeX commands |
| `scripts/` | Graph, corpus, build, review, and semantic retrieval commands |
| `.agents/skills/` | Repository skills, including paper conversion |
| `tools/vscode-semantex/` | Editor navigation backed by the same index |
| `build/` | Generated PDFs, graph exports, semantic indexes, and optional downloaded model weights |

## Bounded research cycle

Recover the exact inputs listed in `workflow/CURRENT.md`. Consult `workflow/PROBLEM.md` for the governing question and assumptions, and `workflow/ROUTES.md` when choosing or revisiting a strategy.
Work on one precise question per assignment. Use its stopping condition to decide when the evidence is sufficient or when a specific obstruction should be handed back. When several routes are live, prefer a check whose outcome would materially change a route decision.
Record the argument, experiment, or counterexample in the topic notes. After a substantive round, update the affected claim or route with a pointer to the evidence, then record the next check in `workflow/CURRENT.md`.
Use [the research cycle guide](workflow/RESEARCH-CYCLE.md) for handoffs and [the user manual](USER-MANUAL.md) for examples, manuscript review, and the optional milestone notebook.

## Drafts and notes

LaTeX is the user's interface to the mathematics.
`draft/` must contain rigorous, polished final-form exposition following `writing-style.md`, even while its review status remains unreviewed.
Do not put a sketch, missing argument, agent conversation, task ledger, or optimistic claim into the draft as if it were a completed proof.
Keep incomplete work in `notes/<topic>/` and record open steps in the topic ledger.
Claims must not be silently weakened to conceal a gap.

`notes/` is the agents' personal workspace, in Markdown, LaTeX, code or other useful formats.
Organize it by topic, with a README, current status, claim/task ledger, sources and a clear next action.
Distinguish conjectures, attempted proofs, proved-but-unreviewed claims, verified counterexamples, failed candidates, and abandoned approaches.
Retain useful failure evidence; archive superseded notes with an explanation and updated links.
A note is not an accepted premise merely because it is written confidently.
Complete and polish the unit before promoting it to `draft/`. Carry its ID when moving it. If both versions are useful, use distinct IDs and record an inspected `equivalent` or `derived-from` link.

## Literature

Maintain all papers relevant to the project in `references/`, including foundational inputs, alternatives, counterexamples and uncited but relevant literature.
Prefer exact pinned TeX source; otherwise keep the original PDF and record why source was unavailable.
Follow `references/README.md`: exact DOI API metadata, actual alpha-style keys, hashes, and paper-specific `audit/` overlays.
Never invent bibliographic fields or edit retained payloads to compile them.
Use the `tex-to-semantex` skill for converting a retained paper into labelled statements and dependency annotations under its `audit/` directory.
Record inaccessible/DOI-less candidates in `references/gaps.json`; an acquisition gap remains visible until resolved.
Before relying on a theorem, read the exact statement and relevant proof, check later versions/errata, and match all hypotheses, definitions and conventions.
Cite standard theory precisely rather than recreating it for artificial self-containment.

## LaTeX and semantic structure

Read `agents/SEMANTEX.md` before editing annotations or shared tooling.
For drafts, keep package choices, macros and environments in `preamble/research.sty` and `preamble/semantex.sty`.
Use stable labels, explicit statement/proof attachments, and local logical references at their point of use.
A mention, citation or upstream label alone does not certify a premise.
Inspect affected rendered pages when layout changes; report missing tools or uninspected layout honestly.
Never call a logical DAG, a successful TeX build, a compiler receipt or a review registry a proof of mathematical truth.

## SemanTeX CLI

Run `scripts/semantex COMMAND` at the repository root. Start with `search` when you know the idea, `get` when you know the ID, and `why` when you need the exact premise use. Use `--json` for agent consumption. Navigation spans all three scopes. Use `--scope draft,notes,references` or `--paper KEY` to focus, and `--within` when a traversal must stay inside the focus.

| Commands | Use |
| --- | --- |
| `get ID [--show description\|statement\|proof\|content] [--proof all] [--latex]` and `locate ID` | Retrieve a unit, its selected proof, and exact authored and original locations. |
| `deps ID`, `rdeps ID`, `why RESULT PREMISE` | Trace declared premises and dependents. Set `--depth` or `--tree` on the traversal commands. |
| `refs ID`, `backrefs ID` | Show exact uses, including mentions and citations. |
| `order [ID]`, `frontier ID`, `fingerprint ID` | Review prerequisites, blockers, and the current review fingerprint. |
| `search QUERY --mode lexical\|semantic\|hybrid` | Find units across the corpus. Lexical search works with the standard Python installation. |
| `neighbors ID --k 16 --show labels\|description\|content` | Browse the nearest indexed units. Current equivalent versions are grouped by default. |
| `context ID… --depth N --max-chars N` | Retrieve a bounded bundle of exact source and proof blocks. |
| `link A B --relation equivalent\|derived-from`, `links ID` | Manage inspected overlap between draft, notes, and reference units. |
| `source-labels KEY`, `paper-graph KEY`, `reference-view KEY --main FILE` | Inspect and navigate original paper structure. |
| `rag profiles`, `rag setup`, `rag build`, `rag status` | View pinned profiles, explicitly fetch weights, refresh vectors, or check coverage. |
| `graph`, `export`, `check`, `check --release --target ID` | Produce diagram and JSON exports, validate the corpus, and gate manuscript release. |

For an exact source application, read the result and inspect the proof and hypotheses before citing it. For ordinary research, use graph or semantic retrieval to find candidates, then read the exact LaTeX and inspect its support. Run `make check` after structural changes and `make pdf` after draft changes. See [the command and annotation guide](agents/SEMANTEX.md) for flags and model setup.


### Work a result from notes into the draft

1. Start with `scripts/semantex search "projection fixed points" --scope notes,references`. If the relevant paper is only partly indexed, inspect its source with `source-labels` or `reference-view` and use `tex-to-semantex` for a bounded conversion.
2. Use `get ID --show content --latex` and `why RESULT PREMISE` to check the exact statement, proof, and use sites. Set `--mode semantic` when the index is available and the query is a paraphrase.
3. Write a described conjecture or result in the topic's LaTeX file and add a proof block once the argument is written. Record open steps and alternative approaches in the Markdown ledger.
4. Move the completed unit into the manuscript with its ID or inspect the two versions and record their link. Establish a cited `src:` application for any retained-paper premise and link its hypothesis-matching audit. Run structural checks, inspect the PDF, and use `frontier ID` and `check --release --target ID` to identify review or assembly gaps.

`show` aliases `get`. `ancestors` and `descendants` alias `deps` and `rdeps`. `editor-index` is the extension's index export. Use `scripts/semantex COMMAND --help` for the flags. Adjacent tools are `scripts/references.py` for corpus acquisition, `scripts/reviews.py` for review registration, and the Makefile for PDF, graph, extension, and release builds.

## Reviews and delegation

Default to one agent for routine exploration or maintenance.
When independent draft verification is requested, use `agents/PROTOCOL.md` and the role prompts in `agents/roles/`.
Ask for bounded mathematical verification, counterexample search, source checking and writing assessment as the task requires.
Give each worker a precise scope, current candidate, dependencies, output path and exclusive file ownership; keep integration serial.
Do not create a standing team, duplicate unchanged investigations, or manufacture independent reviewer identities.
A reviewer who changes the argument cannot certify that changed argument independently.
Only record reports actually produced; keep unresolved disagreements visible.
