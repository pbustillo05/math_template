---
name: research-review
description: Coordinate a requested independent draft review and record formal acceptance.
---

# Independent review

Assign the current candidate by label and fingerprint. Give each reviewer the relevant sources, their [assignment](references/task.md) and a separate [report](references/review.md) to write. Each reviewer reads the project instructions and their assigned skill.

Formal acceptance requires three distinct review contexts. Proof verification and style must each return `pass`, and counterexample search must return `clear-for-review`. The proof verifier must be independent of the author. Request a source audit where a specialization needs one. Preserve disagreements and unavailable evidence in the reports.

Record only reviews actually performed. A changed proof or changed support requires a fresh review of the affected argument. An author of a repair cannot independently certify it.

Use `scripts/semantex fingerprint ID` for the reviewed version and `python3 scripts/reviews.py` to register the author, record each report with its fingerprint, and accept units in prerequisite order. Check the assembled manuscript with `scripts/semantex check --release --target ID`.
