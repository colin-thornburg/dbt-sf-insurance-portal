# stdlib
import logging
from typing import Dict, Optional, Sequence, Tuple

# third party
import pandas as pd
import streamlit as st

# first party
from audit_logger import log_query_execution
from client import ensure_connection, get_query_results
from helpers import (
    ensure_member_context,
    get_portal_title,
    to_arrow_table,
)
from schema import Query
from styles import apply_glassmorphic_theme

st.set_page_config(
    page_title="AI Benefits Portal - Member Dashboard",
    page_icon="📊",
    layout="wide",
)

# Rename the sidebar label from "app" to "Authentication"
st.markdown("""
<style>
    [data-testid="stSidebarNav"] ul li:first-child a span {
        display: none;
    }
    [data-testid="stSidebarNav"] ul li:first-child a::before {
        content: "🔐 Authentication";
        margin-left: 0;
    }
    [data-testid="stSidebarNav"] ul li:first-child a {
        padding-left: 1rem;
    }
</style>
""", unsafe_allow_html=True)

logger = logging.getLogger("member_dashboard")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

conn = ensure_connection()


def member_filter(member_row: pd.Series) -> str:
    email = member_row.get("email")
    if not email:
        raise ValueError("Selected member does not include an email to filter on.")
    return f"{{{{ Dimension('member__email') }}}} = '{email}'"


def simplify_column(name: str) -> str:
    parts = [
        p
        for p in name.lower().split("__")
        if p not in {"member_claims", "member_details", "member", "members", "claim", "claims"}
    ]
    simple = "_".join(parts) if parts else name.lower()
    if simple.endswith("_day"):
        simple = simple[: -len("_day")]
    return simple


@st.cache_data(show_spinner=False)
def run_member_query(
    metrics: Tuple[str, ...],
    *,
    group_by: Sequence[Tuple[str, Optional[str]]] = (),
    where: Sequence[str] = (),
    limit: Optional[int] = None,
    _member_email: Optional[str] = None,
) -> pd.DataFrame:
    query_kwargs: Dict[str, object] = {
        "metrics": [{"name": metric} for metric in metrics],
    }

    if group_by:
        query_kwargs["groupBy"] = [
            {"name": name, "grain": grain.upper() if grain else None}
            for name, grain in group_by
        ]

    if where:
        query_kwargs["where"] = [{"sql": clause} for clause in where]

    if limit is not None:
        query_kwargs["limit"] = limit

    logger.info(
        "Executing member query metrics=%s group_by=%s where=%s limit=%s",
        metrics,
        group_by,
        where,
        limit,
    )

    status = "success"
    error_msg = None
    df = pd.DataFrame()

    try:
        gql_query = Query(**query_kwargs)
        payload = {"query": gql_query.gql, "variables": gql_query.variables}
        data = get_query_results(payload, progress=False, conn=conn)
        arrow_bytes = data.get("arrowResult")
        if not arrow_bytes:
            df = pd.DataFrame()
        else:
            df = to_arrow_table(arrow_bytes)
            if not df.empty:
                df.columns = [simplify_column(col) for col in df.columns]
    except Exception as e:
        status = "failed"
        error_msg = str(e)
        logger.error(f"Query failed: {e}")
        raise
    finally:
        # Log audit event (only if member_email is provided)
        if _member_email:
            log_query_execution(
                query_type="member_dashboard",
                member_email=_member_email,
                filters_applied=list(where),
                metrics=list(metrics),
                dimensions=[f"{name}__{grain}" if grain else name for name, grain in group_by],
                row_count=len(df) if not df.empty else 0,
                status=status,
                error_message=error_msg,
                page="Member Dashboard",
            )

    return df


def get_member_summary(filter_clause: str, member_email: str) -> Dict[str, float]:
    summary = {
        "ytd_member_responsibility": 0.0,
        "total_paid_by_insurance": 0.0,
        "total_claim_amount": 0.0,
        "total_claims_count": 0,
    }
    metrics_df = run_member_query(
        (
            "ytd_member_responsibility",
            "total_paid_by_insurance",
            "total_claim_amount",
            "total_claims_count",
        ),
        where=(filter_clause,),
        _member_email=member_email,
    )
    if not metrics_df.empty:
        row = metrics_df.iloc[0]
        summary["ytd_member_responsibility"] = float(
            row.get("ytd_member_responsibility", 0.0) or 0.0
        )
        summary["total_paid_by_insurance"] = float(
            row.get("total_paid_by_insurance", 0.0) or 0.0
        )
        summary["total_claim_amount"] = float(row.get("total_claim_amount", 0.0) or 0.0)
        summary["total_claims_count"] = int(
            round(row.get("total_claims_count", 0) or 0)
        )
    return summary


def get_spend_timeseries(filter_clause: str, member_email: str) -> pd.DataFrame:
    df = run_member_query(
        ("ytd_member_responsibility", "total_paid_by_insurance"),
        group_by=(("claim__claim_date", "DAY"),),
        where=(filter_clause,),
        _member_email=member_email,
    )
    if not df.empty and "claim_date" in df.columns:
        df["claim_date"] = pd.to_datetime(df["claim_date"])
        df = df.sort_values("claim_date")
    return df


def get_claims_by_type(filter_clause: str, member_email: str) -> pd.DataFrame:
    df = run_member_query(
        ("total_claims_count",),
        group_by=(("claim__claim_type", None),),
        where=(filter_clause,),
        _member_email=member_email,
    )
    if not df.empty:
        df = df.rename(columns={"total_claims_count": "total_claims"})
        df = df.sort_values("total_claims", ascending=False)
    return df


def get_provider_breakdown(filter_clause: str, member_email: str) -> pd.DataFrame:
    df = run_member_query(
        (
            "total_member_responsibility",
            "total_paid_by_insurance",
            "total_claim_amount",
        ),
        group_by=(("claim__provider_name", None),),
        where=(filter_clause,),
        _member_email=member_email,
    )
    if not df.empty:
        df = df.rename(columns={
            "provider_name": "provider",
            "total_member_responsibility": "member_responsibility",
            "total_paid_by_insurance": "insurance_paid",
            "total_claim_amount": "claim_amount",
        })
        df = df.sort_values("insurance_paid", ascending=False)
    return df


def get_claim_status_breakdown(filter_clause: str, member_email: str) -> pd.DataFrame:
    df = run_member_query(
        ("total_claims_count",),
        group_by=(("claim__claim_status", None),),
        where=(filter_clause,),
        _member_email=member_email,
    )
    if not df.empty:
        df = df.rename(columns={"claim_status": "status", "total_claims_count": "total_claims"})
        df = df.sort_values("total_claims", ascending=False)
    return df


def format_currency(value: float) -> str:
    return f"${value:,.0f}"


current_member = ensure_member_context()
company_name = current_member.get("company_display")
portal_title = get_portal_title(company_name)

# Apply glassmorphic theme with company-specific colors
apply_glassmorphic_theme(company_name)

current_member_email = current_member.get("email", "")
member_name = (
    f"{current_member.get('first_name', '').strip()} {current_member.get('last_name', '').strip()}"
    .strip()
    or "Member"
)

st.sidebar.caption(
    f"{portal_title} · {member_name} ({current_member_email or 'No email on file'})"
)
st.sidebar.write("Switch members from the Authentication page to view a different member context.")

st.title(f"{portal_title} · Member Dashboard")
st.markdown(f"""
**Current Member:** {member_name} ({current_member_email or 'No email'})

Personalized claims, spend, and provider insights powered by the dbt Semantic Layer.
""")

st.info(
    "💡 This dashboard stays in lock-step with the member context you choose on the Authentication page. "
    "Every visualization is generated with row-level filters ensuring you only see your data."
)

try:
    member_filter_clause = member_filter(current_member)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

member_summary = get_member_summary(member_filter_clause, current_member_email)

details_col, metrics_col = st.columns([1, 1.5])

with details_col:
    st.subheader("Member Profile")

    def _fmt(value, fallback="—"):
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return fallback
        if isinstance(value, str) and value.strip() == "":
            return fallback
        return value

    member_id_value = current_member.get("member_id")
    if pd.notna(member_id_value):
        try:
            member_id_value = int(member_id_value)
        except (TypeError, ValueError):
            member_id_value = _fmt(member_id_value)
    else:
        member_id_value = "—"

    detail_rows = {
        "Name": f"{current_member.get('first_name', '')} {current_member.get('last_name', '')}".strip(),
        "Email": current_member.get("email", "—"),
        "Member ID": member_id_value,
        "Company": _fmt(current_member.get("company_display", current_member.get("company_name"))),
        "Employee ID": _fmt(current_member.get("employee_id")),
        "Plan ID": _fmt(current_member.get("plan_id")),
        "Department": _fmt(current_member.get("department", "")),
        "Primary?": "Yes"
        if str(current_member.get("is_primary", "")).upper() == "TRUE"
        else "No",
        "Dependent Of": _fmt(current_member.get("dependent_of", "")),
        "Enrollment Date": _fmt(current_member.get("enrollment_date", "")),
    }
    profile_df = pd.DataFrame(detail_rows.items(), columns=["Field", "Value"])
    profile_df["Field"] = profile_df["Field"].astype(str)
    profile_df["Value"] = profile_df["Value"].apply(
        lambda x: "—"
        if x is None
        else ("—" if isinstance(x, float) and pd.isna(x) else str(x))
    )
    st.dataframe(profile_df, hide_index=True, use_container_width=True)

with metrics_col:
    st.subheader("Year-to-Date Metrics")
    metric_cols = st.columns(4)
    metric_cols[0].metric(
        "YTD Member Responsibility",
        format_currency(member_summary["ytd_member_responsibility"]),
    )
    metric_cols[1].metric(
        "Insurance Paid",
        format_currency(member_summary["total_paid_by_insurance"]),
    )
    metric_cols[2].metric(
        "Total Claim Amount",
        format_currency(member_summary["total_claim_amount"]),
    )
    metric_cols[3].metric(
        "Total Claims",
        f"{member_summary['total_claims_count']:,}",
    )

spend_ts = get_spend_timeseries(member_filter_clause, current_member_email)
st.subheader("Spend Over Time")
if spend_ts.empty:
    st.info("No claim activity available for this member yet.")
else:
    chart_df = spend_ts.set_index("claim_date")[
        [
            col
            for col in ["ytd_member_responsibility", "total_paid_by_insurance"]
            if col in spend_ts
        ]
    ]
    st.line_chart(chart_df)

claim_type_df = get_claims_by_type(member_filter_clause, current_member_email)
st.subheader("Claims by Type")
if claim_type_df.empty:
    st.info("No claims by type to display.")
else:
    st.bar_chart(claim_type_df.set_index("claim_type")["total_claims"])

provider_df = get_provider_breakdown(member_filter_clause, current_member_email)
st.subheader("Top Providers")
if provider_df.empty:
    st.info("No provider activity for this member.")
else:
    st.dataframe(
        provider_df.head(5),
        use_container_width=True,
        hide_index=True,
        column_config={
            "member_responsibility": st.column_config.NumberColumn(
                "Member Responsibility", format="$%,.0f"
            ),
            "insurance_paid": st.column_config.NumberColumn(
                "Insurance Paid", format="$%,.0f"
            ),
            "claim_amount": st.column_config.NumberColumn(
                "Claim Amount", format="$%,.0f"
            ),
        },
    )

status_df = get_claim_status_breakdown(member_filter_clause, current_member_email)
st.subheader("Claim Status Overview")
if status_df.empty:
    st.info("No claim status information available.")
else:
    st.dataframe(status_df, use_container_width=True, hide_index=True)

st.divider()

st.subheader("How the Member Filter Works")

st.write(
    """
Protecting member privacy means every query must be scoped before it ever reaches the Semantic Layer.
This dashboard enforces the member filter in two deterministic steps:

1. `member_filter()` (top of this file) builds a SQL clause from the selected member's email and
   raises immediately if the email is missing.
2. Every helper that calls the Semantic Layer (`run_member_query`) injects that clause into the `where`
   argument so only user-scoped queries are executed.

Because the clause is generated from a locked session context, members cannot alter it through the UI,
and every downstream query shares the same guardrail. Below is the exact clause this demo applies:
"""
)

st.code(
    """
member_filter_clause = member_filter(current_member)
member_summary = get_member_summary(member_filter_clause)
spend_ts = get_spend_timeseries(member_filter_clause)
    """,
    language="python",
)

basic_filter, full_filter = st.tabs(["Filter clause", "SDK example"])
basic_filter.code(
    body="""
user_filter = {"sql": f"{{ Dimension('member__email') }} = '{member_email}'"}
    """,
    language="python",
)
full_filter.code(
    body="""
from dbtsl import SemanticLayerClient

client = SemanticLayerClient(
    environment_id=ENV_ID,
    auth_token=SERVICE_TOKEN,
    host="semantic-layer.cloud.getdbt.com",
)

member_email = "bob.johnson@techcorp.com"
where = [f"{{ Dimension('member__email') }} = '{member_email}'"]

with client.session():
    claims = client.query(
        metrics=["ytd_member_responsibility", "total_paid_by_insurance"],
        group_by=["claim__claim_date__day"],
        where=where,
        order_by=["claim__claim_date__day"],
    )

claims_df = claims.to_pandas()
    """,
    language="python",
    line_numbers=True,
)

st.write(
    """
You can extend the same pattern to support company-level or broker-level views:
"""
)

company_filters, company_sdk = st.tabs(["Company filter", "SDK example"])
company_filters.code(
    body="""
company_filter = {"sql": "{{ Dimension('claim__company_id') }} = 1001"}
    """,
    language="python",
)
company_sdk.code(
    body="""
with client.session():
    company_summary = client.query(
        metrics=["total_claims_count"],
        group_by=["claim__claim_status"],
        where=["{{ Dimension('claim__company_id') }} = 1001"],
    )
    """,
    language="python",
    line_numbers=True,
)

st.write(
    """
With governed metrics, reusable filters, and caching built into the Semantic Layer, the member
dashboard stays consistent and performant across every downstream experience.
"""
)
