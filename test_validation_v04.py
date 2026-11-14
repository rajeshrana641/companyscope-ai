import unittest
from validation_v04 import SAMPLES, validate, resolve, report
class TestValidationV04(unittest.TestCase):
    def test_five_distinct_entities(self):
        self.assertEqual(len({x.entity_id for x in SAMPLES}),5)
    def test_apple_reconciliation(self):
        a=validate(SAMPLES[0]);self.assertEqual(a['calculated_growth_percent'],'11.72');self.assertTrue(a['headline_reconciles'])
    def test_lvmh_reported_growth(self):
        a=validate(SAMPLES[2]);self.assertEqual(a['calculated_growth_percent'],'-1.62')
    def test_no_invented_prior(self):
        for e in (SAMPLES[1],SAMPLES[3],SAMPLES[4]):
            self.assertIsNone(validate(e)['calculated_growth_percent'])
    def test_ambiguous_tata_blocked(self):
        with self.assertRaises(ValueError):resolve('Tata Motors')
    def test_distinct_tata_entities(self):
        self.assertNotEqual(resolve('Tata Motors Limited'),resolve('Tata Motors Passenger Vehicles'))
    def test_no_false_live_claim(self):
        self.assertTrue(all(not x['live_download_verified'] for x in report()['companies']))
    def test_sources_are_https(self):
        self.assertTrue(all(x['source'].startswith('https://') for x in report()['companies']))
if __name__=='__main__':unittest.main()
