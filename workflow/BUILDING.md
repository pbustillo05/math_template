# Building the manuscript and notes

Open the repository as the VS Code workspace. LaTeX Workshop uses **Checked project build**, which generates validated SemanTeX bindings and supplies the shared preamble and bibliography paths. For a subfiles note, the editor offers its standalone document or the parent manuscript. The **Math: build active TeX** task builds the active entrypoint directly.

From the project root:

```sh
make pdf
make pdf SOURCE=notes/example/units.tex
python3 scripts/build_latex.py --source draft/main.tex
```

The full draft sweep builds the manuscript first, then its standalone chapters. A selected build accepts authored documentclass entrypoints under `draft/`, `notes/`, or `references/<KEY>/audit/`; retained reference payloads and symlinks into them remain excluded.

Every successful manuscript build atomically updates `draft/main.pdf`, which is the persistent document to open or share. Compiler or semantic-validation failures preserve the previous successful PDF and report an error; that PDF then represents the last good source state. LaTeX Workshop previews the corresponding output under `build/latex/`. Successful note PDFs can be discarded after verification.

`make clean` removes only temporary TeX output directories and preserves `draft/main.pdf`, the semantic runtime, embedding models and the vector index. Build diagnostics live beside the temporary PDF; each entrypoint has its own `.build.log` as well as a compiler `.log`.

Bare editor recipes that invoke `pdflatex` or `latexmk` without this project configuration do not supply the shared package and runtime paths. Use the configured recipe or these commands. A successful compiler run does not establish mathematical acceptance.
