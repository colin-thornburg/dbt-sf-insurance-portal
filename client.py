# stdlib
import logging
import os
from dataclasses import dataclass
from typing import Dict
from urllib.parse import parse_qs, urlparse

# third party
import requests
import streamlit as st

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv()

# first party
from queries import GRAPHQL_QUERIES


logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


@dataclass
class ConnAttr:
    host: str  # "grpc+tls:semantic-layer.cloud.getdbt.com:443"
    params: dict  # {"environmentId": 42}
    auth_header: str  # "Bearer dbts_thisismyprivateservicetoken"


RESULT_STATUSES = ["pending", "running", "compiled", "failed", "successful"]


def _mask_token(token: str, *, keep_start: int = 6, keep_end: int = 4) -> str:
    if not token:
        return ""
    if len(token) <= keep_start + keep_end:
        return "*" * len(token)
    return f"{token[:keep_start]}***{token[-keep_end:]}"


def get_company_from_email(email: str) -> str:
    """Extract company name from email domain"""
    if not email or "@" not in email:
        return "default"

    domain = email.split("@")[-1].lower()

    # Map domains to company names
    domain_map = {
        "techcorp.com": "techcorp",
        "retailplus.com": "retailplus",
        "manufacturingco.com": "manufacturingco",
    }

    return domain_map.get(domain, "default")


def get_company_token(company: str) -> str:
    """Get company-specific service token"""
    token_map = {
        "techcorp": os.getenv("DBT_TECHCORP_TOKEN", "").strip(),
        "retailplus": os.getenv("DBT_RETAILPLUS_TOKEN", "").strip(),
        "manufacturingco": os.getenv("DBT_MANUFACTURINGCO_TOKEN", "").strip(),
    }

    token = token_map.get(company.lower(), "")

    # Fallback to generic token if company-specific not found
    if not token:
        token = os.getenv("DBT_TOKEN", "").strip()
        logger.warning(
            f"Company-specific token not found for {company}, falling back to DBT_TOKEN"
        )

    return token


def resolve_jdbc_url(member_email: str = None) -> str:
    """
    Resolve JDBC URL with company-specific token based on member email.

    Args:
        member_email: Email address to determine which company token to use
    """
    try:
        jdbc_url = st.secrets["JDBC_URL"]
    except Exception:
        # Determine which token to use based on member email
        if member_email:
            company = get_company_from_email(member_email)
            token = get_company_token(company)
            logger.info(
                "Using company-specific token company=%s email=%s token=%s",
                company,
                member_email,
                _mask_token(token),
            )
        else:
            # Fallback to generic token for initial connection
            token = os.getenv("DBT_TOKEN", "").strip()
            logger.info("Using default token for initial connection")

        if not token:
            logger.warning("No JDBC source available; service token missing from environment")
            return ""

        env_id = os.getenv("DBT_PROD_ENV_ID", "").strip() or "384973"
        host = os.getenv("DBT_SL_HOST", "").strip() or "semantic-layer.cloud.getdbt.com"
        jdbc_url = (
            "jdbc:arrow-flight-sql://"
            f"{host}:443?environmentId={env_id}&token={token}"
        )
        logger.info(
            "Resolved JDBC URL from environment host=%s env_id=%s token=%s",
            host,
            env_id,
            _mask_token(token),
        )
    else:
        parsed = urlparse(jdbc_url)
        logger.info(
            "Resolved JDBC URL from secrets scheme=%s path=%s has_query=%s",
            parsed.scheme,
            parsed.path,
            bool(parsed.query),
        )
    return jdbc_url


def ensure_connection(force_refresh: bool = False, member_email: str = None) -> ConnAttr:
    """
    Ensure connection to dbt Semantic Layer with company-specific token.

    Args:
        force_refresh: Force refresh the connection
        member_email: Email to determine which company token to use
    """
    # Get member email from session state if not provided
    if not member_email:
        member_email = st.session_state.get("selected_member_email")

    jdbc_url = resolve_jdbc_url(member_email)
    if not jdbc_url:
        st.error(
            "JDBC connection details are not configured. Set `JDBC_URL` in `.streamlit/secrets.toml` or provide service tokens in your environment/.env file."
        )
        st.stop()

    # Force refresh if member email changed (switching companies)
    current_member = st.session_state.get("_conn_member_email")
    if member_email and current_member != member_email:
        logger.info(f"Member changed from {current_member} to {member_email}, refreshing connection")
        force_refresh = True
        st.session_state._conn_member_email = member_email

    if force_refresh or st.session_state.get("jdbc_url") != jdbc_url:
        st.session_state.jdbc_url = jdbc_url
        try:
            get_connection_attributes.clear()
        except AttributeError:
            st.cache_data.clear()

    if force_refresh or "conn" not in st.session_state or st.session_state.conn is None:
        conn = get_connection_attributes(jdbc_url)
        if conn is None:
            st.error("Unable to initialize the Semantic Layer connection.")
            st.stop()
        st.session_state.conn = conn

    return st.session_state.conn


def submit_request(
    _conn_attr: ConnAttr,
    payload: Dict,
    source: str = None,
    host_override: str = None,
    path: str = "/api/graphql",
) -> Dict:
    # TODO: This should take into account multi-region and single-tenant
    url = f"{host_override or _conn_attr.host}{path}"
    logger.info(
        "Submitting GraphQL request url=%s has_variables=%s snippet=%s",
        url,
        "variables" in payload,
        payload.get("query", "")[:120].replace("\n", " "),
    )
    if "variables" not in payload:
        payload["variables"] = {}
    payload["variables"]["environmentId"] = _conn_attr.params["environmentid"]
    r = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": _conn_attr.auth_header,
            "x-dbt-partner-source": source or "streamlit",
        },
    )
    logger.info("Received response status=%s ok=%s", r.status_code, r.ok)
    if not r.ok:
        logger.error(
            "GraphQL request failed status=%s body=%s",
            r.status_code,
            r.text[:500],
        )
    return r.json()


@st.cache_data
def get_connection_attributes(uri):
    """Helper function to convert the JDBC url into ConnAttr."""
    parsed = urlparse(uri)
    logger.info(
        "Parsing JDBC URL scheme=%s netloc=%s path=%s query=%s",
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.query,
    )
    params = {k.lower(): v[0] for k, v in parse_qs(parsed.query).items()}
    logger.info("Extracted JDBC query params keys=%s", list(params.keys()))
    try:
        token = params.pop("token")
    except KeyError:
        st.error("Token is missing from the JDBC URL.")
        logger.error("Token missing from JDBC URL; cannot create connection attributes")
    else:
        host = parsed.path.replace("arrow-flight-sql", "https").replace(":443", "")
        auth_header = f"Bearer {token}"
        conn_attr = ConnAttr(host=host, params=params, auth_header=auth_header)
        logger.info(
            "Constructed connection attributes host=%s params=%s token=%s",
            conn_attr.host,
            conn_attr.params,
            _mask_token(token),
        )
        return conn_attr


@st.cache_data(show_spinner=False)
def get_query_results(
    payload: Dict,
    source: str = None,
    key: str = "createQuery",
    progress: bool = True,
    conn: ConnAttr = None,
):
    conn = conn or st.session_state.conn
    if progress:
        progress_bar = st.progress(0, "Submitting Query ... ")
    json = submit_request(conn, payload, source=source)
    try:
        query_id = json["data"][key]["queryId"]
    except TypeError:
        if progress:
            progress_bar.progress(80, "Query Failed!")
        error_msg = json.get("errors", [{}])[0].get("message", "Unknown error")
        logger.error("GraphQL create query failed response=%s", json)
        st.error(error_msg)
        st.stop()
    while True:
        graphql_query = GRAPHQL_QUERIES["get_results"]
        results_payload = {"variables": {"queryId": query_id}, "query": graphql_query}
        json = submit_request(conn, results_payload)
        try:
            data = json["data"]["query"]
        except TypeError:
            if progress:
                progress_bar.progress(80, "Query Failed!")
            error_msg = json.get("errors", [{}])[0].get("message", "Unknown error")
            logger.error(
                "GraphQL query polling failed query_id=%s response=%s",
                query_id,
                json,
            )
            st.error(error_msg)
            st.stop()
        else:
            status = data["status"].lower()
            if status == "successful":
                if progress:
                    progress_bar.progress(100, "Query Successful!")
                break
            elif status == "failed":
                if progress:
                    progress_bar.progress(
                        (RESULT_STATUSES.index(status) + 1) * 20, "red:Query Failed!"
                    )
                logger.error(
                    "Semantic Layer query failed query_id=%s error=%s sql=%s",
                    query_id,
                    data.get("error"),
                    data.get("sql"),
                )
                st.error(data["error"])
                st.stop()
            else:
                if progress:
                    progress_bar.progress(
                        (RESULT_STATUSES.index(status) + 1) * 20,
                        f"Query is {status.capitalize()}...",
                    )

    return data
