# Agentic writing, feedback, revision, and evaluation research

Research date: 2026-11-15. Primary audience: agents preparing publishable mathematical research prose, including arXiv preprints. Homework/competition benchmarks below supply indirect cautions; they are not evidence of improved research-paper exposition.

## Main finding

The most relevant evidence supports **specific, context-grounded critique followed by controlled revision**, with checks for changes to scientific content. It does not establish an optimal autonomous team for mathematical papers. Research-paper studies mostly involve machine learning or biomedicine; math-specific studies mostly concern short competition/university proofs. Evidence that a review sounds specific, a revision wins a preference comparison, or a paper receives a higher automated score must be kept separate from evidence of mathematical correctness.

Sources A01–A10 concern scientific manuscripts or writing interaction; A11–A15 concern general feedback/refinement and grounded drafting; A16–A26 concern limits and evaluation. Entries record selective inspection honestly. “Body inspected” means named sections were read, not a replication or a complete audit. All numerical findings below are the authors' reports unless expressly labeled our calculation. No recommendation is a proven theorem about agent design.

## Research-paper feedback and revision

### A01 — D’Arcy, Hope, Birnbaum, Downey: *MARG: Multi-Agent Review Generation for Scientific Papers* (2024)

- **Source/version:** [arXiv:2401.04259v1](https://arxiv.org/html/2401.04259v1); [official implementation](https://github.com/allenai/marg-reviewer).
- **Inspected:** abstract, selected §7.1 participant details, §8 failure-analysis passages, and conclusion; architecture summarized from introduction.
- **Finding:** GPT-4 agents receive different manuscript chunks and specialize in experiments, clarity, or impact. Nine NLP/HCI researchers evaluated comments on their own work. MARG-S produced 3.7 good comments per paper versus 1.7 for the best user-study baseline; generic comments fell from 60% to 29%. Crucially, most comments across methods were still rated bad; 38–48% were highly inaccurate. Refinement could introduce unsupported requests without another validity check.
- **Use/limit:** closest early evidence for specialized manuscript critics, but small participant sample and no mathematical paper trial. **Inference:** adopt explicit aspect assignments and a comment-validation stage; specificity alone is insufficient.

### A02 — Liang et al.: *Can Large Language Models Provide Useful Feedback on Research Papers? A Large-Scale Empirical Analysis* (2023 preprint; 2024 journal publication)

- **Source/version inspected:** [arXiv:2310.01783v1](https://arxiv.org/html/2310.01783v1). Publication located through [NSF-hosted NEJM AI paper](https://par.nsf.gov/servlets/purl/10617069); journal version not compared line by line.
- **Inspected:** abstract and introduction of preprint, including summarized results/limitations; full methods not audited.
- **Finding:** GPT-4 feedback was compared with reviews of 3,096 Nature-family and 1,709 ICLR papers. A prospective study involved 308 researchers from 110 US institutions; 57.4% rated feedback helpful/very helpful. Models tended to request more experiments and struggled with deep methodological criticism. Review-point overlap is a similarity measure, not a correctness measure.
- **Use/limit:** supports cheap preliminary feedback as a complement to experts, with evidence from AI/computational biology rather than math exposition. **Inference:** ask for paper-specific deficiencies and let the author reject generic or irrelevant requests.

### A03 — Chamoun, Schlichtkrull, Vlachos: *Automated Focused Feedback Generation for Scientific Writing Assistance* (ACL Findings 2024)

- **Source:** [publisher page and DOI 10.18653/v1/2024.findings-acl.580](https://aclanthology.org/2024.findings-acl.580/); [paper](https://aclanthology.org/2024.findings-acl.580.pdf).
- **Inspected:** publisher abstract; paper pp.9742–9744 on task and architecture. Evaluation conclusions are author-reported; full annotation/statistical audit not performed.
- **Finding:** SWIF²T separates planner, investigator, reviewer, and controller. Investigation supplies manuscript/literature context before the reviewer identifies a passage and weakness type. The dataset contains 300 paragraph-specific peer-review examples. Human evaluations favor its feedback on specificity, reading comprehension, and helpfulness over the tested alternatives.
- **Use/limit:** directly relevant to a paragraph-level mathematical style referee, although not mathematics-specific and not a demonstration of improved final manuscripts. **Inference:** attach each criticism to a precise passage, explain the reader difficulty, and require an actionable repair.

### A04 — Lu et al.: *Agent Reviewers: Domain-specific Multimodal Agents with Shared Memory for Paper Review* (ICML 2025)

- **Source:** [official PMLR record](https://proceedings.mlr.press/v267/lu25p.html), pp.40803–40830; PDF linked there.
- **Inspected:** publisher abstract/metadata only. No numerical superiority claim adopted beyond the abstract's report.
- **Finding:** domain-specific reviewers share historical paper metadata and include multimodal reviewers for visual material. Evaluation uses ICLR 2024 papers; the authors report improvements and component ablations.
- **Use/limit:** useful architecture lead for separating manuscript prose, diagrams, and domain context. Shared memory can help context acquisition but does not create independent evidence. Research-paper review quality is the endpoint; improved mathematical exposition and proof validity are untested here. **Inference:** add rendered-PDF inspection as a separate bounded task when figures or layout matter.

### A05 — Hou, Lin, Chen, Gong, He: *PaperDebugger: A Plugin-Based Multi-Agent System for In-Editor Academic Writing, Review, and Editing* (WWW Companion 2026)

- **Source/version:** [arXiv:2512.02589v2](https://arxiv.org/html/2512.02589v2); [DOI 10.1145/3774905.3793122](https://doi.org/10.1145/3774905.3793122).
- **Inspected:** abstract and introduction; system/usage section map. Full analytics not audited.
- **Finding:** an Overleaf-integrated system provides localized patching, literature lookup, structured reviews, scoring, persistent history, and multi-agent execution. Usage analytics establish adoption/interaction patterns and the demo shows workflow feasibility.
- **Use/limit:** architecture and integration evidence, not a controlled writing-quality trial. User engagement cannot establish improved clarity or mathematical validity. **Inference:** preserve document state, stable locations, exact before/after patches, and revision provenance rather than passing rewritten whole papers among agents.

### A06 — Chen et al.: *XtraGPT: Context-Aware and Controllable Academic Paper Revision via Human-AI Collaboration* (inspected 2026 revision)

- **Source/version:** [arXiv:2505.11336v4](https://arxiv.org/html/2505.11336v4), 23 Apr 2026; [code/models](https://github.com/Xtra-Computing/XtraGPT).
- **Inspected:** selected §§3–4, especially Tables 7–8 and §4.4; method overview in abstract/introduction.
- **Finding:** section-specific criteria and surrounding context guide revision; a 7,000-paper dataset supplies 140,000 instruction/revision pairs for specialized fine-tuning. Three human evaluators rate revisions; much full-paper evaluation uses an automated AI-Scientist judge on 54 ICLR papers. Automated presentation scores rose, but automated “soundness” scores are not independent correctness checks.
- **Use/limit:** directly supports intent-specific, contextual revision. Its training/evaluation setting does not establish that prompting an untrained team reproduces these gains, or that pure math papers improve. **Inference:** specify the defect and intended effect before authorizing a rewrite.

### A07 — Zhao et al.: *APRES: An Agentic Paper Revision and Evaluation System* (2026)

- **Source/version:** [arXiv:2603.03142v1](https://arxiv.org/html/2603.03142v1).
- **Inspected:** §§3.2, 4.2, 5; Table 3.
- **Finding:** learned review criteria drive local search/replace edits, with experimental tables protected. In blinded comparisons, three participants rated each of 364 original/revised ML-paper pairs; a majority preferred revision for 287 pairs (78.8%, our division). Citation-prediction accuracy is a separate endpoint and does not demonstrate that revisions cause more citations. The stated 70.1–79.0% confidence interval deserves checking against the raw counts; do not reuse it uncritically.
- **Use/limit:** comparatively direct evidence about revised research-paper quality, but not mathematical writing or content preservation under proof editing. **Inference:** use reviewable local changes and protected scientific claims; optimize reader understanding, not citation prediction.

### A08 — Goyal et al.: *ScholarPeer: A Multi-Agent Framework for Automated Peer Review* (2026 revision)

- **Source/version:** [arXiv:2601.22638v2](https://arxiv.org/html/2601.22638v2), 9 May 2026. The v1 title included “Context-Aware”; do not mix its DeepReview-13K description with v2's experiment.
- **Inspected:** introduction, selected §4 including Table 1, and limitations/prompts map; full methods not audited.
- **Finding:** historian, baseline scout, and question/answer agents acquire external context before critique. V2 evaluates about 1,800 ICLR submissions; many side-by-side comparisons use an LLM judge. Same-backbone search-enabled comparisons help isolate the framework better than comparisons against smaller fine-tuned models.
- **Use/limit:** retrieval-grounded review is relevant; headline review win rates are not a mathematics correctness audit or a final-writing trial. **Inference:** source-audit a suspected missing theorem/citation rather than turning a reviewer's recollection into a new premise.

### A09 — Zhou et al.: *Discuss More, Comment Less: Boosting Automated Research via Multi-Perspective Collaborative Review* (October 2026)

- **Source/version:** [arXiv:2610.24050v1](https://arxiv.org/html/2610.24050v1).
- **Inspected:** abstract and selected §4 including Table 3 and ablation descriptions; method map; human-evaluation details not fully audited.
- **Finding:** RoundtableReview uses six reviewers, eight manuscript slots, independent initial reports, cross-examination, weighted voting, and chair synthesis. Two automated research systems revise from a common initial manuscript using competing feedback. Results are mixed across judges/backbones/comparators; the paper reports benefits with fewer comments. Some retrieval perspectives involve patents and policy, unsuitable for routine pure math work.
- **Use/limit:** unusually direct recent review-to-revision experiment, but not evidence for importing six personas or voting into mathematics. **Inference:** test structured disagreement and deduplication; never settle a proof dispute by vote.

### A10 — Benharrak, Zindulka, Lehmann, Heuer, Buschek: *Writer-Defined AI Personas for On-Demand Feedback Generation* (CHI 2024)

- **Source/version:** [arXiv:2309.10433v2](https://arxiv.org/html/2309.10433v2); [DOI 10.1145/3613904.3642406](https://doi.org/10.1145/3613904.3642406); [author project](https://hciaiprojects.uni-bayreuth.de/projects/ai-personas).
- **Inspected:** author project abstract, §4 method extracts, and paper structure; publisher DOI access returned 403, author PDF timed out, arXiv HTML available.
- **Finding:** Impressona lets writers define simulated audiences and request passage-specific feedback. Two exploratory studies (N=5 and N=11) found users valued multiple perspectives and used feedback to revise; feedback was often repetitive, verbose, or nonspecific. The second study emphasized academic writing.
- **Use/limit:** supports reader-perspective elicitation as an interaction design idea, not factual expertise or faithful simulation of real mathematicians. **Inference:** define a reader's background and reading task instead of inventing a famous mathematician persona.

## General revision, drafting, and collaboration mechanisms

### A11 — Madaan et al.: *Self-Refine: Iterative Refinement with Self-Feedback* (NeurIPS 2023)

- **Source/version inspected:** [arXiv:2303.17651v2](https://arxiv.org/html/2303.17651v2); [conference paper](https://proceedings.neurips.cc/paper_files/paper/2023/file/91edff07232fb1b55a505a9e9f6c0ff3-Paper-Conference.pdf). Table below refers to v2, not an audited comparison of versions.
- **Inspected:** abstract and selected §3.2–3.3 including Table 1; method/analysis/appendix map.
- **Finding:** one model generates, criticizes, and revises. Seven tasks include response quality, sentiment reversal, code readability, and arithmetic. Human A/B preferences apply to some tasks; others use automated measures. V2 Table 1 math solve-rate gains are only 0–0.2 points, including GPT-4 92.9→93.1. Large across-task averages must not be presented as mathematical writing gains.
- **Use/limit:** a practical critique/rewrite pattern; no research-paper exposition experiment. **Inference:** supply a concrete style rubric and retain the original until a separate check approves the change.

### A12 — Shinn et al.: *Reflexion: Language Agents with Verbal Reinforcement Learning* (NeurIPS 2023)

- **Source/version:** [arXiv:2303.11366v4](https://arxiv.org/html/2303.11366v4), especially §§3–5 and appendix D.
- **Inspected:** abstract/introduction architecture and experiment summary, plus paper section map; no full experimental audit or replication.
- **Finding:** an actor stores verbal reflections on evaluation feedback in an episodic buffer and uses them in subsequent trials. Tasks include ALFWorld, HotpotQA, and code; feedback can be environmental, heuristic, or model-produced. The often-cited HumanEval improvement concerns programming rather than writing.
- **Use/limit:** memory can carry concrete failures into the next revision, but incorrect reflections can persist too. **Inference:** store accepted issue/repair pairs and recurring mistakes in notes; do not promote an agent's self-reflection to a mathematical fact or keep appending an unfiltered conversation history.

### A13 — Bai et al.: *Constitutional AI: Harmlessness from AI Feedback* (2022)

- **Source/version:** [arXiv:2212.08073v1](https://arxiv.org/html/2212.08073v1), §§1.2, 3, appendix C.
- **Inspected:** abstract/introduction method overview, critique/revision and principles section map; no training-result audit.
- **Finding:** explicit principles guide generated critiques/revisions, then supervised training and reinforcement learning from AI preferences. Its evaluated objective concerns assistant harmlessness/helpfulness, not mathematical exposition.
- **Use/limit:** a source for principle-based critique, not evidence that inference-time prompting alone obtains the training results. **Inference:** a short, operational mathematical style policy can serve as a shared rubric, provided reviewers name the violated principle and check the actual passage. Broad imperatives without examples are harder to evaluate consistently.

### A14 — Shao et al.: *Assisting in Writing Wikipedia-like Articles From Scratch with Large Language Models* / STORM (NAACL 2024)

- **Source:** [publisher record, DOI 10.18653/v1/2024.naacl-long.347](https://aclanthology.org/2024.naacl-long.347/); [arXiv:2402.14207](https://arxiv.org/abs/2402.14207).
- **Inspected:** publisher abstract and architecture description; no full results-table audit.
- **Finding:** diversified questions and source-grounded simulated interviews precede outlining and drafting. Experienced Wikipedia editors rated more outputs organized (+25 percentage points) and broad in coverage (+10) than the tested outline-driven retrieval baseline. Source bias transfer and association of unrelated facts remained problems.
- **Use/limit:** evidence for research-before-outline and multiple informational perspectives; Wikipedia breadth can be inappropriate for a focused theorem paper. **Inference:** assemble a checked mathematical story before composing the introduction, but exclude tangential material even when retrieved successfully.

### A15 — Jiang et al.: *Into the Unknown Unknowns: Engaged Human Learning through Participation in Language Model Agent Conversations* / Co-STORM (EMNLP 2024)

- **Source:** [publisher record, DOI 10.18653/v1/2024.emnlp-main.554](https://aclanthology.org/2024.emnlp-main.554/).
- **Inspected:** publisher abstract only; mechanisms and percentages below are abstract-level claims.
- **Finding:** users observe/steer conversations among agents; a dynamic mind map organizes discoveries and a report summarizes them. WildSeek evaluates information seeking; participants preferred it to search engines or a retrieval chatbot in the reported human study.
- **Use/limit:** discovery and user preference, not mathematical research-paper quality. **Inference:** a bounded exploratory conversation may reveal missing motivation or related literature before drafting. It should terminate in a checked outline rather than become the manuscript itself.

## Negative results and evaluation discipline

### A16 — Huang et al.: *Large Language Models Cannot Self-Correct Reasoning Yet* (ICLR 2024)

- **Source/version:** [arXiv:2310.01798v2](https://arxiv.org/html/2310.01798v2), §§3–5; [conference record](https://openreview.net/forum?id=IkmD3fKBPQ).
- **Inspected:** abstract/introduction, including experimental conclusions and prompt-design critique; full experiment tables not audited.
- **Finding:** intrinsic correction without new information often fails or degrades reasoning in the tested models/tasks. Some apparent gains depended on oracle information, weaker initial prompts, or unfair inference budgets. Cost-matched self-consistency can rival debate.
- **Use/limit:** a dated model/task result, not a universal impossibility theorem and not a style study. **Inference:** do not assume that adding a second opinion or an extra rewrite improves a correct proof. Track introduced errors, compare against a strong one-pass baseline, and require new evidence when revising mathematical content.

### A17 — Tyen, Mansoor, Carbune, Chen, Mak: *LLMs Cannot Find Reasoning Errors, but Can Correct Them Given the Error Location* (ACL Findings 2024)

- **Source:** [publisher record, DOI 10.18653/v1/2024.findings-acl.826](https://aclanthology.org/2024.findings-acl.826/).
- **Inspected:** publisher abstract only; no direct numerical claim adopted.
- **Finding:** mistake finding and correction are evaluated separately across five reasoning tasks. Ground-truth error locations substantially help correction; a small classifier trained out of domain can improve localization. That location signal is additional information, not free self-knowledge.
- **Use/limit:** indirect but useful evidence for distinguishing critic and fixer. Does not establish research-proof localization reliability. **Inference:** require a pinpointed faulty inference, undefined symbol, or reader obstacle before repair; refuse vague “make it more rigorous” complaints as sufficient grounds to rewrite a whole proof.

### A18 — Gou et al.: *CRITIC: Large Language Models Can Self-Correct with Tool-Interactive Critiquing* (ICLR 2024)

- **Source/version:** [arXiv:2305.11738v4](https://arxiv.org/html/2305.11738v4), §§3–4, appendices A and D.
- **Inspected:** abstract/introduction architecture/task overview and ablation/limitations section map; full quantitative ablations not audited.
- **Finding:** external tools produce information used to validate and revise generated outputs. Experiments concern free-form QA, mathematical program synthesis, and toxicity reduction; tools matter to the reported improvements.
- **Use/limit:** mathematical program synthesis is not a paper proof or exposition benchmark. **Inference:** use exact source retrieval, symbolic computation, and proof assistants where appropriate to validate a specific criticism. A successful LaTeX build remains only evidence of compilation; it is not the type of correctness feedback supplied by an applicable mathematical checker.

### A19 — Kamoi et al.: *When Can LLMs Actually Correct Their Own Mistakes? A Critical Survey of Self-Correction of LLMs* (TACL 2024)

- **Source/version:** [arXiv:2406.01297v3](https://arxiv.org/html/2406.01297v3); [DOI 10.1162/tacl_a_00713](https://doi.org/10.1162/tacl_a_00713).
- **Inspected:** abstract/introduction and section map for §§3–8 (experimental fairness, external information, baselines, checklist); not the complete literature audit.
- **Finding:** the survey separates intrinsic correction, external information, and fine-tuning. It identifies inflated claims caused by privileged feedback, suboptimal initial prompts, and weak baselines. Reliable external feedback is a key favorable condition. Its synthesis has a stated literature timeframe and is not a verdict on all later reasoning models.
- **Use/limit:** methodological synthesis rather than an experiment on mathematics prose. **Inference:** evaluate the feedback generator and the revision separately; measure harmful changes as well as repaired defects and compare methods at equivalent budgets.

### A20 — Du, Li, Torralba, Tenenbaum, Mordatch: *Improving Factuality and Reasoning in Language Models through Multiagent Debate* (2023 preprint; ICML 2024)

- **Source/version inspected:** [arXiv:2305.14325v1](https://arxiv.org/html/2305.14325v1), §§2–3 and limitations.
- **Inspected:** abstract/introduction mechanism/task summary and analysis map; full experimental tables and conference-version changes not audited.
- **Finding:** independently initialized answers are exposed to each other and revised over debate rounds. The tested tasks include arithmetic, grade-school math, chess, factual biographies, and MMLU. This demonstrates potential gains for some configurations, not an automatic benefit of discussion.
- **Use/limit:** no final mathematical-paper writing measurement, and later cost-matched studies question the advantage. **Inference:** obtain independent first reports before allowing discussion, retain minority objections, and settle disagreements by a checked argument rather than convergence or confidence.

### A21 — Zhu et al.: *Demystifying Multi-Agent Debate: The Role of Confidence and Diversity* (2026)

- **Source/version:** [arXiv:2601.19921v3](https://arxiv.org/html/2601.19921v3), §§4–7, appendix C.
- **Inspected:** abstract, motivation/method, experiment map; mathematical analysis not independently verified.
- **Finding:** the authors analyze homogeneous debate's limitations and test diverse initialization plus calibrated-confidence updates across six reasoning QA benchmarks. Calibration and confidence handling are specific mechanisms, not simply asking every agent to sound confident.
- **Use/limit:** does not show that role names create independent expertise or that voting certifies a proof. **Inference:** vary concrete responsibilities and available evidence; use confidence only as a triage signal. An unverified numerical confidence estimate should never overrule a located mathematical gap.

### A22 — Zheng et al.: *When “A Helpful Assistant” Is Not Really Helpful: Personas in System Prompts Do Not Improve Performances of Large Language Models* (EMNLP Findings 2024)

- **Source/version:** [arXiv:2311.10054v3](https://arxiv.org/html/2311.10054v3); [DOI 10.18653/v1/2024.findings-emnlp.888](https://aclanthology.org/2024.findings-emnlp.888/).
- **Inspected:** §§3–5 and limitations.
- **Finding:** 162 personas were tested on 2,410 MMLU questions across four model families. Persona additions did not reliably outperform the no-role condition; some harmed accuracy. Audience versus speaker framing produced only small effects.
- **Use/limit:** objective factual QA, not writing style. The study does not prove that a reader role is useless for eliciting readability feedback. **Inference:** replace status-heavy prompts such as “famous Fields medalist” with explicit review questions, allowed evidence, reader background, and output requirements.

### A23 — Luz de Araujo, Röttger, Hovy, Roth: *Principled Personas: Defining and Measuring the Intended Effects of Persona Prompting on Task Performance* (EMNLP 2025)

- **Source:** [publisher record, DOI 10.18653/v1/2025.emnlp-main.1364](https://aclanthology.org/2025.emnlp-main.1364/); [arXiv:2508.19764](https://arxiv.org/abs/2508.19764).
- **Inspected:** publisher abstract only.
- **Finding:** nine models across 27 tasks are assessed for expert advantage, robustness to irrelevant attributes, and fidelity. Expert roles often had positive or nonsignificant effects, while irrelevant details could cause large losses. This qualifies an overly broad claim that personas never help.
- **Use/limit:** no mathematical-manuscript quality test; numerical extremes should not be treated as typical effects. **Inference:** use minimal role descriptions and test them on the actual writing task. A “nit-picking PhD student” is at most a perspective cue, not a validated source of mathematical judgment.

### A24 — Zheng et al.: *Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena* (NeurIPS 2023)

- **Source/version:** [arXiv:2306.05685v4](https://arxiv.org/html/2306.05685v4), §§3.3–4, appendix D.
- **Inspected:** abstract/introduction evaluation setup and bias descriptions, plus section map; full category-specific results not audited.
- **Finding:** strong judges can agree with human preferences on tested conversational outputs, but exhibit position, verbosity, self-enhancement, and reasoning limitations. MT-Bench has 80 questions; controlled expert votes and crowdsourced data support the reported agreement.
- **Use/limit:** user preference agreement does not establish research-math truth or expert exposition quality. **Inference:** blind candidate identity, reverse order for close A/B comparisons, allow ties, and require a passage-based reason. Do not promote a higher style score into proof acceptance.

### A25 — Petrov, Dekoninck, Dimitrov, Vechev: *Not All Proofs Are Equal: Evaluating LLM Proof Quality Beyond Correctness* / ProofRank (2026)

- **Source/version:** [arXiv:2605.10379v3](https://arxiv.org/html/2605.10379v3), §§3–4.4; Table 2; appendices A, E, G.
- **Inspected:** methodology, steering results, correctness filtering, validation/limitations map.
- **Finding:** 382 competition final-answer problems support proxies for conciseness, computational ease, cognitive simplicity, diversity, and adaptivity. Across 11 steered models, mild/strong brevity prompts reduced median correctness by 5.5/10.9 points; omitted critical steps are a failure mode. Removing correctness filtering rewards some simple but wrong proofs.
- **Use/limit:** unusually relevant mathematical style evidence, but short competition proofs, proxy metrics, and model-based evaluation differ substantially from research papers. **Inference:** optimize exposition subject to preserved correctness, never by word count alone; recheck every substantive shortening.

### A26 — Gonzalez et al.: *QEDBench: Quantifying the Alignment Gap in Automated Evaluation of University-Level Mathematical Proofs* (2026)

- **Source/version:** [arXiv:2602.20629v3](https://arxiv.org/html/2602.20629v3), especially §§4.2–4.4 and appendices N–P.
- **Inspected:** abstract/structure, evaluation framework and qualitative failure-case headings; detailed statistical tables not audited.
- **Finding:** evaluates the gap between human and automated grading of university-level proofs, distinguishing expert correctness from course-specific constraints. Qualitative cases include overlooking fatal breakdowns, rewarding empty arguments, and performative self-correction.
- **Use/limit:** university proofs, not research exposition or a tested polishing pipeline. **Inference:** use automated referees for located objections and triage, retain expert checking for acceptance, and avoid assuming that a polished proof or a detailed rubric closes the evaluation gap.

## Additional primary sources and open leads

These broaden the survey without being used to claim effective autonomous polishing of mathematical research papers.

| ID | Source | Inspection and relevance |
|---|---|---|
| L01 | Mina Lee, Percy Liang, Qian Yang, [*CoAuthor: Designing a Human-AI Collaborative Writing Dataset for Exploring Language Model Capabilities*](https://arxiv.org/html/2201.06796), CHI 2022; [author site](https://coauthor.stanford.edu/) | Abstract, overview, and section map inspected. 63 writers and 1,445 GPT-3 sessions in creative/argumentative writing. Useful for evaluating interaction, ownership, and productivity; not evidence about autonomous teams or math manuscripts. |
| L02 | Chao Jiang, Wei Xu, Samuel Stevens, [*arXivEdits: Understanding the Human Revision Process in Scientific Writing*](https://aclanthology.org/2022.emnlp-main.641/), DOI [10.18653/v1/2022.emnlp-main.641](https://doi.org/10.18653/v1/2022.emnlp-main.641) | Publisher abstract inspected. Corpus has 751 papers with revision alignment and 1,000 annotated sentence pairs. Promising source for constructing realistic style-edit benchmarks; descriptive dataset, not an agent experiment. |
| L03 | [*A local, privacy-oriented multi-agent LLM framework for framework-grounded manuscript editing: A proof-of-concept*](https://www.sciencedirect.com/science/article/pii/S1386505626003904), IJMI 220 (Nov 2026), 106650; earlier [medRxiv manuscript](https://www.medrxiv.org/content/10.64898/2026.04.13.26350761v1.full) | Search result and preprint abstract only. Medical manuscript editing and linguistic metrics. Publication title/evaluation appear changed; versions must be compared before quoting numbers. Do not generalize Flesch scores or passive-voice reduction to mathematical clarity. |
| L04 | [*Can LLMs Correct Themselves? A Benchmark of Self-Correction in LLMs*](https://papers.nips.cc/paper_files/paper/2025/hash/ec07904adc847a45f53dceb44078f8f0-Abstract-Datasets_and_Benchmarks_Track.html), NeurIPS 2025 | Publisher abstract found. CorrectBench compares intrinsic/external/fine-tuned strategies across commonsense, math, and code. Full body not read. Useful follow-up to update the older intrinsic-correction evidence. |
| L05 | [*Self-Correction Bench: Uncovering and Addressing the Self-Correction Blind Spot in Large Language Models*](https://arxiv.org/abs/2507.02778) | Abstract found. Controlled error injection contrasts correction of own/external errors; full methods not inspected. Possible lead on fresh-context checking. |
| L06 | [*Towards Full Authorship with AI: Supporting Revision with AI-Generated Views*](https://arxiv.org/abs/2403.01055) | Discovery lead only; not used in recommendations. Relevant to preserving authorship during revision. |
| L07 | [*Judging LLM-as-a-Judge: Concerning Rubric Artifacts in LLM-based Automated Text Generation Evaluation*](https://arxiv.org/abs/2609.02942) | Abstract found. Tests whether rubric wording predicts judge scores without candidate responses. Full results uninspected; useful recent caution for future evaluation work. |
| L08 | [*IMProofBench: Benchmarking AI on Research-Level Mathematical Proof Generation*](https://www.sri.inf.ethz.ch/publications/schmitt2025improofbench), arXiv:2509.26076 | Author/lab page found. Closer research-level mathematics context than competition tasks, but proof-generation benchmark rather than writing-style intervention. Read before using particular results. |

## Evidence comparison

| Question | Most relevant evidence | Strength for our specific goal |
|---|---|---|
| Can feedback guide better scientific manuscripts? | A06–A09, especially A07's blinded original/revised comparisons | Direct scientific writing evidence, predominantly ML; transfer to math remains open. |
| Can specialized critics produce better comments? | A01, A03, A04, A08 | Useful human/automated review evaluations; comment accuracy and final-writing gains are distinct. |
| Should we provide a reader perspective? | A10; A22–A23 constrain claims about expert personas | Exploratory HCI support for perspective taking; no evidence that a prestige label creates expertise. |
| Does critique-and-rewrite work without new evidence? | A11 contrasted with A16–A19 | Task- and model-dependent. Style objectives can be easier to assess than logical correctness. |
| Is shorter mathematical prose necessarily better? | A25 | Direct short-proof evidence against indiscriminate shortening; research-paper transfer is an inference. |
| Do more agents or discussion rounds guarantee improvement? | A16, A20–A21 | No; baseline, diversity, calibration, information, and cost matter. |
| Can a judge certify the improved proof? | A24–A26 | No demonstrated guarantee. Correctness and exposition need separate checks. |

## Recommended bounded setup for this repository

This is our proposed design, inferred from the literature and the repository's existing `agents/PROTOCOL.md`; it has not been experimentally validated here. Keep that protocol's distinct actual workers, finite scope, fingerprints, and re-review requirements for independent acceptance. Do not replace it with agent consensus.

1. **Freeze a candidate and its contract.** Record intended readers, prerequisite knowledge, main contribution, exact theorem statements, hypotheses, definitions, labels, source applications, and which changes are permitted. Supply the relevant support closure rather than the whole exploration history.
2. **Run independent diagnostics before edits.** A mathematical verifier checks correctness; the existing counterexample role attacks scope; a style reader reconstructs the argument and marks the first reader obstacles. Add a source auditor only for located source questions. Routine polish can use one editor plus one fresh reader without manufacturing independent acceptance.
3. **Ask style questions with observable answers.** For each section: state its purpose; give the argument in three sentences; list unexplained notation, missing transitions, unnecessary repetition, and motivation absent from the text. Request exact locations and a reason. Permit “no issue found”; do not impose a complaint quota.
4. **Triage an issue table.** Each issue has location, category, reader consequence, evidence, proposed repair, confidence/uncertainty, and whether mathematical content changes. Distinguish genuine ambiguity from taste. Reject incorrect/generic criticisms before giving them to the editor.
5. **Edit serially and locally.** One editor applies accepted repairs using reviewable patches. Protect statements and proof dependencies by default. If notation, hypotheses, scope, quantifiers, or an inferential step changes, classify it as a mathematical change and route it for verification. Keep rejected alternatives and useful critiques in notes.
6. **Compare old and new.** A fresh reader sees anonymous A/B candidates in balanced order and judges purpose, clarity of the central idea, recoverability of dependencies, notation burden, and completeness. Word count is a diagnostic, not the objective. Permit ties and preserving the old text.
7. **Verify the actual final candidate.** Run repository structural/build checks as appropriate, inspect affected rendered pages, recompute fingerprints, and review changed support according to the existing protocol. A style pass cannot pass the proof.
8. **Stop with explicit conditions.** Stop after accepted local defects are repaired and no new substantive regression appears. Start with one diagnosis/repair/check cycle and allow a second only for a located remaining defect. Escalate unresolved mathematical disagreement to the researcher; do not run until critics agree or silently weaken a claim. Two cycles is a proposed cost-control default, not a number established by the cited studies.

### Concrete reviewer prompt

> Read the specified manuscript unit and prerequisites yourself. The intended reader knows [background] and wants to understand [purpose]. Do not edit. First reconstruct the claim and proof strategy in at most three sentences. Then report only located obstacles to understanding, precision, economy, notation, or source use. For each, give label/source line, the reader difficulty, a minimal repair, and whether the repair might change mathematical content. Distinguish must-fix ambiguity, useful improvement, and preference. A missing argument is a mathematical issue, not a style preference. Do not invent objections to satisfy a quota. A clean report is allowed. Do not use prior favorable reviews as authority.

### Concrete editor prompt

> Apply only accepted issue IDs to the frozen candidate, using local patches. Preserve statements, hypotheses, scope, notation meaning, source claims, and every nontrivial inference. Keep conceptual explanation that reduces reader effort. Do not replace missing proof with confident connective prose. Report each issue as repaired, rejected with reason, or requiring mathematical work; show a concise before/after rationale and identify changed mathematical support. Return for fresh review after any substantive argument change.

### A useful local experiment before expanding the team

Select 4–6 representative units: introduction, definition plus first example, short proof, technical proof, theorem application, and a rendered page with displays. Compare the current policy, a revised policy in one pass, and revised policy plus one independent critique/repair cycle, using comparable budgets and frozen input mathematics. Have the researcher judge anonymized pairs. Record preference with reasons, time to reconstruct the proof, notation lookups, verified mathematical regressions, useful versus invalid comments, edit acceptance, and elapsed/cost budget. Never promote an unsafe variant merely because its prose wins preference comparisons. This is a practical pilot, not a statistically powered experiment.

## Search and provenance log

Search families used (English, broad web search plus primary-source follow-through):

- `Self-Refine Iterative Refinement with Self-Feedback paper 2023`
- `LLMs cannot self-correct reasoning yet intrinsic self correction paper`
- `Can Large Language Models Provide Useful Feedback on Research Papers 2023 2024`
- `agent scientific writing peer review multi agent writing paper 2025 2026`
- `Reflexion language agents verbal reinforcement learning arxiv 2303.11366`
- `STORM Assisting in Writing Wikipedia-like Articles From Scratch language models 2024`
- `Co-STORM Collaborative Discourse Wikipedia 2024 paper`
- `CoAuthor designing human AI collaborative writing dataset 2022`
- `persona prompting does not improve objective performance 2024 arxiv`
- `LLM peer review scientific manuscript revision multi agent ReviewAgent PaperReviewAgent 2025`
- `scientific writing multi-agent manuscript revision human evaluation`
- `Impressona AI personas feedback writing 2024 Benharrak paper`
- `math proof critique benchmark 2025 2026 reviewer`
- `Not All Proofs Are Equal Evaluating LLM Proof Quality Beyond Correctness`
- `ScholarPeer arxiv`

Search results included news, commercial summaries, and social posts. These were discovery aids only; substantive source entries use papers, author pages, or publisher records. No controlled study was found establishing the best number of agents, persona, or review loop for publishable pure-math research papers. This is a bounded search result, not proof that none exists. Stronger 2026 systems and recently revised papers make older results especially unsuitable for universal claims.

## Acquisition and reading gaps

No paper payload was retained by this worker; all links above are remote source readings or discovery records. Consequently no local paper has been assigned a fabricated alpha key, DOI metadata response, or payload hash, and none has been promoted into the project's mathematical reference corpus. The version identifiers above pin the inspected arXiv text where known. HTML source views can themselves change; they are not checksummed archives.

| Records | Status | Next action if used in a formal project literature review |
|---|---|---|
| A01–A03, A05–A13, A16, A18–A22, A24–A25 | Primary text selectively read remotely; payload not acquired | Acquire exact TeX or original PDF, retrieve DOI API metadata where available, hash payload, compare versions/errata, and record reading audit. |
| A04, A14–A15, A17, A23 | Publisher abstract/overview only or partial reading, as specified | Read complete method/evaluation/limitations before relying on detailed findings; then acquire pinned evidence if needed. |
| A26 | Selective framework/qualitative inspection; detailed tables not audited | Audit exact experiment/rubric limitations before quantitative use. |
| L01–L08 | Discovery or shallow reading only | Triage for relevance; compare versions, read full text, and acquire only if promoted. |

DOIs in this file are copied from inspected primary/publisher records when verified; arXiv URLs suffice where no publication DOI was verified. “No DOI recorded” does not mean a DOI does not exist. No experiment was replicated, no alleged theorem was independently verified, and no final draft was edited.
