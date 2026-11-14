# Tooling provenance

The initial template was assembled on 2026-11-14 from local sibling repositories at the user's request.
No paper corpus, personal paths, credentials, session history, research claims or acceptance records were imported.

- `scripts/manuscript_graph.py` and the retained-source index in `scripts/semantex_sources.py` adapt `stratified/scripts/`'s structural scanner, exact environment retrieval, dependency traversal and fingerprinted review checks.
- `scripts/bibtex_utils.py` adapts `stratified/scripts/build_references.py`'s metadata transport, accent handling and actual `alpha.bst` label calculation.
- Bibliography acquisition, transactional corpus updates, optional Lean receipts, draft scaffolding and the VS Code hover/tree companion were built for this template.
- `texphage`'s local `unfold.py` and `semantex.py` informed conservative source flattening and virtual environment labels; its macro expansion/diagram conversion pipeline was not imported.
- `BourbakIA` supplied design inspiration for separate acquisition, semantic model, editor integration and critique roles; its unfinished orchestration and user-level configuration installer were not imported.

This is a project-local annotation layer called SemanTeX, not a dependency on the CTAN package with a similar name.
Retained third-party papers keep their own upstream notices and rights; acquisition does not grant a redistribution license.
The template does not assign a new license to the user's projects or to adapted upstream code.

Technical references consulted during implementation:

- [Crossref DOI content negotiation](https://www.crossref.org/documentation/retrieve-metadata/content-negotiation/) documents DOI resolver content negotiation and BibTeX formats.
- [arXiv source availability](https://info.arxiv.org/help/faq/whytex.html) describes source distribution and its limitations.
- [VS Code programmatic language features](https://code.visualstudio.com/api/language-extensions/programmatic-language-features) documents hover, definition, reference and diagnostic providers.
- `alpha.bst` in the installed TeX distribution is the authority for generated keys; the code does not approximate its author-name or collision rules.
