# LaTeX Mathematical Writing-Style

Use [Kerodon](https://kerodon.net/) and [the Stacks Project](https://stacks.math.columbia.edu/tag/0013) as online models for high quality writing-style.
Require a higher standard of rigor than any source in `references/`.

- **Cut the fluff ruthlessly.** Delete a sentence if removing it changes neither the mathematics nor essential navigation.
  Each sentence must define, state, construct, prove, qualify, cite, or supply indispensable context.
- **Be extremely formal and explicit.** Replace vague prose with objects named with precise notations, mathematical formulas, quantifiers and hypotheses. Don't describe verbally steps that you can easily write formally with mathematical symbols.
- **Use notations wisely.** Humans have limited short-term memory: renaming too many variables makes it difficult for them to keep track. Prefer **modular lego-like self-explanatory** notations with subscript and superscript who meaning is easy to deduce. For examples, do not write $L=\Link_Y(X)$ merely to shorten one formula; use $\Link_Y(X)$ directly. Introduce an abbreviation only when its repeated use outweighs the reader's memory cost.
- **Keep latex environments focused.** Give each definition one principal notion and each result one principal assertion. Separate independently useful claims; put substantial examples, caveats, and comparisons in labelled remarks.
- **Structure proofs by mathematical steps.** Use short paragraphs and displaystyle math formulae; extract a lemma only for an independently useful claim or a substantial conceptual step. Never omit a hypothesis or argument to shorten the page.
- **Prove only the new theory.** Prove any new results in our notation, but cite checked primary sources for standard PL topology, general topology, and category theory, with exact locators and matched hypotheses “Standard” is not a substitute for an applicable reference or proof.
- **Keep bookkeeping out of exposition.** Put source matching, diagnostic tests, and review records in audits or workflow files. Keep the needed mathematical qualifications and citations in the text; distinguish definitions, proved claims, and unresolved obligations.
- **Make the source and PDF readable.** Use one semantic sentence per LaTeX source line and indent displays and lists. Follow `agents/SEMANTEX.md` for labels, dependencies, source locators, and proof attachments; name reference types when numbers can coincide, as in `Definition~\dxref{...}`. Keep declarations in the shared preamble and inspect rendered pages for dense blocks and poor breaks.
