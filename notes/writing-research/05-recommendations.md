# Recommendations for this repository

Prepared 2026-11-15 from the linked surveys. These are our proposed design choices, not an experimentally established optimum for mathematical authorship. The active `writing-style.md` and `agents/PROTOCOL.md` have not been changed.

## Executive finding

Keep the repository's unusually good safeguards for complete arguments, exact source applications, explicit dependencies, stable notation, source/PDF readability, and separate mathematical acceptance. Change its stylistic objective from maximal formality and aggressive deletion to **precise mathematics with low reader reconstruction cost**. Add a reader-facing structure pass and an actual first-reading test before final sentence polishing.

The most directly relevant public implementations are [Loher's mathematical writing and campaign skills](https://github.com/amelieloher/math-paper-skills), [Enomoto's writer/reader/polisher skills](https://github.com/haruhisa-enomoto/math-paper-skills), and [Ishiki's adaptation](https://github.com/yoshito-ishiki-math/math-paper-skills). They are inspectable practitioner designs, not controlled demonstrations of superiority. Ishiki credits Enomoto, so they should not be counted as independent evidence. Their specific typography, model preferences, punctuation bans, and abstract-length defaults are not universal mathematical standards.

**Scope:** publication-oriented mathematics, including arXiv preprints, research papers, and publishable notes. Author credentials are not an inclusion requirement. Homework prompts and competition-paper templates are outside the recommended core. Lecture notes remain useful models for explaining difficult new concepts.

## What to change in writing-style.md

Read the concrete [proposed replacement](writing-style.proposed.md). It preserves the current source-line and semantic-reference conventions and adds explicit reader and preservation criteria. The following comparison explains the consequential changes.

| Current instruction | Problem or missing distinction | Recommended change and evidence |
|---|---|---|
| “Be extremely formal and explicit”; replace verbal steps by symbols whenever possible | Symbolic form can hide purpose, logical emphasis, and the distinction between a construction and its use. Precision and symbol density differ. | Use formulas for exact relations/calculations and English for reasoning, choices, purpose and mechanism. Tao explicitly argues for this balance ([H20](01-human-writing.md); [original essay](https://terrytao.wordpress.com/advice-on-writing-papers/take-advantage-of-the-english-language/)); Loher S03/S06 and even Kerodon's opening E11 supply practical models. |
| “Cut the fluff ruthlessly”; every sentence must perform a narrow enumerated task | The guide allows indispensable context, but the tone can lead an agent to delete examples, orientation, interpretation, and useful reminders. | Add a deletion test for reader understanding as well as mathematical content. Functional explanation earns its space. See S06, E02/E07/E12, and the human guides. |
| “Require a higher standard of rigor than any source” | No operational meaning for “higher”; risks re-proving standard theory and confusing maximal expansion with rigor. | Require complete, defensible arguments for our claims and checked applicability of every imported input. Do not treat a source's reputation as verification. Keep precise citation of established theory. |
| Stacks and Kerodon as the two models | Excellent reference works, but not sufficient calibration for a research introduction, an explanatory proof, or a survey. | Preserve them for exact local interfaces; add selected passages from Milnor, Serre, Ghrist, and Vakil for different jobs. E10–E14 distinguish audience and genre. |
| Prefer self-explanatory decorated notation; avoid unnecessary aliases | Good concern, but a long repeated expression or many subscripts can burden readers more than a short symbol. | Optimize total reading/memory cost. Introduce notation by kind, role, scope and sustained use. Recall it after a long interruption. See S03/S18 and Poonen/Conrad. |
| Each result has one principal assertion | Can cause artificial fragmentation of jointly chosen data, equivalent conditions, or a coherent multipurpose construction. | Require one coherent mathematical purpose; group genuinely linked conclusions with explicit quantifier scope. Preserve independent lemmas when they reduce a long proof's memory burden. Poonen, Important things (5), explicitly allows a lemma used once. |
| Short paragraphs, displays, and substantial lemmas | Useful, but lacks a test for whether the new idea is visible. | Identify the obstacle and decisive move; give long proofs a short route map; explain the consequence of difficult estimates. Do not expand routine arithmetic mechanically. |
| No explicit mathematics-preservation checklist for prose edits | Labels and formulas can survive while prose changes quantifier scope, uniformity, a hypothesis, or proof status. | Protect the full claim contract, audit new explanations/examples, and recheck affected uses after substantive rewriting (S01/S05/S09/S17/S18). |
| No stated research-article architecture | An agent can produce locally tidy paragraphs in discovery order. | Introduce the problem, exact contribution relative to prior work, and core mechanism early; stabilize the body before final abstract/introduction; order the body by mathematical dependence and teaching need. |
| A single style referee covers everything | A global editor already knows later explanations and may not notice first-encounter confusion. | Select first-reader, whole-paper editorial, or local regression mode explicitly. Keep proof checking separate (S08/S12/S14 in the AI-instructions survey; [R03–R07 in the referee survey](04-exemplars-and-refereeing.md)). |

The proposed replacement is longer than the current file because it specifies tradeoffs and tests rather than adding a vocabulary blacklist. If it proves too long in use, keep the core priorities and short rules in `writing-style.md` and move examples/task-specific checklists to `agents/` references. Do not copy multiple entire skills into the root policy; they contain conflicting conventions.

## A better agent setup

### Routine local polishing

Use **one editor and, when useful, one fresh reader**. Give them the same finite text and a declared audience. The reader reports; the editor decides and edits. Routine wording work does not require a standing team or a new acceptance ceremony. A completed wording pass is not independent mathematical acceptance.

For a short unchanged argument, review the relevant unit and nearby dependencies. For a coherent long proof, work on a meaningful proof unit rather than one isolated sentence at a time; otherwise local patches can destroy the narrative. For a manuscript-wide reading pass, keep one reader across sections so it can notice accumulated notation burden.

### A substantial draft or publication candidate

Use this sequence, with one canonical editor throughout:

1. **Freeze and brief.** Record the exact candidate, audience, prerequisites, main contribution, style examples, theorem/definition surface, source applications, and mathematical status. Incomplete work stays in notes. Preserve the baseline and a PDF; no commit or push is needed unless requested.
2. **Architecture and meaning.** Map the route from question to main theorem; identify which definitions/lemmas do useful work. Decide what moves, merges, or needs explanation before polishing vocabulary. A proof-verifier, counterexample reviewer, and source auditor have their own finite mathematical tasks under the existing protocol.
3. **First encounter.** Give a fresh reader cumulative segments in manuscript order, with neither later segments nor the writer's history. Ask where the intended reader first has to guess the meaning, purpose, or justification. The reader's inability to reconstruct something is an editorial finding, not automatically a proof gap.
4. **Whole-paper editorial pass.** A separate mode can see all the text and ask whether every construction and named result earns its space, the contribution matches the introduction, and the symbols stay recognizable. It can distinguish a deferred explanation from an unnecessary passage. Do not call this forward-blind.
5. **Triage and revise.** Validate each objection against the frozen text. Accept, reject with reason, or route to mathematics/source checking. One editor integrates accepted repairs in coherent paragraphs. Critics have no canonical write access. No quota of criticisms and no majority vote on truth.
6. **Natural prose pass.** Once structure is stable, read the current text without old criticism logs and repair accumulated patch syntax, repetitive definitions, telegraphic proofs, private shorthand, and abrupt transitions. Preserve the mathematics and log substantive touches outside the draft.
7. **Audit the changed mathematics.** Compare against the baseline: hypotheses, conclusions, quantifiers, choices, constant dependence, notation, citations and inferential edges. Inspect new motivation/examples for false mathematical assertions. A diff audit catches regressions but does not replace the full proof review required for acceptance.
8. **Build, render, read, accept.** Run `make check` for structural edits and `make pdf` for draft edits; inspect affected PDF pages and the assembled reading order. Recompute fingerprints and re-review changed support as required by `agents/PROTOCOL.md`. A final candidate's acceptance comes from actual fresh reports, not the number of prior cycles.

These stages are task types, not eight permanent agents. With this environment's four active slots, an editor can coordinate three bounded read-only specialists, then reuse freed capacity for the next type of review. A tiny edit usually needs only the editor; a major theorem follows the existing distinct-worker acceptance requirements.

### What a “nit-picking PhD student” should actually do

Give the agent a concrete background and reading task, not a prestige identity or a mandate to find mistakes. For instance: “Knows basic PL topology and category theory; has not seen our construction; identify the first undefined object, hidden choice, unexplained transition, or reference requiring reconstruction.” Require a locator, a reader consequence, and a minimal proposed repair. Permit “no issue found.” A separately assigned specialist checks any resulting mathematical objection.

Distinguish three things in each finding:

- **Observed defect:** what is absent, ambiguous, inconsistent, or needlessly difficult in the actual text.
- **Consequence:** what a reader cannot recover, or which assertion may have changed.
- **Proposed repair:** a suggestion to assess, not an accepted mathematical premise.

A reader should also identify passages that work well, so revisions preserve useful compression and explanation. Separate “must fix,” “useful improvement,” and “author preference.” An endless search for more objections rewards overediting.

### Stopping and regression

Start with one diagnosis–repair–check cycle. A second is justified by a located unresolved problem or an introduced regression. Stop optional polishing when substantive findings are discharged, the final unit reads coherently, and the remaining suggestions trade equally valid preferences. This two-cycle starting budget is our cost-control choice, not a literature-proven optimum. A budget stop never means a mathematically incomplete draft is accepted; record the remaining obligation and keep incomplete mathematics out of the final-form draft.

Keep the stronger acceptance rules already present in `agents/PROTOCOL.md`. Re-review changed arguments and affected support. Do not re-run unchanged investigations just to collect three matching verdicts. A reviewer who rewrites the argument cannot independently certify that rewrite.

## What research does and does not establish

- **Direct scientific-paper evidence:** A01/A03 evaluate the usefulness and specificity of comments; A06–A09 study paper revision/review systems. Much of this is ML, not pure mathematical exposition. Some studies use LLM judges, fine-tuned systems, or private/limited human evaluation. See the explicit methods and limitations in [03-agent-research.md](03-agent-research.md).
- **A concrete caution:** MARG's specialized reviewers generate more useful comments in a small user study, but inaccurate comments remain common. That supports comment validation, not automatic acceptance of every suggestion. [MARG primary paper](https://arxiv.org/html/2401.04259v1).
- **General self-correction evidence:** A11–A21 show that feedback quality, external evidence, initial prompts, and matched computation budgets matter. A good critique/rewrite result on a non-mathematical task is not evidence that a proof has become correct.
- **Mathematical quality evidence:** A25 studies style-related proxies for short competition proofs, not publishable manuscripts. It is a useful warning about deletion, not a definitive metric for writing research mathematics.
- **Personas:** A10 and A22–A23 support trying reader perspectives while warning against assuming that a title supplies expertise. Minimal role prompts should be tested on this actual writing task.
- **Our inference:** one editor, independent located criticism, exact source checks, controlled rewrites, semantic comparison, and final reading are a reasonable starting design. No source found establishes the universally best agent count, model combination, or number of rounds for mathematical-paper style.

## A small calibration experiment

Before expanding the system, select six representative units from a real future project: an introduction, a definition with its first example, a short proof, a long technical proof, a source application, and a display-heavy page. Compare:

1. current policy, one editorial pass;
2. proposed policy, one editorial pass;
3. proposed policy plus one fresh critique/repair cycle.

Freeze input mathematics and use comparable effort budgets. Ask the researcher to judge anonymous A/B outputs; reverse presentation order on a second comparison when practical and allow ties. Measure whether the reader can state the result and key move, identify hypotheses at use, resolve notation, and follow the proof without reconstructing missing premises. Record useful/invalid comments, accepted edits, mathematical regressions, time and cost. Keep the old text when a proposed change does not improve it. This is practical calibration, not a powered experiment or a substitute for review.

## Repository integration proposed for a later implementation

| Location | Proposed action |
|---|---|
| `writing-style.md` | Adapt the proposed replacement after the author has assessed its voice and detail level. |
| `agents/roles/style-referee.md` | Add audience/genre; choose reading mode; require positive preservation notes and located findings; keep mathematical issues separate. |
| New short reader/editor role references | Put cold-reading and polish prompts here rather than increasing the root instruction load indefinitely. Reuse existing templates. |
| `agents/PROTOCOL.md` | Preserve its mathematical acceptance conditions. Add the optional editorial sequence and distinguish readability evidence from correctness. |
| Existing report template | Add reader consequence, issue ID/disposition, and inspected reading order when useful; do not create a second review registry. |
| Notes/workflow | Keep a small issue ledger, exact baseline and accepted mathematical-preservation record. Keep it outside the manuscript. |

No installation, manuscript rewriting, independent theorem verification, commit, push, or journal submission was performed in this research task. Ready-to-use proposed role briefs are in [06-agent-prompts.proposed.md](06-agent-prompts.proposed.md).
