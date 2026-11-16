# Mathematical writing for research papers and notes

Proposed policy, prepared 2026-11-15. This is a reviewable recommendation, not the active repository policy.

Write for a mathematically mature reader who knows the stated prerequisites but not the project's history. For each manuscript, record its audience, purpose, assumed background, and two or three approved passages that illustrate its intended voice. Use Kerodon and the Stacks Project for exact statements, local references, and stable terminology; choose complementary examples for motivation and proof narrative. Expository papers, lecture notes, and reference works need different amounts of explanation.

## Priorities and preservation

Mathematical correctness and honest claim status come first, followed by fidelity to sources and conventions, reader comprehension, and economy. Venue requirements and explicit author choices govern compatible stylistic details. Concision never justifies deleting a hypothesis, a necessary inference, a useful explanation, or a qualification that changes the claim.

A stylistic revision must preserve hypotheses, conclusions, quantifier order, domains, choices, parameter dependencies, uniformity, signs, exponents, endpoints, normalizations, and the meaning of notation. Preserve stable labels, citations, and unresolved obligations. Flag a suspected error separately; any mathematical repair requires its argument and a renewed check of affected uses. New explanations and examples make mathematical assertions too.

## Organization and reader guidance

- **Organize around the mathematical route.** State the question, principal results, comparison with previous work, and new ideas early. Arrange the body by dependencies and conceptual milestones. Introduce technical machinery when its role is apparent. Finalize the abstract and introduction after the claims stabilize, then check them against the final body.
- **Explain purpose and mechanism.** Before a major construction or long proof, identify the obstacle and the decisive move. Give a short route map when it helps a reader follow the proof. After a difficult calculation, explain the consequence needed next. Prefer a concrete explanation to generic roadmap sentences.
- **Use examples deliberately.** Include a representative example, special case, diagram, or counterexample when it explains a definition, tests a hypothesis, or reveals the mechanism. Verify it. Distinguish intuition from proof and do not let an illustration replace an argument.
- **Keep environments coherent.** Give each result one coherent mathematical purpose. Keep jointly chosen data and interdependent conclusions together when splitting would obscure their quantifiers or use. Separate independently useful claims. Use remarks for substantial interpretation, comparisons, and caveats that would interrupt a statement.

## Statements and proofs

- **State the mathematical assertion exactly.** Declare objects, hypotheses, quantifiers, and conclusions with an unmistakable grammatical boundary. Make choice order and essential constant dependencies explicit. Distinguish canonical constructions from arbitrary choices, equality from identification, and existence from a specified construction. Give well-definedness arguments where needed.
- **Expose the logical work.** Give each proof paragraph a coherent job: reduction, construction, application, calculation, or conclusion. Identify the reason for a nontrivial implication at its point of use. State why an invoked theorem's hypotheses hold. Justify relevant boundary cases, exhaustive alternatives, both directions of equivalences, and claimed uniformity.
- **Calibrate detail to the reader and the argument.** Expand novel or delicate steps. Routine algebra may remain compressed when the stated audience can follow it without guessing an extra premise. Extract a lemma when it gives a substantial step a clear interface or reduces the burden of a long proof, even if used only once. Do not create a named result for every elementary observation.
- **Prove new claims and cite established inputs precisely.** Give complete arguments for new results. Cite checked primary or authoritative sources for standard theory with exact locators and matched hypotheses. Reproduce an established proof only when its adaptation, mechanism, accessibility, or later use justifies doing so. An assertion that something is standard does not discharge it.

## Prose and notation

- **Use English and formulas for their respective jobs.** Use formulas for exact relations and calculations; use English for logical connections, purpose, choices, and strategy. Prefer the form that the intended reader can parse with less reconstruction. Do not replace connected prose with a chain of symbols or telegraphic commands merely to save words.
- **Control notation by reader effort.** Define symbols before their first substantive use, state their kinds and roles, and keep temporary notation local. Prefer standard, stable terminology. Introduce an abbreviation when it reduces repeated complexity or reveals structure; avoid aliases that add memory cost without benefit. A readable short symbol can be better than repeated long decorated expressions. Recall a convention after a long interruption when confusion is likely.
- **Write natural mathematical sentences.** Make antecedents and inference markers precise. Prefer familiar verbs and exact mathematical nouns. Preserve deliberate parallelism and standard technical terms; avoid forced synonym variation, stacked private shorthand, generic praise, and ornamental transitions. Do not hide a logical step inside a vague verb or adjective.
- **Apply a reader-aware deletion test.** Remove repetition and sentences whose deletion loses neither mathematical content nor useful orientation, interpretation, or comprehension. Keep targeted reminders and meaningful limitations. Do not impose word counts, symbol density, or banned-word quotas as substitutes for judgment.
- **Keep process records outside the manuscript.** Source matching, review disputes, diagnostic tests, and editing ledgers belong in notes or audits. Keep mathematical qualifications and citations in the text. A paragraph must serve the reader's mathematical task rather than answer a private agent conversation.

## LaTeX and final reading

Use one semantic sentence per source line and indent displays and lists. Keep package choices, macros, and environments in the shared preamble. Follow `agents/SEMANTEX.md` for labels, dependencies, source locators, and proof attachments; name reference types when numbers may coincide. Treat displayed formulas as parts of punctuated sentences; align calculations by their mathematical structure and number what needs reference.

After structural changes, run `make check`; after draft changes, run `make pdf`. Inspect affected rendered pages and then read the assembled text in order for delayed definitions, notation burden, broken transitions, dense blocks, and poor breaks. State the actual verification and page-inspection coverage. A successful build or review registry is not proof of mathematical truth. Independent acceptance follows `agents/PROTOCOL.md`; polishing does not transfer an earlier verdict to changed arguments.
