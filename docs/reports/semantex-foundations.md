# Finding the big picture and the details in SemanTeX

Design review and measured changes · 18 November 2026

**The project already has an overview.** `AGENTS.md` directs a new agent to the blueprint. The blueprint README identifies the governing design, the roadmap records editorial decisions, and the skeleton contains the actual mathematics. In particular, `\mention{rem:mod-book-proof-route}` is an author-written tour of the argument for `\mention{thm:mod-book-moduli}`. My earlier suggestion to register the same information in a second volume overview would have given someone another document to keep in sync. I withdraw it. [Project entry point](../../AGENTS.md) · [Blueprint README](../../notes/blueprint/README.md) · [Roadmap](../../notes/blueprint/roadmap.md) · [Skeleton](../../notes/blueprint/moduli-book-skeleton.tex)

The useful distinction is **where the agent starts**. An agent entering the repository can follow the blueprint. An agent arriving at one lemma through a search, a proof, or a citation needs a way *back* to the notes that discuss it. That second journey is where the CLI can help.

## From a label back to the notes

Markdown notes already mention mathematical entries by stable label. SemanTeX already indexes those mentions. The new `backrefs ID --markdown` option presents them as a short list of files. For `\mention{thm:mod-book-moduli}`, it finds the [notes README](../../notes/README.md), [blueprint README](../../notes/blueprint/README.md), [blueprint ledger](../../notes/blueprint/ledger.md), and [roadmap](../../notes/blueprint/roadmap.md).

```sh
scripts/semantex backrefs thm:mod-book-moduli --markdown
```

The link belongs in the Markdown that discusses the result. Its file path is discovered at query time. Move the roadmap with its mention intact and the next lookup gives the new path. Remove the mention and the file disappears from that result’s list. If three passages in one file mention the same label, the terminal shows the file once at the first matching line. JSON gives all three occurrences. A note can also point to a synopsis or interface label if that is what it actually discusses. [CLI reference](../../workflow/SEMANTEX.md)

**A mention answers “where is this discussed?” An editorial decision answers “which strategy are we following?”** If a replacement blueprint and its predecessor both discuss the same theorem, both paths are legitimate search results. The blueprint README should name the chosen strategy and direct readers to the superseded one when useful. The CLI has no reason to guess which strategy won from a filename, modification time, or number of mentions. A document with no explicit mention will not appear in this lookup. The topic README remains the place to introduce a subject more broadly.

**When the TeX moves or gains a label**, run `python3 scripts/semantex_runtime.py register PATH`. It preserves the document’s identity and updates its path and declarations without touching unrelated bindings. Recording a new note now takes the same command as updating an existing one. [Context registration](../../scripts/semantex_runtime.py)

## What the context budget means

Suppose an agent opens `\mention{thm:mod-book-moduli}` and wants to read the proofs it uses. There are two useful questions.

| Question | Command | What happens in this example |
| --- | --- | --- |
| Which results does this proof use directly? | `scripts/semantex deps thm:mod-book-moduli --depth 1` | Lists all seven direct premises. |
| Can I read the proof and some of those premises together? | `scripts/semantex context thm:mod-book-moduli` | Within the default 8,000-character allowance, returns the root and four premises with their proofs, and names the three omitted premises. |

Two of the omitted entries were `\mention{thm:mod-book-arrays}` and `\mention{thm:mod-book-generation}`. They are on the main route. They fell outside the text allowance because the current command visits peers in label order and includes whole blocks. Nothing was missing from the underlying proof or dependency list.

My suggestion was simply to **show all seven names at the top, even when only four proofs fit below**. That would help someone using `context` alone. Today `deps --depth 1` already gives the complete list, and `get ID --latex` opens any chosen entry. I would only change the `context` display if agents repeatedly overlook its existing omission list. [Context implementation](../../scripts/semantex_rag.py)

## What was slow and what changed

An agent could append one ordinary sentence to a topic ledger, then wait several seconds to open a theorem whose source had never changed. SemanTeX was rescanning only changed files but still reassembling the whole graph and, in a fresh CLI process, writing a new graph snapshot. The corpus used for the test had about 55,500 anchors.

The cache now distinguishes edits to existing note prose from edits that can change the mathematics or its bindings. For an edited Markdown file in `notes/` or `draft/`, it reads the current bytes, runs the same Markdown parser and link checks, and updates the incoming references and their positions. A mistyped label is still an error. Moving, adding, or deleting a file, changing TeX or a registry, or changing pinned redirect evidence still triggers the full graph checks. The worker can also keep its mathematical search data in memory across a Markdown-only edit. [Cache](../../scripts/semantex_cache.py) · [Graph and Markdown parser](../../scripts/manuscript_graph.py) · [Query worker](../../scripts/semantex_service.py)

| Time to open the same theorem in a fresh CLI process | Before | After |
| --- | ---: | ---: |
| Empty SemanTeX cache | 11.53 s | 11.22 s |
| Usable disk snapshot, no edit | 0.48 s | 0.34 s |
| Immediately after appending one sentence to a ledger, median of three edits | **6.68 s** | **0.40 s** |
| Immediately after adding a label mention to that ledger | 6.69 s | 0.33 s |

Each run used a disposable copy of the same project inputs on the same Mac. The command read `\mention{thm:mod-book-moduli}` with `get --show content --latex`. Each result was byte-identical, and a subsequent `backrefs` found the new mention at the correct line. The three post-edit samples were 7.67, 6.68, and 6.52 seconds before the change and 0.39, 0.55, and 0.40 seconds after it. Empty caches, unchanged snapshots, and the added mention each had one observation per version. Regression tests also compare incremental results with a fresh graph, including changed positions, removed mentions, bad labels, moves, and pinned evidence. These numbers describe the Markdown edit case. A TeX edit has different costs. [Regression tests](../../scripts/tests/test_semantex_cache.py)

Graph export also used to scan the shared preamble and review instructions separately for every anchor, and repeatedly hash the same premises. The exporter now reuses those inputs within a command. In one before-and-after run exporting every hundredth sorted label (555 labels), the export stage took 3.43 seconds before and 0.62 seconds after. All 555 review fingerprints matched byte for byte. Each new worker request refreshes its review inputs so a policy edit is visible in the next lookup.

## Which further improvements are worth making

**Measure editing TeX next.** Editing a sentence in a proof, changing the proof selected for a statement, and changing a shared definition affect different readers and checks. Time those three operations separately. For each, compare the exact text, incoming uses, selected premises, and review freshness with a clean rebuild. That would tell us whether to spend the next engineering effort on parsing, rebinding, or writing the snapshot. It would also catch the most expensive kind of speedup to get wrong, where a reader sees yesterday’s proof after today’s edit.

**Evaluate search on the questions agents ask.** In four known-destination searches over draft and notes, hybrid search placed `\mention{thm:mod-book-arrays}` and `\mention{lem:mod-book-right-globes}` first on their respective queries. It missed `\mention{rem:mod-book-proof-route}` in its first 16 results for a question about the book’s outline. Adding `--kind thm` moved `\mention{thm:mod-book-moduli}` from outside the first 16 to second for a question about the main comparison. Four examples cannot rank embedding models. They do illustrate why “find a result described in different words” and “take me to the current plan” deserve different entry points. Keep the existing small model benchmark. Add real questions from research sessions, especially near-misses with different hypotheses or historical versions, before spending time on a larger model or another search index. [Existing benchmark](../../scripts/benchmark_semantex.py)

**Preserve the strongest parts of the DAG and bibliography.** A selected proof can be inspected verbatim, each declared use can be traced to its position, and an alternative proof can retain its own prerequisites. A cited paper, the exact passage in its pinned edition, and the project’s checked application serve different purposes. Preserve those distinctions. One improvement I would prioritize once independent reviews accumulate is showing *why* a review went stale. The fingerprint includes the entire reference lock, shared policy files, and the transitive support. A reviewer should be able to tell whether the argument changed, a cited source changed, or an unrelated paper was added before deciding what needs rereading. The review writer now locks the registry across the read, decision, and atomic replacement. Two agents recording independent reports can both keep their changes. [Review fingerprints](../../scripts/manuscript_graph.py) · [Review writer](../../scripts/reviews.py) · [Link writer](../../scripts/semantex_links.py) · [Reference source guide](../../references/REFERENCE-VIEWS.md)

**Keep documentation organized by what it is for.** A topic README explains where to enter the mathematics. Its ledger records decisions, failed routes, and the next open question. The precise statements and proofs live in TeX. The writing survey now lives in `docs/methods/writing-research/`. Its dated record and original artifact inventory travel with it. [Notes index](../../notes/INDEX.md) · [Writing research survey](../methods/writing-research/README.md)

**Keep one blueprint while writing one volume.** If a second volume begins, split `notes/blueprint/` into `volume_1/` and `volume_2/`, give each a README, and update the shared entry point. Stable mathematical labels let topic notes serve both. A release manifest or a new cross-volume citation mechanism becomes worth designing when there is a concrete published revision a later volume needs to cite.
