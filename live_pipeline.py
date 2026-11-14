"""Network-ready discovery pipeline; does not assert financial figures are verified.

Uses public RSS metadata as a discovery signal (check feed terms before commercial use).
Official document candidates must be independently parsed/reconciled before publishing.
"""
from __future__ import annotations
import json
import re
import ssl
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from monitoring import COMPANIES, run_batch, record_official_check

USER_AGENT = 'CompanyScopeResearchPrototype/0.6 (research; contact: configure-before-production)'
FEED_QUERIES = {
    'apple': '"Apple" (earnings OR "financial results" OR "quarterly results")',
    'siemens': '"Siemens AG" (earnings OR "financial results" OR "quarterly results")',
    'lvmh': '"LVMH" (earnings OR "financial results" OR "revenue results")',
    'unilever': '"Unilever" (earnings OR "financial results" OR "quarterly results")',
    'tata_pv': '"Tata Motors Passenger Vehicles" (earnings OR "quarterly results")',
}
# A feed is used for discovery only, never for republishing full articles.
FEED_URL = 'https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en'


def fetch_bytes(url, *, timeout=12, max_bytes=2_000_000, opener=None):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!='https' or not parsed.hostname:
        raise ValueError('HTTPS URL required')
    if opener is None: opener=urllib.request.urlopen
    request=urllib.request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'application/rss+xml, application/xml, text/html'})
    with opener(request,timeout=timeout) as response:
        data=response.read(max_bytes+1)
        if len(data)>max_bytes: raise ValueError('Response too large')
        return data


def parse_rss(xml_bytes):
    root=ET.fromstring(xml_bytes)
    if root.tag not in ('rss','{http://www.w3.org/2005/Atom}feed'):
        raise ValueError('Not an RSS/Atom feed')
    items=[]
    for node in root.findall('./channel/item'):
        title=(node.findtext('title') or '').strip()
        link=(node.findtext('link') or '').strip()
        pub=(node.findtext('pubDate') or '').strip()
        try:
            from email.utils import parsedate_to_datetime
            published=parsedate_to_datetime(pub).astimezone(timezone.utc).date().isoformat()
        except (TypeError,ValueError,OverflowError,AttributeError): continue
        if title and link.startswith('https://'):
            items.append({'title':title,'url':link,'published_at':published,'feed':'google_news_rss'})
    for node in root.findall('{http://www.w3.org/2005/Atom}entry'):
        title=(node.findtext('{http://www.w3.org/2005/Atom}title') or '').strip()
        link=next((e.attrib.get('href','') for e in node.findall('{http://www.w3.org/2005/Atom}link') if e.attrib.get('rel','alternate')=='alternate'),'')
        pub=node.findtext('{http://www.w3.org/2005/Atom}published') or node.findtext('{http://www.w3.org/2005/Atom}updated')
        try: published=date.fromisoformat(pub[:10]).isoformat()
        except (TypeError,ValueError): continue
        if title and link.startswith('https://'):items.append({'title':title,'url':link,'published_at':published,'feed':'atom'})
    return items


def collect_headlines(fetcher=fetch_bytes):
    headlines=[]; errors={}
    for cid, query in FEED_QUERIES.items():
        url=FEED_URL.format(query=urllib.parse.quote(query))
        try:
            records=parse_rss(fetcher(url))
            for item in records: item['feed_company_id']=cid
            headlines.extend(records)
        except Exception as exc:
            errors[cid]=f'{type(exc).__name__}: {str(exc)[:200]}'
    return headlines,errors

class LinkParser(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.current=None
    def handle_starttag(self,tag,attrs):
        if tag=='a':
            d=dict(attrs);self.current={'href':d.get('href',''),'label':''}
    def handle_data(self,data):
        if self.current:self.current['label']+=data
    def handle_endtag(self,tag):
        if tag=='a' and self.current:
            self.links.append(self.current);self.current=None

RESULT_WORDS=re.compile(r'\b(?:financial results|quarterly results|annual report|earnings release|full.year results|half.year results|q[1-4] results|fy20\d\d)\b',re.I)

def discover_official_documents(company_id, fetcher=fetch_bytes):
    """Return unverified links from official homepage. No claim of report validity."""
    company=COMPANIES[company_id];root=company['official']
    raw=fetcher(root)
    parser=LinkParser();parser.feed(raw.decode('utf-8','replace'))
    base_host=urllib.parse.urlparse(root).hostname
    candidates=[];seen=set()
    for item in parser.links:
        link=urllib.parse.urljoin(root,item['href'])
        parsed=urllib.parse.urlparse(link)
        if parsed.scheme!='https' or not parsed.hostname:continue
        # Allow the official host or subdomains, not arbitrary third-party destinations.
        if not (parsed.hostname==base_host or parsed.hostname.endswith('.'+base_host)):continue
        if not RESULT_WORDS.search(item['label']+' '+parsed.path):continue
        if link not in seen:
            seen.add(link);candidates.append({'url':link,'label':item['label'].strip()[:180],'status':'candidate_unverified'})
    return candidates


def run_once(states, as_of=None, *, fetcher=fetch_bytes):
    as_of=as_of or datetime.now(timezone.utc).date().isoformat()
    news,errors=collect_headlines(fetcher)
    batch=run_batch(states,news,as_of)
    discoveries={};official_errors={}
    for result in batch['results']:
        if any(e['type']=='check_official_results' for e in result['events']):
            cid=result['company_id']
            try: discoveries[cid]=discover_official_documents(cid,fetcher)
            except Exception as exc: official_errors[cid]=f'{type(exc).__name__}: {str(exc)[:200]}'
    batch.update({'news_feed_errors':errors,'official_discovery_errors':official_errors,
                  'official_document_candidates':discoveries,
                  'verified_financial_reports':0,'financial_figures_published':0,
                  'live_fetch_performed':not bool(errors) or bool(discoveries),
                  'note':'Discovery only. Candidate documents require original filing verification and financial reconciliation.'})
    return batch

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument('--state',required=True)
    p.add_argument('--output',required=True)
    p.add_argument('--as-of')
    args=p.parse_args()
    states=json.loads(Path(args.state).read_text())
    output=run_once(states,args.as_of)
    Path(args.output).write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps({'news_feed_errors':output['news_feed_errors'], 'official_discovery_errors':output['official_discovery_errors'], 'checks_requested':output['summary']['official_checks_requested'],'verified_financial_reports':0},indent=2))
if __name__=='__main__':main()
