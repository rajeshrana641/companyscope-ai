"""Conservative SEC Company Facts annual metric extraction; no LLM/API charges."""
import re
import requests
from datetime import date
from urllib.parse import urlparse

SEC = 'https://data.sec.gov'
TICKERS = 'https://www.sec.gov/files/company_tickers.json'
HEADERS = {'User-Agent': 'CompanyScope Research contact@example.com', 'Accept-Encoding': 'gzip, deflate'}
TAGS = {
 'Revenue': [('us-gaap','RevenueFromContractWithCustomerExcludingAssessedTax'), ('us-gaap','Revenues'), ('us-gaap','SalesRevenueNet')],
 'Net income': [('us-gaap','NetIncomeLoss')],
 'Operating income': [('us-gaap','OperatingIncomeLoss')],
 'Operating cash flow': [('us-gaap','NetCashProvidedByUsedInOperatingActivities')],
 'Current assets': [('us-gaap','AssetsCurrent')],
 'Current liabilities': [('us-gaap','LiabilitiesCurrent')],
 'Total assets': [('us-gaap','Assets')],
 'Total liabilities': [('us-gaap','Liabilities')],
}

def configure_contact(email):
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email or ''):
        raise ValueError('Provide a real contact email for SEC fair-access compliance.')
    HEADERS['User-Agent'] = f'CompanyScope Research {email}'

def fetch_json(url):
    if not url.startswith((SEC+'/', 'https://www.sec.gov/')):
        raise ValueError('Unapproved source URL')
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def ticker_candidates(query, ticker_records):
    q=query.strip().lower()
    if not q: return []
    records=ticker_records.values() if isinstance(ticker_records,dict) else ticker_records
    ranked=[]
    for rec in records:
        ticker=rec['ticker']; title=rec['title']
        if q==ticker.lower(): score=0
        elif q==title.lower(): score=1
        elif title.lower().startswith(q): score=2
        elif q in title.lower(): score=3
        else: continue
        ranked.append((score, title.lower(), rec))
    return [r for _,_,r in sorted(ranked)[:15]]

def annual_values(facts, metric):
    # No silent combination of distinct revenue taxonomies. Use the first with valid data.
    for taxonomy, tag in TAGS[metric]:
        node=facts.get('facts',{}).get(taxonomy,{}).get(tag,{})
        items=node.get('units',{}).get('USD',[])
        vals={}
        for x in items:
            if x.get('form') not in ('10-K','10-K/A') or x.get('val') is None: continue
            start,end=x.get('start'),x.get('end')
            if not end or not x.get('filed'): continue
            if start:
                try: duration=(date.fromisoformat(end)-date.fromisoformat(start)).days
                except ValueError: continue
                if not 330<=duration<=380: continue
            # Balance sheet point-in-time facts have no start; ignore duration only for these.
            elif metric not in ('Current assets','Current liabilities','Total assets','Total liabilities'):
                continue
            fy=x.get('fy'); fp=x.get('fp')
            if not isinstance(fy,int) or fp!='FY': continue
            key=end
            old=vals.get(key)
            if old is None or (x['filed'],x.get('accn',''))>(old['filed'],old.get('accn','')):
                vals[key]={'value':x['val'],'end':end,'filed':x['filed'],'accn':x.get('accn'),'tag':tag,'taxonomy':taxonomy}
        if vals: return sorted(vals.values(),key=lambda z:z['end'],reverse=True)[:5]
    return []

def evaluate(facts):
    metrics={m:annual_values(facts,m) for m in TAGS}
    alerts=[]
    rev=metrics['Revenue']
    if len(rev)>1 and rev[1]['value']>0:
        change=(rev[0]['value']/rev[1]['value']-1)*100
        if change<=-10: alerts.append(f'Revenue decreased {abs(change):.1f}% between the latest two available annual periods.')
    ocf=metrics['Operating cash flow']
    if ocf and ocf[0]['value']<0: alerts.append('Latest available annual operating cash flow is negative.')
    ca=metrics['Current assets']; cl=metrics['Current liabilities']
    if ca and cl and ca[0]['end']==cl[0]['end'] and cl[0]['value']>0:
        ratio=ca[0]['value']/cl[0]['value']
        if ratio<1: alerts.append(f'Current ratio is {ratio:.2f}x for {ca[0]["end"]}, below 1.0x.')
    if not alerts: alerts.append('No configured deterioration triggers were identified in available metrics; this is not a low-risk conclusion.')
    return metrics, alerts

def filing_url(cik, accn):
    if not accn: return None
    return f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace("-", "")}/'
