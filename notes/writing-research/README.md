# Mathematical research writing and agentic revision

**Research date: 2026-11-15. Status: completed broad survey. This folder is intentionally git-ignored.**

The scope is publishable mathematical research: journal papers, arXiv preprints, and research notes. Authorship by a mathematician is not required. Lecture notes and expository articles are included as requested; homework, tutoring, and competition-paper prompts are excluded from the recommended core.

## Start here

- [Recommendations and comparison with the current repository](05-recommendations.md)
- [Proposed replacement for writing-style.md](writing-style.proposed.md)
- [Ready-to-adapt agent briefs and report format](06-agent-prompts.proposed.md)

**Main conclusion:** preserve exact mathematics while reducing the reader's reconstruction work. Explain new ideas, choices and logical transitions in natural mathematical prose; do not optimize for symbol density or minimum length. Use one editor with bounded, read-only reviewers, validate objections before repair, and check the actual revised mathematics.

The active `writing-style.md`, draft and acceptance protocol remain unchanged. The proposed guide and agent setup are recommendations, not an empirically established optimum or a proof review.

## Source library

| File | Numbered entries | Contents |
|---|---:|---|
| [01-human-writing.md](01-human-writing.md) | 37 | Manuals, research-writing essays, author advice, lecture guidance; includes multiple Tao essays and an index, not 37 independent authorities. |
| [02-ai-instructions.md](02-ai-instructions.md) | 24 | Publication-oriented skills/Markdown, detailed writing/review protocols, and adjacent boundary examples. |
| [03-agent-research.md](03-agent-research.md) | 26 | Primary research on scientific-paper critique/revision, self-feedback, personas, debate and evaluation. |
| [04-exemplars-and-refereeing.md](04-exemplars-and-refereeing.md) | 30 | 22 exemplary text entries and 8 referee/editorial resources; specific craft lessons, reputation evidence and limits. |
| **Total** | **117** | Annotated entries, with additional separately marked discovery leads. Not 117 full-text audits or statistically independent sources. |

The exemplar collection includes Serre's FAC/GAGA, Milnor's papers and graduate lecture notes, Atiyah–Bott, Hartshorne, Ghrist, Vakil, Stacks and Kerodon. Award-backed reputation, specific mathematician praise, our selection, and metadata-only leads are distinguished; there is no asserted consensus ranking of “best ever.”

## Quick reading path

1. Poonen (H03) and Bell et al. (H04): practical checks for justification, quantifiers, source locators and cognitive load.
2. Tao's English/motivation essays (H20/H23), Pak (H05), Barwick (H06): why complete mathematics still needs conceptual organization.
3. Loher (S01–S06), Enomoto (S07–S12), Ishiki (S13–S16): directly relevant public writing/review instructions. Related implementations are not independent empirical evidence.
4. MARG (A01), focused feedback (A03), XtraGPT/APRES (A06–A07): scientific-paper systems and their evaluation limits.
5. Self-correction/persona/judge cautions (A16–A26): why more criticism, stronger personalities, shorter proofs or higher model scores do not establish improvement.
6. Match exemplar passages to the task: Milnor for proof architecture; Serre for structural setup; Ghrist/Kerodon for motivation of abstractions; Stacks for exact reusable local interfaces.

## Provenance and inspection

Four actual workers divided discovery by topic; integration and proposed-policy writing were serial. Two workers then checked source alignment of the recommendations and prompts. This was a research survey, not independent mathematical verification. No synthetic reviewer reports or proof-acceptance records were created.

Each source card records direct URLs/DOIs, authorship/title, the text or metadata inspected, a concise original summary, relevance and limitations. Selected-section reading, abstract-only evidence, blocked text and uninspected leads are explicitly distinguished. The scope of “inspected” is not cover-to-cover validation. No empirical experiments were replicated.

The survey deliberately retains summaries and links rather than entire original paper/skill payloads. [sources.json](sources.json) is a discovery index, **not** a DOI-API bibliography. [gaps.json](gaps.json) lists open acquisition work; detailed reading/access/version gaps are in each topic file. No source is adopted as a premise of the sample theorem and no payload has been promoted to the mathematical `references/` corpus. Exact pinned TeX/PDF, DOI resolver metadata, alpha keys, hashes and paper-specific audits remain required before any later corpus promotion.

## Coverage and validation

[search-log.md](search-log.md) records method, coverage and limitations. [ledger.md](ledger.md) records tasks, evidence status, quality checks and remaining optional work.

This is broad, reproducible discovery, not a claim to have found every relevant document. Private/unindexed instructions, unavailable books, unreviewed leads, language coverage, mutable web text and recent preprints remain limits. A specific writing rule or agent setup needs calibration on the user's actual mathematics.

**Next useful action:** select representative units from a real manuscript and compare the current style policy, the proposed policy, and one bounded critique/repair cycle. No mathematical project direction has been inferred from the demonstration theorem.
