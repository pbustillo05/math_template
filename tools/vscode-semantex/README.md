# SemanTeX Research Navigation

A dependency-free VS Code companion for this template's Python parser.

Run `make vscode` in the repository root, then `code --install-extension build/semantex-navigation.vsix`.
Open the repository as a trusted workspace and reload the window.
No user-level agent settings are modified and nothing is published to an extension marketplace.

Features:

- Label hover displays the description, exact enclosing LaTeX environment and selected proof, review status, and declared prerequisites. Structured citations resolve to their exact source destination.
- F12 / Go to Definition opens the precise source label, including retained upstream labels and deterministic virtual labels.
- Shift+F12 / Find All References returns incoming local uses and upstream literal references.
- **SemanTeX: Show Label Dependencies** roots the Explorer tree at the label under the cursor.
- **SemanTeX: Refresh Index** rebuilds all open project indexes.
- Structural problems appear in the Problems panel; an invalid index clears navigation instead of serving stale results.

The extension calls `python3 -B scripts/manuscript_graph.py editor-index --source-ranges` directly. It transfers source positions and reads the hovered blocks on demand.
Set `semantex.pythonPath` to another Python 3.10+ executable if needed.
Each project has its own index in multi-root workspaces.
Saved edits trigger refresh; unsaved open `.tex` files are supplied as an overlay, so hover and diagnostics see current editor text.
An environment must still be structurally complete for the parser to index it.
The command-line checks and PDF builds always use saved files.

Hover is bounded to 16,000 characters per block; `scripts/semantex get LABEL --latex` retrieves the full exact block.
The companion does not expand TeX macros, infer mathematical dependencies, evaluate conditionals or certify proofs.
The upstream mention graph is available through `scripts/semantex paper-graph KEY`; the dependency tree shows only explicitly declared logical uses.
LaTeX Workshop supplies PDF preview/SyncTeX independently; no private Workshop APIs or pinned extension-version adapter are used.

Development: `node --check tools/vscode-semantex/extension.js` and `node --test tools/vscode-semantex/test.js`.
Open this directory in VS Code and press F5 using the included launch configuration for a real extension-host smoke test.
