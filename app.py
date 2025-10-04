# third party
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# first party
from audit_logger import get_audit_stats, init_audit_log
from helpers import (
    ensure_member_context,
    get_member_roster,
    get_portal_title,
    set_member_context,
)
from init_app import initialize_app
from styles import apply_glassmorphic_theme


st.set_page_config(
    page_title="AI Benefits Portal - Authentication",
    page_icon="🛡️",
    layout="wide",
)

# Apply theme IMMEDIATELY to prevent flash of unstyled content
# We'll apply a default theme first, then update with company-specific colors later
initialize_app(show_spinner=True)

# Get member context early to determine company theme
member_roster = get_member_roster()
if not member_roster.empty:
    # Try to get company from current member context if it exists
    if st.session_state.get("current_member"):
        company_name = st.session_state.current_member.get("company_display")
    else:
        # Default to first member's company for initial theme
        company_name = member_roster.iloc[0].get("company_display")
    
    # Apply theme FIRST, before any content
    apply_glassmorphic_theme(company_name)
else:
    # Apply default theme if no members
    apply_glassmorphic_theme(None)

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

if "metric_dict" in st.session_state and st.session_state.metric_dict:
    st.success("Connected to the dbt Semantic Layer. Metrics are ready to use.")

# member_roster was already loaded earlier for theme application
if member_roster.empty:
    st.stop()

options = member_roster["display_name"].tolist()
default_index = 0
if st.session_state.get("selected_member_display") in options:
    default_index = options.index(st.session_state.selected_member_display)

selected_display = st.selectbox(
    label="Select a member context",
    options=options,
    index=default_index,
)

if selected_display != st.session_state.get("selected_member_display"):
    selected_row = member_roster.loc[
        member_roster["display_name"] == selected_display
    ].iloc[0]
    set_member_context(selected_row)
    current_member = pd.Series(st.session_state.current_member)
    # Re-apply theme with new company context
    company_name = current_member.get("company_display")
    apply_glassmorphic_theme(company_name)
else:
    current_member = ensure_member_context()
    company_name = current_member.get("company_display")

portal_title = get_portal_title(company_name)

st.title(portal_title)
st.markdown(
    """
    Use this portal to explore governed metrics from the dbt Semantic Layer. All downstream experiences automatically inherit the member context you select here.
    """
)

st.caption(
    "All experiences (LLM, Embedded Analytics) are automatically filtered to the member selected above."
)

profile_fields = {
    "Member": f"{current_member['first_name']} {current_member['last_name']}",
    "Email": current_member["email"],
    "Member ID": current_member.get("member_id", "—"),
    "Company": current_member.get("company_display", current_member.get("company_name", "—")),
    "Department": current_member.get("department", "—"),
    "Plan Type": current_member.get("plan_type", "—"),
}

profile_df = pd.DataFrame(profile_fields.items(), columns=["Field", "Value"])
profile_df["Field"] = profile_df["Field"].astype(str)
profile_df["Value"] = profile_df["Value"].apply(
    lambda x: "—"
    if x is None
    else ("—" if isinstance(x, float) and pd.isna(x) else str(x))
)
st.dataframe(profile_df, hide_index=True, use_container_width=True)

# Show security context
with st.expander("🔐 Security Context", expanded=False):
    from client import get_company_from_email, get_company_token, _mask_token

    member_email = current_member.get("email", "")
    company = get_company_from_email(member_email)
    token = get_company_token(company)

    st.markdown("**Company-Specific Service Token**")
    st.markdown(f"- **Email Domain**: `{member_email.split('@')[-1] if '@' in member_email else 'N/A'}`")
    st.markdown(f"- **Mapped Company**: `{company.title()}`")
    st.markdown(f"- **Service Token**: `{_mask_token(token)}`")
    st.markdown(f"- **Environment Variable**: `DBT_{company.upper()}_TOKEN`")

    st.info(
        "💡 Each company has its own service token. When you switch members, "
        "the app automatically uses the appropriate token based on email domain. "
        "This provides an additional security layer beyond row-level filters."
    )

st.markdown(
    """
    ---
    **👈 Select a page from the sidebar** to explore the Semantic Layer.
"""
)

# Show audit log summary
init_audit_log()
audit_stats = get_audit_stats()

if audit_stats["total_queries"] > 0:
    st.divider()
    st.subheader("📊 Session Activity")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Queries", audit_stats["total_queries"])
    col2.metric("Unique Members Queried", audit_stats["unique_members"])
    col3.metric("Success Rate", f"{audit_stats['success_rate']:.1f}%")

    st.caption("View detailed audit logs in the 🔍 Audit Log page")
