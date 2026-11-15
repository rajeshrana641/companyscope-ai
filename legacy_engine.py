"""CompanyScope: SEC financial analysis prototype. No persistent report storage."""
import json, re, urllib.request
from datetime import date
from urllib.parse import urlparse

SEC='https://data.sec.gov'
TICKERS='https://www.sec.gov/files/company_tickers.json'
METRICS={
 'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet','RevenueFromContractWithCustomerIncludingAssessedTax'],
 'net_income':['NetIncomeLoss'],
 'operating_income':['OperatingIncomeLoss'],
 'operating_cash_flow':['NetCashProvidedByUsedInOperatingActivities'],
 'research_development':['ResearchAndDevelopmentExpense'],
}

def fetch_json(url, contact):
    if not contact or '@' not in contact: raise ValueError('Set a real SEC_CONTACT_EMAIL to comply with SEC identification requirements')
    req=urllib.request.Request(url,headers={'User-Agent':f'CompanyScope Research {contact}','Accept':'application/json'})
    with urllib.request.urlopen(req,timeout=25) as r: return json.load(r)

def normalize_search(q):
    q=q.strip()
    if '://' in q or ('.' in q and ' ' not in q):
        host=urlparse(q if '://' in q else 'https://'+q).hostname or ''
        return re.sub(r'\.(com|co|org|net|io|in|uk|de|fr)$','',host.removeprefix('www.')).split('.')[0].lower()
    return q.lower()

def resolve_us(query, tickers):
    term=normalize_search(query)
    entries=list(tickers.values()) if isinstance(tickers,dict) else tickers
    exact=[x for x in entries if x['ticker'].lower()==term or x['title'].lower()==term]
    if exact:return exact[0]
    candidates=[x for x in entries if term in x['title'].lower()]
    if len(candidates)==1:return candidates[0]
    if candidates:raise ValueError('Ambiguous company name; enter an exact ticker: '+', '.join(x['ticker'] for x in candidates[:8]))
    raise ValueError('Company not found in SEC ticker directory; website matching needs independent entity verification')

def annual_series(facts, tags):
    gaap=facts.get('facts',{}).get('us-gaap',{})
    for tag in tags:
        concept=gaap.get(tag,{})
        usd=concept.get('units',{}).get('USD',[])
        records=[r for r in usd if r.get('form') in ('10-K','10-K/A') and r.get('fp')=='FY' and r.get('start') and r.get('end') and 330 <= (date.fromisoformat(r['end'])-date.fromisoformat(r['start'])).days <= 380]
        if not records:continue
        # A period may be repeated in later filings. Prefer latest filed observation, and preserve its accession.
        by_end={}
        for r in sorted(records,key=lambda r:(r.get('filed',''),r.get('accn',''))):by_end[r['end']]=r
        return sorted(by_end.values(),key=lambda r:r['end'])[-4:],tag
    return [],None

def analyze(facts, cik):
    metrics={}; warnings=[]
    for name,tags in METRICS.items():
        observations,tag=annual_series(facts,tags)
        rows=[{'period_end':r['end'],'value':r['val'],'filed':r.get('filed'),'accession':r.get('accn'),'form':r.get('form'),'source':f'https://www.sec.gov/Archives/edgar/data/{int(cik)}/{r.get("accn", "").replace("-", "")}/' if r.get('accn') else None} for r in observations]
        yoy=None
        if len(rows)>=2 and rows[-2]['value']>0:yoy=round((rows[-1]['value']/rows[-2]['value']-1)*100,2)
        metrics[name]={'taxonomy_tag':tag,'history':rows,'yoy_percent':yoy,'status':'reported' if rows else 'not_available'}
    rev=metrics['revenue']['history'];op=metrics['operating_income']['history']
    if rev and op and rev[-1]['period_end']==op[-1]['period_end'] and rev[-1]['value']:
        metrics['operating_margin_percent']=round(op[-1]['value']/rev[-1]['value']*100,2)
    if metrics['revenue']['yoy_percent'] is not None and metrics['revenue']['yoy_percent']<0:warnings.append('Revenue decreased year over year')
    if metrics['operating_income']['yoy_percent'] is not None and metrics['operating_income']['yoy_percent']<0:warnings.append('Operating income decreased year over year')
    if metrics['operating_cash_flow']['yoy_percent'] is not None and metrics['operating_cash_flow']['yoy_percent']<0:warnings.append('Operating cash flow decreased year over year')
    return {'company':facts.get('entityName'),'cik':str(cik).zfill(10),'metrics':metrics,'rule_based_warnings':warnings,'limitations':['US-GAAP entity-level annual facts only','No narrative risk extraction or news monitoring in this prototype','Website domain is not a verified legal entity identifier','SEC filing facts may be restated; latest-filed facts are selected per period','Annual financial data is not real-time market data']}

def run(query,contact):
    entry=resolve_us(query,fetch_json(TICKERS,contact))
    cik=str(entry['cik_str']).zfill(10)
    facts=fetch_json(f'{SEC}/api/xbrl/companyfacts/CIK{cik}.json',contact)
    result=analyze(facts,cik)
    result['ticker']=entry['ticker'];result['entity_match']='ticker/name directory match; confirm legal entity for domain queries'
    return result
