import json, pathlib, sys, unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
from official_ir import analyze_official, growth, safe_domain, apple_extract
FIXTURES=json.loads((pathlib.Path(__file__).resolve().parents[1]/'fixtures'/'official_extracts.json').read_text())
class OfficialIRTests(unittest.TestCase):
 def test_apple(self):
  m=analyze_official('apple',FIXTURES['apple'])['metrics'];self.assertEqual(m['growth_percent'],11.72);self.assertEqual(m['annual_growth_percent'],15.06)
 def test_siemens(self):self.assertEqual(analyze_official('siemens',FIXTURES['siemens'])['metrics']['current'],83.4)
 def test_lvmh(self):self.assertEqual(analyze_official('lvmh',FIXTURES['lvmh'])['metrics']['growth_percent'],-1.62)
 def test_unilever(self):self.assertEqual(analyze_official('unilever',FIXTURES['unilever'])['metrics']['underlying_growth_percent'],5.2)
 def test_reject_untrusted_domain(self):self.assertFalse(safe_domain('https://apple.com.attacker.com/file.pdf'))
 def test_reject_http(self):self.assertFalse(safe_domain('http://www.apple.com/a'))
 def test_missing_revenue(self):
  with self.assertRaises(ValueError):apple_extract('Nothing relevant')
 def test_no_prior_growth(self):
  with self.assertRaises(ValueError):growth(5,0)
if __name__=='__main__':unittest.main()
