"""Document identities survive moves without changing authored result labels."""
from pathlib import Path
import json,sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph
class DocumentContextTests(unittest.TestCase):
 def fixture(self,root):
  (root/'notes').mkdir();(root/'workflow').mkdir()
  record={'file':'notes/original.tex','labels':{'def:x':'def:old:x','lem:x':'lem:old:x','prf:x':'prf:old:x'},'references':{'def:external':'def:real'}}
  (root/'workflow/document-contexts.json').write_text(json.dumps({'schema_version':1,'contexts':{'ctx:historical':record}}))
  (root/'notes/current.tex').write_text(r'\begin{definition}\label[A current object.]{def:real}Object.\end{definition}')
  text=r'''\SemanTeXContext{ctx:historical}
\begin{definition}\label[A historical object.]{def:x}Object.\end{definition}
% @proof: prf:x
\begin{lemma}\label[A historical claim.]{lem:x}Claim.\end{lemma}
\begin{proof}[label={prf:x},proves={lem:x},description={Uses local and external data.}]\use{def:x}\use{def:external}\end{proof}'''
  (root/'notes/original.tex').write_text(text)
 def test_move_preserves_scope_and_proof_identity(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.fixture(root);before=Graph(root)
   self.assertEqual(before.errors,[])
   (root/'notes/moved').mkdir();(root/'notes/original.tex').rename(root/'notes/moved/history.tex')
   after=Graph(root)
   self.assertEqual(after.errors,[])
   self.assertEqual(after.edges,before.edges)
   self.assertEqual(after.proofs,{'prf:old:x':'lem:old:x'})
   self.assertEqual(after.edges['lem:old:x'],{'def:old:x','def:real'})
   self.assertEqual(after.nodes['lem:old:x']['source_label'],'lem:x')
   self.assertEqual(after.context_files['ctx:historical'],'notes/moved/history.tex')
 def test_missing_context_and_duplicate_owner_are_errors(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);self.fixture(root)
   (root/'notes/other.tex').write_text(r'\SemanTeXContext{ctx:historical}')
   self.assertTrue(any('also belongs' in e for e in Graph(root).errors))
   (root/'notes/other.tex').write_text(r'\SemanTeXContext{ctx:missing}')
   self.assertTrue(any('unknown document context' in e for e in Graph(root).errors))
if __name__=='__main__':unittest.main()
