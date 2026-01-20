# OIDC Test Harness (Streamlit)

Simple Streamlit app to:
- fetch an OIDC discovery document,
- generate an authorization request (PKCE),
- exchange the code for tokens,
- decode JWTs without signature verification.

## Run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Notes
- Default redirect URI is `http://localhost:8501`.
- JWT decoding is for inspection only and skips signature verification.
- State (including secrets/tokens) is persisted to `oidc-streamlit/oidc_state.json` (override with `OIDC_STATE_FILE`).
