"""Evidence-preserving narrative and news triage. Inputs are supplied text, not scraped here."""
import re
from datetime import date, timedelta
from urllib.parse import urlparse

TRIGGERS={
 'guidance_reduction':(r'\b(?:lowered|cut|reduced|downgraded)\b.{0,90}\b(?:guidance|outlook|forecast|expectations?)\b', 'high'),
 'margin_pressure':(r'\b(?:margin pressure|pressure on (?:gross |operating )?margins?|higher (?:input|component|commodity) costs?)\b','medium'),
 'cyber_disruption':(r'\b(?:cyberattack|ransomware|cyber incident)\b','high'),
 'restructuring':(r'\b(?:restructuring|demerger|spin.off|discontinued operations)\b','context'),
 'concentration':(r'\b(?:customer concentration|single customer|largest customer|major customer)\b','review'),
}

def classify_evidence(text, source_url, published_at, source_type='official'):
    """Returns flagged excerpts, preserving provenance. No invented quantified claims."""
    if not source_url or urlparse(source_url).scheme not in ('https','http'):
        raise ValueError('A valid evidence URL is required')
    date.fromisoformat(published_at)
    if source_type not in ('official','regulatory','trusted_third_party'):
        raise ValueError('Unsupported evidence source type')
    sentences=re.split(r'(?<=[.!?])\s+|\n+',text.strip())
    findings=[]
    for sentence in sentences:
        for label,(pattern,severity) in TRIGGERS.items():
            if re.search(pattern,sentence,re.I):
                findings.append({'indicator':label,'severity':severity,'evidence_excerpt':sentence[:600],
                                 'source_url':source_url,'published_at':published_at,'source_type':source_type,
                                 'status':'requires_analyst_review'})
    return findings

def filter_news(items, company_aliases, as_of, days=90):
    """Filter supplied metadata for dates/entity aliases and deduplicate URLs/headlines.
    This is *not* a news crawler and does not prove exhaustive coverage.
    """
    today=date.fromisoformat(as_of)
    aliases=[a.casefold() for a in company_aliases if len(a.strip())>=3]
    if not aliases:raise ValueError('At least one unambiguous company alias is required')
    seen=set();out=[]
    for item in items:
        try:
            d=date.fromisoformat(item['published_at'][:10]);url=item['url'];title=item['title']
            if not (today-timedelta(days=days) <= d <= today):continue
            if urlparse(url).scheme not in ('https','http'):continue
            combined=(title+' '+item.get('summary','')).casefold()
            if not any(re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',combined) for alias in aliases):continue
            key=(urlparse(url).netloc.lower(),re.sub(r'\W+','',title.casefold()))
            if key in seen:continue
            seen.add(key)
            out.append({'title':title,'url':url,'published_at':d.isoformat(),'publisher':item.get('publisher','unknown'),
                        'summary':item.get('summary',''),'classification':'not_assessed'})
        except (KeyError,TypeError,ValueError):continue
    return sorted(out,key=lambda x:x['published_at'],reverse=True)
