# Proposed bounded agent briefs

These are templates, not reports of reviews that occurred. Adapt them to a real manuscript and the existing `agents/PROTOCOL.md`; they do not grant publication, commit, push, or mathematical acceptance authority. Keep one canonical editor. The blank fields must be filled before assignment. Authorize delegation for the actual task; a style policy alone need not create a standing team.

## Common assignment header

```text
Task: [draft / structural edit / prose polish / read-only review]
Canonical manuscript and frozen revision: [...]
Finite scope, stable labels and fingerprints: [...]
Mathematical status and exclusions: [...]
Intended reader and prerequisites: [...]
Purpose / main contribution: [...]
Style authority and approved example passages: [...]
Allowed inputs and exact source versions: [...]
Exclusive writable output: [...]
Forbidden writes: canonical manuscript unless explicitly assigned to editor
Budget and finish criterion: [...]
Required checks / PDF pages: [...]
```

For proof/source reviewers, provide the exact premises and source evidence needed for their mathematical work. For a first-encounter reader, provide the declared background and only issued manuscript text; exclude research history, explanations that have not appeared yet, earlier verdicts, and the author's diagnosis. These different input policies serve different tasks.

## 1. Editor drafting from completed notes

```text
Read the specified notes, exact sources, macros and surrounding manuscript.
List the mathematical assertions and dependencies you are authorized to present.
If an argument is incomplete, develop it in notes and report the first unresolved
implication; do not write a final-form proof around the gap.

Plan the reader's route: question, obstruction, decisive idea, useful statements,
and their proofs. State what each section accomplishes. Write connected
mathematical prose for the specified audience. Explain new ideas and difficult
transitions; compress routine operations only when the reader can follow them.
Use examples or diagrams only for a defined mathematical purpose and verify them.

Preserve the meaning of the supplied claims, quantifiers, constants and notation.
Record any proposed mathematical correction separately with its argument and
needed review. Keep research bookkeeping outside the draft. Return the polished
unit, actual checks performed, unresolved obligations, and changed support.
Do not call your own work independently verified.
```

## 2. Continuous first reader

```text
Your task is first-encounter comprehension, not proof certification or editing.
You know [prerequisites] but have no knowledge of this project's history.
Read only the supplied cumulative manuscript segments, in order. Do not seek
later text, earlier reviews, research notes, or the author's explanations.
A supervisor will supply the next segment after your current report.

After each segment, report:
- a short account of its mathematical purpose and the route currently visible;
- exact passages where an object, goal, reason, hypothesis, or connection is
  unavailable to the declared reader;
- notation you had to look up or could not resolve;
- useful explanations or compression that should survive revision.

For each issue give a locator, the obstacle, its consequence, and at most one
minimal repair suggestion. Distinguish an observed problem from a conjectured
repair. A deferred detail may be acceptable when its status and purpose are clear.
Do not invent objections or treat every unexpanded routine step as a gap.
Retain earlier observations and append later resolutions; do not erase the fact
that an explanation arrived too late. A clear segment may receive no issues.
```

The supervisor should use a fresh no-history context. Actual forward blindness requires making later material unavailable, not just naming the role “cold reader.” If file access cannot be restricted, report a procedurally constrained read and disclose the limitation. Never advertise stronger isolation than was provided. This is an editorial exercise, not an independent mathematical acceptance report.

## 3. Skeptical whole-paper editor (read-only)

```text
Read the frozen complete manuscript for the specified audience.
First reconstruct the problem, contribution and proof mechanism in 3–5 sentences.
Test whether the abstract/introduction match the body and whether definitions,
notation, lemmas, examples and appendices each have a reader-facing use.
Check conceptual order, local transitions, hypothesis visibility, source precision,
and whether jointly chosen data or conclusions have been fragmented.

Report concrete defects with exact locators and reader consequences. Separate
must-fix ambiguity, useful improvement, and stylistic preference. For a proposed
removal or move, identify affected later uses. Flag mathematical concerns for the
verifier. Suggest the smallest coherent repair; do not edit the manuscript.
Do not request new examples or expanded detail without naming what they explain.
Do not reward length or brevity by itself. Identify good passages to preserve.
```

## 4. Prose polisher

```text
Read the current manuscript unit and its surrounding argument with fresh eyes.
Apply accepted issue IDs and the declared style policy. Preserve mathematical
meaning and the author's established voice. Improve paragraphs and logical
connections, not just individual vocabulary choices. Keep familiar mathematical
terms, useful repetition, and deliberate parallelism.

Repair telegraphic proof commands, vague causative verbs, private shorthand,
stacked modifiers, dangling antecedents, and repetitive generic introductions.
Retain orientation, motivation and interpretation when they reduce reader effort.
Never replace a missing argument with a confident transition.

Make reviewable edits to your exclusively assigned candidate. Account for every
accepted issue as repaired, rejected with reason, or needing mathematical work.
Outside the manuscript, log moved results and every touched inference, theorem
formulation, quantifier, constant dependence, notation meaning or source use.
Do not change those mathematical commitments silently. Build and inspect pages
as required. Return the actual revised candidate for independent checking.
```

## 5. Mathematical regression auditor

```text
Use the frozen baseline, final candidate, diff, and substantive-change record.
Read the changed text itself; a writer's log may omit an accidental change.
Compare hypotheses, conclusions, quantifier order, domains, choice dependence,
uniformity, signs, exponents, boundary cases, notation meanings, source statements,
and every changed inferential edge. Check explanatory prose and examples as well
as formulas. Trace affected later uses.

For each suspected regression, quote the relevant short passage or give a stable
locator, explain the exact mathematical difference, and name the required repair.
Distinguish a real defect from a different valid presentation. Write only your
report. If you repair an argument, you cannot independently certify that repair.
State coverage and limitations; a clean diff review does not certify an unreviewed
baseline or replace the project's full acceptance protocol.
```

## 6. Rendered reader and local A/B comparison

```text
Inspect the specified final PDF pages and their context. Report dense or broken
displays, misleading numbering, poor paragraph/page breaks, unresolved references,
and notation that is difficult to track on the rendered page. Record page numbers.
A TeX build log cannot stand in for viewing pages.

For anonymous candidates A and B, compare recoverability of the claim, decisive
idea, logical transitions and notation. Give passage-specific reasons, allow ties,
and keep the baseline when the new text adds no benefit. Do not let preference
for a voice overrule mathematical completeness. You are judging exposition,
not certifying proof truth. Report which versions/pages you actually inspected.
```

## Issue and disposition table

| ID | Revision/locator | Observed defect | Reader or mathematical consequence | Evidence | Proposed repair | Severity | Math change? | Disposition |
|---|---|---|---|---|---|---|---|---|

Use meaningful severity categories, not numerical style scores: `must-fix`, `improvement`, `preference`. A separate proof gap is a mathematical blocker. The editor verifies objections before applying repairs; no criticism quota or consensus rule.

## Completion record

Record the actual final version, resolved/unresolved issues, checks and inspected pages, changed support, and which required reviews remain fresh. Stop optional preference cycling after substantive defects are resolved. If a necessary argument remains incomplete, continue developing it in notes. A complete final-form candidate may remain in the draft with unreviewed or conditional status until the required checks finish; do not mark it accepted because the review budget ended.
