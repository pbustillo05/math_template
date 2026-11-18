# AI instructions for publishable mathematical research writing

Search and access date: 2026-11-15. Researcher: primary agent. **Scope clarification:** the author need not be a mathematician. Intended use in mathematical research papers, preprints, or publishable notes is decisive; tutoring/homework resources are excluded from the main recommendations.

These are publicly inspectable practitioner artifacts, **not controlled evidence that their workflows improve writing**. GitHub `main`/`master` links are mutable; this survey records observed text and access date, not a pinned installation. No packages were installed or executed. Reading a skill as evidence does not activate it as instructions for this repository.

## Best starting points

1. Loher's writing skill and paper campaign: unusually close match to this repository, including claim preservation, explanatory prose, exact citations, one editor, and independent reviews (S01–S06).
2. Enomoto's paired writer/reader and separate prose polisher: explicit first-reading vs whole-paper editorial vs regression review (S07–S12).
3. Ishiki's adaptation: shared author profile, manuscript-local exceptions, bounded independent readers, and recorded proof-detail decisions (S13–S16).
4. `math-prose`: use mathematical meaning to select verbs rather than mechanically varying synonyms (S18).
5. AI4Math-Writing: a source-backed publication workflow and specialized audit routing (S19).

## Detailed source cards

### S01 — Amélie Loher, `latex-math-writing/SKILL.md`

- **Source:** [entry point](https://github.com/amelieloher/math-paper-skills/blob/main/skills/latex-math-writing/SKILL.md); [raw text](https://raw.githubusercontent.com/amelieloher/math-paper-skills/main/skills/latex-math-writing/SKILL.md).
- **Audience / inspection:** research-level mathematical LaTeX; inspected task routing, authority, contract preservation, writing, and campaign sections. [Author's academic homepage](https://amelieloher.github.io/index.html) identifies her mathematics research position; credentials are contextual, not our inclusion criterion.
- **Content:** separates the readable mathematical paper from research notes and agent reports. Preserves quantifiers, constants, hypotheses, labels, and uncertainty. Gives long proofs a route map, introduces objects by kind and purpose, and explains the consequence of decisive calculations. Whole-paper work uses one canonical editor and bounded review assignments.
- **Use here:** strong model for the style/workflow split; no need to import its particular preamble or source-format preferences.

### S02 — Loher, `references/writing-rules.md`

- **Source:** [raw guide](https://raw.githubusercontent.com/amelieloher/math-paper-skills/main/skills/latex-math-writing/references/writing-rules.md).
- **Inspection:** priority order, safety invariants, source conventions, task selector, before/after checklists.
- **Content:** places mathematical correctness and fixed meaning above editorial taste. Separates mathematical invariants from local conventions. Has task-specific routes for theorem statements, displays, introductions, and notation conversion. Requires build and affected-page checks for substantive changes.
- **Caveat:** its paragraph-per-source-line convention conflicts with our sentence-per-line rule; punctuation and display-environment preferences are house choices. Adopt the separation of priorities, not the entire formatting list.

### S03 — Loher, `references/artisan-writing.md`

- **Source:** [guide](https://raw.githubusercontent.com/amelieloher/math-paper-skills/main/skills/latex-math-writing/references/artisan-writing.md).
- **Inspection:** statement construction, proof paragraphs, notation, and first-use guidance (§§ Craft statements, Write proofs artisanally, Control notation and definitions).
- **Content:** theorem statements express usable mathematical assertions; motivation sits nearby. Proof paragraphs carry a reduction, construction, application, or calculation. Parameters are chosen in dependency order and uniform choices are distinguished from separate choices. Local notation must reduce reader effort or expose structure. It recognizes both the cost of abbreviations and the cost of repeatedly displaying long objects.
- **Use here:** replace blanket symbol maximalism with precise formulas plus English explanations of purpose and mechanism. Some strict rules, such as displaying every identity in a conclusion, remain optional.

### S04 — Loher, `math-paper-campaign/SKILL.md`

- **Source:** [campaign](https://raw.githubusercontent.com/amelieloher/math-paper-skills/main/skills/math-paper-campaign/SKILL.md).
- **Inspection:** routes, shared controls, and prohibited shortcuts.
- **Content:** distinguishes building complete mathematics from polishing mathematics checked at a named revision. Uses bounded statement/proof units, a single editor, and separate mathematical/manuscript status. Polishing proceeds through reduction, citation, reading order, prose, introduction, and final audit.
- **Use here:** two distinct workflows for incomplete notes and a settled draft. Avoid imposing a full-paper campaign on a typo correction.

### S05 — Loher, `shared-controls.md`

- **Source:** [shared controls](https://raw.githubusercontent.com/amelieloher/math-paper-skills/main/skills/math-paper-campaign/references/shared-controls.md).
- **Inspection:** mathematical contract, one editor, statement packets, drift protocol, reviewer roles.
- **Content:** lists semantic invariants and routes changes back to mathematical review. Reviewers inspect exact snapshots and return evidence and smallest repairs; they do not concurrently edit the canonical manuscript. Separate reviewers may examine architecture, notation, exposition, sources, or rendered pages. Review effort scales with the claim.
- **Use here:** preserve our existing acceptance protocol; add explicit readability checks and audit new explanatory sentences, not formulas alone. Its controls are an engineering proposal, not a proof of independence or reliability.

### S06 — Loher, `route-polish.md`

- **Source:** [polishing route](https://raw.githubusercontent.com/amelieloher/math-paper-skills/main/skills/math-paper-campaign/references/route-polish.md).
- **Inspection:** aim, readiness, baseline, reduction, citation phases.
- **Content:** optimizes reader effort rather than line count. A reminder or explanation is redundant only if removing it preserves followability as well as correctness. Freezes a baseline, uses questions for a cold reader, preserves reasons for source applicability, and separates reducing the proof route from polishing prose.
- **Use here:** revise the current deletion test to retain orientation and functional repetition. Page budgets should be soft diagnostic constraints.

### S07 — Haruhisa Enomoto, `write-research-paper/SKILL.md`

- **Source:** [writer](https://raw.githubusercontent.com/haruhisa-enomoto/math-paper-skills/main/skills/write-research-paper/SKILL.md); [repository](https://github.com/haruhisa-enomoto/math-paper-skills).
- **Inspection:** writer entry point and repository workflow description.
- **Content:** three phases: structural/exposition review, a fresh prose and proof-presentation rewrite, then mathematical comparison against the baseline. Writer and review-supervisor turns can be separate. Model-specific examples in the repository are suggestions, not comparative evidence.
- **Use here:** architecture before sentence polish; mathematical audit after polish. Retain one canonical integrator. Do not adopt numerical model rankings or permission rules from this external artifact.

### S08 — Enomoto, `read-research-paper/SKILL.md`

- **Source:** [reader](https://raw.githubusercontent.com/haruhisa-enomoto/math-paper-skills/main/skills/read-research-paper/SKILL.md).
- **Inspection:** complete entry-point text.
- **Content:** distinguishes continuous first reading, whole-paper editorial review, and delta regression. A reader receives frozen text, specified audience and permitted inputs, writes only a report, and does not certify proof correctness. Withholds writer history and favorable prior verdicts.
- **Use here:** split the present style-referee assignment into separately selectable reading tasks rather than asking one reader to do everything simultaneously.

### S09 — Enomoto, `polish-math-prose/SKILL.md`

- **Source:** [polisher](https://raw.githubusercontent.com/haruhisa-enomoto/math-paper-skills/main/skills/polish-math-prose/SKILL.md).
- **Inspection:** rewrite and repair modes, structural changes, mathematical-touch log, build checks.
- **Content:** targets accumulated patches, compressed proof steps, awkward causative constructions, and telegraphic imperatives. A fresh reader of the current TeX rewrites coherent passages, logs substantive argument changes, and sends the result to a mathematical diff auditor. Repairs should be integrated into natural sentences, rather than appended as defensive clauses.
- **Use here:** a dedicated final coherence pass can remove the scars of many individually sensible reviewer repairs. Audit explanations too: unchanged theorem displays do not guarantee unchanged mathematics.

### S10 — Enomoto, mathematical exposition standard

- **Source:** [standard](https://raw.githubusercontent.com/haruhisa-enomoto/math-paper-skills/main/skills/write-research-paper/references/exposition-standard.md).
- **Inspection:** reader/purpose, exact language, formulas/prose, organization and first encounters.
- **Content:** gives every passage a reader-visible purpose, defines local terms before semantic use, and rejects project conversation as manuscript narrative. Prefers ordinary mathematical syntax and stable terminology. Separates theorem correctness from whether a reader can actually follow the exposition.
- **Caveat:** contains personal defaults (abstract length, introduction length, formulas over prose, exact heading layout). Treat these as examples requiring local calibration, not consensus. It illustrates why combining unfiltered style guides can produce contradictory commands.

### S11 — Enomoto, AI mathematical prose anti-patterns

- **Source:** [guide](https://raw.githubusercontent.com/haruhisa-enomoto/math-paper-skills/main/skills/polish-math-prose/references/anti-patterns.md).
- **Inspection:** core principle and concrete examples of causative compression, imperative chains, object/index confusion, private shorthand.
- **Content:** diagnoses mathematical prose that hides reasons behind verbs, stacks modifiers, or reads like pseudocode. Recommends naming the actual object and connecting premises, operations, and conclusions. Provides before/after examples rather than only a forbidden-word list.
- **Caveat:** the grammatical rules are stylistic judgments; some displayed examples contain substantive mathematical claims and must not be copied as verified facts. The transferable lesson is functional diagnosis of ambiguity.

### S12 — Enomoto, continuous first-reader protocol

- **Source:** [protocol](https://raw.githubusercontent.com/haruhisa-enomoto/math-paper-skills/main/skills/read-research-paper/references/first-reader-review.md).
- **Inspection:** purpose, contamination/read-ahead distinction, requirements, reader/supervisor responsibilities.
- **Content:** one persistent fresh reader receives cumulative segments in order and cannot use later explanations to excuse an earlier difficulty. Distinguishes first-encounter readability from proof audit and whole-paper necessity. Retains earlier observations and later resolutions.
- **Use here:** test whether the strategy and notation are available when needed. True read-ahead prevention needs an isolated artifact/environment; asking an agent with full-repository access not to open later files is a procedural constraint, not technical isolation.

### S13 — Yoshito Ishiki, `write-research-paper/SKILL.md`

- **Source:** [writer](https://raw.githubusercontent.com/yoshito-ishiki-math/math-paper-skills/main/skills/write-research-paper/SKILL.md); [public tools and provenance](https://yoshito-ishiki-math.github.io/research-tools.html).
- **Inspection:** scope, author/profile routing, proof-detail decisions, local conventions.
- **Content:** ordinary edits stay with one writer; authorial voice, math correctness, build health, and review evidence are distinct. Shared author guidance is supplemented by manuscript-local conventions. A recorded choice to omit routine detail should not be repeatedly reopened without a concrete new defect.
- **Use here:** avoid review inflation. Our proof-verification requirements still apply; a proof-detail preference does not discharge a mathematical obligation. Ishiki explicitly credits Enomoto as upstream, so these are related artifacts rather than independent endorsements.

### S14 — Ishiki, independent reader

- **Source:** [reader](https://github.com/yoshito-ishiki-math/math-paper-skills/blob/main/skills/read-research-paper/SKILL.md).
- **Inspection:** rendered entry point, context validation, review modes and input restrictions.
- **Content:** freezes the revision and reader contract; continuous, editorial, and delta modes answer different questions. Reviewer observes burden and proposes repairs; writer adjudicates. Recorded brevity decisions remain scoped and do not certify correctness.
- **Use here:** require the reader to distinguish a missing definition from an intentional harmless deferral, and a real defect from a preference.

### S15 — Ishiki, optional `examples/author-style.md`

- **Source:** [example profile](https://github.com/yoshito-ishiki-math/math-paper-skills/blob/main/examples/author-style.md).
- **Inspection:** adoption guidance and opening concrete-preference section.
- **Content:** explicitly says it is an optional author's profile, not universal mathematical English. Some restrictions concern punctuation, selected verbs, and contradiction syntax. The adopted profile belongs separately from manuscript-specific choices.
- **Use here:** separate hard semantic obligations from preferences. Do not indiscriminately merge personal bans into `writing-style.md`; first test whether a prohibition helps this author's intended papers.

### S16 — Ishiki, public research harness overview

- **Source:** [harness and skills](https://yoshito-ishiki-math.github.io/research-tools.html).
- **Inspection:** tool roles, author-style separation, provenance and public scope.
- **Content:** research state, evidence, manuscript projects, writing skills, and paragraph identifiers have separate responsibilities. Shared writing profiles are referenced by manuscript-local styles. Public examples exclude private manuscript corpora.
- **Use here:** retain this repository's durable notes and evidence structure. No need for a second incompatible review registry or paragraph-ID system.

### S17 — JiahaoLi-creator, `mathematical-academic-writing`

- **Source:** [skill](https://raw.githubusercontent.com/JiahaoLi-creator/mathematical-academic-writing/main/SKILL.md); [development/validation account](https://github.com/JiahaoLi-creator/mathematical-academic-writing).
- **Inspection:** priority order, modes, working register, paragraph functions, evidence language, integrity checks; repository's validation description.
- **Content:** protects formal meaning and evidence strength while revising mathematical/statistical writing. Separates drafting, review, verification, and artifact inspection. A claim register includes assumptions, support, location, and scope; functional auditing preserves meaningful limitations while deleting empty defensive prose.
- **Use here:** prioritize correctness, source fidelity, audience fit, directness, then concision. Broad scope includes publishable research despite course-note origins. Private validation claims are not publicly reproduced evidence of writing improvement; no author credential inference is needed.

### S18 — TianhuaGao, `math-prose`

- **Source:** [skill](https://raw.githubusercontent.com/TianhuaGao/math-prose/main/SKILL.md).
- **Inspection:** workflow, semantic distinctions, high-risk composition checks, revision modes.
- **Content:** chooses prose by mathematical action: assigning notation, defining, giving a formula, deriving, interpreting, or asserting a consequence. Preserves technical terms and deliberate parallelism; does not rotate synonyms for variety. Flags unjustified equivalence, quantifier changes, undefined objects, and unsupported stronger verbs.
- **Use here:** add short original before/after examples of reasoning prose, with meaning-preservation checks. Prefer semantic review to word-frequency quotas.

### S19 — VeryMath, `AI4Math-Writing/paper-writing`

- **Source:** [skill](https://raw.githubusercontent.com/VeryMath/AI4Math-Writing/main/skills/paper-writing/SKILL.md).
- **Inspection:** purpose, input/output contract, audit routing, templates.
- **Content:** drafts mathematical papers from verified notes, proofs, experiments, or reviews; unsupported claims are explicitly tracked. Routes specialized checks for proof obligations, notation, displays, bibliography and build/layout. Includes skeleton and submission-readiness templates.
- **Use here:** publication-specific and directly relevant. Maintain a claim/evidence mapping during revision without printing a ledger in the paper. No controlled evaluation inspected.

### S20 — mmogib, `math-research-writer`

- **Source:** [skill](https://raw.githubusercontent.com/mmogib/research-toolkit/main/skills/math-research-writer/SKILL.md); [research toolkit](https://github.com/mmogib/research-toolkit).
- **Inspection:** overview, basic workflow, paper outline, numerical audit, literature section; not all 869 lines exhaustively audited.
- **Content:** a publication workflow for computational/applied mathematics, particularly optimization, with theorem/proof structure, algorithms, numerical experiments and literature positioning. Requires actual reading notes to support related-work claims and separates computational audit from prose drafting.
- **Use here:** useful for applied mathematics, less suitable as the default shape of a pure theorem paper. Its conclusion/experiment templates should be conditional, not compulsory.

### S21 — fcescob, `terence-tao-skills/mathematical-writing`

- **Source:** [skill](https://raw.githubusercontent.com/fcescob/terence-tao-skills/main/skills/mathematical-writing/SKILL.md); [provenance/disclaimer](https://github.com/fcescob/terence-tao-skills).
- **Inspection:** production steps through proofreading and repository provenance.
- **Content:** translates linked Tao advice into an operational workflow: organize the logical route, put key ideas early, motivate, calibrate detail, manage notation, preserve accurate scope, and proofread. Links upstream sources and describes internal review rounds.
- **Use here:** a useful route map, but **not authored or endorsed by Tao**. Attribute advice to the original pages after checking them. Self-reported referee rounds are not an independent benchmark.

### S22 — K-Dense-AI, pure-mathematician `AGENTS.md`

- **Source:** [agent instructions](https://raw.githubusercontent.com/K-Dense-AI/scientific-agents/main/scientific-agents/pure-mathematician/AGENTS.md).
- **Inspection:** mindset, workflow, critical-thinking, communicating-results sections.
- **Content:** research-oriented agent persona covering claim status, source use, counterexamples, proof architecture, conventions, paper communication, and arXiv submission. Distinguishes paper, survey, and talk audiences.
- **Caveat:** broad checklist rather than a focused writing treatment. Specific editorial claims (for instance a universal bibliography-order rule) need venue verification and should not be imported. Calling an agent a pure mathematician is not evidence of expertise.

### S23 — mathcommunity, `oai-math-revised/AGENTS.md`

- **Source:** [instructions](https://github.com/mathcommunity/oai-math-revised/blob/main/AGENTS.md).
- **Inspection:** purpose/layout, permissible changes, human checking and epistemic warnings.
- **Content:** constrains contributions to correcting and contextualizing a corpus of model manuscripts. Explicitly prohibits treating manuscripts or agent notes as verified. Style rewriting is outside that repository's present scope without discussion.
- **Use here:** an instructive **boundary case**, not a style recipe: paper-maintenance instructions may intentionally prohibit stylistic rewrites. Do not count it as evidence for a polishing method.

### S24 — txmy, `ultra-mathematician/AGENTS.md`

- **Source:** [instructions](https://raw.githubusercontent.com/txmy/ultra-mathematician/main/AGENTS.md).
- **Inspection:** mission, roles, operating model, closure and evidence standards.
- **Content:** research orchestration separates scouting, solving, criticism, and formalization and uses bounded tasks and explicit stopping/evidence states.
- **Use here:** adjacent research-workflow example, not a strong prose-style guide. Its autonomous problem-selection agenda and strict formal closure policy do not apply to this repository. Do not mistake many critics for many independent correct judgments.

## Excluded and unresolved leads

| Lead | Disposition and reason |
|---|---|
| [abinzzz/mathlatex-skill](https://raw.githubusercontent.com/abinzzz/mathlatex-skill/main/SKILL.md) | Entry point inspected. Explicitly centers coursework/probability exercises and an assignment template; excluded from main recommendations under the user's clarification, although some equation hygiene transfers. |
| [Escap1ng/math-modeling-skill](https://github.com/Escap1ng/math-modeling-skill) | Competition modeling-paper workflow; discovery description only. Not evidence for research-paper prose; self-scored completion claims unvalidated. |
| [HappymathLabs/happymath](https://github.com/HappymathLabs/happymath) | Competition-paper lead, not promoted. |
| [Wholiver/Math.Skill](https://github.com/Wholiver/Math.Skill) | General mathematical reasoning; insufficient specific publication-writing relevance for main shortlist. |
| [xshi19/xshi-skills](https://github.com/xshi19/xshi-skills) | README inspected; math-notation skill raw fetch failed. Notation-focused candidate, content not assessed. |
| [juanitorduz/website_projects/AGENTS.md](https://github.com/juanitorduz/website_projects/blob/master/AGENTS.md) | Search snippet only; direct/raw fetch failures. Website-writing scope not established as paper-writing. Mirror search hit not used as primary evidence. |
| [jmf-enigma/math-research](https://github.com/jmf-enigma/math-research) | Research-loop instructions discovered and scoped. Defers polished fixed-proof exposition to a separate `math-proof-writing` skill; that exact separate artifact not yet inspected. |
| [scottnarmstrong/LeanAutoformalizationSkills](https://github.com/scottnarmstrong/LeanAutoformalizationSkills) | Repository overview inspected. Formalization/handoff rather than primary prose-style resource; keep adjacent, not as proof of writing gains. |
| [teorth/tao-web](https://github.com/teorth/tao-web) | Author-maintained web infrastructure with AI assistance; not a mathematical-paper writing skill. |
| [Tao's living AI views](https://teorth.github.io/tao-web/ai-views.html) | Author-reviewed AI-assisted summary inspected as context, not a controlled evaluation or a style skill. |

## Search record and limits

Search families included `mathematician "CLAUDE.md" "writing"`, `mathematician "AGENTS.md" mathematical writing style`, `"mathematical writing" "SKILL.md"`, `"mathematician" "writing-style.md"`, `"mathematics" "AGENTS.md" "exposition"`, `"mathematical writing" "skills" "github" mathematician`, `"math research" "writing" "SKILL.md"`, and snowballing through Loher → Armstrong and Ishiki → Enomoto. Later passes removed the mathematician-authorship restriction and excluded homework/competition/tutoring defaults. Generic academic/ML writing skills were not fully enumerated; their proliferation does not imply relevance to theorem-proof research prose. Search engines miss private/unindexed instructions. No finite saturation claim.

No primary research paper payload was retained by this subtask. These source cards are web-reading notes and access gaps, not a DOI-API bibliography or a theorem-source audit. Mutable skills should be pinned and license-checked before adoption; they were not installed as part of the survey.
