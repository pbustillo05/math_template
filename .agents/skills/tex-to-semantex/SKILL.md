---
name: tex-to-semantex
description: Index mathematical definitions, statements, and proof dependencies from one retained TeX or PDF paper as a SemanTeX audit overlay with exact original locators. Use when asked to convert, annotate, or extend the searchable coverage of a paper in references/.
---

# Convert a retained paper to SemanTeX

Use the paper key and scope specified by the researcher. Express new annotations in the existing `references/KEY/audit/` directory. The original source, PDF, metadata, and lock are evidence. Read them and write the overlay separately.

1. Verify the retained version with `python3 scripts/references.py verify`. Consult the paper's existing audit and coverage ledger so repeated work extends the earlier import. Use `scripts/semantex source-labels KEY` and `scripts/semantex get KEY:LABEL --latex`. For split TeX, choose the entry point from the retained material and run `scripts/semantex reference-view KEY --main MAIN`. Review the source map or original files for locators. For PDF-only sources, inspect the rendered equations and cite the one-based physical page.
2. Inventory the definitions, assumptions, claims, counterexamples, and proofs in scope. Mark macro-generated or ambiguous constructs, inaccessible passages, and missing proof material in the coverage ledger. Compare with the exact retained statement and argument before normalizing any notation.
3. Put labelled LaTeX in one or more files under `audit/`. Use `ref:KEY:NAME` for statements and `prf:ref:KEY:NAME` for proofs. Give each unit a description that identifies its mathematical content or proof technique. Attach proofs through their `proves` option. Include exactly one originating `\cite` with a locator for each manifest entry. Distinguish a transcription from a restatement and keep every hypothesis and conclusion intact.
4. Register the units in `audit/semantex.json` under `units`, with `schema_version: 1`. For each unit record `representation` (`transcription` or `restatement`), `coverage` (`statement`, `proof`, or `statement-and-proof`), `dependencies` (`partial` or `inspected`), and `source_sha256` (the exact cited file's SHA-256).
5. Inspect the argument for each premise edge. Use `\hiddenuse` at a supported use site and `\hiddenmention` for navigational references. Put uncertain or unlocated prerequisites in the ledger. For a checked local application, follow the separate `src:` audit convention in `agents/SEMANTEX.md`. The import records the published argument and its coverage.
6. Run `make check`, verify the retained hashes again, and spot-check `get`, `locate`, and `deps --paper KEY` against the original. Report what was imported, what remains to inspect, and whether the semantic index needs refreshing.

Read `agents/SEMANTEX.md` for syntax and `references/REFERENCE-VIEWS.md` for raw source and virtual label behavior.
