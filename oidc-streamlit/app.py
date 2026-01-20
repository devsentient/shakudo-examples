import base64
import hashlib
import json
import os
import secrets
import urllib.parse
from pathlib import Path
from typing import Optional

import requests
import streamlit as st

try:
    import jwt
except Exception:  # pragma: no cover - fallback if PyJWT is missing
    jwt = None


def base64url_encode(raw_bytes: bytes) -> str:
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")


def build_pkce_pair() -> tuple[str, str]:
    verifier = base64url_encode(secrets.token_bytes(32))
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    challenge = base64url_encode(digest)
    return verifier, challenge


def normalize_query_params() -> dict[str, str]:
    if hasattr(st, "query_params"):
        params = dict(st.query_params)
        normalized = {}
        for key, value in params.items():
            if isinstance(value, list):
                normalized[key] = value[0] if value else ""
            else:
                normalized[key] = value
        return normalized

    params = st.experimental_get_query_params()
    return {key: value[0] if value else "" for key, value in params.items()}


def decode_jwt(token: str) -> dict:
    if token.count(".") < 2:
        return {"error": "Token is not in JWT format."}

    if jwt is not None:
        try:
            header = jwt.get_unverified_header(token)
            payload = jwt.decode(
                token,
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_iss": False,
                },
            )
            return {"header": header, "payload": payload}
        except Exception as exc:  # pragma: no cover - fallback for decode failures
            fallback = manual_decode_jwt(token)
            fallback["warning"] = f"PyJWT decode failed: {exc}"
            return fallback

    return manual_decode_jwt(token)


def manual_decode_jwt(token: str) -> dict:
    try:
        header_b64, payload_b64, _signature = token.split(".", 2)

        def pad(segment: str) -> str:
            return segment + "=" * (-len(segment) % 4)

        header_json = base64.urlsafe_b64decode(pad(header_b64)).decode("utf-8")
        payload_json = base64.urlsafe_b64decode(pad(payload_b64)).decode("utf-8")
        return {"header": json.loads(header_json), "payload": json.loads(payload_json)}
    except Exception as exc:
        return {"error": f"Failed to decode JWT: {exc}"}


def resolve_state_file() -> Path:
    env_path = os.environ.get("OIDC_STATE_FILE")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return Path(__file__).resolve().parent / "oidc_state.json"


STATE_FILE = resolve_state_file()
PERSIST_KEYS = (
    "discovery_url",
    "discovery",
    "client_id",
    "client_secret",
    "redirect_uri",
    "scopes",
    "auth_request",
    "token_response",
    "last_query_params",
)


def load_persisted_state() -> tuple[dict, Optional[str]]:
    if not STATE_FILE.exists():
        return {}, None

    try:
        with STATE_FILE.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict):
            return data, None
        return {}, "Persisted state is not a JSON object."
    except Exception as exc:
        return {}, f"Failed to read persisted state: {exc}"


def persist_state(state: dict) -> None:
    data = {key: state.get(key) for key in PERSIST_KEYS if key in state}
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = STATE_FILE.with_name(f"{STATE_FILE.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
    os.replace(tmp_path, STATE_FILE)


def fetch_discovery(url: str) -> dict:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def exchange_code(
    token_endpoint: str,
    code: str,
    redirect_uri: str,
    client_id: str,
    client_secret: str,
    code_verifier: str,
) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }
    if client_secret:
        payload["client_secret"] = client_secret

    response = requests.post(
        token_endpoint,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


st.set_page_config(page_title="OIDC Test Harness", layout="wide")

if "persist_loaded" not in st.session_state:
    persisted_state, persist_error = load_persisted_state()
    st.session_state.update(persisted_state)
    st.session_state.persist_error = persist_error
    st.session_state.persist_loaded = True

st.title("OIDC Test Harness")
st.caption("Discovery, authorization flow, and JWT decoding in one place.")

if "discovery" not in st.session_state:
    st.session_state.discovery = None
if "auth_request" not in st.session_state:
    st.session_state.auth_request = None
if "token_response" not in st.session_state:
    st.session_state.token_response = None
if "last_query_params" not in st.session_state:
    st.session_state.last_query_params = {}

if st.session_state.persist_error:
    st.warning(st.session_state.persist_error)

with st.expander("Step 1: Discovery", expanded=False):
    discovery_url = st.text_input(
        "OIDC discovery endpoint",
        value=st.session_state.get("discovery_url", ""),
        placeholder="https://issuer/.well-known/openid-configuration",
    )

    col_fetch, col_clear = st.columns([1, 1])
    with col_fetch:
        if st.button("Fetch configuration"):
            if not discovery_url:
                st.error("Enter a discovery endpoint URL.")
            else:
                try:
                    st.session_state.discovery = fetch_discovery(discovery_url)
                    st.session_state.discovery_url = discovery_url
                    st.success("Discovery document loaded.")
                except Exception as exc:
                    st.error(f"Failed to fetch discovery document: {exc}")

    with col_clear:
        if st.button("Clear discovery"):
            st.session_state.discovery = None
            st.session_state.discovery_url = ""

    if st.session_state.discovery:
        st.json(st.session_state.discovery, expanded=False)

with st.expander("Step 2: Client configuration", expanded=False):
    client_id = st.text_input(
        "Client ID",
        value=st.session_state.get("client_id", ""),
    )
    client_secret = st.text_input(
        "Client secret (optional)",
        value=st.session_state.get("client_secret", ""),
        type="password",
    )
    redirect_uri = st.text_input(
        "Redirect URI",
        value=st.session_state.get("redirect_uri", "http://localhost:8501"),
    )
    scopes = st.text_input(
        "Scopes",
        value=st.session_state.get("scopes", "openid profile email"),
    )

    st.session_state.client_id = client_id
    st.session_state.client_secret = client_secret
    st.session_state.redirect_uri = redirect_uri
    st.session_state.scopes = scopes

with st.expander("Step 3: Authorization request", expanded=False):
    if not st.session_state.discovery:
        st.info("Load a discovery document first.")
    elif not client_id:
        st.info("Provide a client ID to build the authorization URL.")
    else:
        auth_endpoint = st.session_state.discovery.get("authorization_endpoint", "")
        if not auth_endpoint:
            st.warning("Discovery document does not include authorization_endpoint.")
        else:
            col_auth, col_reset = st.columns([1, 1])
            with col_auth:
                if st.button("Generate authorization URL"):
                    state = secrets.token_urlsafe(16)
                    nonce = secrets.token_urlsafe(16)
                    verifier, challenge = build_pkce_pair()

                    params = {
                        "client_id": client_id,
                        "response_type": "code",
                        "scope": scopes,
                        "redirect_uri": redirect_uri,
                        "state": state,
                        "nonce": nonce,
                        "code_challenge": challenge,
                        "code_challenge_method": "S256",
                    }
                    auth_url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"

                    st.session_state.auth_request = {
                        "auth_url": auth_url,
                        "state": state,
                        "nonce": nonce,
                        "code_verifier": verifier,
                    }
                    st.success("Authorization URL generated.")

            with col_reset:
                if st.button("Clear auth request"):
                    st.session_state.auth_request = None

        if st.session_state.auth_request:
            st.markdown(
                "Open the authorization URL:"
            )
            auth_url = st.session_state.auth_request['auth_url']
            st.link_button("Authorize", auth_url)
            st.code(st.session_state.auth_request["auth_url"], language="text")
            st.json(
                {
                    "state": st.session_state.auth_request["state"],
                    "nonce": st.session_state.auth_request["nonce"],
                    "code_verifier": st.session_state.auth_request["code_verifier"],
                }
            , expanded=False)

with st.expander("Step 4: Handle redirect and exchange code", expanded=False):
    params = normalize_query_params()
    params_source = "current"
    if params:
        st.session_state.last_query_params = params
    elif st.session_state.last_query_params:
        params = st.session_state.last_query_params
        params_source = "saved"

    if params:
        if params_source == "saved":
            st.info("Showing last saved redirect parameters from local storage.")
        st.json(params, expanded=False)
    else:
        st.info("No query parameters found yet.")

    code = params.get("code", "")
    returned_state = params.get("state", "")
    error = params.get("error", "")

    if error:
        st.error(f"Authorization error: {error}")

    expected_state = (
        st.session_state.auth_request.get("state")
        if st.session_state.auth_request
        else ""
    )

    if returned_state and expected_state and returned_state != expected_state:
        st.warning("State mismatch detected. Verify the response is expected.")

    if code and st.session_state.discovery:
        token_endpoint = st.session_state.discovery.get("token_endpoint", "")
        if not token_endpoint:
            st.warning("Discovery document does not include token_endpoint.")
        elif not st.session_state.auth_request:
            st.warning("Generate an authorization request to capture PKCE verifier.")
        else:
            if st.button("Exchange code for tokens"):
                try:
                    st.session_state.token_response = exchange_code(
                        token_endpoint=token_endpoint,
                        code=code,
                        redirect_uri=redirect_uri,
                        client_id=client_id,
                        client_secret=client_secret,
                        code_verifier=st.session_state.auth_request["code_verifier"],
                    )
                    st.success("Token response received.")
                except Exception as exc:
                    st.error(f"Token request failed: {exc}")

    if st.session_state.token_response:
        st.json(st.session_state.token_response, expanded=False)

with st.expander("Step 5: Decode JWTs", expanded=False):
    candidates = {}

    if params:
        for key in ("id_token", "access_token", "refresh_token"):
            if key in params:
                candidates[f"redirect::{key}"] = params[key]

    if st.session_state.token_response:
        for key in ("id_token", "access_token", "refresh_token"):
            value = st.session_state.token_response.get(key)
            if value:
                candidates[f"token_response::{key}"] = value

    manual_token = st.text_area("Manual JWT", value="", height=120)
    if manual_token.strip():
        candidates["manual"] = manual_token.strip()

    if not candidates:
        st.info("No JWTs detected yet. Paste one above to decode.")
    else:
        for label, token in candidates.items():
            st.subheader(label)
            result = decode_jwt(token)
            st.json(result, expanded=False)

st.caption("Notes: JWTs are decoded without signature verification in this tool.")

try:
    persist_state(st.session_state)
except Exception as exc:
    st.warning(f"Failed to persist state to {STATE_FILE}: {exc}")
