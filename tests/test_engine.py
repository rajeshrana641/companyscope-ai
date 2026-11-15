import unittest
from engine import ticker_candidates,annual_values,evaluate,filing_url
class TestEngine(unittest.TestCase):
 def test_ticker(self):
  d={'0':{'ticker':'ABC','title':'ABC Industries','cik_str':123},'1':{'ticker':'XYZ','title':'XYZ Holdings','cik_str':456}}
  self.assertEqual(ticker_candidates('abc',d)[0]['ticker'],'ABC')
 def test_duration_excludes_quarter(self):
  d={'facts':{'us-gaap':{'NetIncomeLoss':{'units':{'USD':[{'form':'10-K','val':9,'start':'2025-10-01','end':'2025-12-31','filed':'2026-02-01','fy':2025,'fp':'FY'}]}}}}}
  self.assertEqual(annual_values(d,'Net income'),[])
 def test_negative_ocf(self):
  d={'facts':{'us-gaap':{'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':[{'form':'10-K','val':-10,'start':'2025-01-01','end':'2025-12-31','filed':'2026-02-01','fy':2025,'fp':'FY','accn':'0000000000-26-000001'}]}}}}}
  _,alerts=evaluate(d)
  self.assertTrue(any('negative' in a for a in alerts))
 def test_filing(self):
  self.assertEqual(filing_url(123,'0000123456-26-000001'),'https://www.sec.gov/Archives/edgar/data/123/000012345626000001/')
if __name__=='__main__':unittest.main()
