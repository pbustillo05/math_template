# Research workspace

Use one directory per mathematical topic.
Each topic has a README identifying purpose, current status, entry points, dependencies, source gaps and the next useful action, plus a claim/task ledger.
Markdown, LaTeX, scripts and experiments are all welcome; notes need not imitate a finished paper.
Keep related material together and make the current argument discoverable without conversation history.

Use statuses such as `question`, `conjecture`, `attempt`, `proved-unreviewed`, `needs-repair`, `counterexample-verified`, `abandoned`, and `promoted`.
A failed proof attempt is not a counterexample.
A numerical experiment is evidence about that experiment, not a theorem.
Record assumptions, exact source versions and failure mechanisms.
Link promoted work to the manuscript label and preserve relevant earlier evidence.

Start from [the example topic](example/README.md), then replace it with your own organization.
Dated scratch files are fine inside a topic, but dates alone are not an index.

Scratch LaTeX is not structurally checked or indexed by default. Add `% semantex: on` on its own line to opt a note into the shared label/dependency CLI and its annotation contract.
