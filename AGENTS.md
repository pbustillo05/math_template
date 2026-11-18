# Instructions for research agents

This repository is a mathematics research workspace. Read [the current frontier](workflow/CURRENT.md) and the relevant topic README before starting; update them when the frontier changes. Explicit user instructions take precedence over this template. Do not invent a project direction from the demonstration theorem. Preserve unrelated edits, source evidence, and useful failed attempts. Commit and push only when the user requests them.

## Where to write

**Markdown research notes are AI-owned and written for AI readers only.** Use them for ideas, brainstorming, informal sketches, plans, open questions, audits, reviews and handoffs.

**Write every precise mathematical definition, construction, statement, conjecture and proof in a described SemanTeX unit in a `.tex` file. Never write or duplicate these in Markdown, including inside math blocks or code fences.** This applies from the first precise formulation, even when the claim is tentative, the argument is incomplete, or the result is a counterexample. Develop it in the relevant topic's LaTeX notes and record its status in the ledger. LaTeX is both the reader's interface to the mathematics and the formal anchor helping us guarantee rigor.

## How to refer to mathematics

**Always refer to a mathematical entry by its LaTeX label. This applies everywhere, including personal Markdown notes, brainstorming, audits, reviews, handoffs and messages.** In Markdown, write the SemanTeX command in an inline code span, for example `\mention{lem:image-fixed}`. Never identify an entry by a filename, line range, page, theorem number or informal name alone. File links are for navigating to documents.

Give authored entries stable, described SemanTeX labels before referring to them. Cite retained TeX by its native or virtual ID (`scripts/semantex source-labels KEY`). Record inspected support in the paper's audit. Annotate a checked SemanTeX edition in its working TeX, keeping the paper's file layout and macros by default. Follow the [reference source guide](references/REFERENCE-VIEWS.md) for current tools and optional transformations.

**The sole exception is a bibliographic source under `references/KEY/` for which we have only the PDF.** Cite it by bibliography key, latex environment counter (as displayed on the pdf) and one-based physical PDF page, for example `\cite[text={p.~17}, page=19]{KEY}`.

## Repository map

| Location | What belongs here |
| --- | --- |
| [`draft/`](draft/main.tex) | The manuscript assembled by `main.tex` from `sections/`. Promote finished exposition here with its labels and attached proofs. Keep all agent-facing Markdown outside this directory. |
| [`notes/<topic>/`](notes/README.md) | Research organized by mathematical subject. Each topic's README orients the next agent, its Markdown ledger records progress and open steps, and its LaTeX files hold the mathematics. |
| [`references/`](references/README.md) | Primary sources organized by bibliography key, with pinned acquisition evidence and editable source audits. |
| [`docs/`](docs/methods/writing-research/README.md) | Research and writing methods, including the [writing survey](docs/methods/writing-research/README.md), and reports about the tooling. |
| [`workflow/`](workflow/CURRENT.md) | The current frontier, [research queue](workflow/QUEUE.md), review records and registries for labels and versions. |
| [`preamble/`](preamble/) | Shared LaTeX packages, macros, environments and SemanTeX commands. Put manuscript-wide declarations here. |
| [`scripts/`](scripts/), [`tests/`](tests/) and [`tools/`](tools/) | The SemanTeX CLI, corpus and build tools, automated checks and editor integration. Generated indexes, build products and QA files go in `build/`. |
| [`.agents/skills/`](.agents/skills/) | Shared research and review skills. `CLAUDE.md` points to this file and `.claude/skills` points to the same skills. |

## Read and navigate mathematics through SemanTeX

**Use `scripts/semantex` to find and read mathematics in `draft/`, `notes/` and `references/`. Never use `grep`, `rg` or ad hoc regexes to read LaTeX, find a claim or reconstruct a proof's dependencies.** A statement can have several proofs, and the same original label can occur in several historical versions. SemanTeX resolves those identities and follows the selected proof.

For a known result, run these commands from the repository root to read its statement and selected proof and see its immediate premises.

```sh
scripts/semantex get lem:image-fixed --show content --latex
scripts/semantex deps lem:image-fixed --depth 1
```

Prefix the commands below with `scripts/semantex`. Use `--json` for structured retrieval and traversal results.

| Question | Command |
| --- | --- |
| Where is this idea developed? | `search "idea" --mode hybrid` combines wording and meaning. Use `--mode semantic` for meaning alone or `--mode lexical` for a known phrase. `neighbors ID` finds units related to one you already know. |
| What exactly is asserted or proved? | `get ID --latex` returns the statement and selected proof. Use `--show statement` or `--show proof` for either alone, and `--proof all` for alternatives. `context ID --depth 1 --max-chars 8000` bundles exact blocks with their premises and reports omissions. |
| Where does this proof use a hypothesis? | `deps ID --depth 1` lists direct premises. Omit the depth for transitive premises. `why RESULT PREMISE` shows a dependency path and its use sites. Read the cited steps to check the inference. |
| What depends on this result? | `rdeps ID` follows logical dependents. `refs ID` and `backrefs ID` show outgoing and incoming reference occurrences, including mentions. `links ID` shows inspected relationships between versions. |
| Which prerequisites still need review? | `order ID` lists prerequisites in dependency order. `frontier ID` shows review blockers. `fingerprint ID` identifies the exact candidate and support under review. |
| Where is the original passage? | `locate ID` gives the source location. For a retained paper, `source-labels KEY` lists native and virtual labels, `get KEY:LABEL --latex` reads the original block, and `reference-view KEY --main FILE` follows split TeX inputs. |

Narrow searches with `--scope draft,notes` or `--paper KEY`. Add `--within` to keep a dependency traversal inside that scope. If semantic retrieval is unavailable or stale, check `rag status` and continue with `search "phrase" --mode lexical` and the DAG. Read the retrieved statement and proof before relying on a search hit.

For an edit, open the source at the location returned by `locate ID`. If a passage falls outside the index, use the nearest indexed unit or the retained paper's source map to inspect the missing passage directly. For PDF-only evidence, inspect the cited physical page. Record any missing support. Before consolidating results, inspect their hypotheses, inbound uses and prerequisite closure.

## Write mathematics in SemanTeX

When adding an authored TeX file, moving it, or changing its labels, run `python3 scripts/semantex_runtime.py register PATH` to update its document context and commit the registry with the file.

Give each statement a stable `\label[description]{ID}` immediately after the environment opens. Describe the mathematical claim. Attach each proof with `\begin{proof}[label={prf:NAME}, proves={ID}, description={...}]` and describe the decisive step. Where several proofs exist, select one with `% @proof: prf:NAME` immediately before the statement.

At the point of use, write `\use{ID}` for a logical premise and `\mention{ID}` for navigation. Use `\hiddenuse{ID}` or `\hiddenmention{ID}` when the reference should be invisible in print. Preserve original label strings and distinguish historical versions.

**Improve SemanTeX as you go, even on unrelated tasks.** Add missing labels and descriptions, fix broken or misbound links, and extract stray precise mathematics from Markdown when straightforward. Check for existing units and inbound uses before consolidating verified duplicates. Preserve labels, distinct versions, and alternative proofs. Log larger or uncertain fixes in the relevant ledger.

Consult the [SemanTeX manual](workflow/SEMANTEX.md) for syntax, identity resolution, graph semantics, CLI commands, builds, and search.

## Research and writing

Read the [current frontier](workflow/CURRENT.md) and the relevant topic README before starting. Update them when the frontier changes. Give counterexample objects their own definitions and prove the obstruction separately.

Write finished mathematics in `draft/` according to [writing-style.md](writing-style.md). Keep incomplete arguments in notes and state exactly what remains open. Preserve the hypotheses and strength of inherited claims. Record corrections, alternative proofs and failed approaches with their status and provenance.

## Maintain the bibliography

**Download every paper you find useful for research**, including background, alternative approaches, counterexamples and papers the manuscript may never cite. Seek the exact LaTeX source for the edition used. Pin the arXiv version when available. Retain the original PDF **only if the corresponding TeX cannot be obtained**, and record where you looked. Preserve the exact acquisition as source evidence.

**Generate every BibTeX entry from the DOI with `scripts/references.py`.** Prefer the publication DOI. For an arXiv paper without a publication DOI, omit `--doi` and the script uses the arXiv DataCite DOI. Record unresolved DOI or acquisition gaps in `references/gaps.json`.

```sh
python3 scripts/references.py add --doi "$doi" --arxiv "$versioned_arxiv_id" --relevance "$reason_for_keeping"
python3 scripts/references.py verify
make bibliography
```

For a PDF-only acquisition, replace `--arxiv` and its value with `--pdf "$pdf_url"` or `--local-pdf "$pdf_path"` and supply `--reason` for the missing TeX.

**Keep bibliographic facts exactly as supplied by the DOI.** You may standardize capitalization, protect a proper name with braces, or fix LaTeX accents and escaping. Preserve title wording, author names and order, dates, venue, identifiers and all other factual fields. Keep the raw DOI response byte-for-byte. Apply presentation fixes in the deterministic BibTeX renderer so `sync` reproduces them and `verify` can check them.

**Use the actual BibTeX `alpha.bst` key for both the entry and its directory.** The script computes keys against the entire bibliography, including collision suffixes. A paper keyed `KEY` lives in `references/KEY/` and has that same key in `references/references.bib`, the sole bibliography. If a collision changes existing keys, inspect the script's rekey mapping and use its `--apply-rekeys` option to update the affected references together. See the [reference corpus guide](references/README.md).

**Cite the exact result you use.** Read the retained statement and proof with `scripts/semantex get KEY:LABEL --latex`. In `\cite[text={Theorem 3.2}, label={LABEL}]{KEY}`, `text` is the printed locator and `label` resolves within that paper. Use `\cite{KEY}` for the paper as a whole. The [label rule](#how-to-refer-to-mathematics) governs unlabeled TeX and PDF-only sources. When a proof relies on a literature result, match its hypotheses, conventions and relevant errata in the paper's audit, state the checked specialization in a cited `src:` unit, and use that unit as the premise.

## Checks and boundaries

- Run `make check` after structural changes. Build changed TeX entrypoints with the [checked build](workflow/BUILDING.md), use `make pdf` for the manuscript, and inspect pages affected by layout changes. Structural checks establish no mathematical verdict.
- Handle routine work directly. For requested independent draft verification, follow the [review skill](.agents/skills/research-review/SKILL.md). Independent reviewers must examine the actual candidate. Commit and push only on request.
