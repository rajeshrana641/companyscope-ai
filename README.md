# CompanyScope AI — research-engine MVP

This is a **working U.S. SEC structured-financial-data prototype**, not the completed five-country AI research service. It does not yet fetch PDFs, parse management commentary, retrieve 90-day news, or independently verify a company website against its legal entity.

## Run locally

```bash
pip install -r requirements.txt
export SEC_CONTACT_EMAIL='your-real-email@example.com'
streamlit run app.py
```

On Windows PowerShell: `$env:SEC_CONTACT_EMAIL="your-real-email@example.com"`.

The app accepts a company name, ticker, or website. Website matching is heuristic only; a website domain is **not** legal-entity verification. The program retrieves SEC ticker records and Company Facts on demand, computes annual YoY comparisons and simple deterioration warnings, and returns source references. It does **not** persist report data to disk or a database. Streamlit may retain ephemeral session memory.

## Test without network

```bash
python -m unittest discover -s tests -v
```

## Data accuracy notes

- Annual records require an approximately full-year duration and 10-K form; some non-calendar fiscal years and non-US-GAAP reporters are unsupported.
- The latest-filed value is selected for each annual period; this may reflect restatements. Explicit restatement alerts are not yet implemented.
- Company Facts includes entity-level standard taxonomy data; segment and custom-tag values are not covered.
- Revenue tag selection is first-available, not full taxonomy reconciliation; manual validation is necessary before commercial publication.
- Financial values are not a substitute for the latest full 10-K or 10-Q narrative.
- Respect SEC fair-access policy and supply your own truthful contact email.

## Next milestones

1. Official filing-link resolution and accession-document verification.
2. Quarterly fiscal-period reconciliation and corporate-action handling.
3. Filing narrative extraction with explicit evidence passages and report-page links.
4. News provider integration with licensed/permitted summaries, 90-day filtering, entity disambiguation, and deduplication.
5. Country-specific adapters for UK, Germany, France, India; do not label them operational before tested.
6. Caching, rate limits, monitoring, source-error handling and deployment.

## November 14, 2026 validation update

- Added `intelligence.py`: evidence-preserving candidate warning extraction from **supplied** filing/news passages, with required URL, date and source category. These indicators require review; the tool does not assert that a risk has materialized.
- Added a separate 90-day metadata filter for **supplied** news records: entity-alias matching, date window, basic duplicate removal. This is not an integrated news search provider and does not guarantee full coverage or perfect legal-entity matching.
- Added an experimental source-passage triage section to the Streamlit UI.
- Live SEC connection test from this sandbox failed due to DNS/network restriction; no live SEC result was validated here.
- Run all tests with `python -m unittest discover -s tests -v`.
- Future work: retrieve original filing narratives, verify extracted excerpts and guidance changes against official documents, implement licensed news retrieval, and connect other countries.

## v0.3 Official investor-relations retrieval experiment (November 14, 2026)

New: `official_ir.py`, `run_official_ir.py`, `fixtures/official_extracts.json`, `tests/test_official_ir.py`.

Run deterministic offline regression tests:

```bash
python -m unittest discover -s tests -v
python run_official_ir.py apple --fixture
python run_official_ir.py lvmh --fixture
```

Run a real official-site request **from a machine with working internet access**:

```bash
pip install requests beautifulsoup4 pymupdf
python run_official_ir.py apple
python run_official_ir.py siemens
python run_official_ir.py lvmh
python run_official_ir.py unilever
```

**Honest scope:** Offline fixtures are short excerpts transcribed from the companies' official financial releases, NOT original downloaded documents. Tests demonstrate parsing/calculation logic against those excerpts, not production-grade PDF extraction. The execution container has DNS resolution failures for apple.com; live fetching has NOT passed. Official web search independently confirmed the source URLs. PDF and HTML layouts may break the prototype parsers and require source-specific table extraction. LVMH's parser is designed for the fixture excerpt and may not work on the current website's table ordering. Siemens and Unilever parsers detect company-reported figures but cannot independently calculate their reported growth without prior comparable period values. Tata Motors Passenger Vehicles is deliberately not implemented because of corporate restructuring and unresolved current official source mapping. Do not mistake a fixture result for a live result. No Reuters/Yahoo/BBC automatic retrieval, no complete 90-day news crawl, no production-grade entity resolver, and no independent background scheduler yet.

Safety: Only allowlisted HTTPS official-site domains are retrieved; redirects rejected; 18MB size cap. Data is held in memory, not saved as source PDFs.

## v0.4 five-company validation (2026-11-14)

Run `python -m unittest discover -s tests -v` and `python validation_v04.py`.
The v0.4 source-backed validation module checks five distinct entities and calculations against selected values manually transcribed from the linked official investor documents. This is an **offline regression**. It does **not** claim that the application automatically downloaded, discovered, or fully parsed those documents, and it does not provide exhaustive 90-day news coverage. Live Python download failed due to DNS resolution in this environment. `validation_v04.py` explicitly marks every live retrieval and full-document parse as unverified. The Tata Motors test is the commercial-vehicle legal entity (TMCV), not the passenger-vehicle entity (TMPV); do not merge the two.

## v0.5 — News-triggered monitoring + calendar backup (November 14, 2026)

New `monitoring.py` and `tests/test_monitoring.py` implement **decision logic**, not a connected live news crawler. All monitoring examples in `fixtures/monitor_news_demo.json` are **synthetic demonstrations**, not factual news reports; `example.org` is a placeholder and never a research source.

To run the deterministic five-company demo:

```bash
python monitoring.py --news fixtures/monitor_news_demo.json --state fixtures/monitor_state_demo.json --as-of 2026-11-14 --output monitoring_demo_output.json
python -m unittest discover -s tests -v
```

The output lists `check_official_results` requests and a proposed state update. `status=requested_not_executed` means **no website was actually checked**. To integrate with a real scheduler, provide permitted news headline metadata once daily and persisted minimal state. Only call `record_official_check(..., found=True, report_key=..., published_at=..., period_end=...)` after an independently validated official report is located. Do not treat a news article as the financial filing itself.

The calendar fallback starts after the most recent verified publication plus a provisional 91-day interval and then checks at most weekly (not daily). This is a **temporary generic default**, not a verified company-specific earnings calendar. Annual/half-year reporting, holiday shifts, and advance published earnings dates need separate company-specific configuration before production. News headline matching is conservative but not perfect; an article mentioning earnings is not necessarily a newly published official result. Pending-news retries back off up to 7 days. A real news-feed connector, licensing assessment, official-document verifier, durable state, deployment, logs and monitoring are still required. No live end-to-end results were obtained here.

## v0.6: Network-ready discovery and actual connectivity attempt (2026-11-14)

`live_pipeline.py` adds:
- Five company-specific public RSS news search queries for **discovery only** (not a license to redistribute news).
- RSS/Atom parsing, timestamp normalization, and existing headline/entity matching.
- Calendar backup via `monitoring.py`.
- Official-website link discovery, constrained to the configured official host.
- Explicit errors and unverified candidate status. No figures are published by this module.

Run: `python live_pipeline.py --state fixtures/monitor_state_demo.json --as-of 2026-11-14 --output run.json`

Tests: `python -m unittest discover -s tests -v` (45 passing as of 2026-11-14).

**Actual connectivity attempt:** All five news RSS requests and official-site requests failed with DNS resolution errors in this execution environment. This is an environment limitation, NOT proof of a working live connector. No live reports were retrieved or verified.

**Not production-ready:** Google News RSS terms and reuse permissions require review before commercial deployment. Company IR homepages may link to filings hosted on separate official document domains, which are intentionally blocked by the strict host filter until verified allowlists are added. RSS feed results may include syndication suffixes or ambiguous entity mentions. No PDF financial table reconciliation, automatic state persistence, cron scheduler, full 90-day coverage guarantee, or deployment is included. Do not publish any financial figures from candidate links without original-document verification.
