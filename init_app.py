"""
Shared initialization logic for the Streamlit app.
This ensures metrics and connection are loaded regardless of which page the user visits first.
"""

import streamlit as st
from client import ensure_connection, submit_request
from llm.semantic_layer_docs import create_chroma_db
from queries import GRAPHQL_QUERIES


def retrieve_saved_queries():
    """Fetch saved queries from the Semantic Layer."""
    payload = {"query": GRAPHQL_QUERIES["saved_queries"]}
    json_data = submit_request(st.session_state.conn, payload)
    saved_queries = json_data.get("data", {}).get("savedQueries", [])
    if saved_queries:
        st.session_state.saved_queries = saved_queries


def retrieve_account_id():
    """Fetch account and project IDs from the Semantic Layer."""
    from helpers import url_for_disco

    payload = {"query": GRAPHQL_QUERIES["account"], "variables": {"first": 1}}
    host = url_for_disco()

    try:
        json_data = submit_request(
            st.session_state.conn, payload, host_override=host, path="/beta/graphql"
        )
    except Exception as e:
        print(f"Error running disco API query for {host}; {e}")
    else:
        try:
            edges = (
                json_data.get("data", {})
                .get("environment", {})
                .get("applied", {})
                .get("models", {})
                .get("edges", [])
            )
        except AttributeError:
            pass
        else:
            if edges:
                st.session_state.account_id = edges[0]["node"]["accountId"]
                st.session_state.project_id = edges[0]["node"]["projectId"]


def initialize_app(show_spinner: bool = True):
    """
    Initialize the app by ensuring connection and loading metrics.
    This function is safe to call from any page.

    Args:
        show_spinner: Whether to show a loading spinner (default True)

    Returns:
        bool: True if initialization was successful, False otherwise
    """
    # Ensure connection is established
    ensure_connection()

    # Check if metrics are already loaded
    if "metric_dict" in st.session_state and "dimension_dict" in st.session_state:
        return True

    # Load metrics from Semantic Layer
    spinner_text = "Gathering Metrics..." if show_spinner else None

    if show_spinner:
        with st.spinner(spinner_text):
            return _load_metrics()
    else:
        return _load_metrics()


def _load_metrics():
    """Internal function to load metrics from the Semantic Layer."""
    payload = {"query": GRAPHQL_QUERIES["metrics"]}
    json = submit_request(st.session_state.conn, payload)

    try:
        metrics = json["data"]["metrics"]
    except TypeError:
        # `data` is None and there may be an error
        try:
            error = json["errors"][0]["message"]
            st.error(f"Error loading metrics: {error}")
        except (KeyError, TypeError):
            st.warning(
                "No metrics returned. Ensure your project has metrics defined "
                "and a production job has been run successfully."
            )
        return False
    else:
        # Create vector database for LLM usage
        create_chroma_db(metrics)

        # Store metrics in session state
        st.session_state.metric_dict = {m["name"]: m for m in metrics}
        st.session_state.dimension_dict = {
            dim["name"]: dim for metric in metrics for dim in metric["dimensions"]
        }

        # Flatten dimensions list for each metric
        for metric in st.session_state.metric_dict:
            st.session_state.metric_dict[metric]["dimensions"] = [
                d["name"]
                for d in st.session_state.metric_dict[metric]["dimensions"]
            ]

        if not st.session_state.metric_dict:
            st.warning(
                "No Metrics returned! Ensure your project has metrics defined "
                "and a production job has been run successfully."
            )
            return False
        else:
            # Load additional metadata
            retrieve_saved_queries()
            retrieve_account_id()
            return True
