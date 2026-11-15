# CompanyScope Risk — Integrated Free Beta

This integrates the standalone Streamlit SEC financial-risk beta with the uploaded CompanyScope research modules. It does **not** claim five-country live research is working.

## Start locally
```bash
python -m pip install -r requirements.txt
```
Set `SEC_CONTACT_EMAIL` to a real contact address (required by SEC fair access), then:
```bash
streamlit run app.py
```
Windows PowerShell: `$env:SEC_CONTACT_EMAIL="your-email@example.com"`

## Test
```bash
python -m unittest discover -s tests -v
```

## Scope and limitations
- Public beta UI uses `engine.py` (SEC Company Facts). Uploaded original financial prototype is preserved as `legacy_engine.py`.
- Research modules (`intelligence.py`, `official_ir.py`, `monitoring.py`, `live_pipeline.py`, `validation_v04.py`) are preserved, **not connected to the public report**.
- Cross-country fixtures are offline examples, not independently live-verified company reports.
- No AI API, paid financial feed, domain, or database required for local tests.
- Live SEC access, correct filing selection and free public deployment **remain unverified**.
- SEC data alone is insufficient for private-company financial-risk ratings. No legal-entity equivalence is inferred.
- A deployment requires you to connect a hosting account and supply your SEC contact email. Do not place your contact email in public source code.
