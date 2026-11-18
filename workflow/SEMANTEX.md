# SemanTeX reference

SemanTeX gives mathematical units stable IDs, exposes their exact LaTeX, and records the premises they declare. This guide covers the annotation syntax, command line, graph semantics, checked builds, and local search used by Moduli.

| I want to… | Start here |
| --- | --- |
| Read or search the project | [Quick start](#quick-start) and [CLI](#cli) |
| Write labels, proofs, references, or citations | [Files and labels](#files-and-labels) and [Literature](#literature) |
| Understand why an ID resolves where it does | [Identity and provenance](#identity-and-provenance) |
| Interpret a dependency, check, or review status | [Graph semantics](#graph-semantics) |
| Build TeX or navigate from VS Code | [Build and editor](#build-and-editor) |
| Set up semantic search | [Local semantic retrieval](#local-semantic-retrieval) |
| Read an upstream paper or plan its conversion | [Reference source guide](../references/REFERENCE-VIEWS.md) |

## Quick start

Run commands from the repository root. This example opens `\mention{lem:image-fixed}`, follows its immediate declared premises, and bundles exact blocks for reading.

```sh
scripts/semantex get lem:image-fixed --show content --latex
scripts/semantex deps lem:image-fixed --depth 1
scripts/semantex context lem:image-fixed --depth 1 --max-chars 8000
```

Start from `search "phrase" --mode lexical` if you have a phrase and from `locate ID` before editing a retrieved unit. Use `--json` where supported to read resolved identities, blocks, and locations as data. For authoring policy and evidence requirements, see [AGENTS.md](../AGENTS.md) and the [writing guide](../writing-style.md).

## Files and labels

The index covers the manuscript in `draft/`, active LaTeX notes in `notes/`, and retained papers and their editable LaTeX audits in `references/`. It reads literal saved source and masks comments and verbatim. It also indexes SemanTeX navigation links in Markdown. Write semantic commands directly, outside macros and conditionals.

Give each mathematical environment one principal label directly after its opening. Use stable IDs such as `def:`, `lem:`, `thm:`, `prf:`, `src:`, or `cex:`. Use `sec:`, `eq:`, `fig:`, or `tab:` for navigation anchors. Descriptions are mandatory for principal mathematical labels and optional for anchors. Describe the objects, decisive hypotheses, and conclusion in one or two sentences. Proof descriptions should name the technique and the step it achieves.

```latex
\begin{lemma}
\label[Description of the statement.]{lem:NAME}
% Statement body.
\end{lemma}
\begin{proof}[
  label={prf:NAME},
  proves={lem:NAME},
  description={Description of the decisive step.}
]
% Proof body with the relevant premise links at their points of use.
\end{proof}
```

| Command | PDF | Recorded relationship |
| --- | --- | --- |
| `\mention{ID}` | Typed, linked reference | Mention |
| `\hiddenmention{ID}` | Invisible | Mention |
| `\use{ID}` | Typed, linked reference | Premise |
| `\hiddenuse{ID}` | Invisible | Premise |

Give each command one literal label and place it at the use site. The visible forms use `autoref`. Visible proof references use the form “Proof of Lemma 1.2.” Subordinate equations own their anchors and the surrounding mathematical unit owns its premise uses. Dependency arrows point toward the prerequisite. Logical cycles fail validation.

Every theorem, lemma, proposition, and corollary needs an attached proof for review acceptance. If several proofs attach to one claim, select one with `% @proof: prf:chosen` immediately before the claim. The graph includes the chosen proof’s premise uses. A proof heading can be set with `heading={...}`.

A comment block immediately before a unit may supply `@title`, `@sketch`, `@sources`, `@tags`, `@related`, `@supersedes`, and `@proof`. Related and superseded links are navigational.

## Identity and provenance

| Identity | Resolution |
| --- | --- |
| Authored label | Resolves to the unit in active TeX. A document's literal `\SemanTeXContext` and `workflow/document-contexts.json` bind local spellings to qualified graph IDs and external targets. The embedded context travels with the document. The namespace and reference-binding JSON files cover older documents. |
| Native alias | Resolves to the canonical unit and retains its own declaration location. Native aliases must label the same semantic frame. |
| Retired unit redirect | Resolves a historical ID to a reviewed canonical replacement. `workflow/unit-redirects.json` records the original source span, proof attachment where applicable, and hash-pinned evidence. |
| Retained source ID | A bibliography-key namespace plus a native or generated virtual label. The same native spelling in different papers has a different graph ID. |
| Audit overlay ID | Resolves to editable project TeX and carries provenance pointing to the exact retained source. See [Provenance overlays](#provenance-overlays). |
| Explicit gap | `workflow/unresolved.json` records known missing support or source destinations. The graph carries the gap with status `unresolved`. |

Use `locate ID --json` to inspect the destination and available alias or provenance information. Links between independently authored versions are a separate relationship. See [Versions and release](#versions-and-release).

### Registering a new note or a changed label set

In a checkout with `workflow/document-contexts.json`, run `python3 scripts/semantex_runtime.py register PATH` after creating an authored TeX file, moving it, or changing its declarations. The command inserts a document identity when needed and refreshes that file’s bindings. Keep the context line when moving a file. Commit the source and registry together. Use `make pdf SOURCE=PATH` to check a standalone entry point.

## Literature

```latex
\cite[text={Theorem 3.2}, label={thm:main}]{KEY}
\cite[text={p.~17}, page=19]{KEY}
```

Use one key per citation. For a TeX source, resolve `label` within the retained paper. For an unlabeled entry, use its indexed virtual label or assign a LaTeX label in the audit overlay. A page citation is permitted only for a bibliographic source under `references/KEY/` whose corresponding TeX is unavailable. Here `page` counts physical PDF pages from one and `text` gives the printed locator. Supply the relative PDF filename in `file` when needed to disambiguate the source. Use `\cite{KEY}` for a citation of the whole paper.

Retained labels use a paper-key namespace such as `KEY:thm:main`. The original blocks and adjacent proof are retrievable when structurally identifiable. Ordinary upstream cross-references provide mentions. Join the project’s argument to the published result through a checked authored `src:` application with an exact citation. Record the original hypotheses, matched conventions, specialization, proof dependencies, and errata checks in a Markdown audit. Register the audit path, relative to the paper’s audit directory, in `references/KEY/audit/semantex.json`.

```json
{
  "schema_version": 1,
  "applications": {"src:application": "application.md"}
}
```

`workflow/source-documents.json` separately registers hash-pinned background PDFs and explicit physical page locators. These locators open the document at the registered page. The [bibliography guide](../references/README.md) governs acquisition and project keys, and the [reference source guide](../references/REFERENCE-VIEWS.md) covers upstream labels and citations.

## CLI

Prefix these commands with `scripts/semantex`. Run `scripts/semantex COMMAND --help` for its accepted options.

| Command | Use |
| --- | --- |
| `get ID --latex` | Exact statement and selected proof. `--show` selects statement, proof, description, or content. `--proof all` or `--proof PROOF_ID` selects alternative attached proofs. `show` is a command alias. |
| `locate ID --json` | Resolve a label to an editable file, retained source, or physical PDF page. Inspect alias and origin information here. |
| `search "phrase" --mode lexical` | Search labels, metadata, and source. Lexical is the default. Use semantic mode for paraphrases or hybrid mode to combine rankings. |
| `neighbors ID` | Rank units near an indexed unit using its stored embedding. |
| `deps ID --depth 1` / `rdeps ID --tree` | Follow prerequisites or dependents. Depth defaults to all. `ancestors` and `descendants` are aliases. |
| `refs ID --json` / `backrefs ID --json` | Inspect outgoing or incoming occurrences, with their use sites, relation, visibility, and resolved targets. |
| `backrefs ID --markdown` | List the Markdown files that mention this label, with the first matching line in each. Use `--json` for every occurrence or `--scope notes` to restrict the source files. Results can include historical discussions. |
| `why RESULT INPUT --json` | Show a shortest logical path and the exact use sites along it. |
| `order ID` / `frontier ID` / `fingerprint ID` | Read prerequisites in dependency order, inspect review blockers, or identify the reviewed candidate and support. |
| `context ID [ID …]` | Return exact source blocks for seeds and their nearby premises. `--depth` defaults to one and `--max-chars` defaults to 8,000. Over-budget or out-of-scope units are reported as omissions. |
| `links ID` / `link A B --relation equivalent` | Inspect or record version relationships. See [Versions and release](#versions-and-release). |
| `source-labels KEY` / `paper-graph KEY` / `reference-view KEY --main FILE` | List retained-source anchors, inspect their paper-local graph, or produce a flattened reading view with a source map. |
| `graph --target ID --format dot` / `export --output build/semantex/index.json` | Export a diagram or a machine-readable graph snapshot. `make graph` writes JSON, Mermaid, and DOT. |
| `check` / `check --release --target ID` | Validate structure and freshness of accepted reviews, or check release requirements for the assembled manuscript. |

Use `--scope draft,notes,references` or `--paper KEY` where supported to focus results. A focused traversal can show intermediate units outside the focus. Add `--within` to restrict the traversal itself. Use `--mentions` on dependency walks to include navigation and citation edges. For an integration, start with `get --json` for exact blocks and metadata, `refs --json` for occurrences, and `export` for the broader index.

## Graph semantics

- A direct logical edge runs from the **unit that uses a premise** to the premise. A statement's logical dependencies include those of its selected proof. Review support also includes the selected proof unit itself. Alternative proofs remain separately retrievable and their premises belong to their own proof units.
- Mentions and exact citation locators are recorded with their source positions. They provide navigation. Use the explicit logical commands at the point where a premise is actually used. A paper graph can contain unresolved upstream destinations and ambiguous native labels. Its ordinary cross-references describe where the paper points.
- `workflow/reviews.json` records review state. Authored units start as `unreviewed`, and retained sources have status `source-unreviewed`. An acceptance can become `stale` when its fingerprint or required support changes. Fingerprints cover the exact reviewed text, selected proofs, transitive premises, source and audit inputs, and shared preamble and instructions. SemanTeX descriptions are excluded from the mathematical body fingerprint. A pinned source file contributes its full file hash. See [the review protocol](../.agents/skills/research-review/SKILL.md).

`scripts/semantex check` covers structural validity and review freshness. `make check` also verifies reference integrity and runs the tests. Mathematical validity requires reading the argument.

## Provenance overlays

Use the repository’s `tex-to-semantex` skill to annotate a retained paper. Write a `ref:KEY:NAME` label for a statement or `prf:ref:KEY:NAME` for a proof in `references/KEY/audit/`. Put exactly one originating citation with an exact locator in the unit. Use other papers’ exact citations where needed. Keep unresolved use sites and partial coverage in the audit ledger.

In `audit/semantex.json`, add entries under `units` such as:

```json
{
  "schema_version": 1,
  "units": {
    "ref:KEY:main": {
      "representation": "restatement",
      "coverage": "statement-and-proof",
      "dependencies": "partial",
      "source_sha256": "SHA-256 of the exact retained file"
    }
  }
}
```

The locator and hash connect the annotation to the original. When a unit cites several locations in the same paper, set the `source` field to the originating locator ID returned by `refs`. `locate ref:KEY:main --json` gives both locations. `get ref:KEY:main` retrieves the overlay and its selected proof. `get KEY:upstream-label --latex` retrieves the original TeX. For physical PDF locators, install Poppler's `pdfinfo` to check the page range.

## Versions and release

Use `scripts/semantex link A B --relation equivalent` after checking that two units state the same mathematics under matching hypotheses and conventions. The command pins each statement. Descriptive edits preserve the relationship. A change to a statement marks the link stale, and rerunning the command records a new inspection. Use `derived-from` for a directional relationship from a revised unit to its source. `scripts/semantex links ID` shows either relation.

The release gate follows literal includes from `draft/main.tex`. It checks current acceptance of the selected support and reports visible references and required premises outside the manuscript. Bring the support into the assembly or establish an applicable literature result through a cited `src:` unit and its audit.

## Build and editor

Use `make pdf SOURCE=PATH` for a checked build of a draft, note, or authored audit entry point. The builder validates the graph and prepares `build/semantex/semantex-runtime.tex`. The [TeX package](../preamble/semantex.sty) uses this table to resolve document contexts, aliases, proof titles, and links to source locations. The compiler produces local numbering and anchors through the usual LaTeX passes. See [build commands and output paths](BUILDING.md).

The [VS Code companion](../tools/vscode-semantex/README.md) reads the same graph for hover, definitions, references, and dependency trees. Its editor index can include unsaved TeX buffers. The regular CLI and checked PDF build read saved files by default.

| Implementation | Where to look |
| --- | --- |
| Literal authored scanner, graph assembly, and CLI | [manuscript_graph.py](../scripts/manuscript_graph.py) |
| Native and virtual upstream labels and flattened views | [semantex_sources.py](../scripts/semantex_sources.py) and [reference_views.py](../scripts/reference_views.py) |
| Checked build and generated TeX bindings | [build_latex.py](../scripts/build_latex.py) and [semantex_runtime.py](../scripts/semantex_runtime.py) |
| Reference acquisition, lock checks and bibliography key migrations | [references.py](../scripts/references.py) |
| Related versions and review records | [semantex_links.py](../scripts/semantex_links.py) and [reviews.py](../scripts/reviews.py) |
| Interactive worker, graph caches and retrieval | [semantex_service.py](../scripts/semantex_service.py), [semantex_cache.py](../scripts/semantex_cache.py), and [semantex_rag.py](../scripts/semantex_rag.py) |

## Index caches and the local worker

SemanTeX reuses the checked graph and keeps a separate cache of parsed files under `build/semantex/`. Editing an existing Markdown file in `notes/` or `draft/` refreshes that file’s navigation links and their positions against the checked graph. New or moved paths, changes to mathematical sources or bindings, and edits to hash-pinned redirect evidence trigger graph revalidation. The VS Code index uses the same file cache and previews source on hover.

Interactive commands start a private worker for the checkout. The worker keeps the current graph, Python modules, and search caches open. A semantic query or indexing pass loads the requested model into llama.cpp, which keeps it resident for subsequent commands. Loading a different embedding profile releases the previous model. `scripts/semantex rag stop` releases the worker and model. Set `SEMANTEX_ONESHOT=1` to run commands without the worker.

Use `scripts/semantex --rebuild check` to reparse the corpus and refresh the graph cache. Use `scripts/semantex --rebuild rag build` to regenerate the selected profile’s vectors as well.

Saved TeX and the registries are authoritative. `build/semantex/scans.sqlite3` caches file parses, `graph.sqlite3` holds a checked snapshot, and `rag/PROFILE/index.sqlite3` holds embedding vectors and their unit mappings. The exported `index.json` is a snapshot for other consumers.

## Local semantic retrieval

Install `llama-server` from [llama.cpp build b12359](https://github.com/ggml-org/llama.cpp/releases/tag/b12359) or set `SEMANTEX_LLAMA_SERVER` to the binary. Model download and indexing are explicit commands. Search runs locally, with a single slot and a 512-token embedding cap.

```sh
scripts/semantex rag profiles
scripts/semantex rag setup
scripts/semantex rag build
scripts/semantex rag status
scripts/semantex search "why do projection images consist of fixed points" --mode hybrid
scripts/semantex neighbors lem:image-fixed --scope draft,notes --show description
scripts/semantex get lem:image-fixed --show content --latex
scripts/semantex context lem:image-fixed --depth 1 --max-chars 8000 --json
```

| Profile | Model |
| --- | --- |
| `light` (default for 8 GB) | Qwen3-Embedding-0.6B Q8_0, 639 MB on disk |
| `mac8` (higher memory use) | Qwen3-Embedding-4B Q4_K_M, 2.50 GB |
| `gemma` | Text-only EmbeddingGemma 2 BF16, 558 MB |
| `mac16` | Qwen3-Embedding-8B Q5_K_M, 5.42 GB |
| `mac24` | Qwen3-Embedding-8B Q8_0, 8.05 GB |
| `mac32` | Qwen3-Embedding-8B F16, 15.1 GB |

Pass `--profile NAME` consistently to the setup, build, search, and neighbor commands when switching models. `rag build` initializes the vector index and incrementally updates it. A query against an existing index adds new or changed inputs when it encounters stale units in its scope. File moves preserve cached vectors when the embedding input stays the same. `rag status --scope references --paper KEY` reports eligibility, description coverage, and the worker’s resident model if one is loaded.

Nearest-neighbor search ranks exact cosine similarities. The worker uses NumPy when it is installed and keeps the vector matrix in memory across queries. A standard-library scorer is available on installations without NumPy. The Metal runtime uses automatic GPU offloading by default.

Search and neighbor queries default to 16 hits. `--kind` and `--status` filter eligible units before ranking. Choose `--show labels`, `--show description`, or `--show content`. Use `--all-versions` to inspect linked versions separately. Neighbor lookup from an indexed ID uses the cached vector, and text queries use the local embedder. Hybrid queries fuse semantic and lexical ranks. `context` returns complete blocks up to its source-character budget and reports omissions.

[Qwen GGUF models](https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF) · [EmbeddingGemma 2 GGUF](https://huggingface.co/ggml-org/embeddinggemma-2-GGUF)


### M2 measurements

The benchmark uses 34 mathematical units across the three scopes and 20 paraphrased queries with expected IDs. On the 8 GB M2 MacBook Air with llama.cpp b12359, the three semantic profiles each found all 20 expected IDs in the first 16 hits. The lightweight Qwen profile offered the best retrieval quality among the two low-memory profiles. The 4B model ranked more expected hits near the top, with system swap increasing during both of its runs. Memory figures below are maximum child resident set sizes. The heavier 8B profiles are suggestions for machines with more memory.

| Profile | Semantic MRR@5 | Warm median query | Max child RSS |
| --- | ---: | ---: | ---: |
| light | 0.702 | 41 ms | 766 MiB |
| mac8 | 0.775 | 283 ms | 2,363 MiB |
| gemma | 0.438 | 25 ms | 721 MiB |

The lexical baseline found 15 of 20 expected IDs in its first 16 hits. Rerun the fixture with `python3 scripts/benchmark_semantex.py --profile NAME` after setting up the corresponding weights. Supply `--fixture PATH` to use a project-specific set of questions and expected labels. The benchmark uses a disposable corpus so it can run alongside a real project.
