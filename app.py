import os
import streamlit as st
from engine import configure_contact,fetch_json,ticker_candidates,evaluate,filing_url,TICKERS,SEC
st.set_page_config(page_title='CompanyScope Risk | Public Beta',layout='wide')
st.title('CompanyScope Risk')
st.caption('Free public beta · US SEC filers only · Not investment advice or a credit rating')
email=os.getenv('SEC_CONTACT_EMAIL','')
if not email:
    st.error('Site owner must configure SEC_CONTACT_EMAIL in hosting secrets before using live SEC data.')
    st.stop()
try: configure_contact(email)
except ValueError as e: st.error(str(e)); st.stop()
@st.cache_data(ttl=86400,show_spinner=False)
def tickers(): return fetch_json(TICKERS)
@st.cache_data(ttl=21600,show_spinner=False)
def company_facts(cik): return fetch_json(f'{SEC}/api/xbrl/companyfacts/CIK{cik:010d}.json')
query=st.text_input('Enter US-listed company name or ticker',placeholder='e.g. MSFT or Microsoft')
if query:
    try:
        candidates=ticker_candidates(query,tickers())
        if not candidates: st.warning('No SEC ticker match. Try a ticker symbol.'); st.stop()
        choices={f"{r['ticker']} — {r['title']} (CIK {r['cik_str']})":r for r in candidates}
        selected=choices[st.selectbox('Confirm reporting entity (do not assume parent/subsidiary equivalence)',list(choices))]
        if st.button('Analyze verified SEC facts',type='primary'):
            with st.spinner('Retrieving SEC Company Facts…'):
                data=company_facts(int(selected['cik_str']))
            metrics,alerts=evaluate(data)
            st.subheader(data.get('entityName',selected['title']))
            st.caption(f"Reporting CIK: {int(selected['cik_str']):010d} · SEC taxonomy data, not a full filing review")
            for metric,items in metrics.items():
                with st.expander(metric,expanded=metric in ('Revenue','Operating cash flow')):
                    if not items: st.write('Not available in supported taxonomy / annual filing selection')
                    for x in items[:3]:
                        st.write(f"**{x['end']}**: ${x['value']:,.0f} · filed {x['filed']} · {x['tag']}")
                        url=filing_url(selected['cik_str'],x['accn'])
                        if url: st.markdown(f'[SEC accession directory]({url})')
            st.subheader('Rule-based observations')
            for a in alerts: st.write('• '+a)
            st.warning('Not a comprehensive financial-risk rating. Restatements, taxonomy choices, segment data, and the latest 10-Q require separate verification. Do not infer legal-entity equivalence from ticker matches.')
    except Exception as e:
        st.error('Unable to retrieve or interpret live SEC data. No report has been generated.')
        st.caption(f'Diagnostic: {type(e).__name__}: {e}')
st.divider()
st.caption('Data source: US Securities and Exchange Commission (SEC). No paid AI API is used. This beta stores no reports in a database.')
