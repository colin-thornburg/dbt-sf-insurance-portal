# stdlib
import base64
import binascii
import json
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

# third party
import pandas as pd
import pyarrow as pa
import streamlit as st

# first party
from client import ConnAttr
from schema import Query


def keys_exist_in_dict(keys_list: Iterable[str], dct: Mapping[str, Any]) -> bool:
    return all(key in dct for key in keys_list)


MEMBER_ROSTER_PATH = Path(__file__).resolve().parent / "data" / "members.csv"
USER_FILTER_DIMENSION = "member__email"

COMPANY_ID_MAP = {
    1001: "TechCorp",
    1002: "RetailPlus",
    1003: "ManufacturingCo",
}

COMPANY_DOMAIN_MAP = {
    "techcorp.com": "TechCorp",
    "retailplus.com": "RetailPlus",
    "manufacturingco.com": "ManufacturingCo",
}

COMPANY_THEMES = {
    "TechCorp": {
        "font": "Inter",
        "primary": "#4F46E5",
        "primary_hover": "#4338CA",
        "bg_start": "#EEF2FF",
        "bg_end": "#FFFFFF",
        "sidebar_bg": "#111827",
        "sidebar_text": "#F9FAFB",
        "text": "#111827",
        "button_text": "#FFFFFF",
    },
    "RetailPlus": {
        "font": "Poppins",
        "primary": "#EA580C",
        "primary_hover": "#C2410C",
        "bg_start": "#FFF7ED",
        "bg_end": "#FFFFFF",
        "sidebar_bg": "#7F1D1D",
        "sidebar_text": "#FDE68A",
        "text": "#1F2937",
        "button_text": "#FFFFFF",
    },
    "ManufacturingCo": {
        "font": "Roboto",
        "primary": "#0EA5E9",
        "primary_hover": "#0284C7",
        "bg_start": "#ECFEFF",
        "bg_end": "#FFFFFF",
        "sidebar_bg": "#0F172A",
        "sidebar_text": "#E0F2FE",
        "text": "#0F172A",
        "button_text": "#FFFFFF",
    },
    "default": {
        "font": "Inter",
        "primary": "#2563EB",
        "primary_hover": "#1D4ED8",
        "bg_start": "#EFF6FF",
        "bg_end": "#FFFFFF",
        "sidebar_bg": "#1E293B",
        "sidebar_text": "#F8FAFC",
        "text": "#0F172A",
        "button_text": "#FFFFFF",
    },
}


def infer_company_name(member_row: pd.Series) -> Optional[str]:
    company = member_row.get("company_name")
    if isinstance(company, str) and company.strip():
        return company.strip()

    company_id = member_row.get("company_id")
    if pd.notna(company_id):
        company_id = int(company_id)
        if company_id in COMPANY_ID_MAP:
            return COMPANY_ID_MAP[company_id]

    email = member_row.get("email", "")
    if isinstance(email, str) and "@" in email:
        domain = email.split("@")[-1].lower()
        if domain in COMPANY_DOMAIN_MAP:
            return COMPANY_DOMAIN_MAP[domain]

    return None


def get_shared_elements(all_elements: Sequence[Sequence[Any]]) -> List[Any]:
    if not all_elements:
        return []

    shared = set(all_elements[0])
    for elements in all_elements[1:]:
        shared.intersection_update(elements)
        if not shared:
            break
    return list(shared)


@st.cache_data(show_spinner=False)
def get_member_roster() -> pd.DataFrame:
    try:
        df = pd.read_csv(MEMBER_ROSTER_PATH)
    except FileNotFoundError:
        st.error(
            "Member roster file not found. Ensure `data/members.csv` exists."
        )
        return pd.DataFrame()

    required_columns = {"first_name", "last_name", "email"}
    missing = required_columns.difference(df.columns)
    if missing:
        st.error(
            "Member roster is missing required columns: " + ", ".join(sorted(missing))
        )
        return pd.DataFrame()

    df["display_name"] = (
        df["first_name"].fillna("")
        + " "
        + df["last_name"].fillna("")
        + " · "
        + df["email"].fillna("")
    )
    return df.sort_values(["first_name", "last_name", "email"]).reset_index(drop=True)


def set_member_context(member_row: pd.Series) -> None:
    member_row = member_row.copy()
    company_display = infer_company_name(member_row)
    member_row["company_display"] = company_display

    st.session_state.selected_member_email = member_row.get("email")
    st.session_state.selected_member_display = member_row.get("display_name")
    st.session_state.selected_company_name = company_display
    st.session_state.current_member = member_row.to_dict()


def ensure_member_context() -> pd.Series:
    roster = get_member_roster()
    if roster.empty:
        st.error("No members available for selection.")
        st.stop()

    email = st.session_state.get("selected_member_email")
    if email:
        match = roster[roster["email"] == email]
        if not match.empty:
            member_row = match.iloc[0]
            set_member_context(member_row)
            return pd.Series(st.session_state.current_member)

    member_row = roster.iloc[0]
    set_member_context(member_row)
    return pd.Series(st.session_state.current_member)


def get_company_theme(company_name: Optional[str]) -> Dict[str, str]:
    if company_name and company_name in COMPANY_THEMES:
        return COMPANY_THEMES[company_name]
    return COMPANY_THEMES["default"]


def apply_portal_theme(company_name: Optional[str]) -> None:
    theme = get_company_theme(company_name)
    font_import = theme["font"].replace(" ", "+")
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family={font_import}:wght@400;500;600;700&display=swap');
        html, body, [class*="css"] {{
            font-family: '{theme['font']}', sans-serif;
            color: {theme['text']};
        }}
        div[data-testid="stAppViewContainer"] {{
            background: linear-gradient(160deg, {theme['bg_start']} 0%, {theme['bg_end']} 60%);
        }}
        div[data-testid="stSidebar"] {{
            background: {theme['sidebar_bg']};
            color: {theme['sidebar_text']};
        }}
        div[data-testid="stSidebar"] * {{
            color: {theme['sidebar_text']} !important;
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {theme['primary']};
            font-weight: 600;
        }}
        .stButton>button {{
            background-color: {theme['primary']};
            color: {theme['button_text']};
            border: none;
            border-radius: 999px;
            font-weight: 600;
            padding: 0.5rem 1.5rem;
        }}
        .stButton>button:hover {{
            background-color: {theme['primary_hover']};
            color: {theme['button_text']};
        }}
        .stTabs [data-baseweb="tab"] {{
            font-weight: 600;
            color: {theme['text']};
        }}
        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            color: {theme['primary']};
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner=False)
def load_plan_documents() -> Dict[str, str]:
    docs_dir = Path("docs/plan_details")
    documents: Dict[str, str] = {}
    if docs_dir.exists():
        for path in sorted(docs_dir.glob("*.md")):
            try:
                documents[path.stem.lower()] = path.read_text(encoding="utf-8")
            except OSError:
                continue
    return documents


def get_portal_title(company_name: Optional[str]) -> str:
    if company_name:
        return f"{company_name} Portal"
    return "Member Portal"


def to_arrow_table(byte_string: str, to_pandas: bool = True) -> pa.Table:
    with pa.ipc.open_stream(base64.b64decode(byte_string)) as reader:
        arrow_table = pa.Table.from_batches(reader, reader.schema)

    if to_pandas:
        return arrow_table.to_pandas()

    return arrow_table


def create_graphql_code(query: Query) -> str:
    return f"""
import requests


url = '{st.session_state.conn.host}/api/graphql'
query = \'\'\'{query.gql}\'\'\'
payload = {{'query': query, 'variables': {query.variables}}}
response = requests.post(url, json=payload, headers={{'Authorization': 'Bearer ***'}})
    """


def create_python_sdk_code(query: Query) -> str:
    arguments = query.sdk
    arguments_str = ",\n".join(
        [f"            {k}={v}" for k, v in arguments.items() if v]
    )
    return f"""
from dbtsl import SemanticLayerClient

client = SemanticLayerClient(
    environment_id={st.session_state.conn.params['environmentid']},
    auth_token="<your-semantic-layer-api-token>",
    host="{st.session_state.conn.host.replace('https://', '')}",
)

def main():
    with client.session():
        table = client.query(\n{arguments_str}\n        )
        print(table)
        
main()
"""


def convert_df(df, to="to_csv", index=False):
    return getattr(df, to)(index=index).encode("utf8")


def create_explorer_link(query):
    if "account_id" in st.session_state:
        _, col2 = st.columns([4, 1.5])
        url = url_for_explorer(query.metric_names)
        col2.page_link(url, label="View from dbt Explorer", icon="🕵️")


def create_tabs(state: st.session_state, suffix: str) -> None:
    keys = ["query", "df", "compiled_sql"]
    keys_with_suffix = [f"{key}_{suffix}" for key in keys]
    if all(key in state for key in keys_with_suffix):
        sql = getattr(state, f"compiled_sql_{suffix}")
        df = getattr(state, f"df_{suffix}")
        query = getattr(state, f"query_{suffix}")
        tab1, tab2 = st.tabs(["📊 Data", "💻 SQL"])
        with tab1:
            st.dataframe(df, use_container_width=True)
        with tab2:
            st.code(sql, language="sql")
        create_explorer_link(query)


def encode_dictionary(data: Mapping[str, Any]) -> str:
    """Serialize a mapping to a base64 encoded JSON string."""

    json_bytes = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.b64encode(json_bytes).decode("ascii")


def _coerce_single_value(value: Sequence[str] | str | None) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value[0] if value else None


def decode_string(value: Sequence[str] | str | None) -> Optional[Dict[str, Any]]:
    """Decode a base64 encoded JSON payload into a dictionary."""

    encoded = _coerce_single_value(value)
    if not encoded:
        return None

    try:
        json_bytes = base64.b64decode(encoded.encode("utf-8"), validate=True)
    except (AttributeError, binascii.Error):
        return None

    try:
        return json.loads(json_bytes.decode("utf-8"))
    except json.JSONDecodeError:
        return None


def set_context_query_param(params: Sequence[str]) -> None:
    d = {k: st.session_state[k] for k in params if k in st.session_state}
    encoded = encode_dictionary(d)
    st.query_params = {"context": encoded}


def retrieve_context_query_param() -> Optional[Dict[str, Any]]:
    context = st.query_params.get("context", None)
    return decode_string(context)


def get_access_url(conn: ConnAttr = None):
    if conn is None:
        conn = st.session_state.conn

    if conn.host.endswith(".semantic-layer"):
        host = conn.host.replace(".semantic-layer", "")
    elif conn.host.startswith("https://semantic-layer."):
        host = conn.host.replace("https://semantic-layer.", "https://")
    else:
        host = conn.host.replace(".semantic-layer.", ".")

    return host


def url_for_disco(conn: ConnAttr = None):
    access_url = get_access_url(conn)
    netloc = urllib.parse.urlparse(access_url).netloc
    netloc_split = netloc.split(".")
    if "us1" in netloc_split or "us2" in netloc_split:
        account_prefix = netloc_split[0]
        the_rest = ".".join(netloc_split[1:])
        host = f"https://{account_prefix}.metadata.{the_rest}"
    else:
        host = f"https://metadata.{netloc}"
    return host


def url_for_explorer(metrics: List[str], *, conn: ConnAttr = None):
    if "account_id" not in st.session_state or "project_id" not in st.session_state:
        return

    metric_string = " ".join(f"+metric:{metric}" for metric in metrics)
    encoded_param = urllib.parse.quote_plus(metric_string)
    account_id = st.session_state.account_id
    project_id = st.session_state.project_id
    host = get_access_url(conn)
    full_url = f"{host}/explore/{account_id}/projects/{project_id}/environments/production/lineage/?select={encoded_param}"
    return full_url


def construct_cli_command(query: Query):
    metrics = ",".join(query.metric_names)
    group_by = ",".join(query.dimension_names)
    command = f"dbt sl query --metrics {metrics}"

    if group_by:
        command += f" --group-by {group_by}"

    if query.where:
        where_str = " AND ".join([w.sql for w in query.where])
        command += f' --where "{where_str}"'

    if query.limit:
        command += f" --limit {query.limit}"

    if query.orderBy:
        order_by_inputs = []
        for order_by_input in query.orderBy:
            if order_by_input.metric:
                col = order_by_input.metric.name
            else:
                col = order_by_input.groupBy.name
                if order_by_input.groupBy.grain:
                    col += f"__{order_by_input.groupBy.grain}"
            if order_by_input.descending:
                col = f"-{col}"
            order_by_inputs.append(col)

        order_by = ",".join(order_by_inputs)
        command += f" --order-by {order_by}"

    return command
