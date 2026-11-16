PYTHON ?= python3
export PYTHONDONTWRITEBYTECODE = 1
.PHONY: all doctor check test pdf notebook bibliography graph vscode release clean
all: pdf
doctor:
	$(PYTHON) scripts/doctor.py
check:
	$(PYTHON) scripts/check.py
	$(PYTHON) -m unittest discover -s scripts/tests -v
test:
	$(PYTHON) -m unittest discover -s scripts/tests -v
pdf:
	$(PYTHON) scripts/build_latex.py
notebook:
	$(PYTHON) scripts/build_latex.py --notebook
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
	$(PYTHON) -c "import shutil; shutil.rmtree('build', ignore_errors=True)"
