# Independent draft verification

## Candidate and assignment

Finish the argument in notes, then integrate a polished candidate into `draft/`.
Run structural checks and build it before asking reviewers to assess it.
State the finite review scope by stable labels, source revision/diff and current `scripts/semantex fingerprint LABEL` values.
The dispatcher reads the support closure with `deps`, `get`, `why`, and `frontier`; it does not flood each reviewer with the whole research history.

For each requested reviewer, provide the current statement/proof, definitions and prerequisites, exact retained source applications, relevant conventions, output path and the appropriate role prompt.
Give an explicit verdict vocabulary and discharge criterion.
A worker writes only its assigned report or exclusively leased candidate file; integrate manuscript changes serially.
Reviewers must read files themselves and record what they actually inspected.
Fresh context means no author's exploratory conversation or favorable earlier verdicts supplied as authority.

## Separate checks

Use a proof verifier, counterexample reviewer and style referee for acceptance of a draft unit; source auditing is an additional bounded assignment when the source application needs it.
The author and verifier must differ, and the three reviewers must be distinct actual workers/contexts.
Names in JSON are provenance, not evidence of independent execution.
When independent workers are unavailable, leave the work `unreviewed` or `conditional`; do not synthesize their reports.

The proof verifier checks every deduction and source specialization.
The counterexample reviewer probes degenerate, limiting, relative and family cases and distinguishes a counterexample from an incomplete proof.
The style referee examines mathematical ambiguity, verbosity, clarity, memory cost of notation, citations, organization and the rendered pages.
A role's `pass` does not substitute for another role.
Source availability, compilation and the declared DAG are necessary tooling evidence, not correctness verdicts.

## Reports and repair

Use `agents/templates/review.md`.
Record covered IDs and their exact fingerprints, inspected source/version/locators, verdict, limitations and issue rows with severity, consequence and repair.
A `pass` has no unresolved gap within the stated scope.
Counterexample `clear-for-review` means the specified attacks found no counterexample, not that one cannot exist.
An unavailable source yields an unresolved source obligation, not a verdict that the theorem is false.

Repair the candidate, integrate serially, then compute new fingerprints.
Re-review changed statements/proofs and affected support; do not repeat unchanged investigations merely to fill a quota.
A reviewer who rewrites an argument returns it for a fresh independent check.
Review the assembled final text; approval of an earlier candidate does not transfer automatically.

## Registry and release

`workflow/reviews.json` records informal acceptance; all template entries start absent/unreviewed.
For each mathematical unit in prerequisite-first order:

```sh
python3 scripts/reviews.py author LABEL actual-author
python3 scripts/reviews.py record LABEL --role proof-verifier \
  --reviewer actual-verifier --verdict pass --report workflow/reports/proof.md \
  --fingerprint HASH_FROM_THAT_REPORT
# Record style-referee/pass and counterexample/clear-for-review similarly.
python3 scripts/reviews.py accept LABEL
scripts/semantex check --release --target LABEL
```

Never renew a hash without a new review of changed support.
Reports live outside fingerprinted candidate/evidence paths to avoid self-referential hashes.
Each report is itself SHA-256 pinned; modifying it invalidates its recorded review.
Accepted units need author identity, complete fresh reports, an attached proof where appropriate, accepted prerequisites and no open obligation in selected support.
Source applications additionally need both retained-source and audit evidence attachments.
Definitions and proof blocks also need their appropriate reviews when in a release closure; for definitions, review well-formedness rather than asking for a proof of a convention.

The registry format is schema version 1 with `records` keyed by label.
Each record has `status`, `author`, and `reviews`.
Each review has `role`, `reviewer`, `verdict`, `fingerprint`, `report`, and `report_sha256`.
Supported states: `unreviewed`, `conditional`, `accepted`, `disputed`, `refuted`, `obsolete`; the CLI computes `stale` when an accepted record has invalid support.
Only record acceptance after reading the actual reports and resolving disagreement.
The checker validates structure and freshness, not reviewer honesty or mathematical truth.
