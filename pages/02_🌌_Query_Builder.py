# stdlib
from datetime import datetime, timedelta
from typing import Dict, List

# third party
import streamlit as st

# first party
from client import ensure_connection, get_query_results
from helpers import (
    USER_FILTER_DIMENSION,
    construct_cli_command,
    create_graphql_code,
    create_python_sdk_code,
    create_tabs,
    ensure_member_context,
    get_portal_title,
    get_shared_elements,
    to_arrow_table,
)
from styles import apply_glassmorphic_theme
from queries import GRAPHQL_QUERIES
from schema import Query, QueryLoader, WhereInput

st.set_page_config(
    page_title="AI Benefits Portal - Query Builder",
    page_icon="🌌",
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

ensure_connection()

if "metric_dict" not in st.session_state:
    st.warning(
        "No metrics found.  Ensure your project has metrics defined and a production "
        "job has been run successfully."
    )
    st.stop()

current_member = ensure_member_context()
current_member_email = current_member.get("email")
if not current_member_email:
    st.error("Selected member does not have an email address configured.")
    st.stop()

USER_FILTER_SQL = f"{{{{ Dimension('{USER_FILTER_DIMENSION}') }}}} = '{current_member_email}'"
company_name = current_member.get("company_display")

# Apply glassmorphic theme with company-specific colors
apply_glassmorphic_theme(company_name)
portal_title = get_portal_title(company_name)
st.title(f"{portal_title} · Query Builder")


def ensure_where_inputs(where_inputs: List[WhereInput] | None) -> List[WhereInput]:
    where_inputs = list(where_inputs or [])
    if not any(w.sql == USER_FILTER_SQL for w in where_inputs):
        where_inputs.append(WhereInput(sql=USER_FILTER_SQL))
    return where_inputs


def ensure_where_dicts(where_dicts: List[Dict] | None) -> List[Dict]:
    where_dicts = list(where_dicts or [])
    if not any(w.get("sql") == USER_FILTER_SQL for w in where_dicts):
        where_dicts.append({"sql": USER_FILTER_SQL})
    return where_dicts


OPERATORS = {
    "CATEGORICAL": ["IN", "NOT IN", "=", "<>", "LIKE", "ILIKE"],
    "TIME": ["=", "<>", ">=", "<=", ">", "<", "BETWEEN"],
}

today = datetime.now()

DEFAULT_DATES = {
    "first": datetime(today.year, 1, 1),
    "7": today - timedelta(days=7),
    "30": today - timedelta(days=30),
    "90": today - timedelta(days=90),
    "365": today - timedelta(days=365),
}


def get_time_kwargs(operator: str) -> Dict:
    if operator == "BETWEEN":
        value = (DEFAULT_DATES["7"], today)
    else:
        value = "today"
    return {
        "input": "date_input",
        "label": "Select Date(s)",
        "value": value,
        "format": "YYYY-MM-DD",
    }


def get_categorical_kwargs(dimension: str, operator: str):
    if operator in ["IN", "NOT IN"]:
        input = "multiselect"
    elif operator in ["LIKE", "ILIKE"]:
        input = "text_input"
    else:
        input = "selectbox"

    kwargs = {"input": input}
    if input != "text_input":
        payload = {
            "query": GRAPHQL_QUERIES["dimension_values"],
            "variables": {
                "groupBy": [{"name": dimension}],
                "metrics": [],
                "where": ensure_where_dicts(None),
            },
        }
        with st.spinner("Retrieving dimension values..."):
            data = get_query_results(
                payload, key="createDimensionValuesQuery", progress=False
            )
            df = to_arrow_table(data["arrowResult"])
        kwargs["options"] = sorted(df.iloc[:, 0].tolist())
        kwargs["label"] = (
            "Select Option" if input == "selectbox" else "Select Option(s)"
        )
    else:
        kwargs["label"] = "Input text (without single quotes)"

    return kwargs


def get_condition_kwargs(dimension: str, operator: str):
    dimension_type = get_dimension_type(dimension)
    if dimension_type == "TIME":
        return get_time_kwargs(operator)

    return get_categorical_kwargs(dimension, operator)


def get_dimension_type(dimension: str):
    try:
        return st.session_state.dimension_dict[dimension]["type"]
    except KeyError:
        return "TIME"


def get_time_length(interval):
    time_lengths = {"day": 1, "week": 7, "month": 30, "quarter": 90, "year": 365}
    return time_lengths.get(interval, 0)


def sort_by_time_length(time_intervals):
    return sorted(time_intervals, key=lambda x: get_time_length(x))


def add_where_state():
    st.session_state.where_items += 1


def subtract_where_state():
    st.session_state.where_items -= 1
    i = st.session_state.where_items
    for component in ["column", "operator", "condition", "add", "subtract"]:
        where_component = f"where_{component}_{i}"
        if where_component in st.session_state:
            del st.session_state[where_component]


def add_order_state():
    st.session_state.order_items += 1


def subtract_order_state():
    st.session_state.order_items -= 1
    i = st.session_state.order_items
    for component in ["column", "direction", "add", "subtract"]:
        order_component = f"order_{component}_{i}"
        if order_component in st.session_state:
            del st.session_state[order_component]


# Initialize number of items in where clause
if "where_items" not in st.session_state:
    st.session_state.where_items = 0

# Initialize number of items in order by clause
if "order_items" not in st.session_state:
    st.session_state.order_items = 0


st.caption(
    f"All queries are automatically filtered to {current_member.get('first_name', '')} {current_member.get('last_name', '')} ({current_member_email}). Switch context from the Home page."
)

ad_hoc_tab, saved_query_tab = st.tabs(["Ad Hoc", "Saved Query"])

with ad_hoc_tab:

    col1, col2 = st.columns(2)

    # Retrieve metrics from dictionary
    col1.multiselect(
        label="Select Metric(s)",
        options=sorted(st.session_state.metric_dict.keys()),
        default=None,
        key="selected_metrics",
        placeholder="Select a Metric",
    )

    # Retrieve unique dimensions based on overlap of metrics selected
    all_dimensions = [
        v["dimensions"]
        for k, v in st.session_state.metric_dict.items()
        if k in st.session_state.selected_metrics
    ]
    unique_dimensions = get_shared_elements(all_dimensions)

    # A cumulative metric needs to always be viewed over time so we select metric_time
    requires_metric_time = any(
        [
            v["requiresMetricTime"]
            for k, v in st.session_state.metric_dict.items()
            if k in st.session_state.get("selected_metrics", [])
        ]
    )

    default_options = ["metric_time"] if requires_metric_time else None

    col2.multiselect(
        label="Select Dimension(s)",
        options=sorted(unique_dimensions),
        default=default_options,
        key="selected_dimensions",
        placeholder="Select a dimension",
    )

    # Only add grain if a time dimension has been selected
    dimension_types = set(
        [
            st.session_state.dimension_dict[dim]["type"].lower()
            for dim in st.session_state.get("selected_dimensions", [])
        ]
    )
    if "time" in dimension_types or requires_metric_time:
        col1, col2 = st.columns(2)
        grains = [
            st.session_state.metric_dict[metric]["queryableGranularities"]
            for metric in st.session_state.selected_metrics
        ]
        col1.selectbox(
            label="Select Grain",
            options=sort_by_time_length(
                [g.strip().lower() for g in get_shared_elements(grains)]
            ),
            key="selected_grain",
        )

    # Filtering and ordering sections hidden for simplified UX

    col1, col2 = st.columns(2)
    col1.number_input(
        label="Limit Rows",
        min_value=0,
        value=0,
        key="selected_limit",
        help="Limit the amount of rows returned by the query with a limit clause",
    )
    col1.caption("If set to 0, no limit will be applied")

    query = QueryLoader(st.session_state).create()
    query = query.model_copy(update={"where": ensure_where_inputs(query.where)})
    with st.expander("View API Request", expanded=False):
        tab1, tab2, tab3, tab4 = st.tabs(["GraphQL", "JDBC", "Python SDK", "CLI"])
        python_code = create_graphql_code(query)
        sdk_code = create_python_sdk_code(query)
        tab1.code(python_code, language="python")
        tab2.code(query.jdbc_query, language="sql")
        tab3.write(
            "More info [here](https://github.com/dbt-labs/semantic-layer-sdk-python)"
        )
        tab3.code(sdk_code, language="python")
        cli_command = construct_cli_command(query)
        tab4.code(cli_command, language="bash")

    if st.button("Submit Query"):
        if len(st.session_state.selected_metrics) == 0:
            st.warning("You must select at least one metric!")
            st.stop()

        payload = {"query": query.gql, "variables": query.variables}
        data = get_query_results(payload)
        df = to_arrow_table(data["arrowResult"])
        df.columns = [col.lower() for col in df.columns]
        st.session_state.query_qm = query
        st.session_state.df_qm = df
        st.session_state.compiled_sql_qm = data["sql"]

    create_tabs(st.session_state, "qm")


def retrieve_saved_query(name: str) -> Dict:
    try:
        return [
            sq for sq in st.session_state.get("saved_queries", []) if sq["name"] == name
        ][0]
    except IndexError:
        return dict()


with saved_query_tab:
    col1, col2 = st.columns(2)

    saved_queries = [sq for sq in st.session_state.get("saved_queries", [])]
    sorted_saved_queries = sorted(sq["name"] for sq in saved_queries)

    st.selectbox(
        label="Select Saved Query",
        options=sorted_saved_queries,
        key="selected_saved_query",
    )
    saved_query = retrieve_saved_query(st.session_state.selected_saved_query)
    st.caption(saved_query.get("description", ""))
    query_params = saved_query.get("queryParams", None)
    if query_params:
        sql = query_params.get("where", {})
        if sql is None:
            where = []
        else:
            where = [{"sql": sql.get("whereSqlTemplate", None)}]
        query = Query(
            metrics=query_params.get("metrics") or [],
            groupBy=query_params.get("groupBy") or [],
            where=where,
        )
        query = query.model_copy(update={"where": ensure_where_inputs(query.where)})

        with st.expander("View API Request", expanded=False):
            tab1, tab2, tab3 = st.tabs(["GraphQL", "JDBC", "Python SDK"])
            python_code = create_graphql_code(query)
            sdk_code = create_python_sdk_code(query)
            tab1.code(python_code, language="python")
            tab2.code(query.jdbc_query, language="sql")
            tab3.code(sdk_code, language="python")

        if st.button("Submit Query", key="submit_query_sq"):
            payload = {"query": query.gql, "variables": query.variables}
            data = get_query_results(payload)
            df = to_arrow_table(data["arrowResult"])
            df.columns = [col.lower() for col in df.columns]
            st.session_state.query_sq = query
            st.session_state.df_sq = df
            st.session_state.compiled_sql_sq = data["sql"]

        create_tabs(st.session_state, "sq")
