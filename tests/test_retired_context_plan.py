"""Context plans keep native calls to retired, version-qualified declarations."""
from pathlib import Path
import json,sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_unit_redirects as redirect_fixture
from manuscript_graph import Graph
from semantex_runtime import plan_contexts,generate_runtime,runtime_key

class RetiredContextPlanTests(unittest.TestCase):
 def test_retired_namespace_binding_survives_plan_context_refresh_and_move(self):
  fixture=redirect_fixture.RedirectTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
  root=fixture.root
  fixture.write('notes/consumer.tex',r'\begin{lemma}\label[Consumer.]{lem:consumer}\use{lem:native}\mention{prf:native}\end{lemma}')
  fixture.write('workflow/label-namespaces.json',json.dumps({'files':{'notes/consumer.tex':{'lem:native':'lem:old','prf:native':'prf:old'}}}))
  before=fixture.graph();plan,manifest=plan_contexts(before)
  ctx=next(v for v in plan['contexts'].values() if v['file']=='notes/consumer.tex')
  self.assertEqual(ctx['references']['lem:native'],'lem:old');self.assertEqual(ctx['references']['prf:native'],'prf:old')
  for edit in manifest['files']:
   path=root/edit['file'];text=path.read_text()
   for ins in sorted(edit['insertions'],key=lambda x:x['offset'],reverse=True):text=text[:ins['offset']]+ins['text']+text[ins['offset']:]
   path.write_text(text)
  fixture.write('workflow/document-contexts.json',json.dumps(plan));after=fixture.graph()
  self.assertEqual(before.edges,after.edges);self.assertEqual(before.proofs,after.proofs)
  runtime=generate_runtime(after,plan);self.assertIn(runtime_key('lem:old'),runtime)
  (root/'notes/consumer.tex').rename(root/'notes/moved.tex');moved=fixture.graph()
  self.assertEqual(before.edges,moved.edges)
  calls=[x for x in moved.occurrences if x['file']=='notes/moved.tex'];self.assertEqual(calls[0]['requested_target'],'lem:old');self.assertEqual(calls[0]['target'],'lem:new');self.assertTrue(calls[0]['dependency'])
  self.assertEqual(calls[1]['requested_target'],'prf:old');self.assertFalse(calls[1]['dependency'])
  # Existing embedded contexts can also retain now-retired entries in labels;
  # refreshing moves those names to references without changing their meaning.
  identity=next(k for k,v in plan['contexts'].items() if v['file']=='notes/consumer.tex')
  plan['contexts'][identity]['labels']['lem:native']='lem:old';plan['contexts'][identity]['references'].pop('lem:native')
  fixture.write('workflow/document-contexts.json',json.dumps(plan));g=fixture.graph();refreshed,_=plan_contexts(g,plan)
  self.assertNotIn('lem:native',refreshed['contexts'][identity]['labels']);self.assertEqual(refreshed['contexts'][identity]['references']['lem:native'],'lem:old')
  generate_runtime(g,refreshed)

if __name__=='__main__':unittest.main()
