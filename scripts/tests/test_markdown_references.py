"""Markdown links navigate exact units without creating unsupported logical owners."""
from pathlib import Path
import json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph
class MarkdownReferencesTests(unittest.TestCase):
 def fixture(self,root):
  (root/'notes').mkdir();(root/'workflow').mkdir()
  (root/'notes/units.tex').write_text(r'\begin{definition}\label[A stable object.]{def:object}Object.\end{definition}')
 def test_navigation_survives_mathematics_move(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.fixture(root)
   (root/'notes/ledger.md').write_text('A link: `\\mention{def:object}`.\n')
   before=Graph(root);self.assertEqual(before.errors,[])
   refs=before.references('def:object',reverse=True)
   self.assertEqual(len(refs),1);self.assertEqual(refs[0]['owner'],None)
   self.assertEqual(refs[0]['file'],'notes/ledger.md');self.assertEqual(refs[0]['column'],10)
   (root/'notes/units.tex').rename(root/'notes/moved.tex')
   after=Graph(root);moved=after.references('def:object',reverse=True)
   self.assertEqual(moved[0]['target'],refs[0]['target'])
   self.assertEqual(moved[0]['target_location']['file'],'notes/moved.tex')
   self.assertEqual(moved[0]['file'],'notes/ledger.md')
   self.assertEqual(after.edges['def:object'],set())
 def test_literal_examples_do_not_create_references(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.fixture(root)
   (root/'notes/ledger.md').write_text(r'''<!-- \mention{def:comment} -->
```tex
\mention{def:fenced}
```
~~~
\use{def:tilde}
~~~
    \mention{def:indented}
`print("\mention{def:code}")`
\\mention{def:escaped}
`\mention{def:object}` and \hiddenmention{def:object}.
''')
   graph=Graph(root);self.assertEqual(graph.errors,[])
   self.assertEqual(len(graph.references('def:object',reverse=True)),2)
 def test_bindings_missing_targets_and_unowned_dependencies(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.fixture(root)
   audit=root/'references/KEY/audit';audit.mkdir(parents=True)
   (audit/'ledger.md').write_text(r'`\mention{def:old}` and `\use{def:object}` and `\mention{def:missing}`.')
   (root/'workflow/reference-bindings.json').write_text(json.dumps({'files':{'references/KEY/audit/ledger.md':{'def:old':'def:object'}}}))
   graph=Graph(root)
   self.assertTrue(any('dependency reference has no mathematical owner' in e for e in graph.errors))
   self.assertTrue(any('unresolved reference def:missing' in e for e in graph.errors))
   self.assertEqual(len(graph.references('def:object',reverse=True)),2)
   self.assertEqual(graph.edges['def:object'],set())
if __name__=='__main__':unittest.main()
