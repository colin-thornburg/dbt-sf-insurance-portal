# stdlib
import json
from datetime import datetime, timedelta

# third party
import pandas as pd
import streamlit as st

# first party
from audit_logger import (
    clear_audit_log,
    get_audit_log,
    get_audit_stats,
    get_security_violations,
    init_audit_log,
    validate_filter_applied,
)
from helpers import (
    ensure_member_context,
    get_portal_title,
)
from styles import apply_glassmorphic_theme

st.set_page_config(
    page_title="AI Benefits Portal - Audit Log",
    page_icon="🔍",
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

init_audit_log()

current_member = ensure_member_context()
company_name = current_member.get("company_display")
portal_title = get_portal_title(company_name)

# Apply glassmorphic theme with company-specific colors
apply_glassmorphic_theme(company_name)

st.title(f"{portal_title} · Audit Log")

st.markdown(
    """
    This page displays all queries executed through the portal, showing which member context was used,
    what filters were applied, and whether the proper security filters were enforced.
    """
)

# Summary statistics
st.subheader("📊 Query Statistics")

stats = get_audit_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Queries", stats["total_queries"])
col2.metric("Unique Members", stats["unique_members"])
col3.metric("Success Rate", f"{stats['success_rate']:.1f}%")

# Check for security violations
violations_df = get_security_violations()
violation_count = len(violations_df)
col4.metric(
    "Security Violations",
    violation_count,
    delta=None if violation_count == 0 else f"⚠️ {violation_count} found",
    delta_color="inverse",
)

# Security violations section
if not violations_df.empty:
    st.subheader("⚠️ Security Violations Detected")
    st.error(
        f"Found {len(violations_df)} queries that may not have the proper member email filter applied!"
    )

    st.dataframe(
        violations_df[
            ["timestamp", "member_email", "query_type", "filters_applied", "metrics"]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD HH:mm:ss"),
            "member_email": "Member Email",
            "query_type": "Query Type",
            "filters_applied": st.column_config.ListColumn("Filters Applied"),
            "metrics": st.column_config.ListColumn("Metrics"),
        },
    )
else:
    st.success("✅ No security violations detected. All queries have proper member filters.")

# Full audit log
st.subheader("🔍 Full Audit Log")

audit_df = get_audit_log()

if audit_df.empty:
    st.info("No queries logged yet. Execute some queries from the Member Dashboard to see them here.")
else:
    # Filters
    col1, col2, col3 = st.columns(3)

    with col1:
        filter_member = st.multiselect(
            "Filter by Member Email",
            options=sorted(audit_df["member_email"].unique()),
            default=None,
        )

    with col2:
        filter_query_type = st.multiselect(
            "Filter by Query Type",
            options=sorted(audit_df["query_type"].unique()),
            default=None,
        )

    with col3:
        filter_status = st.multiselect(
            "Filter by Status",
            options=sorted(audit_df["status"].unique()),
            default=None,
        )

    # Apply filters
    filtered_df = audit_df.copy()

    if filter_member:
        filtered_df = filtered_df[filtered_df["member_email"].isin(filter_member)]

    if filter_query_type:
        filtered_df = filtered_df[filtered_df["query_type"].isin(filter_query_type)]

    if filter_status:
        filtered_df = filtered_df[filtered_df["status"].isin(filter_status)]

    st.caption(f"Showing {len(filtered_df)} of {len(audit_df)} queries")

    # Display audit log
    st.dataframe(
        filtered_df[
            [
                "timestamp",
                "member_email",
                "query_type",
                "page",
                "metrics",
                "filters_applied",
                "row_count",
                "status",
            ]
        ],
        use_container_width=True,
        hide_index=True,
        column_config={
            "timestamp": st.column_config.DatetimeColumn("Timestamp", format="YYYY-MM-DD HH:mm:ss"),
            "member_email": "Member Email",
            "query_type": "Query Type",
            "page": "Page",
            "metrics": st.column_config.ListColumn("Metrics Queried"),
            "filters_applied": st.column_config.ListColumn("Filters Applied"),
            "row_count": "Rows Returned",
            "status": "Status",
        },
    )

    # Detailed view expander
    st.subheader("📝 Query Details")

    if not filtered_df.empty:
        # Select a query to inspect
        selected_idx = st.selectbox(
            "Select a query to inspect",
            options=range(len(filtered_df)),
            format_func=lambda i: f"Query {i+1}: {filtered_df.iloc[i]['query_type']} at {filtered_df.iloc[i]['timestamp']}",
        )

        if selected_idx is not None:
            selected_query = filtered_df.iloc[selected_idx]

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**Query Information**")
                st.json({
                    "timestamp": str(selected_query["timestamp"]),
                    "query_type": selected_query["query_type"],
                    "page": selected_query["page"],
                    "member_email": selected_query["member_email"],
                    "status": selected_query["status"],
                    "row_count": int(selected_query["row_count"]) if pd.notna(selected_query["row_count"]) else None,
                })

            with col2:
                st.markdown("**Security Validation**")

                # Validate filter
                filters = selected_query["filters_applied"]
                member_email = selected_query["member_email"]

                filter_valid = validate_filter_applied(member_email, filters)

                if filter_valid:
                    st.success(f"✅ Correct filter applied: member email '{member_email}' found in filters")
                else:
                    st.error(f"⚠️ Security issue: member email '{member_email}' NOT found in filters!")

                st.markdown("**Filters Applied:**")
                if filters:
                    for f in filters:
                        st.code(f, language="sql")
                else:
                    st.warning("No filters applied to this query")

            st.markdown("**Metrics & Dimensions**")
            col3, col4 = st.columns(2)

            with col3:
                st.markdown("**Metrics:**")
                if selected_query["metrics"]:
                    for metric in selected_query["metrics"]:
                        st.markdown(f"- `{metric}`")
                else:
                    st.caption("None")

            with col4:
                st.markdown("**Dimensions:**")
                if selected_query["dimensions"] and selected_query["dimensions"]:
                    for dim in selected_query["dimensions"]:
                        st.markdown(f"- `{dim}`")
                else:
                    st.caption("None")

            if selected_query["error_message"]:
                st.error(f"**Error:** {selected_query['error_message']}")

# Actions
st.divider()

col1, col2 = st.columns([3, 1])

with col1:
    st.caption("Use the audit log to validate security filters and monitor query activity")

with col2:
    if st.button("🗑️ Clear Audit Log", type="secondary"):
        clear_audit_log()
        st.rerun()
