import unittest
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from live_pipeline import parse_rss, collect_headlines, discover_official_documents, run_once, fetch_bytes

RSS=b'''<rss version="2.0"><channel><item><title>Apple reports Q4 2026 earnings</title><link>https://example.org/story</link><pubDate>Fri, 13 Nov 2026 10:00:00 GMT</pubDate></item></channel></rss>'''
HTML=b'''<html><a href="/investors/2026-results.pdf">FY2026 annual report</a><a href="https://malicious.example/results">Financial results</a></html>'''
class TestLivePipeline(unittest.TestCase):
 def test_rss(self):
  rows=parse_rss(RSS);self.assertEqual(len(rows),1);self.assertEqual(rows[0]['published_at'],'2026-11-13')
 def test_reject_nonfeed(self):
  with self.assertRaises(ValueError):parse_rss(b'<html/>')
 def test_news_collection(self):
  rows,errors=collect_headlines(lambda url: RSS)
  self.assertEqual(len(rows),5);self.assertEqual(errors,{})
 def test_official_link_filter(self):
  rows=discover_official_documents('apple',lambda url: HTML)
  self.assertEqual(len(rows),1);self.assertIn('investors/2026-results.pdf',rows[0]['url'])
 def test_unverified_only(self):
  result=run_once({'apple':{'last_published':'2026-08-01'}},'2026-11-14',fetcher=lambda url: HTML if 'investor.apple.com' in url else RSS)
  self.assertEqual(result['verified_financial_reports'],0)
  self.assertEqual(result['financial_figures_published'],0)
 def test_no_network_false_claim(self):
  def fail(url):raise OSError('offline')
  result=run_once({},'2026-11-14',fetcher=fail)
  self.assertEqual(len(result['news_feed_errors']),5)
  self.assertFalse(result['live_fetch_performed'])
 def test_https_enforced(self):
  with self.assertRaises(ValueError):fetch_bytes('http://example.com')
if __name__=='__main__':unittest.main()
