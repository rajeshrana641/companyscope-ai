import json, os
import streamlit as st
from engine import run
from intelligence import classify_evidence, filter_news
st.set_page_config(page_title='CompanyScope AI',page_icon='📊',layout='wide')
st.title('CompanyScope AI')
st.caption('Evidence-first public company intelligence · U.S. SEC pilot')
query=st.text_input('Company name, ticker or website','AAPL')
st.info('Website-name matching is tentative, not verified. U.S. listed issuers only in this prototype.')
if st.button('Analyze company',type='primary'):
    try:
        with st.spinner('Retrieving official SEC data…'):
            report=run(query,os.getenv('SEC_CONTACT_EMAIL',''))
        st.subheader(f"{report['company']} · {report['ticker']}")
        for name,item in report['metrics'].items():
            if not isinstance(item,dict):continue
            if item['history']:
                x=item['history'][-1]; st.metric(name.replace('_',' ').title(),f"${x['value']/1e9:,.2f}B",f"{item['yoy_percent']}% YoY" if item['yoy_percent'] is not None else None)
                st.caption(f"FY ending {x['period_end']} · filed {x['filed']} · [SEC filing archive]({x['source']})")
            else:st.write(f"{name.replace('_',' ').title()}: Not available in supported taxonomy")
        st.subheader('Rule-based warning indicators')
        for warning in report['rule_based_warnings']:st.warning(warning)
        if not report['rule_based_warnings']:st.write('No negative YoY trends detected among available metrics. This is not a clean-risk certification.')
        st.subheader('Coverage limitations')
        for note in report['limitations']:st.write('• '+note)
        st.download_button('Download analysis JSON',json.dumps(report,indent=2),file_name='companyscope_analysis.json',mime='application/json')
    except Exception as e:st.error(str(e))


st.divider()
st.subheader('Evidence triage (experimental)')
st.caption('Paste a passage from an official filing or trusted third-party source. Findings are candidate indicators, not verified risk conclusions.')
with st.expander('Analyze a sourced passage'):
    passage=st.text_area('Source passage')
    source_url=st.text_input('Direct source URL')
    published_at=st.date_input('Source publication date').isoformat()
    source_type=st.selectbox('Source category',['official','regulatory','trusted_third_party'])
    if st.button('Extract evidence indicators'):
        try:
            findings=classify_evidence(passage,source_url,published_at,source_type)
            if findings: st.json(findings)
            else: st.info('No supported trigger phrases detected; this is not evidence of zero risk.')
        except ValueError as exc:st.error(str(exc))
