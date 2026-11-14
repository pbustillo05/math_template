# Retained reference corpus

Keep **all relevant papers**, including background, alternatives, negative results and uncited literature.
The template ships with an empty corpus.
A reference is acquired evidence; it is not automatically an accepted mathematical input.

## Acquire one paper

Prefer the publication DOI, and an exact arXiv version supplying TeX:

```sh
python3 scripts/references.py add --doi 10.1000/example --arxiv 2301.01234v2 \
  --relevance 'Supplies the theorem needed in the main argument'
```

Example identifiers are placeholders; substitute the actual paper.
If no publication DOI exists, omit `--doi` with `--arxiv` to request the DataCite DOI `10.48550/arXiv.ID`.
For a genuinely source-unavailable paper:

```sh
python3 scripts/references.py add --doi 10.1000/example --pdf https://example.org/paper.pdf \
  --reason 'Checked author and arXiv pages; only PDF available' --relevance 'Background input'
# Or use --local-pdf /path/to/original.pdf in place of --pdf.
```

Keep DOI-less or inaccessible candidates in `gaps.json` under `candidates`, with title, URL/identifier, relevance, checked locations, status, reason and next action.
Do not fabricate a DOI or bibliography entry. Keep a locally obtained source outside the keyed corpus until its identity is resolved, and record that location in the gap record without personal absolute paths.
Acquisition checks reject HTML responses, traversal, links, special files and oversized archives.
They never execute imported TeX.

## Contents and invariants

- `catalog.json`: stable DOI-based IDs, actual alpha key, pinned arXiv version, relevance and any source gap.
- `lock.json`: catalog snapshot and SHA-256 of every retained file outside `audit/`.
- `references.bib`: the sole bibliography, generated exclusively from retained DOI resolver responses.
- `KEY/`: one directory per paper, using the real `alpha.bst` label for the entire corpus.
- `KEY/metadata/doi-response.bib`: exact API response; `doi.json` records request/resolved URLs and response hash.
- `KEY/metadata/source.archive`: exact original arXiv payload; `source.json` records format, identifier, URLs and hash.
- `KEY/*.tex` and supporting files: safely extracted exact bytes; a PDF-only paper instead has `original.pdf`.
- `KEY/audit/`: editable reading notes, hypothesis matching, errata and claim ledgers, excluded from payload hashes.

Never edit retained payloads, even to repair compilation or insert labels.
Use derived views or scratch copies for normalization, flattening, annotation, macro expansion and compilation.
Acquisition preserves upstream bytes including bundled metadata; inspect the diff and upstream redistribution terms before publishing a real corpus.
An exact download is recoverable from its pinned identifier and archive hash, but network availability is not guaranteed: keep the retained archive under version control or an explicitly managed artifact store.

## Deterministic metadata and keys

```sh
python3 scripts/references.py doi 10.1000/example --key provisional
python3 scripts/references.py alpha path/to/entries.bib
python3 scripts/references.py arxiv 2301.01234v2 --dest build/downloads/paper
python3 scripts/references.py sync
python3 scripts/references.py verify
make bibliography
```

`doi` caches raw response/provenance under ignored `build/doi-metadata/`; `add` promotes that exact evidence into the tracked corpus.
Rendering performs documented HTML/entity, Unicode/accent and month transport adjustments, without inventing words or fields.
Unsupported metadata fails visibly instead of guessing.
An uncached DOI query can differ later; deterministic replay starts from retained evidence, not today's API.
`sync` has no network access and refuses changed locked bytes rather than blessing them with new hashes.
`verify` recomputes hashes, actual keys and generated bibliography and rejects missing/extra paper directories.

Alpha collisions are global: adding a paper can change existing keys from `AB24` to `AB24a`/`AB24b`.
The command reports the mapping and refuses to change existing keys unless rerun with `--apply-rekeys`.
That option prepares the entire new corpus and locator edits before integration, migrates key namespaces and paths in authored `.tex`/`.md`/`.json` plus audit paths, and reports touched files.
Inspect the diff, search for old keys, run `make check`, rebuild citations, and renew affected reviews afterwards.
The migration is a structured-token aid; it does not understand arbitrary user scripts, macro-generated citations or external links.
Do not hand-rename paper directories, silently change a pinned version, or merge editions as though they were the same payload.
A deliberate version replacement requires a separately reviewed migration retaining old evidence in a version archive outside the active keyed corpus.

## Reading and dependency navigation

See `agents/SEMANTEX.md` for exact `\cite` locators and checked local `src:` applications.
The same CLI retrieves upstream labels in the `KEY:upstream-label` namespace.
Generated virtual labels and conservative flattening are documented in `REFERENCE-VIEWS.md`.
Upstream references are a mention graph unless a logical dependency was explicitly declared; do not promote citation links into inferred proof premises.

Before use, record the statement, exact version and locator, matched hypotheses/conventions, relevant proof dependencies, later-version/errata checks and open gaps under `KEY/audit/`.
Compile retained papers only in scratch copies, with shell escape disabled, and keep compiler compatibility changes out of the original.
