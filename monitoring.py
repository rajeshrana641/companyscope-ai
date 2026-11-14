"""News-triggered earnings monitoring with calendar fallback.

This module consumes supplied, licensed/permitted headline metadata; it does not
scrape news, download filings or assert that a financial report was retrieved.
All dates are UTC ISO calendar dates. State contains metadata only.
"""
from __future__ import annotations
import json
import re
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

EARNINGS = re.compile(r'\b(?:reports?|announces?|publishes?|releases?|posts?|files?)\b.{0,85}\b(?:quarterly|annual|half.year|full.year|q[1-4]|fy\d{2,4}|earnings|financial results|results|revenue|trading update)\b|\b(?:quarterly|annual|half.year|full.year|q[1-4]|fy\d{2,4}|earnings|financial results|trading update)\b.{0,75}\b(?:results?|released?|published?|reported?|announced?)\b', re.I)
NEGATION = re.compile(r'\b(?:will|to|expects? to|scheduled to|ahead of|preview|anticipates?|rumou?rs?|may|could)\b', re.I)
PERIOD = re.compile(r'\b(?:Q[1-4]\s*(?:FY)?\s*20\d{2}|(?:FY\s*)?20\d{2}\s*(?:Q[1-4])?|H[12]\s*20\d{2})\b',re.I)

COMPANIES = {
    'apple': {'name':'Apple Inc.', 'aliases':['Apple Inc','Apple'], 'ticker':'AAPL', 'country':'US', 'official':'https://investor.apple.com/', 'frequency_days':91},
    'siemens': {'name':'Siemens AG', 'aliases':['Siemens AG','Siemens'], 'ticker':'SIE', 'country':'DE', 'official':'https://www.siemens.com/', 'frequency_days':91},
    'lvmh': {'name':'LVMH Moet Hennessy Louis Vuitton SE', 'aliases':['LVMH'], 'ticker':'MC', 'country':'FR', 'official':'https://www.lvmh.com/', 'frequency_days':91},
    'unilever': {'name':'Unilever PLC', 'aliases':['Unilever PLC','Unilever'], 'ticker':'ULVR', 'country':'UK', 'official':'https://www.unilever.com/', 'frequency_days':91},
    'tata_pv': {'name':'Tata Motors Passenger Vehicles Limited', 'aliases':['Tata Motors Passenger Vehicles','TMPV'], 'ticker':'TMPV', 'country':'IN', 'official':'https://www.tatamotors.com/', 'frequency_days':91},
}

def _whole_alias(text, aliases):
    return any(re.search(r'(?<![\w])'+re.escape(a)+r'(?![\w])', text, re.I) for a in aliases)

def _date(s): return date.fromisoformat(s[:10])

def classify_headline(item, company, today):
    """Conservative candidate detection, not a guarantee that filing exists."""
    try:
        published=_date(item['published_at'])
        if not today-timedelta(days=90) <= published <= today: return None
        title=item['title'].strip()
        url=item['url']
        if urlparse(url).scheme != 'https' or not urlparse(url).hostname: return None
        if not _whole_alias(title, company['aliases']): return None
        if not EARNINGS.search(title): return None
        if NEGATION.search(title): return None
        # A company may share an ambiguous short alias with a subsidiary.
        if company['ticker']=='TMPV' and re.search(r'\b(?:commercial vehicles|TMCV)\b', title, re.I): return None
        period=PERIOD.search(title)
        return {'title':title,'url':url,'published_at':published.isoformat(),
                'period_hint':period.group(0).upper().replace(' ','') if period else None,
                'source':'news_trigger','status':'candidate_unverified'}
    except (KeyError, TypeError, ValueError, AttributeError):
        return None

def monitor(company_id, company_state, news, as_of):
    """Returns decisions without performing external requests.

    state: last_published (date), next_expected (optional), last_report_key,
    pending (optional), last_fallback_check (optional).
    """
    if company_id not in COMPANIES: raise ValueError('Unknown or ambiguous company ID')
    today=_date(as_of); company=COMPANIES[company_id]
    state=dict(company_state)
    events=[]
    candidates=[]; seen=set()
    for item in news:
        hit=classify_headline(item,company,today)
        if hit:
            key=hit['url'].split('#')[0].split('?')[0]
            if key not in seen: seen.add(key);candidates.append(hit)
    candidates.sort(key=lambda x:x['published_at'],reverse=True)
    last=_date(state['last_published']) if state.get('last_published') else None
    # Reject old headline events already covered by the latest confirmed filing.
    candidates=[x for x in candidates if not last or _date(x['published_at'])>last]
    pending=state.get('pending')
    if candidates:
        chosen=candidates[0]
        if not pending or pending.get('url') != chosen['url']:
            pending={'url':chosen['url'],'headline':chosen['title'], 'detected_at':as_of,
                     'period_hint':chosen['period_hint'], 'attempts':0, 'next_retry':as_of}
            events.append({'type':'news_results_detected','company_id':company_id,'headline':chosen['title'], 'url':chosen['url']})
    if pending:
        retry_date=_date(pending['next_retry'])
        if today>=retry_date:
            events.append({'type':'check_official_results','company_id':company_id,'reason':'news_trigger',
                           'official_url':company['official'],'status':'requested_not_executed'})
    else:
        next_expected=(_date(state['next_expected']) if state.get('next_expected')
                       else (last+timedelta(days=company['frequency_days']) if last else None))
        # Weekly backup when results are due, not daily scanning.
        last_check=_date(state['last_fallback_check']) if state.get('last_fallback_check') else None
        if next_expected and today>=next_expected and (not last_check or (today-last_check).days>=7):
            events.append({'type':'check_official_results','company_id':company_id,'reason':'calendar_backup',
                           'official_url':company['official'],'status':'requested_not_executed'})
            state['last_fallback_check']=as_of
    state['pending']=pending
    return {'company_id':company_id,'as_of':as_of,'events':events,'state':state,
            'news_candidates':len(candidates),'live_fetch_performed':False}

def record_official_check(state, as_of, found, report_key=None, published_at=None, period_end=None):
    """Update state ONLY after an independent official-source verifier returns a result.
    Caller is responsible for validating the official report and company identity.
    """
    state=dict(state);pending=state.get('pending')
    if found:
        if not report_key or not published_at or not period_end: raise ValueError('Verified report metadata required')
        if state.get('last_report_key')==report_key:
            state['pending']=None
            return state
        state['last_report_key']=report_key
        state['last_published']=published_at
        state['last_period_end']=period_end
        state['next_expected']=None # company frequency used to compute next window
        state['pending']=None
        state['last_fallback_check']=None
    elif pending:
        attempts=pending.get('attempts',0)+1
        # Bounded exponential retry, max seven days; no tight loops.
        delay=min(7,2**min(attempts-1,3))
        pending['attempts']=attempts
        pending['next_retry']=(_date(as_of)+timedelta(days=delay)).isoformat()
        state['pending']=pending
    return state

def run_batch(states, news, as_of):
    results=[monitor(cid, states.get(cid,{}), news, as_of) for cid in COMPANIES]
    return {'as_of':as_of,'results':results,'states':{r['company_id']:r['state'] for r in results},
            'summary':{'official_checks_requested':sum(e['type']=='check_official_results' for r in results for e in r['events']),
                       'news_triggers':sum(e['type']=='news_results_detected' for r in results for e in r['events']),
                       'live_fetch_performed':False}}

def main():
    import argparse
    p=argparse.ArgumentParser(description='Offline news-trigger and calendar-backup decision engine')
    p.add_argument('--news',required=True,help='JSON list of licensed/permitted headline metadata')
    p.add_argument('--state',required=True,help='JSON object of company monitoring metadata')
    p.add_argument('--as-of',required=True,help='ISO date (UTC)')
    p.add_argument('--output',help='Write result JSON to this file')
    a=p.parse_args()
    result=run_batch(json.loads(Path(a.state).read_text()),json.loads(Path(a.news).read_text()),a.as_of)
    output=json.dumps(result,indent=2)
    if a.output:Path(a.output).write_text(output+'\n')
    print(output)
if __name__=='__main__': main()
