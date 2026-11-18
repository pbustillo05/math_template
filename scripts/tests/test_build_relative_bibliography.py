"""Relative authored bibliography paths remain valid with ignored output directories."""
import importlib.util,pathlib,shutil,subprocess,tempfile,unittest,sys
HERE=pathlib.Path(__file__).resolve()
sys.path.insert(0,str(HERE.parents[1]))
spec=importlib.util.spec_from_file_location('relative_bib_builder',HERE.parents[1]/'build_latex.py');builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
@unittest.skipUnless(all(shutil.which(x) for x in ['latexmk','pdflatex','bibtex','pdftotext']),'TeX and Poppler required')
class RelativeBibliographyBuildTests(unittest.TestCase):
 def test_actual_bibtex_resolves_source_relative_database_in_ignored_output(self):
  with tempfile.TemporaryDirectory(prefix='relative-bib-build-') as directory:
   root=pathlib.Path(directory);(root/'draft').mkdir();(root/'references').mkdir()
   main=root/'draft/main.tex';bib=root/'references/references.bib'
   main.write_text(r'''\documentclass{article}
\begin{document}Synthetic bibliography mechanics fixture.
\nocite{Fixture}\bibliographystyle{alpha}\bibliography{../references/references}
\end{document}''')
   bib.write_text('@book{Fixture,author={Example, A.},title={Synthetic bibliography mechanics fixture},year={2000}}\n')
   before={p:p.read_bytes() for p in [main,bib]};builder.build(root)
   out=root/'build/latex/draft';self.assertTrue((out/'main.pdf').exists());self.assertTrue((out/'main.bbl').exists())
   text=subprocess.check_output(['pdftotext',str(out/'main.pdf'),'-'],text=True);self.assertIn('A. Example',text);self.assertIn('2000',text)
   self.assertNotIn('undefined citations',(out/'main.log').read_text())
   self.assertFalse(list((root/'draft').glob('*.aux')));self.assertFalse(list((root/'references').glob('*.aux')))
   for p,data in before.items():self.assertEqual(p.read_bytes(),data)
if __name__=='__main__':unittest.main()
