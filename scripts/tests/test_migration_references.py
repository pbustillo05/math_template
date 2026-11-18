"""Migration gaps remain explicit and do not bypass retained-byte verification."""
import json
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import references as refs
class MigrationReferenceTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.paper=self.root/'references/AA24';(self.paper/'metadata').mkdir(parents=True)
  doi='10.1234/migration';self.record={'id':'r'+refs.sha(doi.encode())[:16],'key':'AA24','doi':doi,'source_gap':'Original acquisition archive unavailable'}
  data=b'@article{source,title={Fixture},author={Ada Alpha},year={2024}}'
  (self.paper/'metadata/doi-response.bib').write_bytes(data)
  refs.write_json(self.paper/'metadata/doi.json',{'doi':doi,'sha256':refs.sha(data)})
  payload=b'\\begin{lemma}Original bytes.\\end{lemma}\n';(self.paper/'paper.tex').write_bytes(payload)
  self.source={'kind':'inherited-source-tree','acquisition_gap':'No archive hash retained','inherited_file_sha256':{'paper.tex':refs.sha(payload)}}
 def lock(self):
  refs.write_json(self.paper/'metadata/source.json',self.source)
  refs.write_json(self.root/'references/catalog.json',{'schema_version':1,'records':[self.record]})
  refs.write_json(self.root/'references/lock.json',{'schema_version':1,'records':[{'id':self.record['id'],'record':self.record,'files':refs.manifest(self.paper)}]})
 def test_hash_locked_tree_with_explicit_gap(self):
  self.lock();self.assertEqual(refs.verify(self.root,alpha=False),[self.record])
 def test_gap_cannot_be_omitted(self):
  self.source.pop('acquisition_gap');self.lock()
  with self.assertRaisesRegex(ValueError,'explicit acquisition gap'):refs.verify(self.root,alpha=False)
 def test_fresh_lock_cannot_bless_changed_inherited_bytes(self):
  (self.paper/'paper.tex').write_text('changed');self.lock()
  with self.assertRaisesRegex(ValueError,'hash mismatch'):refs.verify(self.root,alpha=False)
 def test_missing_inherited_file_needs_explicit_exclusion(self):
  self.source['inherited_file_sha256']['compiled.pdf']='a'*64;self.lock()
  with self.assertRaisesRegex(ValueError,'missing without'):refs.verify(self.root,alpha=False)
  self.source['excluded_files']=['compiled.pdf'];self.lock();refs.verify(self.root,alpha=False)
 def test_original_pdf_alias_and_traversal_guard(self):
  data=b'%PDF-1.5 fixture';(self.paper/'paper.pdf').write_bytes(data)
  self.source={'original_file':'paper.pdf','sha256':refs.sha(data)};self.lock();refs.verify(self.root,alpha=False)
  self.source['original_file']='../paper.pdf';self.lock()
  with self.assertRaisesRegex(ValueError,'unsafe'):refs.verify(self.root,alpha=False)
if __name__=='__main__':unittest.main()
