"""Historical graph identities qualify, but never rename, authored LaTeX labels."""
from pathlib import Path
import sys,json,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph
class NamespaceTests(unittest.TestCase):
 def test_local_proofs_and_uses_resolve_inside_version(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'notes').mkdir();(root/'workflow').mkdir()
   text=r'''\begin{definition}\label[An object.]{def:x}An object.\end{definition}
\begin{lemma}\label[A claim about the object.]{lem:x}A claim.\end{lemma}
\begin{proof}[label={prf:x},proves={lem:x},description={Uses the definition.}]\use{def:x}.\end{proof}'''
   (root/'notes/current.tex').write_text(text);(root/'notes/historical.tex').write_text(text)
   mapping={'def:x':'def:vtest:x','lem:x':'lem:vtest:x','prf:x':'prf:vtest:x'}
   (root/'workflow/label-namespaces.json').write_text(json.dumps({'schema_version':1,'files':{'notes/historical.tex':mapping}}))
   g=Graph(root)
   self.assertEqual(g.errors,[])
   self.assertEqual(g.proofs['prf:vtest:x'],'lem:vtest:x')
   self.assertEqual(g.edges['lem:vtest:x'],{'def:vtest:x'})
   self.assertEqual(g.edges['lem:x'],{'def:x'})
   self.assertEqual(g.nodes['lem:vtest:x']['source_label'],'lem:x')
   self.assertIn(r'\label[A claim about the object.]{lem:x}',g.source('lem:vtest:x'))
 def test_missing_namespace_does_not_hide_a_collision(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'notes').mkdir()
   for name in ('one','two'):(root/'notes'/f'{name}.tex').write_text(r'\begin{lemma}\label[A claim.]{lem:x}Claim.\end{lemma}')
   self.assertTrue(any('duplicate node ID' in e for e in Graph(root).errors))
 def test_proof_selection_and_related_metadata_respect_local_version(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'notes').mkdir();(root/'workflow').mkdir()
   text=r'''\begin{definition}\label[An object.]{def:x}Object.\end{definition}
% @proof: prf:second
% @related: def:x
\begin{lemma}\label[A claim.]{lem:x}Claim.\end{lemma}
\begin{proof}[label={prf:first},proves={lem:x},description={First argument.}]Argument.\end{proof}
\begin{proof}[label={prf:second},proves={lem:x},description={Second argument.}]Argument.\end{proof}'''
   (root/'notes/historical.tex').write_text(text)
   mapping={k:k.split(':')[0]+':vtest:'+k.split(':')[1] for k in ('def:x','lem:x','prf:first','prf:second')}
   (root/'workflow/label-namespaces.json').write_text(json.dumps({'schema_version':1,'files':{'notes/historical.tex':mapping}}))
   g=Graph(root)
   self.assertEqual(g.errors,[])
   self.assertEqual(g.selected_proofs['lem:vtest:x'],'prf:vtest:second')
   self.assertEqual(g.nodes['lem:vtest:x']['metadata']['related'],['def:vtest:x'])
   self.assertEqual([o['target'] for o in g.occurrences if o['relation']=='related'],['def:vtest:x'])
if __name__=='__main__':unittest.main()
