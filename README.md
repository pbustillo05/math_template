# Hybrid math research template

A workspace for comparing research approaches, finding exact mathematics in notes and papers, and reviewing a polished LaTeX manuscript. The [user manual](USER-MANUAL.md) walks through setup, a research round, manuscript review, and the optional milestone notebook.

The included mathematics is a small, **unreviewed** demonstration. Replace it with your project when ready.

## Start here

Requirements: Python 3.10+ (standard library only), Git, and a TeX distribution with `latexmk`, `pdflatex`, `bibtex`, `alpha.bst`, `amsmath`, `amsthm`, `amssymb`, `hyperref`, `aliascnt`, and `subfiles`.
Poppler validates physical PDF citation pages. Semantic search uses optional local model weights and a llama.cpp runtime.
Node.js 18+ is needed only for extension development/tests; VS Code runs the installed extension itself.

From the project folder, run these commands.

```sh
make doctor
make check
make pdf
```

Open `build/latex/draft/main.pdf`.
For your first research round, fill in the [problem statement](workflow/PROBLEM.md), add an approach to the [route registry](workflow/ROUTES.md), and put one bounded question in the [current frontier](workflow/CURRENT.md).

## Workspace map

| Path | Purpose |
| --- | --- |
| `draft/` | Polished user-facing LaTeX; shared setup in `preamble/` |
| `notes/` | Agents' organized workspace: calculations, failed attempts, experiments, ledgers |
| `references/` | All relevant papers, exact DOI metadata, pinned sources and separate audit notes |
| `scripts/semantex` | Exact environment retrieval, dependency traversal, review freshness |
| `tools/vscode-semantex/` | Label hover, Go to Definition, references and dependency tree |
| `writing-style.md` | Mathematical exposition and aesthetics |
| `agents/SEMANTEX.md` | Separate LaTeX/code/annotation contract |
| `agents/` | Bounded author, proof, counterexample, source and style review protocols |
| `workflow/` | Problem, current frontier, routes, research cycle, optional task queue, and review evidence |
| `notebook/` | Optional dated LaTeX entries for mathematical milestones |

## Navigate mathematics

```sh
scripts/semantex get lem:image-fixed --json
scripts/semantex get lem:image-fixed --latex
scripts/semantex deps lem:image-fixed --depth all --tree
scripts/semantex rdeps def:idempotent --depth 1
scripts/semantex why lem:image-fixed def:idempotent
scripts/semantex backrefs def:idempotent --json
scripts/semantex graph --format mermaid
scripts/semantex export --output build/semantex/index.json
```

Logical arrows point **from the result to its prerequisite**.
Proof attachments are structural and do not create premise edges.
Queries rebuild from saved source every time; the parser never executes TeX or infers a proof.
See [the annotation and CLI guide](agents/SEMANTEX.md).

## Find related mathematics

Lexical search and graph navigation work on a fresh checkout. Follow the [semantic setup guide](agents/SEMANTEX.md#local-semantic-retrieval) for pinned model profiles and runtime setup. Then try:

```sh
scripts/semantex search "why do projection images consist of fixed points" --mode semantic
scripts/semantex neighbors lem:image-fixed --scope notes --all-versions --show content
scripts/semantex links lem:image-fixed
scripts/semantex context lem:image-fixed --depth 1 --json
```

The [example topic](notes/example/README.md) includes a separately indexed notes version of the draft lemma. Use the `tex-to-semantex` repository skill to add indexed units from a retained paper without changing the original source.

## Retain literature

```sh
# Replace these example identifiers with a relevant paper and an exact version.
python3 scripts/references.py add --doi 10.1000/example \
  --arxiv 2301.01234v2 --relevance 'Supplies the comparison theorem'
# Prefer publication DOI; omit --doi to use the arXiv DataCite DOI.
python3 scripts/references.py verify
```

The scripts negotiate BibTeX through the DOI resolver, retain the exact response, compute keys with the real `alpha.bst`, and safely extract source without altering it.
Network services can change their metadata; reproducibility comes from the **retained response and hashes**, not a promise that fresh API calls are identical.
PDF fallback, DOI gaps, collision migration, and exact citation locators are covered in [references/README.md](references/README.md).

## VS Code

```sh
make vscode
code --install-extension build/semantex-navigation.vsix
```

Open this folder in VS Code, trust the workspace, and reload the window.
Hover over a literal label inside a reference command to see its exact LaTeX environment and selected proof.
Use F12 to jump to the label, Shift+F12 for uses, and the **SemanTeX dependencies** Explorer pane to browse prerequisites.
The extension refreshes after edits and validates current unsaved LaTeX buffers for navigation; CLI/build commands use saved files.
LaTeX Workshop is recommended for PDF preview and SyncTeX; it is independent of SemanTeX.
See [extension details](tools/vscode-semantex/README.md).

## Checks and builds

- `make check`: source graph, reference integrity, structural checks and regression tests. No network.
- `make pdf`: compile the main manuscript and standalone section into ignored `build/latex/` with SyncTeX.
- `make notebook`: compile the optional milestone notebook into `build/latex/notebook/notebook.pdf`.
- `make bibliography`: compile `references/cite-all.tex` into `build/latex/references/`.
- `make graph`: JSON index plus Mermaid and Graphviz diagrams under `build/semantex/`.
- `make release TARGET=lem:image-fixed`: require fresh independent reviews for this result's entire support closure. The untouched demo intentionally fails this gate.

A successful build is not mathematical verification.
Read [AGENTS.md](AGENTS.md) and [the review protocol](agents/PROTOCOL.md) before research or drafting.
The template supplies review roles and evidence checks; it does not pretend that an agent has reviewed its own output independently.

## Origins

The structural SemanTeX parser and BibTeX transport were adapted from the sibling `stratified` project.
BourbakIA informed the separation of bibliography acquisition, semantic indexing, editor support, and bounded critique roles.
See [PROVENANCE.md](PROVENANCE.md) for adaptation boundaries and upstream technical documentation.
