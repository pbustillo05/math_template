"""Unenclosed retained labels are navigable without an invented environment kind."""
import pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from manuscript_graph import Graph
from semantex_runtime import local_kind_name,plan_contexts,generate_runtime,runtime_key
class RetainedAnchorRuntimeTests(unittest.TestCase):
 def test_retained_anchor_without_environment_generates_external_navigation(self):
  with tempfile.TemporaryDirectory() as directory:
   root=pathlib.Path(directory);(root/'references/TST').mkdir(parents=True);(root/'notes').mkdir();(root/'workflow').mkdir()
   (root/'references/TST/paper.tex').write_text(r'\label{native:anchor} Retained prose outside an environment.')
   (root/'notes/use.tex').write_text(r'\begin{remark}\label[Source navigation.]{rem:use}\mention{TST:native:anchor}\end{remark}')
   graph=Graph(root);self.assertEqual(graph.errors,[]);node=graph.nodes['TST:native:anchor'];self.assertIsNone(node['environment']);self.assertIsNone(local_kind_name(node))
   registry,manifest=plan_contexts(graph)
   import json
   for edit in manifest['files']:
    path=root/edit['file'];text=path.read_text()
    for ins in sorted(edit['insertions'],key=lambda x:x['offset'],reverse=True):text=text[:ins['offset']]+ins['text']+text[ins['offset']:]
    path.write_text(text)
   (root/'workflow/document-contexts.json').write_text(json.dumps(registry));graph=Graph(root);self.assertEqual(graph.errors,[]);runtime=generate_runtime(graph,registry);key=runtime_key('TST:native:anchor')
   self.assertIn('\\SemanTeXDeclareExternalKey{'+key+'}',runtime)
   self.assertNotIn('\\SemanTeXDeclareKindKey{'+key+'}',runtime)
   self.assertEqual(graph.status('TST:native:anchor'),'source-unreviewed')
if __name__=='__main__':unittest.main()
