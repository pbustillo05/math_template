# SemanTeX

Use the shared preamble for mathematical environments and packages. See [writing-style.md](../writing-style.md) for exposition.

## Files and labels

The index covers the manuscript in `draft/`, active LaTeX notes in `notes/`, and retained papers and their editable LaTeX audits in `references/`. Archives stay outside the active graph. The CLI reads literal saved source and skips comments and verbatim. Write semantic commands directly, outside macros and conditionals.

Give each mathematical environment one principal label directly after its opening. Use stable IDs such as `def:`, `lem:`, `thm:`, `prf:`, `src:`, or `cex:`. Use `sec:`, `eq:`, `fig:`, or `tab:` for navigation anchors. Descriptions are mandatory for principal mathematical labels and optional for anchors. Describe the objects, decisive hypotheses, and conclusion in one or two sentences. Proof descriptions should name the technique and the step it achieves.

```latex
\begin{lemma}
\label[The image of an idempotent map equals its fixed-point set.]{lem:image-fixed}
Let $p$ be idempotent in the sense of \use{def:idempotent}.
% Write the statement here.
\end{lemma}
\begin{proof}[
  label={prf:image-fixed},
  proves={lem:image-fixed},
  description={Applies idempotence to points in the image.}
]
% Write the proof here.
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

## Literature

```latex
\cite[text={Theorem 3.2}, label={thm:main}]{KEY}
\cite[text={Proof of Theorem 3.2}, file={paper.tex}, line=120]{KEY}
\cite[text={p.~17}, page=19]{KEY}
```

Use one key per citation. Resolve `label` within the retained paper. Paths in `file` are relative to the retained paper directory. `page` is a one-based physical page. Supply `file` when several PDFs are available. `text` gives the printed locator. Use `\cite{KEY}` for a citation of the whole paper.

Retained labels use a paper-key namespace such as `KEY:thm:main`. The original blocks and adjacent proof are retrievable when structurally identifiable. Ordinary upstream cross-references provide mentions. Join the project’s argument to the published result through a checked authored `src:` application with an exact citation. Record the original hypotheses, matched conventions, specialization, proof dependencies, and errata checks in a Markdown audit. Register the audit path, relative to the paper’s audit directory, in `references/KEY/audit/semantex.json`.

```json
{
  "schema_version": 1,
  "applications": {"src:application": "application.md"}
}
```

## CLI

```sh
scripts/semantex get ID --show content --latex
scripts/semantex get ID --show description
scripts/semantex get ID --proof all --json
scripts/semantex locate ID
scripts/semantex deps ID --depth 1
scripts/semantex rdeps ID --tree
scripts/semantex refs ID --json
scripts/semantex backrefs ID --json
scripts/semantex why RESULT INPUT
scripts/semantex order ID
scripts/semantex frontier ID
scripts/semantex fingerprint ID
scripts/semantex search idempotent --scope draft,notes
scripts/semantex graph --target ID --format dot
scripts/semantex export --output build/semantex/index.json
scripts/semantex check
scripts/semantex check --release --target ID
```

Default dependency depth is `all`. Use `--within` with `--scope` or `--paper` to restrict graph traversal. Add `--mentions` to `deps` or `rdeps` to explore mention and citation links. See [retained-source navigation](../references/REFERENCE-VIEWS.md) for the paper-specific commands.

`workflow/reviews.json` records informal acceptance. Fingerprints cover the exact mathematical text, selected proofs, transitive premises, source and audit inputs, and shared preamble and instructions. Retrieval descriptions can be edited independently. See [the review protocol](PROTOCOL.md) for report requirements. The checker establishes structural validity and review freshness. Checking mathematical validity requires inspecting the argument.

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

Pass `--profile NAME` consistently to the setup, build, search, and neighbor commands when switching models. The index reuses unchanged embedding inputs and rejects stale units in the query scope. File moves preserve cached vectors when the embedding input stays the same. `rag status --scope references --paper KEY` reports eligibility and description coverage.

Search and neighbor queries default to 16 hits. `--kind` and `--status` filter eligible units before ranking. Choose `--show labels`, `--show description`, or `--show content`. Use `--all-versions` to inspect linked versions separately. Neighbor lookup from an indexed ID uses the cached vector, and text queries use the local embedder. Hybrid queries fuse semantic and lexical ranks. `context` returns complete blocks up to its source-character budget and reports omissions.

[Qwen GGUF models](https://huggingface.co/Qwen/Qwen3-Embedding-4B-GGUF) · [EmbeddingGemma 2 GGUF](https://huggingface.co/ggml-org/embeddinggemma-2-GGUF)


### M2 measurements

The benchmark uses 34 mathematical units across the three scopes and 20 paraphrased queries with expected IDs. On the 8 GB M2 MacBook Air with llama.cpp b12359, the three semantic profiles each found all 20 expected IDs in the first 16 hits. The lightweight Qwen profile offered the best retrieval quality among the two low-memory profiles. The 4B model ranked more expected hits near the top, with system swap increasing during both of its runs. Memory figures below are maximum child resident set sizes. The heavier 8B profiles are suggestions for machines with more memory.

| Profile | Semantic MRR@5 | Warm median query | Max child RSS |
| --- | ---: | ---: | ---: |
| light | 0.702 | 41 ms | 766 MiB |
| mac8 | 0.775 | 283 ms | 2,363 MiB |
| gemma | 0.438 | 25 ms | 721 MiB |

The lexical baseline found 15 of 20 expected IDs in its first 16 hits. Rerun the fixture with `python3 scripts/benchmark_semantex.py --profile NAME` after setting up the corresponding weights. The benchmark uses a disposable corpus so it can run alongside a real project.
