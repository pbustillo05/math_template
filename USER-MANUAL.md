# Hybrid math research user manual

Use this template to explore several mathematical approaches, recover the state of a project in a fresh session, and develop completed arguments into a reviewed manuscript. A research round resolves one bounded question. Its result can advance a proof, expose an obstruction, or change which route you pursue.

## Set up a project

1. Open the project folder in your editor or research agent. Run `make doctor` to check the local tools. The core workspace uses Python 3.10+ and a TeX distribution with `latexmk`, `pdflatex`, and BibTeX. See the [dependency list](README.md#start-here).
2. Run `make check` and `make pdf`. Open `build/latex/draft/main.pdf` to see the unreviewed demonstration. You can also run `make notebook` to see the optional human-readable record.
3. Write your question, assumptions, and success criterion in [PROBLEM.md](workflow/PROBLEM.md). Make a topic directory under `notes/` with a short `README.md` and a claim ledger. Use the [example topic](notes/example/README.md) as a model.
4. Add your first strategy to [ROUTES.md](workflow/ROUTES.md), then fill in [CURRENT.md](workflow/CURRENT.md) with one precise check. Give it a stopping condition and link the few files or labels a fresh agent should open first.
5. Set the manuscript title and author in `draft/main.tex`. When retiring the demo, update its `\subfile` line and remove its row from `workflow/links.json` if you remove or rename either of the linked demo labels. Replace the notebook’s example include when you begin your own entries.

If you want version control, initialize this folder as a new Git repository with `git init`. The workspace uses relative paths, so a project can have its own folder name.

## Find the right record

| To answer | Open |
| --- | --- |
| What are we trying to establish, and under which assumptions? | [Problem statement](workflow/PROBLEM.md) |
| What one question should I work on next? | [Current frontier](workflow/CURRENT.md) |
| What alternatives are live or blocked, and why? | [Route registry](workflow/ROUTES.md) |
| What was actually proved, calculated, or refuted? | The topic ledger and its linked evidence under [`notes/`](notes/README.md) |
| Where is the exact statement, proof, or source? | [SemanTeX](agents/SEMANTEX.md) over notes, draft, and retained papers |
| Which version was reviewed, and by whom? | [Review registry](workflow/reviews.json) and its linked reports |
| How did the strategy change over time? | [Optional milestone notebook](notebook/notebook.tex) |

Give each piece of evidence a primary home. For example, write a counterexample in a topic's LaTeX notes, link its label and file in the route registry, and name the next check in `CURRENT.md`. The frontier can then stay short as evidence accumulates.

## Run a research cycle

1. **Recover.** Read `CURRENT.md` and the relevant topic README. Follow the listed inputs to the exact hypotheses, candidate argument, and sources the check requires. Use the route registry when you need to compare strategies or recover why one stalled.
2. **Bound the task.** State what would settle the question for this round. For example, “prove the lemma under hypotheses A and B, produce a counterexample, or identify the first implication that needs an additional hypothesis.” For parallel work, give each agent a distinct task and its own output file. Use [QUEUE.md](workflow/QUEUE.md) to track those assignments.
3. **Investigate.** Search by idea when you lack a label. Retrieve exact LaTeX once a hit looks relevant. Read the retained original and match the hypotheses before relying on a published result. Use Markdown for strategies, sketches, and calculations. Label precise claims, proofs, and counterexamples in active LaTeX notes so a later session can retrieve them.
4. **Close.** Link the result and its status from the topic ledger. If it changes a route, record the exact consequence and the condition for reopening a blocked route. Update `CURRENT.md` with the next check, its inputs, and its stopping condition. The next session should be able to start from that page and the topic index.

You can start an agent with this request.

> Perform one bounded research round. Start with `workflow/CURRENT.md` and the relevant topic README. Use the linked inputs and stopping condition. Save the exact mathematical evidence in the topic notes, update the affected claim or route, and leave the next question in `workflow/CURRENT.md`.

The [short cycle guide](workflow/RESEARCH-CYCLE.md) is a reference for handoffs.

## Try a worked research round

The demonstration asks whether the image of an idempotent map $p\colon X\to X$ equals its set of fixed points. Consider two possible routes. `R001` checks the two inclusions directly. `R002` tries to obtain the stronger identity $p(x)=x$ everywhere by cancelling $p$ from $p(p(x))=p(x)$.

A bounded question for `R002` is whether idempotence alone justifies that cancellation. The round ends with a proof of the implication or a counterexample. From the project root, these commands find and inspect the demonstration and its related draft version.

```sh
scripts/semantex search "idempotent fixed point" --scope notes --show description
scripts/semantex get lem:notes-image-fixed --show content --latex
scripts/semantex links lem:notes-image-fixed
scripts/semantex context lem:image-fixed --depth 1 --max-chars 3000 --json
```

The context command retrieves complete source blocks within the character budget and lists omissions. Open any omitted prerequisite you need to justify a step. For a larger corpus, the optional local semantic index supports paraphrased queries with `--mode hybrid` after `rag setup` and `rag build`. Lexical search, exact retrieval, and context bundles work with the core setup. [Local search setup](agents/SEMANTEX.md#local-semantic-retrieval)

The constant map to $0$ on $\{0,1\}$ is idempotent and sends $1$ to $0$. This refutes `R002` as a general route through the stronger identity. Record the counterexample in the topic notes and link it from the route. Hand off `R001` by asking the next session to verify each inclusion. For $y=p(x)$, check $p(y)=y$. For a fixed point $y$, check that $y=p(y)$ puts $y$ in the image. The supplied note contains that proof. The [sample notebook entry](notebook/entries/example.tex) shows how to communicate why the strategy changed.

## Promote a result and obtain review

Move a complete, polished unit into `draft/` with its existing ID. If you keep both formulations, use distinct IDs and record an inspected `equivalent` or `derived-from` link. Declare actual premises at their use sites. For a literature premise, record a `src:` application with the exact retained location and the registered hypothesis-matching audit. [Annotations and source provenance](agents/SEMANTEX.md)

Run these commands on the assembled candidate. Here the target is the bundled demonstration.

```sh
make check
make pdf
scripts/semantex frontier lem:image-fixed
scripts/semantex fingerprint lem:image-fixed
```

Give independent proof, counterexample, and style reviewers bounded assignments with the exact labels, fingerprints, prerequisites, and source locators they must assess. The style reviewer also needs the relevant rendered pages. Resolve gaps, inspect the real reports, and register them in prerequisite order with `scripts/reviews.py`. The [review protocol](agents/PROTOCOL.md) gives the registration commands, verdicts, and report requirements.

```sh
make release TARGET=lem:image-fixed
```

The demo fails this gate until actual independent reviews and accepted support are recorded. For a project result, a successful release requires fresh review evidence and support in the assembled manuscript or through audited source applications. [Release rules](agents/SEMANTEX.md#versions-and-release)

## Write an optional milestone notebook

Use the notebook when an important counterexample, change of strategy, or completed argument is worth reading in sequence. Give the entry the mathematical question, decisive equations or examples, what changed, and the next question. Point readers to the exact notes or manuscript labels for details.

1. Create `notebook/entries/YYYY-MM-DD-short-title.tex` with a section heading and the entry. Copy the style of the [demonstration entry](notebook/entries/example.tex).
2. Add `\input{entries/YYYY-MM-DD-short-title}` to [the entry index](notebook/entries/index.tex) in chronological order. Replace the sample include when you start recording your own work.
3. Run `make notebook`. Open `build/latex/notebook/notebook.pdf`. The notebook builds independently of the manuscript and stays outside SemanTeX's active graph.

## Resolve common issues

| Symptom | Where to look |
| --- | --- |
| Search misses a working result | Check its label and description in active LaTeX notes, or broaden the search scope. The topic index remains the place to find Markdown sketches and failed attempts. |
| Semantic search reports a stale index | Run `scripts/semantex rag build` for the profile you are using, or use lexical search while the index is stale. |
| A listed premise is outside the manuscript | Include the needed authored unit in the manuscript assembly, or establish the applicable published result through a cited `src:` application and audit. |
| A review became stale | Inspect the changed statement, proof, or support with `get`, `deps`, and `frontier`. Re-review the affected scope and register the resulting report. |
| The notebook entry is missing from the PDF | Check the path and order in `notebook/entries/index.tex` and rerun `make notebook`. Build diagnostics are in `build/latex/notebook/build.log`. |
