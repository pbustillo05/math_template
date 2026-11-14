# SemanTeX: LaTeX/code contract

These instructions govern source structure and invisible mathematical metadata.
For exposition and aesthetics, read `../writing-style.md`.
The parser is adapted from `stratified`; it scans literal saved source, not expanded TeX or inferred mathematics.

## Files and labels

`draft/main.tex` is the main entry point; sections are standalone `subfiles` in `draft/sections/`.
All declarations and package choices belong in the root `preamble/`.
Use one semantic sentence per source line where practical, with readable indentation.
Do not create macros that generate labels or dependency annotations.
The active index covers `draft/**/*.tex`, opted-in notes, and `references/*/audit/**/*.tex`.
Notes remain freeform by default; add a standalone `% semantex: on` line to a note to opt into labels, structural checks and graph navigation.
`archived/`, generated files and retained upstream sources do not become authored claims.
Upstream labels are indexed separately under the paper's key namespace.

Use stable semantic IDs, independent of filenames and numbering: `def:`, `conv:`, `not:`, `thm:`, `lem:`, `prop:`, `cor:`, `prf:`, `ex:`, `cex:`, `rem:`, `conj:`, `src:`, `obl:`.
Navigation anchors use `sec:`, `eq:`, `fig:`, `tab:`; `goal:` is a planning anchor.
Each mathematical environment has one principal label immediately after its opening.
A nested labelled environment owns its references; subordinate equation labels do not steal ownership.
Active literal commands are required; comments and verbatim/listing/minted regions are ignored.
TeX conditionals and macro expansion are unsupported: keep semantic structure outside conditional branches.

## Local references

| Command | Logical premise | Printed text |
| --- | --- | --- |
| `\xref{label}` | No | Ordinary reference number |
| `\dxref{label}` | Yes | Ordinary reference number |
| `\hxref{label}` | No | Invisible |
| `\hdxref{label}` | Yes | Invisible |

Put annotations at their precise use site, in active LaTeX.
One literal label per command; spell out separate references when necessary.
Ordinary `\ref`, `\eqref`, `\autoref`, `\cref`, `\Cref` are mentions, never automatically premises.
The preamble provides ordinary `\ref`/`\eqref`/`\autoref`; load `cleveref` centrally if choosing its commands.
Hidden annotations must not create visible glue or punctuation.
Dependency edges point from user to prerequisite; logical cycles are errors, mention cycles are allowed.
A logical reference needs a mathematical owner and a mathematical target, not merely an equation/section anchor.

```latex
\begin{lemma}\label{lem:claim}
An assertion using Definition~\dxref{def:input}.
\end{lemma}
\begin{proof}
\phantomsection\label{prf:claim}
\proves{prf:claim}{lem:claim}
Apply Lemma~\dxref{lem:ingredient}.
A routine calculation supplies the conclusion\hdxref{def:input}.
Compare Remark~\xref{rem:comparison}.
\end{proof}
```

Replace example labels with real targets before running checks.
`\proves{proof-label}{result-label}` attaches a proof, without adding a logical premise edge.
Every theorem/lemma/proposition/corollary needs an attached proof for review acceptance.
The result's effective prerequisites combine its statement and selected proof.
With multiple proofs, put `% @proof: prf:chosen` immediately before the result.
Unselected proofs retain independent metadata and are not silently merged.
Proof labels are navigation anchors, not new theorem numbers.

A contiguous comment block before an environment may contain `@title`, `@sketch`, `@sources`, `@tags`, `@related`, `@supersedes`, and `@proof`.
Related/superseded labels must exist but are not premises; metadata never certifies mathematics.
New mathematical meanings need new IDs with explicit supersession.

## Exact literature locators and checked applications

```latex
\cite[Theorem 3.2\hxref{KEY:upstream-label}]{KEY}
\cite[Unlabelled argument\sourceat{KEY}{references/KEY/paper.tex}{120}]{KEY}
\cite[p.~17\sourcepage{KEY}{references/KEY/original.pdf}{17}]{KEY}
```

Use one bibliography key per citation; the locator must belong to that retained paper, outside `audit/` and `metadata/`.
`sourcepage` uses the physical PDF page, starting at 1; write the publication's printed page separately if it differs.
The CLI locates source lines and reports explicit PDF pages; it does not manufacture upstream theorem numbers.
Write printed numbers explicitly after checking the retained version.
`KEY:upstream-label` retrieves the exact upstream environment and adjacent proof when structurally available, without editing the source.
Duplicate upstream labels are ambiguous and rejected.

An upstream theorem is a locator, not a certified local premise.
Represent a checked application as a labelled authored `src:` unit (a `proposition`, `remark` or other suitable environment), with a concise mathematical assertion and exact citation.
Attach original source and audit matching evidence:

```latex
\evidence{src:application}{references/KEY/paper.tex,references/KEY/audit/application.md}
```

Use `\dxref{src:application}` at the actual application.
The audit records source version, original hypotheses, matched definitions, specialization, proof dependencies and errata checks.

## Lean correspondence

```latex
\leanref{lem:claim}{Project.claim}{unchecked}
```

Put this invisible three-argument marker immediately after the principal label (whitespace is allowed).
The entity must match `lean/ledger.json`.
Statuses are `unchecked`, `partial`, `checked`, or `stale`.
An absent marker means no formal correspondence is claimed; Lean is entirely optional.
`checked` requires a fresh successful compiler receipt for the exact Lean source snapshot and a manually documented statement correspondence.
It is distinct from independent informal review and from a proof of the LaTeX/Lean translation.
Run `python3 scripts/lean_status.py check`; see `lean/README.md` for the verification command and trust limits.
Markers never print checkmarks or silently promote claims.

## CLI and graph

```sh
scripts/semantex get LABEL --json          # exact environment + selected proof
scripts/semantex get LABEL --proof all --latex
scripts/semantex locate LABEL --json
scripts/semantex deps LABEL --depth 1      # prerequisites (outgoing arrows)
scripts/semantex rdeps LABEL --depth all   # results depending on LABEL
scripts/semantex refs LABEL --json         # mentions and logical uses, with precise positions
scripts/semantex backrefs LABEL --json
scripts/semantex why RESULT INPUT --json   # shortest premise path and use sites
scripts/semantex order LABEL              # prerequisites first
scripts/semantex frontier LABEL           # unaccepted/stale support
scripts/semantex search 'idempotent' --kind def
scripts/semantex fingerprint LABEL
scripts/semantex graph --target LABEL --format dot
scripts/semantex export --output build/semantex/index.json
scripts/semantex check
scripts/semantex check --release --target LABEL
```

Traversal defaults to all depths; `--depth 0` has no neighbors.
`ancestors`/`descendants` alias `deps`/`rdeps`; prefer the unambiguous names above.
JSON preserves owners, targets, source ranges, exact blocks, repeated use sites and minimum distances.
These are structural checks, not a mathematical proof checker.

## Obligations and review freshness

`\sorry{obl:id}{precise missing step}` emits a visible red warning; keep ordinary incomplete research in notes instead.
An obligation in a selected support closure blocks acceptance/release.
`workflow/reviews.json` is the sole informal acceptance registry, schema version 1.
See `agents/PROTOCOL.md` and `scripts/reviews.py --help`.
Fingerprints include exact unit blocks, chosen proofs, transitive premises, evidence, shared preamble, reference lock, Lean ledger and governing instructions.
Unrelated edits or line shifts do not invalidate a unit; changes to its mathematical support do.
A disputed/unaccepted premise or missing/stale report invalidates descendants.
Keep review records and machine-generated artifacts out of printed exposition.
