# stdlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

# third party
import pandas as pd
import streamlit as st


def init_audit_log():
    """Initialize the audit log in session state if it doesn't exist."""
    if "audit_log" not in st.session_state:
        st.session_state.audit_log = []


def log_query_execution(
    query_type: str,
    member_email: str,
    filters_applied: List[str],
    metrics: List[str],
    dimensions: Optional[List[str]] = None,
    row_count: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    page: Optional[str] = None,
) -> None:
    """
    Log a query execution event to the audit log.

    Args:
        query_type: Type of query (e.g., 'member_dashboard', 'llm_query', 'query_builder')
        member_email: Email of the member context being queried
        filters_applied: List of WHERE clause filters applied to the query
        metrics: List of metrics queried
        dimensions: Optional list of dimensions/group_by used
        row_count: Number of rows returned
        status: Query status ('success' or 'failed')
        error_message: Error message if status is 'failed'
        page: Page/tab where query was executed
    """
    init_audit_log()

    audit_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "query_type": query_type,
        "member_email": member_email,
        "filters_applied": filters_applied,
        "metrics": metrics,
        "dimensions": dimensions or [],
        "row_count": row_count,
        "status": status,
        "error_message": error_message,
        "page": page or "unknown",
        "session_id": id(st.session_state),  # Simple session identifier
    }

    st.session_state.audit_log.append(audit_entry)


def get_audit_log() -> pd.DataFrame:
    """
    Retrieve the audit log as a pandas DataFrame.

    Returns:
        DataFrame with all audit log entries
    """
    init_audit_log()

    if not st.session_state.audit_log:
        return pd.DataFrame()

    df = pd.DataFrame(st.session_state.audit_log)

    # Convert timestamp to datetime
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])

    return df


def get_audit_stats() -> Dict[str, Any]:
    """
    Get summary statistics from the audit log.

    Returns:
        Dictionary with audit statistics
    """
    init_audit_log()

    df = get_audit_log()

    if df.empty:
        return {
            "total_queries": 0,
            "unique_members": 0,
            "success_rate": 0.0,
            "queries_by_type": {},
            "queries_by_page": {},
        }

    stats = {
        "total_queries": len(df),
        "unique_members": df["member_email"].nunique(),
        "success_rate": (df["status"] == "success").mean() * 100,
        "queries_by_type": df["query_type"].value_counts().to_dict(),
        "queries_by_page": df["page"].value_counts().to_dict(),
    }

    return stats


def validate_filter_applied(member_email: str, filters_applied: List[str]) -> bool:
    """
    Validate that the correct member filter was applied to the query.

    Args:
        member_email: Email that should be in the filter
        filters_applied: List of filter clauses

    Returns:
        True if the member email filter is present, False otherwise
    """
    if not filters_applied:
        return False

    # Check if any filter contains the member email
    return any(member_email in filter_clause for filter_clause in filters_applied)


def get_security_violations() -> pd.DataFrame:
    """
    Identify potential security violations (queries without proper filters).

    Returns:
        DataFrame of queries that may not have proper member filters
    """
    df = get_audit_log()

    if df.empty:
        return pd.DataFrame()

    # Flag queries where filters might be missing or incorrect
    violations = []
    for _, row in df.iterrows():
        filters_applied = row.get("filters_applied", [])
        member_email = row.get("member_email", "")

        if not validate_filter_applied(member_email, filters_applied):
            violations.append(row.to_dict())

    return pd.DataFrame(violations) if violations else pd.DataFrame()


def clear_audit_log() -> None:
    """Clear all entries from the audit log."""
    st.session_state.audit_log = []
