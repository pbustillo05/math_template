# Reference source navigation and conversion

The commands below describe the current read-only views. The [conversion design](#proposed-semantex-editions) describes how to turn an entire paper into editable SemanTeX while preserving its printed edition. For project-wide commands, see the [SemanTeX guide](../workflow/SEMANTEX.md).

## Current source model

The catalogue pins a work's identity and bibliography key. The lock records the exact source files, including the original acquisition evidence where available. The retained-source scanner reads native LaTeX anchors, and authored TeX in `audit/` can add local applications and provenance-linked annotations. For an exact quotation or source audit, retrieve the retained original by its native or virtual ID. See the [corpus format](README.md#contents-and-invariants) and [overlay format](../workflow/SEMANTEX.md#provenance-overlays).

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

The reference graph records literal LaTeX reference commands, legacy `xref`-family commands, and the four SemanTeX reference commands.
Dashed diagram arrows are mentions. Solid arrows represent logical declarations from `dxref`, `hdxref`, `use`, or `hiddenuse`.
Ordinary upstream cross-references record navigation. A proof dependency requires an explicit declaration.
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
The flattened view serves source navigation. Use the original-file `get` blocks for exact quotation and evidence, and regenerate the view when the corpus changes.

## Proposed SemanTeX editions

Make the **whole paper** the working SemanTeX source. Keep its existing file layout, preamble, macros, and supporting assets by default. A verified SemanTeX edition can span several TeX files. Preserve the pinned acquisition as evidence and keep its original locators usable. Track the working edition’s hashes alongside a source map and conversion record.

### Storage and lookup

- Start in `build/reference-editions/KEY/`. An eventual tracked location could be `references/KEY/edition/`. Introduce that location through an explicit edition registry, with separate checks for acquisition files and converted files. The current lock covers files outside `audit/`, and the retained reader scans TeX under a paper outside `audit/` and `metadata/`. Both need an edition-aware path before a converted paper is installed there.
- Give every converted mathematical unit a canonical ID in a separate paper-edition namespace. A possible scheme is `paper:KEY:lem:NAME`. Record each unit's correspondence to its exact original label or virtual ID and source span. Record the stable work identity and pinned edition separately from the current bibliography key. Keep an explicit origin for ambiguous cases and review correspondence before using it to group search results.
- Preserve the meaning of existing `KEY:native-label` lookups, exact provenance citations, and audit records. Once an edition is verified, prefer its annotated units in paper search, and expose the original through the source map. Keep existing audits for hypothesis matching, errata, and checked applications. This gives agents one paper to annotate in place and a direct route to its evidence.
- Teach the graph, RAG, editor, and build tools about registered editions. The current upstream scanner parses literal `\label{ID}`, and authored SemanTeX parses `\label[description]{ID}` and explicit proof attachments. A conversion needs the authored annotations and an upstream-compatible treatment of the paper's existing TeX. Reading editions also need their own build recipe so they retain their original class, numbering, and bibliography machinery.

### Default annotation workflow

1. **Establish the baseline for a new edition.** Select the actual entry file, build the pinned source in scratch space, and record the edition, input hashes, engine, fonts and package versions, build options, assets, and diagnostics. Use isolated working directories and disable shell escape. Reuse the recorded baseline for later edits when the relevant inputs and toolchain match. Record build limitations for editions that can currently support source navigation only.
2. **Annotate the passages you read in place.** Add stable labels, descriptions, and inspected proof attachments. Preserve theorem and proof boundaries, hypotheses, qualifiers, notation, and proof variants. Check the target of an adjacent proof before attaching it. Treat existing cross-references as mentions and add premise edges after reading the step that uses them.
3. **Preserve print during annotation.** Keep legacy printed references and add `\hiddenmention` or `\hiddenuse` at safe sites when a visible substitution would alter wording, spacing, linking, or layout. Use `\mention` or `\use` in place of an existing reference after checking the rendered result and link destination. A compatibility adapter should forward native labels, citations, and proof headings through the paper's original macros. The current project package writes scoped auxiliary label keys and wraps `\cite` and `proof`, so loading it unchanged is a conversion candidate that needs checking.

During unrelated research, keep edits to the passages at hand and use the existing source views for reading. If a change needs build debugging, macro expansion, or broad restructuring, record it in the paper’s audit and continue the main task.

### Optional unfolding, demacro, and formatting

Try a narrow transformation when it would solve a concrete problem with reading, indexing, or maintaining the paper. Unfolding can help when an environment is split across files. Demacro can help when a particular wrapper hides labels or references from the scanner. `texphage` has limited success on heterogeneous papers, especially those that use custom macros or depend on package internals. Keep the existing TeX as the starting point for each trial.

- **Unfold selected includes.** Preserve the original preamble, file-boundary token behavior, grouping, and `\include` page and counter behavior. Check `\includeonly`, conditional paths, and path-sensitive assets. Keep the split layout wherever it is useful or the flattening fails its checks.
- **Expand selected macros or format a small region.** Start with unambiguous local definitions and call sites. Preserve theorem styles, counters, math operators, package options, diagrams, and trailing-percent behavior. Test expansion, formatting, diagram translation, and preamble changes independently.

Use a disposable copy and a short, explicit time budget for mechanical trials. When delegation is available, give a low-cost agent one narrow pass and ask for the diff and verification result. On a mismatch or when the budget runs out, record what happened and return to the main task. Inspect proof attachments and dependencies separately before incorporating them.

Record the input and output of each stage. Compose its span map with earlier maps so an expanded macro can lead back to its call site and definition. Keep unmapped passages visible for inspection.

For these optional trials, `../texphage` can generate candidates from a recorded source tree. The inspected checkout has working-tree changes on top of `91f3634` and exposes unfold, demacro, formatting, and structural auto-labeling. The full pipeline also converts Xy diagrams, and the demacro pipeline reconstructs a minimal preamble. Its standalone demacro CLI emits a body. Retain diagnostics for unresolved includes and macros. The sibling fidelity suite uses image similarity and text-difference thresholds, so a passing severity result needs the stricter checks below.

### Label renaming toolbox

Build on parsed declarations and reference occurrences. The unit of rename is a resolved declaration in a specific paper edition, including its class of counter or anchor and the binding scope. A preview should show the old and proposed IDs, declaration span, all recognized inbound occurrences, registry edits, and unresolved possible uses.

| Operation | Required behavior |
| --- | --- |
| Plan | Enumerate the declaration and bound uses. Cover supported LaTeX reference commands, list-valued references, explicit internal links, SemanTeX commands, proof options and selectors, citation locators, and project references and registries that intentionally target the reading edition. Treat labels in unrelated papers, comments, literal examples, and exact original-source locators according to their own scopes. |
| Apply | Validate the file hashes and old token values from the plan. Rewrite exact parser spans simultaneously so chains and swaps cannot cascade. Reject collisions with live labels or aliases. Rebuild generated auxiliary and runtime data in scratch space. Preserve compatibility aliases for previously exposed IDs where they still identify the same anchor. |
| Verify | Re-resolve all known inbound references after the change. Compare their destinations, printed counters, links, selected proofs, and logical edges under the proposed ID mapping. Confirm unaffected declarations and references still bind as before. Keep review hashes tied to the evidence actually reviewed. |

Start with literal labels and uses. For custom wrappers, register their actual argument structure. A macro-generated label, unknown wrapper, cross-document import, or dynamically built destination can hide an inbound use. If the binding remains uncertain, retain the original TeX label and add a canonical graph alias where its destination is known. A compiler auxiliary inventory can corroborate the selected build, and parser coverage determines which rewrites can be guaranteed. The current bibliography-key migration provides a precedent for staging collision handling and updating the catalogue. [references.py](../scripts/references.py)

### Linking papers' citations to our catalogue

Keep two keys per mapping where applicable. The **paper's local key** continues to drive its bibliography, and the **Moduli key** opens our retained work or its verified reading edition. Store the binding per citing paper and per local citation key, using the target work's stable catalogue identity and resolving its current alpha key at index time. Match by DOI or versioned arXiv ID when available. Check author, title, year, and edition where identifiers are absent. Report ambiguous or absent matches for review.

The first implementation can index an adjacent nonprinting annotation or an edition registry entry. Keep all printed citation arguments, grouping, prenotes, postnotes, punctuation, order, citation style, and bibliography contents intact. Handle multiple keys item by item and allow per-occurrence locators when the source names a precise destination. Only edit the printed bibliography key itself as a separate verified rename. A paper-level match creates a navigational citation. Add a logical premise edge only for an exact result whose use has been inspected. Existing Moduli `\cite[label=...]{KEY}` continues to target the retained locator.

### Fidelity and promotion

- **Rebuild both sides reproducibly.** Compile the pinned original and each candidate with the same toolchain, assets, output mode, job name, and fresh auxiliary state. Record both build logs and unresolved references. Rebuild the final staged result from its recorded inputs.
- **Compare the PDF that readers see.** Require identical page counts, sizes, visible page labels, and page-by-page raster output with a pinned renderer. Compare extracted text and inspect differences in links, outline entries, and named destinations. Resolve renamed anchors to the same destinations. Compare deterministic PDF bytes when the toolchain produces them. Exact rendered output and equivalent links cover cases where timestamps or internal PDF object IDs differ.
- **Compare the mathematics and graph.** Review changed tokens in statements and proofs through their source map, especially quantifiers, hypotheses, symbols, diagram arrows, counters, and citation qualifiers. Check the counts and destinations of supported labels and references, inspect new dependencies, and verify that existing exact source citations and manuscript support still resolve. PDF fidelity covers typesetting. Source inspection covers the meaning of edited code and the correctness of added semantic metadata.
- **Install as a single staged change.** Keep a receipt with the source and output hashes, tool revisions, applied transformations and maps, PDF and graph results, and remaining coverage gaps. Keep source-backed audits usable, support collision rekeys in edition records, and preserve a recoverable pre-change state. Update search and editor resolution to the verified edition only after these checks.

A dedicated tooling pilot can cover a single-file paper with ordinary labels, a split paper with assets and cross-file references, and a paper with custom macros or a nonstandard citation setup. Include regression fixtures for simultaneous renames, labels shared across papers, unknown macro wrappers, and multi-key citations. After a paper is registered, ordinary reading tasks can add descriptions, fix known links, and inspect new premises directly in its existing TeX.
