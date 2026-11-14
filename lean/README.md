# Optional Lean correspondence

No Lean project is installed by this template and no formalization is claimed by the example.
Create your Lean project under this directory when needed; pin `lean-toolchain`, dependencies and `lake-manifest.json`.
Keep generated `.lake/` output untracked.

For a principal LaTeX label, add an invisible marker immediately after `\label{...}`:

```latex
\leanref{lem:claim}{Project.claim}{unchecked}
```

Add a record under `records` in `ledger.json`:

```json
{
  "lem:claim": {
    "entity": "Project.claim",
    "file": "lean/Project/Claim.lean",
    "coverage": "whole",
    "status": "unchecked",
    "correspondence": "lean/correspondence/claim.md"
  }
}
```

The correspondence file matches quantifiers, hypotheses, definitions, universes and conclusion; identify every informal step or representation mismatch.
Use `coverage: partial` and `status: partial` if only part has been formalized.
When the whole correspondence has actually been inspected:

```sh
python3 scripts/lean_status.py verify lem:claim --confirm-correspondence
# Set the matching LaTeX marker to checked after inspecting the emitted axiom list.
python3 scripts/lean_status.py check
```

The verifier runs `lake env lean --stdin` on the recorded file plus `#check ENTITY` and `#print axioms ENTITY`.
It requires a pinned toolchain, succeeds only if Lean accepts the file/entity, rejects `sorryAx`, and writes a receipt/log under `lean/receipts/`.
The receipt hashes local Lean inputs, dependency/toolchain configuration the correspondence document, and the exact LaTeX statement/proof support and shared preamble.
Review the printed axioms: compiler success can still depend on explicitly introduced axioms, and the tool does not establish that a chosen Lean entity expresses the intended LaTeX statement.
It trusts the local Lean compiler and dependency installation; it is a reproducibility record, not a signed certificate or a replacement for auditing dependencies.

If a checked source snapshot or receipt changes, the expected status becomes `stale` and checks fail until you update both ledger and marker honestly or reverify.
A missing marker claims no correspondence.
`unchecked`, `partial`, `checked` and `stale` markers are all invisible in the PDF and independent of informal review acceptance.
