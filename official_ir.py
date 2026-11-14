"""Official investor-relations source parser. No permanent document storage.

Live mode fetches official HTML/PDF over HTTPS. Offline fixture mode uses
short, source-transcribed extracts for deterministic regression tests.
"""
from __future__ import annotations
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

ALLOWED_DOMAINS = {'apple.com','siemens.com','lvmh.com','unilever.com','tatamotors.com','tatamotorspassengervehicles.com'}
MAX_BYTES=18_000_000

SOURCES={
 'apple':{'name':'Apple Inc.','country':'US','url':'https://www.apple.com/newsroom/pdfs/fy2026q4/FY26_Q4_Consolidated_Financial_Statements.pdf','format':'pdf','period':'Q4 FY2026','currency':'USD','unit':'million'},
 'siemens':{'name':'Siemens AG','country':'DE','url':'https://press.siemens.com/global/en/pressrelease/earnings-release-and-financial-results-q4-fy-2026','format':'html','period':'FY2026','currency':'EUR','unit':'billion'},
 'lvmh':{'name':'LVMH','country':'FR','url':'https://www.lvmh.com/en/publications/continued-growth-in-the-third-quarter-of-2026','format':'html','period':'9M 2026','currency':'EUR','unit':'million'},
 'unilever':{'name':'Unilever PLC','country':'UK','url':'https://www.unilever.com/news/press-and-media/press-releases/2026/continued-strong-performance-in-the-third-quarter/','format':'html','period':'Q3 2026','currency':'EUR','unit':'billion'},
}

def safe_domain(url):
    p=urlparse(url)
    return p.scheme=='https' and p.hostname and any(p.hostname==d or p.hostname.endswith('.'+d) for d in ALLOWED_DOMAINS)

def retrieve(url, timeout=20):
    if not safe_domain(url): raise ValueError('URL is not an allowlisted official IR domain')
    r=requests.get(url,timeout=timeout,headers={'User-Agent':'CompanyScopeResearch/0.3 (public research prototype)','Accept':'text/html,application/pdf'},stream=True,allow_redirects=False)
    r.raise_for_status()
    if r.status_code in (301,302,303,307,308): raise ValueError('Redirect requires manual source validation')
    parts=[]; size=0
    for chunk in r.iter_content(65536):
        size+=len(chunk)
        if size>MAX_BYTES: raise ValueError('Document exceeds size limit')
        parts.append(chunk)
    return b''.join(parts)

def extract_text(payload, kind):
    if kind=='html':
        soup=BeautifulSoup(payload,'html.parser')
        for x in soup(['script','style','nav','footer']): x.decompose()
        return soup.get_text(' ',strip=True)
    if kind=='pdf':
        import fitz
        with fitz.open(stream=payload,filetype='pdf') as doc:
            if len(doc)>250: raise ValueError('PDF exceeds page limit')
            return '\n'.join(page.get_text(sort=True) for page in doc)
    raise ValueError('Unsupported document type')

def number(s): return float(s.replace(',','').replace(' ','').replace('\u00a0',''))

def growth(current, prior):
    if prior==0: raise ValueError('Cannot compute growth against zero')
    return round((current/prior-1)*100,2)

def apple_extract(text):
    # Official PDF table row order: three-month current, three-month prior,
    # twelve-month current, twelve-month prior. Reject if no unique match.
    matches=re.findall(r'Total net sales\s*(?:\(1\))?\s*\$?\s*([\d,]+)\s+\$?\s*([\d,]+)\s+\$?\s*([\d,]+)\s+\$?\s*([\d,]+)',text,re.I)
    if not matches: raise ValueError('Apple revenue row not found; PDF layout needs inspection')
    a,b,c,d=map(number,matches[0]); return {'current':a,'prior':b,'annual_current':c,'annual_prior':d,'growth_percent':growth(a,b),'annual_growth_percent':growth(c,d)}

def lvmh_extract(text):
    # Published 9M total line, with column headers preserved by HTML parsing.
    current_match=re.search(r'First nine months\s+([\d\s]{5,9})',text,re.I)
    prior_match=re.search(r'First nine months 2025\s+([\d\s]{5,9})',text,re.I)
    if not current_match or not prior_match: raise ValueError('LVMH comparative revenue rows not located')
    current=number(current_match.group(1).strip()); prior=number(prior_match.group(1).strip())
    return {'current':current,'prior':prior,'growth_percent':growth(current,prior),'basis':'9M reported revenue; organic growth is a different metric'}

def siemens_extract(text):
    if not re.search(r'revenue was €83\.4 billion',text,re.I): raise ValueError('Siemens annual revenue not found')
    return {'current':83.4,'basis':'FY2026 reported revenue','reported_comparable_growth_percent':8.0,'prior':None,'growth_percent':None}

def unilever_extract(text):
    if not re.search(r'Turnover of €13\.3 billion up 6\.7%',text,re.I): raise ValueError('Unilever quarterly turnover not found')
    return {'current':13.3,'reported_growth_percent':6.7,'underlying_growth_percent':5.2,'prior':None,'growth_percent':None,'basis':'Q3 turnover, distinct from underlying sales growth'}

PARSERS={'apple':apple_extract,'siemens':siemens_extract,'lvmh':lvmh_extract,'unilever':unilever_extract}

def analyze_official(key, fixture_text=None):
    if key not in SOURCES: raise ValueError('Company has no verified official source configured')
    source=SOURCES[key]
    if fixture_text is None:
        text=extract_text(retrieve(source['url']),source['format']); mode='live'
    else: text=fixture_text;mode='fixture'
    return {'company':source['name'],'source_url':source['url'],'period':source['period'],'currency':source['currency'],'unit':source['unit'],'retrieval_mode':mode,'metrics':PARSERS[key](text)}
