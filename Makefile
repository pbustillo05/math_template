PYTHON ?= python3
export PYTHONDONTWRITEBYTECODE = 1
.PHONY: all doctor check test pdf bibliography graph vscode release clean
all: pdf
doctor:
	$(PYTHON) scripts/doctor.py
check:
	$(PYTHON) scripts/check.py
	$(PYTHON) -m unittest discover -s scripts/tests -v
	$(PYTHON) -m unittest discover -s tests -v
test:
	$(PYTHON) -m unittest discover -s scripts/tests -v
	$(PYTHON) -m unittest discover -s tests -v
pdf:
	$(PYTHON) scripts/build_latex.py $(if $(SOURCE),--source "$(SOURCE)",)
bibliography:
	$(PYTHON) scripts/build_latex.py --bibliography
graph:
	@mkdir -p build/semantex
	$(PYTHON) scripts/semantex export --output build/semantex/index.json
	$(PYTHON) scripts/semantex graph --format mermaid > build/semantex/dependencies.mmd
	$(PYTHON) scripts/semantex graph --format dot > build/semantex/dependencies.dot
vscode:
	$(PYTHON) scripts/package_vscode.py
release:
	@test -n "$(TARGET)" || (echo 'Set TARGET to a mathematical label'; exit 1)
	$(PYTHON) scripts/semantex check --release --target "$(TARGET)"
clean:
	$(PYTHON) -c "import shutil; [shutil.rmtree(p, ignore_errors=True) for p in ('build/latex', 'build/bibliography-source', 'build/blueprint-source')]"
