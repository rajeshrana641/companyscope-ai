import unittest
from intelligence import classify_evidence,filter_news
class IntelligenceTests(unittest.TestCase):
 def test_evidence_provenance(self):
  findings=classify_evidence('The company lowered its full-year guidance. Higher component costs may pressure margins.', 'https://example.com/filing','2026-11-12')
  self.assertEqual({f['indicator'] for f in findings},{'guidance_reduction','margin_pressure'})
  self.assertTrue(all(f['status']=='requires_analyst_review' and f['source_url'] for f in findings))
 def test_rejects_unsourced_claim(self):
  with self.assertRaises(ValueError):classify_evidence('cyberattack','', '2026-11-12')
 def test_news_window_entity_and_duplicates(self):
  data=[{'title':'Apple earnings increase','url':'https://news.example/a','published_at':'2026-11-01'},
        {'title':'Apple earnings increase','url':'https://news.example/a','published_at':'2026-11-01'},
        {'title':'Apple 2025 update','url':'https://news.example/b','published_at':'2025-11-01'},
        {'title':'Banana earnings increase','url':'https://news.example/c','published_at':'2026-11-01'}]
  self.assertEqual(len(filter_news(data,['Apple'],'2026-11-14')),1)
 def test_ambiguous_alias_rejected(self):
  with self.assertRaises(ValueError):filter_news([],['AI'],'2026-11-14')
if __name__=='__main__':unittest.main()
