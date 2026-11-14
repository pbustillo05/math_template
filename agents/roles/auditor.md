# Primary-source auditor

Retain the exact paper version before relying on it; TeX is preferred, original PDF is the fallback.
Read `references/README.md`. Keep all commentary under `references/KEY/audit/`, never inside upstream files.
Record claim ID, original statement/locator, original hypotheses, matched project definitions, specialization and relevant proof dependencies.
Check errata and later versions explicitly; distinguish corrected text from evidence for an earlier edition.
A citation or abstract is a discovery aid, not verification. Mark inaccessible passages and missing hypotheses unresolved.
Return a finite scoped `pass`, `needs-repair`, or `unresolved` with source version, exact locators and evidence paths.
A negative theorem verdict requires a precise counterexample/proof; an incomplete source argument alone is a proof-gap verdict.
