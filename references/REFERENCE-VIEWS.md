# Deterministic reference views

This layer was informed by `texphage`'s unfolding, auto-label and graph tools.
It deliberately starts with structural navigation; it does not attempt a general semantics-preserving TeX canonicalizer.
No agent or model is required to index a paper.

## Native and virtual labels

```sh
scripts/semantex source-labels KEY
scripts/semantex get KEY:upstream-label --json
scripts/semantex get KEY:auto:PATHHASH:lemma:3 --latex
scripts/semantex locate KEY:auto:PATHHASH:lemma:3 --json
scripts/semantex paper-graph KEY --format json
scripts/semantex deps KEY:upstream-label --mentions --depth 2 --json
scripts/semantex backrefs KEY:upstream-label --json
```

Substitute IDs returned by `source-labels`; the uppercase tokens are placeholders.
Every structurally complete literal `\begin{environment}...\end{environment}` outside document/verbatim regions receives a virtual ID when it has no own label, including custom theorem environments, equations and proofs.
An inner environment's label does not suppress its parent's virtual ID.
An existing upstream label is retained exactly; duplicate labels remain ambiguous.
The same `get` CLI returns the exact original source block, source encoding and line range; virtual labels do not modify the paper.
Where a proof follows a statement immediately (apart from whitespace/comments), retrieval includes that proof too.

Virtual IDs combine the retained relative path hash, environment name and occurrence ordinal.
They are deterministic for the pinned payload, stable across edits to audit overlays and file line shifts, and **not guaranteed stable across source editions or inserted same-kind environments**.
Treat the exact version and payload hash as part of the locator's identity.
A source correction must not silently reuse an old locator as evidence for a different assertion.

## Graph semantics

The reference graph records literal `ref`, `eqref`, `autoref`, `cref`, `Cref`, `xref`, `hxref`, `dxref`, and `hdxref` use sites.
Dashed diagram arrows are mentions; solid arrows are explicit `dxref`/`hdxref` logical declarations.
Most arXiv papers declare no logical graph: their ordinary cross-references cannot be treated as proof dependencies.
`deps`/`rdeps` traverse only explicit logical declarations by default; add `--mentions` to explore ordinary reference links.
Missing targets remain unresolved graph edges; macro-generated references are not guessed.
The graph is paper-local and reports exact files and lines, independent of the informal acceptance registry.
A later agent audit can describe checked dependencies under `KEY/audit/` without altering upstream bytes or asserting that ordinary references are logical premises.

## Conservative flattening

```sh
scripts/semantex reference-view KEY --main main.tex
# Equivalent: python3 scripts/reference_views.py KEY --main main.tex
```

Output lives under `build/reference-views/KEY/`:

- `flattened.tex`: a single navigation text, with source-boundary and virtual-ID comments.
- `source-map.json`: character-offset spans mapped back to retained source, exact input hashes and diagnostics.
- `graph.json`: native/virtual environments and literal reference links.

Choose the entry file explicitly, after checking upstream arXiv metadata and source.
The tool recursively unrolls braced literal `\input`/`\include`, resolves within the retained paper, and reports cycles, missing files and unsupported controls.
It masks comments and verbatim before scanning, never executes TeX, never follows external paths and preserves unsupported constructs verbatim.
It does not evaluate conditionals, expand macros, rewrite notation, load package definitions, translate diagrams or claim PDF equivalence.
Cross-file split environments, macro-generated environments and plain-TeX result syntax remain limitations; examine diagnostics and original source.
The flattened view is for reading, not a promised compilable replacement.
Use the original-file `get` blocks for exact quotation and evidence, and regenerate after changing the corpus.

Broader texphage normalization can be tried later on disposable copies with before/after rendering and a failure ledger.
The initial template avoids making that lower-success pipeline a prerequisite for reliable acquisition or navigation.
