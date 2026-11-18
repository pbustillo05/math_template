---
name: tex-to-semantex
description: Index a retained paper’s mathematics and proof dependencies in a SemanTeX audit overlay.
---

# Index a retained paper

Extend the existing coverage in `references/KEY/audit/`. Preserve the original hypotheses, conclusions and proof structure. Distinguish transcriptions from restatements and inspected dependencies from open ones.

Give every overlay unit an exact originating citation and register its coverage and source hash in `audit/semantex.json`. The [overlay format](../../../workflow/SEMANTEX.md#provenance-overlays) and [retained-source guide](../../../references/REFERENCE-VIEWS.md) specify the labels and locators. Keep the retained payload intact.

Check that each unit resolves to the intended passage and each premise edge is supported there. Record the limits of the coverage in the paper’s audit.
