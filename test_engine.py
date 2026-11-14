import unittest
from engine import analyze, resolve_us, normalize_search

def record(year,val):return {'start':f'{year}-01-01','end':f'{year}-12-31','val':val,'form':'10-K','fp':'FY','filed':f'{year+1}-02-01','accn':f'0000000000-{year%100:02}-000001'}
class EngineTests(unittest.TestCase):
 def test_resolve(self):
  d={'0':{'ticker':'AAPL','title':'Apple Inc.','cik_str':320193}}
  self.assertEqual(resolve_us('AAPL',d)['cik_str'],320193)
  self.assertEqual(resolve_us('Apple Inc.',d)['ticker'],'AAPL')
 def test_website_normalization(self):self.assertEqual(normalize_search('https://www.apple.com'),'apple')
 def test_financials(self):
  facts={'entityName':'Example','facts':{'us-gaap':{'Revenues':{'units':{'USD':[record(2024,100),record(2025,90)]}},'OperatingIncomeLoss':{'units':{'USD':[record(2024,20),record(2025,10)]}}}}}
  result=analyze(facts,123)
  self.assertEqual(result['metrics']['revenue']['yoy_percent'],-10)
  self.assertEqual(result['metrics']['operating_margin_percent'],11.11)
  self.assertEqual(len(result['rule_based_warnings']),2)
 def test_missing_is_missing(self):
  result=analyze({'entityName':'Empty','facts':{}},123)
  self.assertEqual(result['metrics']['revenue']['status'],'not_available')
if __name__=='__main__':unittest.main()
