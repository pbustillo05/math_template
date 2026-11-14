# Mathematical writing: exposition and aesthetics

This file governs the mathematics the reader sees.
The independent source-code and SemanTeX contract is in `agents/SEMANTEX.md`.
Aim for the precision and navigability of Kerodon and the Stacks Project while checking each argument on its own merits.

## Rigor and scope

State every hypothesis actually used, including finiteness, separation, size, regularity, basepoint, relative and parameter assumptions.
Bind variables before use; specify domains, codomains, categories and conventions where they affect meaning.
Distinguish a definition from a theorem, an equivalent characterization from a sufficient condition, and existence from canonical or unique choice.
“Natural”, “canonical”, “compatible”, “locally”, “generic” and “equivalent” require an exact interpretation.
A proof must justify its construction, well-definedness, claimed property and any independence of choices that the statement requires.

Prove new assertions fully in the project's notation.
Cite established results at exact theorem/definition/page locators after checking their hypotheses in the retained version.
Do not replace a missing reference with “standard”, or expand a standard subject merely to avoid finding its source.
Keep the additional argument when the citation only supplies part of the claim.
Check boundary and degenerate cases when definitions depend on them.
Do not conflate an isomorphism, an equivalence, a bijection on components, weak contractibility or contractible choice.

## Economy without omissions

Apply a deletion test: each sentence should define, state, construct, prove, qualify, cite, or provide necessary orientation.
Remove throat-clearing, repetition, motivational filler and commentary about the writing process.
Use formulas and named objects when they make the assertion more precise; use prose to explain the mathematical role of a formula.
Do not turn a proof into a list of unexplained symbols or omit a step for brevity.
Brief transitions are useful when they expose the structure of the argument.
Avoid announcing that a step is easy or obvious; give the reason or the precise reference.

## Units and proof architecture

Give each definition one principal notion and each result one principal assertion.
Split independently useful claims; separate substantial examples, caveats and comparisons into labelled remarks.
A block near half a page is a prompt to reconsider its organization, not a word-count rule.
State shared hypotheses once with an explicit scope.
Do not make a reader reconstruct the theorem's assumptions from a surrounding discussion.

Structure proofs into short mathematical steps with clear intermediate goals.
Extract a lemma when it isolates an independently useful claim or a substantial conceptual step; avoid a lemma for each routine calculation.
Present prerequisites before their use and distinguish an announced later proof from a usable established input.
Every “therefore” must follow from the preceding argument and available hypotheses.

## Notation and reader memory

Prefer established symbols and modular subscripts/superscripts whose meanings can be recovered.
Do not introduce `L = Link_Y(X)` just to shorten one formula; retain the meaningful expression when repetition does not justify a new name.
Introduce abbreviations only when repeated use pays for the memory cost.
Avoid recycling a symbol with a different meaning inside one argument.
Make choices and their dependencies visible: a family chosen for each parameter is not automatically a continuous choice.
Define conventions close to their first use and reference them precisely later.

## Citations and presentation

Cite the source of a borrowed assertion exactly where it is used.
Include theorem kind when numbering alone is ambiguous, such as `Definition~\dxref{def:idempotent}`.
The printed text must contain the mathematical qualification and locator needed by a reader; acquisition logs, hypothesis-matching tables and review bookkeeping belong in audits or notes.
A citation to an entire paper cannot support an unidentified local step.

Treat displayed equations as grammatical parts of sentences and punctuate accordingly.
Align related formulas at the relation that expresses their logic.
Break long displays at mathematical boundaries; never shrink an entire proof to make it fit.
Use whitespace, short paragraphs and intentional page breaks to reveal structure.
Inspect the rendered PDF for overfull boxes, stranded headings, dense blocks, illegible subscripts and awkward breaks.
Prefer descriptive headings and mathematical statements over slogans.

## Final reading pass

Read the assembled section without the exploratory conversation.
Can every object and convention be located? Does every assertion have its exact strength? Are proof steps and citations sufficient? Is each notation necessary? Are caveats visible where they matter?
Resolve ambiguity and missing arguments before polishing individual words.
A stylish incomplete proof is still incomplete.
