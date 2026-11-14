"""Evidence-backed cross-country regression, using verified official-source excerpts.
Not a live downloader. All currency values are in the units explicitly specified.
"""
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urlparse
import json

@dataclass(frozen=True)
class Evidence:
    company: str
    entity_id: str
    country: str
    period: str
    basis: str
    currency: str
    unit: str
    current: str
    prior: str | None
    published_growth: str | None
    url: str
    status: str = 'official_excerpt_regression'

SAMPLES = [
    Evidence('Apple Inc.','AAPL','US','Q4 FY2026','reported revenue','USD','million','114477','102466','12', 'https://www.apple.com/newsroom/pdfs/fy2026q4/FY26_Q4_Consolidated_Financial_Statements.pdf'),
    Evidence('Siemens AG','SIE','DE','FY2026','reported revenue','EUR','billion','83.4',None,None,'https://press.siemens.com/global/en/pressrelease/earnings-release-and-financial-results-q4-fy-2026'),
    Evidence('LVMH Moet Hennessy Louis Vuitton SE','MC','FR','9M 2026','reported revenue','EUR','million','57148','58090',None,'https://www.lvmh.com/en/publications/continued-growth-in-the-third-quarter-of-2026'),
    Evidence('Unilever PLC','ULVR','UK','Q3 2026','reported turnover','EUR','billion','13.3',None,'6.7','https://www.unilever.com/investors/results-events/results-events-webcasts/latest-results/'),
    Evidence('Tata Motors Limited (commercial vehicles)','TMCV','IN','Q1 FY2027','standalone revenue','INR','crore','19329',None,'23','https://cv.tatamotors.com/news/tata-motors-limited-formerly-tml-commercial-vehicles-ltd-q1-fy27-results'),
]

ENTITY_ALIASES = {
    'tata motors': None, # deliberately ambiguous after demerger
    'tata motors limited': 'TMCV',
    'tata motors passenger vehicles': 'TMPV',
    'tata motors passenger vehicles limited': 'TMPV',
    'tmcv': 'TMCV',
    'apple': 'AAPL',
    'siemens': 'SIE',
    'lvmh': 'MC',
    'unilever': 'ULVR',
}

def resolve(name):
    key=' '.join(name.lower().strip().split())
    if key not in ENTITY_ALIASES: raise LookupError('Unknown entity; do not guess')
    if ENTITY_ALIASES[key] is None: raise ValueError('Ambiguous entity: choose commercial vehicles or passenger vehicles')
    return ENTITY_ALIASES[key]

def validate(e):
    assert urlparse(e.url).scheme == 'https'
    cur=Decimal(e.current)
    if cur <= 0: raise ValueError('Revenue must be positive')
    result={'company':e.company,'entity_id':e.entity_id,'country':e.country,'period':e.period,
            'metric':e.basis,'current':e.current,'prior':e.prior,'currency':e.currency,
            'unit':e.unit,'source':e.url,'evidence_status':e.status,
            'live_download_verified':False,'full_document_parse_verified':False}
    if e.prior is not None:
        prior=Decimal(e.prior)
        if prior <= 0: raise ValueError('Invalid comparative revenue')
        growth=(cur/prior-1)*100
        result['calculated_growth_percent']=str(growth.quantize(Decimal('.01')))
        if e.published_growth is not None:
            # Company releases round headline growth to whole percentage points.
            result['headline_reconciles']=abs(growth-Decimal(e.published_growth)) <= Decimal('.5')
    else:
        result['calculated_growth_percent']=None
        result['headline_reconciles']=None
        result['gap']='Comparable prior-period amount not extracted; cannot independently recalculate growth'
    if e.entity_id == 'TMCV':
        result['gap']='Official CV entity identified; TMPV is separate and its latest Q2 results remain unverified here'
    return result

def report():
    return {'method':'source-grounded excerpts, NOT live network end-to-end',
            'companies':[validate(e) for e in SAMPLES],
            'limitations':['Container DNS blocks live official-site downloads',
                           'No complete PDF or HTML parsing run against downloaded documents',
                           'No third-party news API or complete 90-day news crawl',
                           'No current verified TMPV Q2 primary financial statement']}

if __name__=='__main__':
    print(json.dumps(report(),indent=2))
