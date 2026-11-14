import unittest
from monitoring import monitor, run_batch, record_official_check, classify_headline, COMPANIES

TODAY='2026-11-14'
def item(title, date='2026-11-14', url='https://example.org/story'):
    return {'title':title,'published_at':date,'url':url}

class MonitoringTests(unittest.TestCase):
    def test_five_companies_loaded(self):self.assertEqual(len(COMPANIES),5)
    def test_trigger_apple(self):
        r=monitor('apple',{'last_published':'2026-08-01'},[item('Apple reports Q4 2026 earnings')],TODAY)
        self.assertEqual(r['events'][0]['type'],'news_results_detected')
        self.assertEqual(r['events'][1]['reason'],'news_trigger')
    def test_future_preview_rejected(self):
        self.assertIsNone(classify_headline(item('Apple to report Q4 earnings next week'),COMPANIES['apple'],__import__('datetime').date.fromisoformat(TODAY)))
    def test_old_news_rejected(self):
        r=monitor('apple',{},[item('Apple reports Q1 earnings','2026-06-01')],TODAY)
        self.assertEqual(r['news_candidates'],0)
    def test_other_company_not_matched(self):
        r=monitor('siemens',{},[item('Apple reports Q4 earnings')],TODAY)
        self.assertEqual(r['news_candidates'],0)
    def test_tata_cv_not_pv(self):
        r=monitor('tata_pv',{},[item('Tata Motors Passenger Vehicles commercial vehicles Q2 results released')],TODAY)
        self.assertEqual(r['news_candidates'],0)
    def test_calendar_fallback_due(self):
        r=monitor('lvmh',{'last_published':'2026-08-01'},[],TODAY)
        self.assertEqual(r['events'][0]['reason'],'calendar_backup')
    def test_calendar_sleep(self):
        r=monitor('lvmh',{'last_published':'2026-11-01'},[],TODAY)
        self.assertEqual(r['events'],[])
    def test_calendar_weekly_throttle(self):
        r=monitor('lvmh',{'last_published':'2026-08-01','last_fallback_check':'2026-11-12'},[],TODAY)
        self.assertEqual(r['events'],[])
    def test_retry_backoff(self):
        r=monitor('apple',{},[item('Apple reports Q4 2026 earnings')],TODAY)
        s=record_official_check(r['state'],TODAY,False)
        self.assertEqual(s['pending']['next_retry'],'2026-11-15')
        self.assertEqual(monitor('apple',s,[],TODAY)['events'],[])
    def test_confirmed_report_resets(self):
        s={'pending':{'url':'https://example.org/x','next_retry':TODAY}}
        updated=record_official_check(s,TODAY,True,'apple-fy26','2026-11-14','2026-09-26')
        self.assertIsNone(updated['pending'])
        self.assertEqual(updated['last_report_key'],'apple-fy26')
    def test_cannot_claim_found_without_evidence(self):
        with self.assertRaises(ValueError):record_official_check({},TODAY,True)
    def test_batch_all_five(self):
        r=run_batch({},[item('Apple reports Q4 earnings')],TODAY)
        self.assertEqual(len(r['results']),5)
        self.assertEqual(r['summary']['news_triggers'],1)
        self.assertFalse(r['summary']['live_fetch_performed'])
    def test_ambiguous_company_rejected(self):
        with self.assertRaises(ValueError):monitor('tata',{},[],TODAY)

if __name__=='__main__':unittest.main()
