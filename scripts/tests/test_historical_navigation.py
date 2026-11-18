"""Native equation IDs remain navigation anchors within historical proofs."""
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph
class HistoricalNavigationTests(unittest.TestCase):
 def build(self,root,command):
  (root/'notes').mkdir()
  (root/'notes/history.tex').write_text(r'''\begin{lemma}\label[An identity holds.]{lem:identity}Identity.\end{lemma}
\begin{proof}[label={prf:identity},proves={lem:identity},description={Calculates an identity.}]
\[x=x\label{current-eq:identity}\]
\COMMAND{current-eq:identity} records the calculation.
\end{proof}'''.replace('COMMAND',command))
  return Graph(root)
 def test_equation_is_not_a_second_proof_principal(self):
  with tempfile.TemporaryDirectory() as tmp:
   graph=self.build(Path(tmp),'mention')
   self.assertEqual(graph.errors,[])
   self.assertEqual(graph.nodes['current-eq:identity']['kind'],'eq')
   self.assertEqual(graph.nodes['current-eq:identity']['source_label'],'current-eq:identity')
   self.assertEqual(graph.proofs,{'prf:identity':'lem:identity'})
   self.assertEqual(graph.edges['lem:identity'],set())
 def test_premise_use_is_not_silently_downgraded(self):
  with tempfile.TemporaryDirectory() as tmp:
   graph=self.build(Path(tmp),'use')
   self.assertTrue(any('logical target current-eq:identity is only a navigation anchor' in e for e in graph.errors))
   self.assertTrue(any(o['target']=='current-eq:identity' and o['dependency'] for o in graph.occurrences))
if __name__=='__main__':unittest.main()
