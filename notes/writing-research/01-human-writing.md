# Mathematical writing: manuals, essays, and author advice

Surveyed 2026-11-15. Research-paper and research-monograph writing is the main scope. The user clarified that the author's profession is immaterial; the intended use should be publishable mathematical research, rather than homework or tutoring. This is a source map, not a claim of exhaustive coverage or experimental proof of stylistic effectiveness.

**Inspection key:** `text-selected` means the actual text was opened and the identified portions inspected; it does not claim a cover-to-cover reading. `page` means the author's or publisher's descriptive page was inspected; recommendations cannot be attributed to unseen chapters. `lead` means discovery only. Original texts hosted in university mirrors remain primary textual evidence, but the mirror is not authoritative about version history. No payloads were acquired in this worker's scope; see the acquisition table below.

## Read these first

| Priority | Source | Why it matters here |
|---|---|---|
| 1 | H03 Poonen; H04 Bell et al. | Exceptionally actionable tests for local justification, hypotheses, cognitive load, and citations. |
| 2 | H20 Tao on English; H23 Tao on motivation | Direct corrective to a policy that favors formulas over explanatory prose. |
| 3 | H05 Pak; H06 Barwick | Research-paper architecture, introductions, notation, and reader orientation. |
| 4 | H01 Halmos; H02 Knuth et al. | Broad craft principles plus worked editing examples; not a uniform set of commandments. |
| 5 | H12 Bertozzi; H14 Goldreich | Research-specific advice, realistic audiences, and the limitations of LLM drafts and friendly feedback. |

## Core research-writing guidance

### H01 — Paul R. Halmos, *How to Write Mathematics*

- **Links:** [original essay scan in university course materials](https://i11www.iti.kit.edu/~awolff/lehre/scientific_writing/h-hwm-70.pdf); [1973 reprint scan](https://www.jeffreyheinz.net/classes/22F/materials/Halmos1973-How-to-write-mathematics.pdf). The latter contains Halmos's contribution, despite a cover naming all four booklet authors. The 1970 article is in *L'Enseignement Mathématique* 16, 123–152; [DOI candidate](https://doi.org/10.5169/seals-43857) was discovered but resolver access failed here.
- **Inspection:** `text-selected`, especially preface, §§1, 5–6, and discussion of consistency and words.
- **Content:** Audience, selection and ordering of material, advance planning of notation, and repeated rewriting are central. His preface preserves sharply conflicting advice about examples and lemmas. The spiral writing process revisits earlier material as later sections expose its weaknesses.
- **Use:** Require a reader and a central message; permit global restructuring. Do not elevate an individual writer's preferences or pessimism about teachability into universal law.

### H02 — Donald E. Knuth, Tracy Larrabee, Paul M. Roberts, *Mathematical Writing*

- **Links:** [author's page, downloadable TeX and errata](https://www-cs-faculty.stanford.edu/~knuth/klr.html); [full report PDF](https://jmlr.csail.mit.edu/reviewing-papers/knuth_mathematical_writing.pdf).
- **Inspection:** `text-selected`, §1 minicourse and contents locating §§15–17 refereeing, §§20–21 subscripts, §§31–33 Lamport, §42 Halmos. Author page inspected; it records an errata update dated 6 June 2026.
- **Content:** Before/after editing, grammatical integration of formulas, words between separate expressions, meaningful theorem introductions, largely self-contained statements, restrained notation, and sentence rhythm. Guest lectures expose different approaches rather than a single doctrine.
- **Use:** Build examples of bad and improved research prose. Its warning against excessive subscripts directly qualifies this repository's preference for elaborate modular notation. The report itself warns it is a lecture transcript rather than polished essays.

### H03 — Bjorn Poonen, *Practical Suggestions for Mathematical Writing*

- **Link:** [author's PDF](https://math.mit.edu/~poonen/papers/writing.pdf), dated 6 January 2026 in the inspected version.
- **Inspection:** `text-selected`, §§1–2, especially items 1–18.
- **Content:** Identify the support for each claim and each equality; announce deferred explanations; remove reasonable alternative readings; use one-use lemmas to reduce working memory; reveal which results remain needed later; state quantifiers and the use of hypotheses. Give exact locators and preprint versions. Title, abstract, introduction, and body should communicate the work at different resolutions.
- **Use:** The best source here for operational review questions. Do not reduce these to a demand for symbolic verbosity: explicit support can be supplied in plain prose.

### H04 — Renee Bell, Borys Kadets, Padmavathi Srinivasan, Nicholas Triantafillou, Isabel Vogt, *Practical Suggestions for Mathematical Writing*

- **Links:** [coauthor-hosted article](https://ngtriant.github.io/notes/practical_suggestions_for_mathematical_writing.pdf); [DOI 10.1090/noti2305](https://doi.org/10.1090/noti2305). *Notices AMS* 68(6), 930–934 (2021). Distinct from Poonen's handout.
- **Inspection:** `text-selected`, pp. 930–932, §§1–3.
- **Content:** Choose a concrete reader, outline main results, use consistent notation, and revise the architecture. Introductions should expose contributions and a roadmap. Maintain running examples; show where assumptions enter; split long proofs; tell readers what they can forget. Justify claims at the right moment and distinguish the support for multiple assertions. Diagrams supplement complete arguments.
- **Use:** Especially strong foundation for a research-writing rubric. Their deliberate choice of an imagined person for drafting versus editing supplies a useful human precedent for reader-role prompts, not experimental evidence about agents.

### H05 — Igor Pak, *How to Write a Clear Math Paper: Some 21st Century Tips*

- **Links:** [author's PDF](https://www.math.ucla.edu/~pak/papers/how-to-write1.pdf); [author's accompanying post](https://igorpak.wordpress.com/2017/07/12/how-to-write-math-papers-clearly/).
- **Inspection:** `text-selected`, §1 and §3.6; blog discussion inspected.
- **Content:** Clarity requires substantial author effort because confused readers often abandon a paper. Make notation consistent even when repair takes time. For long technical introductions, a short opening foreword can explain the underlying idea at a more accessible level. Writing guidance and general prose guidance both matter.
- **Use:** Add short conceptual entry points and a serious editing budget. Some punctuation preferences are explicitly disputed in the blog comments; copy those only by deliberate house-style choice. His opening group-theory example is intentionally false, a caution against mistaking clarity for correctness.

### H06 — Clark Barwick, *Notes on Mathematical Writing*

- **Links:** [text mirror](https://bimsa.net/activity/MathematicalCommunication/files/Clark%20Barwick%20--%20Notes%20on%20mathematical%20writing.pdf); [old author-hosted location, now 404](https://www.maths.ed.ac.uk/~cbarwick/papers/style.pdf).
- **Inspection:** `text-selected`, Introductions, Structure, Notation.
- **Content:** Introduce a familiar story, identify its unresolved aspect, and state the contributions. Organize citable mathematical units predictably. Give strategic descriptions around complex proofs, examples and nonexamples after important definitions, and reminders or a glossary for forgotten notation. Prefer words when they express a result more simply. Do not manufacture fashionable applications to justify intrinsic curiosity.
- **Use:** Keep a distinction between indispensable logic and desirable exposition. Several prescriptions are unusually strong, notably about constructions versus existential results; use judgment rather than adopting them wholesale. The mirror's current revision provenance remains unresolved.

### H07 — Michèle Audin, *Écrire des mathématiques* / *Conseils aux auteurs de textes mathématiques*

- **Links:** [author's maintained index](https://audin.pages.math.unistra.fr/autresarticles.html); [current linked PDF](https://audin.pages.math.unistra.fr/autresarticles/newhowto.pdf).
- **Inspection:** `text-selected`, opening and §2.10, introduction and bibliography.
- **Content:** Research exposition involves organization and communication, drawing on the AMS writing booklet. Plan the introduction early, finish it after the content, and make clear which questions the text answers and the background from which they arise.
- **Use:** A French-language source that expands the Anglophone canon. Distinguish planning an introduction from finalizing its prose; this reconciles apparently conflicting advice about writing it first or last. Old Strasbourg PostScript links fail; the new author index resolves this access gap.

### H08 — David Goss, *Some Hints on Mathematical Style*

- **Links:** [2007-revised text mirror](https://www.cnsr.ictas.vt.edu/mentoring/Goss.pdf); [earlier text mirror](https://cr.yp.to/bib/1998/goss-style.pdf).
- **Inspection:** `text-selected`, introductory version note, General Flow, concluding advice.
- **Content:** Define unfamiliar notions, keep statements unambiguous, make quantifiers and dependencies of constants explicit, and reread from the reader's perspective. Some redundancy protects comprehension against small mistakes. The later version records a change prompted by Serre concerning which computations to include.
- **Use:** Replace unconditional deletion of redundancy with a test of whether it prevents misunderstanding. Version comparison matters even for a short style note; the 1998 and 2007 texts should not be silently conflated.

### H09 — Nicholas J. Higham, *Handbook of Writing for the Mathematical Sciences*

- **Links:** [third edition, DOI 10.1137/1.9781611976106](https://epubs.siam.org/doi/book/10.1137/1.9781611976106); [second edition, DOI 10.1137/1.9780898719550](https://epubs.siam.org/doi/10.1137/1.9780898719550).
- **Inspection:** `page` plus visible chapter excerpts; not the entire book.
- **Content:** Broad coverage of writing, revision, words and symbols, equations, publication, workflow, indexing, reviewing, and books. The third edition includes a distinct review chapter and modern version-control and publication topics. The general-principles excerpt treats writing as part of thinking that can reveal gaps, rather than a clerical final stage.
- **Use:** A comprehensive reference manual for targeted consultation. Do not cite unseen detailed recommendations. Prefer the third edition when discussing the current book; the two DOIs are different editions.

### H10 — Steven G. Krantz, *A Primer of Mathematical Writing*, second edition

- **Links:** [arXiv record, v1](https://arxiv.org/abs/1612.04888v1); [HTML text](https://arxiv.org/html/1612.04888v1); [arXiv DOI](https://doi.org/10.48550/arXiv.1612.04888).
- **Inspection:** `page` and contents/selected HTML, not full book.
- **Content:** Grammar, syntax, mathematical writing environments, and publication practices, updated to account for the Internet, preprint servers, electronic journals and open access.
- **Use:** A substantial manual rather than a short checklist. Source TeX is advertised in the arXiv record and is a good acquisition candidate. The 2016 version's publishing discussion should be checked against present journal policy before operational use.

### H11 — Douglas B. West, *The Grammar According to West*

- **Link:** [author's text](https://mail.dwest.web.illinois.edu/grammar.html).
- **Inspection:** `text-selected`, introduction, index, and item on an ambiguous “This”.
- **Content:** A large set of concrete mathematical syntax, terminology and English usage issues, developed from textbooks, theses and journal editing. It covers quantifiers, definitions, formula separation, logical connectors, references, graph-theoretic terminology, and ambiguous antecedents.
- **Use:** A specialized copyeditor's reference after structure is sound. Reviewers should identify the precise reading problem rather than label every deviation an error. The author expressly presents other guides without endorsing them and acknowledges disagreement over his own preferences.

### H12 — Andrea Bertozzi, *Advice for Writing Research Papers and Dissertations*

- **Link:** [author's page](https://www.math.ucla.edu/~bertozzi/advice-papers.html).
- **Inspection:** `text-selected`, Formatting tips content, including subsection (f), Language models; opening level-of-detail discussion.
- **Content:** Learn structural conventions from good papers in the intended journal. Iterate prose, begin with simple sentence structure, and attend to tense, articles, denotation and connotation. Distinguish dissertation background from paper needs. Bertozzi describes having to rewrite the prose of a student's LLM first draft and cautions that language models can introduce false material.
- **Use:** Directly relevant research-author experience with AI. This is practitioner testimony, not a controlled comparison. Her blanket acknowledgment advice should be implemented according to actual venue requirements, not treated as a universal legal rule.

### H13 — Bruce C. Berndt, *How to Write Mathematical Papers*

- **Links:** [author's PDF](https://berndt.web.illinois.edu/writingmath.pdf); [author index](https://berndt.web.illinois.edu/).
- **Inspection:** `text-selected`, §§1–3.
- **Content:** Informative titles; introductions that quickly reveal purpose and prior context; avoid notation dumps and empty name-dropping. Explain the sources of nontrivial transitions in a chain of equations. He favors drafting the introduction first and revisiting it repeatedly.
- **Use:** Require line-level reasons without turning calculations into prose noise. His introduction-first preference differs from Tao's and Audin's finalization advice; the shared principle is continual reorganization around the mathematical message, not a mandatory drafting order.

### H14 — Oded Goldreich, *How to Write a Paper*

- **Links:** [author's version index](https://www.wisdom.weizmann.ac.il/~oded/writing.html); [slightly revised PDF](https://www.wisdom.weizmann.ac.il/~oded/R2/re-writing.pdf).
- **Inspection:** `text-selected`, §§3.1–3.4, 4.5–4.6, opening §5.
- **Content:** Write for a capable reader without privileged access to the authors. Avoid author checklists, obscure generality, excessive initial qualifications, and hidden conceptual difficulty. Allocate detail to the intellectual steps. Use explicit references and consistent navigation. Conclusions are optional when they add no perspective. Friendly readers who already know the work are weak tests of exposition.
- **Use:** Strong rationale for fresh-context readers and concrete reading tasks. It argues for balancing competing needs rather than following a canonical paper template. Its numerical guess about how few papers need conclusions is opinion, not survey evidence.

### H15 — Steven L. Kleiman, with Glenn P. Tesler, *Writing a Math Phase Two Paper*

- **Links:** [MIT OCW source and compiled-artifact entry](https://ocw.mit.edu/courses/18-704-seminar-in-algebra-and-number-theory-computational-commutative-algebra-and-algebraic-geometry-fall-2008/resources/piiujm2-1/); [readable text mirror](https://www.cnsr.ictas.vt.edu/mentoring/Kleiman.pdf).
- **Inspection:** `text-selected`, overview and Language (§3); MIT description inspected.
- **Content:** Organization, language, presentation, and a worked example of a short mathematics paper. It distinguishes informative detail from indiscriminate detail, values precision and clarity, and warns that synonym substitution can weaken coherence or change meaning.
- **Use:** Relevant to short expository research units despite its undergraduate institutional setting. MIT explicitly warns that its description of the former Phase Two requirement is obsolete. Retain that caveat rather than reusing old submission rules.

### H16 — Ashley Reiter, *Writing a Research Paper in Mathematics* (12 September 1995)

- **Link:** [MIT-hosted essay](https://web.mit.edu/jrickert/www/mathadvice.html).
- **Inspection:** `text-selected`, §§1–2 and overview of proof-writing sections.
- **Content:** A research paper must convince readers of deductions and place them in mathematical context. The writer supplies both the paper's internal logical map and the map connecting it to the wider subject. The essay explicitly acknowledges its reliance on the AMS booklet, especially Halmos.
- **Use:** Good conceptual account of why a paper requires more than correct formal steps. It is derivative advice, not an independent line of evidence that the same practices work.

### H17 — Boris Khesin, *Suggestions on Better Writing Math Texts*

- **Link:** [author-hosted one-page PDF](https://www.math.utoronto.ca/khesin/biblio/better_writing.pdf).
- **Inspection:** `text-selected`, all six numbered suggestions.
- **Content:** Titles and captions should carry information independently; expose results early, initially at an informal resolution if necessary. Name the object type alongside a symbol. Keep examples usable through successive hypotheses. Express simple formulas in words when helpful.
- **Use:** A very compact alternative model for a house-style checklist. Particularly useful tests: whether the contents page explains the paper, and whether the running example survives the current level of generality.

### H18 — Leonard Gillman, *Writing Mathematics Well: A Manual for Authors*; appendix, *The Use of Symbols: A Case Study*

- **Link:** [MAA's authorized appendix resource](https://mathcomm.org/folder/the-use-of-symbols-a-case-study/).
- **Inspection:** `page`; resource description inspected, appendix attachment not retrieved in this pass.
- **Content:** The appendix promises a worked simplification of a symbol-heavy mathematical article. The broader manual concerns organization, presentation, language, notation and revision.
- **Use:** Prioritize acquiring the actual paired examples for an editing demonstration. The resource's license restricts derivatives; link to the original and create independent examples rather than republishing an adapted scan. This entry does not certify the effectiveness of an unseen rewrite.

## Tao's research-writing collection

H19 is an index, not independent evidence beyond the individual essays. Each short essay has a distinct operational use; grouping them prevents artificially inflating the count of independent authorities.

### H19 — Terence Tao, *On Writing*

- **Link:** [author's index](https://terrytao.wordpress.com/advice-on-writing-papers/).
- **Inspection:** `text-selected`, main page and resource links.
- **Content/use:** Adapt writing to strengths, subject, audience and medium. The hub links guidance on organization, notation, detail, prototypes, accuracy, professional presentation and submission, and links many other authors surveyed here. Its express qualification against rigid universal rules is part of the advice.

### H20 — Tao, *Take Advantage of the English Language*

- **Link:** [essay](https://terrytao.wordpress.com/advice-on-writing-papers/take-advantage-of-the-english-language/).
- **Inspection:** `text-selected`, complete main essay.
- **Content/use:** Words can convey relevance, contrast, causation and emphasis that a logical conjunction alone does not supply. Slightly longer prose may be easier to read without sacrificing rigor. Routine computations can use compact notation after their role is clear. This directly supports replacing the active policy's instruction to prefer formulas whenever possible.

### H21 — Tao, *Give Appropriate Amounts of Detail*

- **Link:** [essay](https://terrytao.wordpress.com/advice-on-writing-papers/give-appropriate-amounts-of-detail/).
- **Inspection:** `text-selected`, main essay.
- **Content/use:** Spend explanation on innovative or crucial steps; compress genuinely familiar material. Explain unfamiliar conventions even if obvious to the author. State a crucial obscure lemma with an exact citation rather than assuming the reader knows an earlier long paper. Detail should follow reader difficulty and conceptual importance.

### H22 — Tao, *Create Lemmas*

- **Link:** [essay](https://terrytao.wordpress.com/advice-on-writing-papers/create-lemmas/).
- **Inspection:** `text-selected`, main argument and worked dependency example.
- **Content/use:** Lemmas encapsulate local ingredients and notation that readers can forget once the interface result is established. This is useful even without repeated application. A style policy should therefore allow a one-use lemma when it substantially reduces the live context rather than extracting lemmas only for reuse.

### H23 — Tao, *Motivate the Paper*

- **Link:** [essay](https://terrytao.wordpress.com/advice-on-writing-papers/motivate-the-paper/).
- **Inspection:** `text-selected`, main essay.
- **Content/use:** Readers should know the immediate and ultimate objectives and how the current step advances them. Explicitly marked heuristics, special cases and short proof plans can explain plausibility and strategy. Keep those explanations visibly separate from the completed rigorous proof; they are valuable complements to it.

### H24 — Tao, *Organise the Paper*

- **Link:** [essay](https://terrytao.wordpress.com/advice-on-writing-papers/organise-the-paper/).
- **Inspection:** `text-selected`, main essay.
- **Content/use:** Discovery order rarely makes good exposition. State milestones early and put distinct technical material where it least obstructs the main trajectory. Group related facts and place a one-use lemma near its application. Reorganization is an expected author task, not evidence of failure.

### H25 — Tao, *Describe the Results Accurately*

- **Link:** [essay](https://terrytao.wordpress.com/advice-on-writing-papers/describe-the-results-accurately/).
- **Inspection:** `text-selected`, main essay.
- **Content/use:** Explain significance by comparison with actual earlier results; acknowledge limitations and unresolved hypotheses. Use descriptive headings. Readers must be told if a claim is not being proved. For this repository, retain the stricter existing rule that unresolved proof obligations stay outside the finished draft unless the user deliberately requests an incomplete checkpoint.

### H26 — Tao, *Write a Rapid Prototype First*

- **Link:** [essay](https://terrytao.wordpress.com/advice-on-writing-papers/write-a-rapid-prototype-first/).
- **Inspection:** `text-selected`, staged drafting procedure.
- **Content/use:** First sketch architecture and approximate statements, then make them precise, test the key connections, and complete routine parts. Here that prototype belongs in `notes/`; the repository expressly disallows promoting incomplete arguments as finished draft prose. The idea changes the work sequence, not the final standard.

### H27 — Tao, *Don't Overoptimise*

- **Link:** [essay](https://terrytao.wordpress.com/advice-on-writing-papers/dont-overoptimise/).
- **Inspection:** `text-selected`, discussion of lemma optimization and artificial brevity.
- **Content/use:** Elaborate generality, contrived minimal hypotheses and extreme compression can all obscure a paper's purpose. Removing examples, whitespace and explanation does not reliably simplify mathematics. Use a bounded revision loop with remaining reader problems as its target; do not optimize word count by itself.

## Additional perspectives and adjacent material

### H28 — Timothy Gowers, *My Favourite Pedagogical Principle: Examples First!* (2007)

- **Link:** [author's post](https://gowers.wordpress.com/2007/10/19/my-favourite-pedagogical-principle-examples-first/).
- **Inspection:** `text-selected`, main principle and comparison of introductions to fields.
- **Content/use:** Earlier concrete examples can give a reader a mental structure to which formal definitions attach. He reports applying this while editing the *Princeton Companion*. Transfer to a research introduction is conditional: use a short model case when a new definition is hard to parse, without adding elementary teaching material to every paper.

### H29 — Jean-Pierre Serre, *How to Write Mathematics Badly*, Harvard Basic Notions lecture (2003)

- **Links:** [Maxine Calle's transcript](https://bpb-us-w2.wpmucdn.com/web.sas.upenn.edu/dist/0/713/files/2025/05/How_to_write_mathematics_badly__transcript_.pdf); [original recording host](https://wstein.org/edu/basic/serre/); [noise-reduced video mirror](https://www.youtube.com/watch?v=ECQyFzzBHlo).
- **Inspection:** `text-selected`, transcript introduction, On Theorems, On References; video not watched.
- **Content/use:** Satirical bad examples expose uninformative titles, undefined abbreviations, overloaded terminology and uncheckable references. Convert the satire into positive checks. Calle explicitly marks uncertain transcription and acknowledges feedback from Serre; this is a mediated transcript, not an author-written manuscript. Some video uploads are misleadingly labeled 2007; the transcript identifies the talk as 2003.

### H30 — J. S. Milne, *Tips for Authors*

- **Link:** [author's page](https://www.jmilne.org/math/tips.html).
- **Inspection:** `text-selected`, numbered satirical list.
- **Content/use:** Undefined notions, unexplained sign conventions, shifting definitions, hidden source applications, vague references and muddled quantifiers obstruct readers and conceal errors. Useful as a failure-mode checklist. The prescriptions are satire: an agent must reverse their direction rather than literally follow the list.

### H31 — Jonathan Richard Shewchuk, *Three Sins of Authors in Computer Science and Math* (1997)

- **Link:** [author's text](https://www.cs.cmu.edu/~jrs/sins.html).
- **Inspection:** `text-selected`, opening, Grandmothering, concluding discussion.
- **Content/use:** Get to the purpose instead of opening with generic field-wide platitudes; avoid vague invented acronyms; a conclusion should add perspective instead of duplicating the introduction. Useful against AI boilerplate and generic significance claims. Computational-science examples and a deliberately provocative voice limit literal imitation.

### H32 — Dimitri Bertsekas, *Ten Simple Rules for Mathematical Writing*

- **Links:** [author's institutional summary](https://faculty.engineering.asu.edu/bertsekas/ten-simple-rules-for-mathematical-writing/); [MIT slides](https://web.mit.edu/dimitrib/www/Ten_Rules.pdf).
- **Inspection:** `page`, ten-rule institutional summary; slides discovered, not read in full.
- **Content/use:** Segment arguments, develop segments linearly, expose hierarchy, keep notation and result statements consistent, balance explanation, preview objectives, make references informative, and consider examples, counterexamples and visualization. The intended scope includes mathematical papers and books. It supplies a structural checklist rather than evidence about AI workflows.

### H33 — John N. Tsitsiklis, *A Few Tips on Writing Papers with Mathematical Content* (December 2020)

- **Links:** [author's index](https://www.mit.edu/~jnt/write.html); [v5 PDF](https://www.mit.edu/~jnt/Papers/R-20-write-v5.pdf).
- **Inspection:** `text-selected`, indexed PDF and selected notation/logic guidance; accompanying slide file exceeded the browser tool's size limit.
- **Content/use:** Concrete guidance on papers containing mathematics, with emphasis on logical phrasing, notation, clear statement structure and readability. A useful applied-mathematics complement to algebraic-geometric models. The inspected PDF dates this version 13 December 2020 and explicitly limits its strongest applicability to applied mathematics and engineering. Its conventional paper outline includes a conclusion, unlike some pure-mathematics guides; venue and substance govern the choice.

### H34 — Jerzy Trzeciak, *Writing Mathematical Papers in English: A Practical Guide*

- **Links:** [publisher, DOI 10.4171/014](https://ems.press/books/standalone/11); [publisher's preface](https://ems.press/content/book-chapter-files/18522); [contents](https://ems.press/books/standalone/11/contents).
- **Inspection:** `page` plus preface, not full chapters.
- **Content/use:** A research-oriented phrase and usage reference organized by introductions, definitions, theorems, proofs, literature, editorial correspondence and referee reports, with examples from actual mathematics. It explicitly rejects enforced stylistic uniformity. Useful for grammatical precision and idiomatic phrases, especially for writers using English as an additional language; avoid turning the phrase bank into repetitive templates.

### H35 — Francis Edward Su, *Guidelines for Good Mathematical Writing*

- **Links:** [author's index](https://math.hmc.edu/su/writing-math-well/); [three-page handout](https://math.hmc.edu/su/wp-content/uploads/sites/10/2020/08/Guidelines-for-Good-Mathematical-Writing.pdf).
- **Inspection:** `text-selected`, Basics and audience guidance.
- **Content/use:** Audience, complete sentences, integrated equations, inviting voice and reader-friendly explanation. **Secondary priority:** this handout explicitly addresses mathematics majors rather than research-paper authors. Included because the basic sentence-level craft transfers; it should not set the default amount of elementary explanation in an arXiv manuscript.

### H36 — Keith Conrad, *Advice on Mathematical Writing*

- **Link:** [author's PDF](https://kconrad.math.uconn.edu/blurbs/proofs/writingtips.pdf).
- **Inspection:** `text-selected`, §1 Notation, §2 Equations and expressions, §4 Use helpful words.
- **Content/use:** Introduce the type and scope of every symbol, avoid overloaded variables and gratuitous names, integrate equations grammatically, display long derivations readably, and use words to communicate the proof's direction and inference. Its explicit preference for ordinary-language quantifiers is a useful corrective to reflexive symbolization. Examples range from elementary proofs upward; transfer the principles, not an elementary level of detail, into research papers. Some absolute prohibitions are house preferences rather than logical necessities.

### H37 — Tao, *Use Good Notation*

- **Link:** [essay](https://terrytao.wordpress.com/advice-on-writing-papers/use-good-notation/).
- **Inspection:** `text-selected`, main essay; an initial failed refetch was resolved later in the same survey.
- **Content/use:** Make important parameters visible and suppress inessential ones when conventions permit. Localize temporary symbols; recall distant notation; translate crucial cited results into the paper's notation. Repeated expressions often benefit from an abbreviation, while central statements may justify notation even for a single use. Macros allow later consistent renaming. This favors contextual judgment over a fixed prohibition on temporary names or an obligation to encode every parameter in subscripts.

## Located but not substantive premises

| ID | Document / direct discovery location | What remains to inspect |
|---|---|---|
| HL01 | N. David Mermin, [*What's Wrong with These Equations?* PDF](https://www.robots.ox.ac.uk/~phst/Style/mermin.pdf) | Original two-page physics essay; PDF opened but no extractable text. Search result suggests equation integration and descriptive cross-references; do not treat that as a full reading. |
| HL02 | Mermin, [*Writing Physics*](https://mermin.lassp.cornell.edu/KnightLecture.html) | Author-hosted 1999 lecture; adjacent discipline, not math-paper policy. |
| HL03 | Franco Vivaldi, [*Mathematical Writing*, DOI 10.1007/978-1-4471-6527-9](https://link.springer.com/book/10.1007/978-1-4471-6527-9) | Publisher description/contents inspected. Undergraduate orientation lowers priority; thesis chapter may transfer. |
| HL04 | Steenrod, Schiffer and Dieudonné's separate contributions to *How to Write Mathematics* (AMS, 1973), located via [Halmos's reprint cover](https://www.jeffreyheinz.net/classes/22F/materials/Halmos1973-How-to-write-mathematics.pdf) | The inspected scan is not the full booklet. Acquire the actual separate contributions; do not attribute Halmos's advice to all four. |
| HL05 | Tao, *Use Good Notation* | Access resolved; promoted to inspected entry H37. Retain this row as the access-history record, not an additional source. |
| HL06 | [AMS MathGradBlog resources](https://blogs.ams.org/mathgradblog/2010/10/21/resources-for-writing-mathematics/) | Discovery bibliography, not primary support for underlying recommendations. |
| HL07 | [Sina Hazratpour's source collection](https://sinhp.github.io/posts/2018/03/Expert%27s-Advice-On-Writing-Mathematics-Papers/) | Useful citation-chasing index; its quotations are not independent evidence from Goss/Halmos. |
| HL08 | [MAA writing-resource collection](https://dev.mathcomm.org/writing/teaching-writing/) | Additional manuals, examples and classroom materials; triage for research relevance before expanding. |
| HL09 | [Juan Pablo Vigneaux's writing bibliography](https://jpvigneaux.github.io/Ma4/writing/) | Good route to additional classics; teaching page itself is not evidence that every recommendation suits research papers. |
| HL10 | [Ravi Vakil, potential students, On writing](https://math.stanford.edu/~vakil/potentialstudents.html) | Primary endorsement of Serre and Tao for research-paper authors; not a standalone manual. |

## Recommendations for this repository (our synthesis)

1. **Highest priority: replace the symbol-preference sentence.** Preserve explicit hypotheses and quantifiers, but ask for the clearest mixture of words and formulas. State what the step accomplishes and why it follows. H02, H20 and H17 directly oppose equating rigor with symbolic density.
2. **Give every draft an audience and a reading goal.** A capable researcher in the area who lacks the author's recent work is a useful default. Record prerequisites outside the prose, then provide the local reminders necessary to read the paper. H03–H06, H12 and H14.
3. **Permit explanation, motivation and selective redundancy.** The current deletion test can classify useful conceptual orientation as fluff. Retain sentences that explain strategy, reveal the main idea, prevent a plausible misreading or recall a distant definition. H08, H20–H24.
4. **Use a checkable local justification rule.** For each nontrivial claim, identify its immediate support; for multiple claims or chains of equations, distinguish reasons. Announce deferred proof. Show where important hypotheses enter. H03, H04, H13.
5. **Broaden the test for extracting a lemma.** Reuse is only one benefit. A one-use lemma can hide temporary notation, reduce concurrent assumptions and expose an interface. H03, H04, H22. Avoid dozens of trivial fragments; Halmos's contradictory reader feedback is a useful reminder.
6. **Treat notation as a reader-cost optimization.** Standard, short, locally memorable symbols may outperform heavily indexed expressions. Long repeated expressions sometimes deserve a local abbreviation. The current example should be a conditional example, not an absolute prohibition. H02, H06, H17.
7. **Add research-paper architecture.** Identify the question, contribution, relation to prior work, limitations and main proof mechanism early. Prefer descriptive sections. Use a running example where it earns its space. A conclusion is optional. H03–H07, H13–H14, H24–H25, H31.
8. **Keep prototypes and finished drafts distinct.** Outline and explore in `notes/`, then promote complete polished units. Copy Tao's work sequence without violating the existing draft policy. H26.
9. **Evaluate actual reader work.** Ask a fresh reader to reconstruct the goal, strategy, assumptions and reason for a selected transition, recording the first concrete confusion. Goldreich explains why praise from an already-informed friend is weak evidence. This motivates a workflow experiment; it does not establish that any particular AI persona improves writing.

## Acquisition and version gaps

No original PDF/TeX payload, DOI API response or hash was retained by this worker. These URLs are openly recorded acquisition gaps, not entries falsely claimed to satisfy `references/README.md`. The user specifically requested this ignored survey folder; acquisition of a project reference corpus is a separate step if these become enduring policy authorities.

| Scope | Status and next action |
|---|---|
| All H01–H37 | Remote text or page inspection only; if retaining, fetch original bytes, record date/version and SHA-256, request exact DOI metadata where a DOI exists, and preserve source-specific reading notes. Do not fabricate alpha keys. |
| H01 | Resolve 1970 DOI and compare original article to 1973 reprint. |
| H02 | Acquire author-linked TeX and current errata; report illustrations missing from TeX download. Do not silently substitute the mirrored report for later printings. |
| H03 | Pin the inspected 2026-01-06 handout; its URL is mutable. |
| H04 | DOI is present in the inspected author-hosted paper. Publisher PDF returned 403; coauthor copy resolved content access, but exact DOI API acquisition remains undone. |
| H06 | Author's former URL 404. Search the author's current site or contact-free public archive for version provenance before relying on an exact revision. |
| H07 | Author-maintained PDF found; old PostScript 502 no longer prevents reading. |
| H08 | Two versions located; distinguish the 2007 revision from the 1998 file. |
| H09 | Third- and second-edition publisher DOI pages verified. Full book reading and payload access remain incomplete. |
| H10 | arXiv v1 and DataCite DOI verified from record; TeX available but not acquired. |
| H18 | Download and inspect the authorized appendix; full manual acquisition remains open. |
| H29 | Preserve transcript with its uncertainty markers; exact latest transcript version not pinned. Video not watched. |
| H32–H34 | Full slide/chapter inspection remains incomplete. H34 publisher DOI and research orientation verified. |
| HL01–HL10 | Discovery/limited-reading leads, with limitations stated above. |

## Search trail and limits

Search queries included: `mathematical writing advice Halmos how to write mathematics Knuth Larrabee Roberts`; `Tao Gowers advice mathematical writing`; `Poonen mathematical writing advice`; `Igor Pak How to write a clear math paper`; `Some hints on mathematical style Goss`; `Notes on mathematical writing Barwick`; `Conseils aux auteurs de textes mathématiques Audin`; `Writing a Math Phase Two Paper Kleiman`; `How to Write Mathematical Papers Berndt`; `Ten Simple Rules mathematical writing Bertsekas`; `Practical Suggestions Mathematical Writing Bell Kadets Srinivasan Triantafillou Vogt`; `Writing Mathematical Papers in English Trzeciak`.

Citation chasing: Tao's index → Audin, Barwick, Bertozzi, Conrad, Goss, Goldreich, Pak, Reiter, Serre, Milne; Knuth's author page → exact source and errata; Berndt's author page → current PDF; Su's index → original handout; Audin's moved author site → working PDF; Triantafillou's exposition page → 2021 article.

Coverage is strongest for English-language research exposition and the canonical AMS/MAA tradition, with a French-language primary source. It is not a multilingual systematic review. Manual advice is primarily expert judgment, often deliberately opinionated; multiple guides repeat one another. No quantitative claim about agentic writing improvement follows from the number of manuals that recommend a practice.
