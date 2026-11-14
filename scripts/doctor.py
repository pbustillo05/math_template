#!/usr/bin/env python3
"""Report optional and required local tools; make no changes."""
import shutil
import sys
print('Python:', sys.version.split()[0], '(3.10+ required)')
for tool in ('git', 'pdflatex', 'bibtex', 'latexmk', 'node', 'code', 'lake'):
    print(tool + ':', shutil.which(tool) or 'not installed')
print('Python tooling uses only the standard library. Lean and VS Code are optional.')
