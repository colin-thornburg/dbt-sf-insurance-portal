# stdlib
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional

# third party
import streamlit as st
from openai import OpenAI

# first party
from client import get_query_results
from helpers import (
    USER_FILTER_DIMENSION,
    create_tabs,
    ensure_member_context,
    get_portal_title,
    to_arrow_table,
)
from init_app import initialize_app
from schema import Query
from styles import apply_glassmorphic_theme

st.set_page_config(
    page_title="AI Benefits Portal - LLM",
    page_icon="🧠",
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


@dataclass
class Metric:
    name: str
    label: Optional[str]
    description: Optional[str]
    dimensions: List[str]

# Initialize app (loads metrics automatically if needed)
initialize_app(show_spinner=True)

if "metric_dict" not in st.session_state:
    st.warning(
        "No metrics found. Ensure your project has metrics defined and a production job has run."
    )
    st.stop()


if "OPENAI_API_KEY" not in st.session_state and os.getenv("OPENAI_API_KEY"):
    st.session_state.OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


@st.cache_resource
def _init_openai_client() -> OpenAI:
    api_key = (
        st.secrets.get("OPENAI_API_KEY")
        or st.session_state.get("OPENAI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
    )
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY not configured. Add it to .env or secrets and reload the app."
        )
    return OpenAI(api_key=api_key)


def get_openai_client() -> OpenAI:
    try:
        return _init_openai_client()
    except RuntimeError as exc:
        st.error(str(exc))
        st.stop()


def metric_map() -> Dict[str, Metric]:
    metric_dict = {}
    for metric_name, metric in st.session_state.metric_dict.items():
        metric_dict[metric_name] = Metric(
            name=metric_name,
            label=metric.get("label"),
            description=metric.get("description"),
            dimensions=metric.get("dimensions", []),
        )
    return metric_dict


METRICS = metric_map()
DIMENSIONS = st.session_state.dimension_dict

SYSTEM_PROMPT = """You are a helpful assistant that converts natural language questions about metrics into JSON payloads that the dbt Semantic Layer can execute. You must ONLY use the metrics and dimensions provided.

Return a JSON object with the following shape:
{
  "intent": "query" | "metadata",
  "question": "<restated question>",
  "metrics": ["metric_name", ...],
  "dimensions": ["dimension_name", ...],
  "where": ["{{ Dimension('name') }} operator value"],
  "limit": <number or null>
}

Rules:
- Metric names must come from the allowed list.
- Dimension names must come from the allowed list.
- If the user is asking for metadata (e.g., "what metrics are available") set intent="metadata" and omit metrics/dimensions.
- Only include metrics/dimensions explicitly requested or implied.
- If the user mentions a member, filter using Dimension('member__email').
- The current user's email will always be provided; every query MUST include a where clause `{{ Dimension('member__email') }} = '<current user email>'` to limit results to that user.
- Dates should be ISO formatted strings.
- Assume intent="query" unless clearly informational.
- limit should be null unless user specifies a number.
"""


def build_user_context(question: str, user_email: str) -> str:
    metrics_info = [
        {
            "name": metric.name,
            "description": metric.description,
            "dimensions": metric.dimensions,
        }
        for metric in METRICS.values()
    ]
    dimensions_info = [
        {
            "name": name,
            "type": details.get("type"),
            "description": details.get("description"),
        }
        for name, details in DIMENSIONS.items()
    ]
    return (
        f"Question: {question}\n"
        f"Metrics: {metrics_info}\n"
        f"Dimensions: {dimensions_info}\n"
        f"Current user email: {user_email}"
    )


def _metric_display(metric: Metric) -> str:
    label = metric.label or metric.description or metric.name
    return label.replace("_", " ")


def _dimension_display(dimension: str) -> str:
    column = dimension.split("__", 1)[0]
    return column.replace("_", " ")


def build_sample_questions(
    member: Mapping[str, Any], metrics: List[Metric]
) -> List[str]:
    if not metrics:
        return ["What metrics can I explore for myself?"]

    first_metric = metrics[0]
    metric_label = _metric_display(first_metric).lower()
    questions = [f"Show my {metric_label} for the last 12 months."]

    dimension_options = [
        d for d in first_metric.dimensions if d and d != USER_FILTER_DIMENSION
    ]
    if dimension_options:
        questions.append(
            f"Break down my {metric_label} by {_dimension_display(dimension_options[0]).lower()} this quarter."
        )
    else:
        questions.append(f"How has my {metric_label} changed week over week?")

    if len(metrics) > 1:
        second_metric = metrics[1]
        second_label = _metric_display(second_metric).lower()
        questions.append(
            f"Compare my {metric_label} and {second_label} for the past 6 months."
        )

    first_name = str(member.get("first_name") or "").strip()
    self_reference = first_name if first_name else "me"
    questions.append(f"What metrics are available for {self_reference} to explore?")
    return questions[:4]


def call_openai(question: str, user_email: str) -> str:
    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_user_context(question, user_email),
            },
        ],
        max_tokens=600,
        response_format={"type": "json_object"},
    )
    
    if not response.choices:
        return "{}"
    
    return response.choices[0].message.content or "{}"


def parse_response(raw: str) -> Dict:
    try:
        return json.loads(raw)
    except Exception:
        st.warning("Unable to parse LLM response. Please refine your question.")
        return {}


current_member = ensure_member_context()
company_name = current_member.get("company_display")
portal_title = get_portal_title(company_name)

# Apply glassmorphic theme with company-specific colors
apply_glassmorphic_theme(company_name)

st.title(f"{portal_title} · Conversational Analytics")

st.sidebar.markdown("### What can I ask?")
for question in [
    "Show me my claims for the last 6 months",
    "Show how much was paid by my insurance this year",
    "What metrics are available to query",
]:
    st.sidebar.markdown(f"- {question}")

current_member_email = current_member.get("email", "")
if not current_member_email:
    st.error("Selected member does not have an email address configured.")
    st.stop()
st.sidebar.caption(
    f"{portal_title} · {current_member.get('first_name', '')} {current_member.get('last_name', '')} ({current_member_email})."
)
st.sidebar.write("Switch members from the Home page.")

question = st.chat_input("Ask a question about your metrics...")

if "chat" not in st.session_state:
    st.session_state.chat = []

for message in st.session_state.chat:
    st.chat_message(message["role"]).write(message["content"])

if question:
    st.chat_message("user").write(question)
    st.session_state.chat.append({"role": "user", "content": question})

    raw_response = call_openai(question, current_member_email)
    response = parse_response(raw_response)

    if not response:
        st.stop()

    intent = response.get("intent", "query")
    restated = response.get("question", question)

    if intent == "metadata":
        metrics = response.get("metrics") or list(METRICS.keys())
        descriptions = [
            f"**{metric}**: {METRICS[metric].description or 'No description'}"
            for metric in metrics
            if metric in METRICS
        ]
        if descriptions:
            answer = "\n".join(descriptions)
        else:
            answer = "I could not find matching metrics."
        st.chat_message("assistant").markdown(answer)
        st.session_state.chat.append({"role": "assistant", "content": answer})
        st.stop()

    metrics = response.get("metrics", [])
    dimensions = response.get("dimensions", [])
    where_clauses = response.get("where") or []
    if not isinstance(where_clauses, list):
        where_clauses = [str(where_clauses)]
    user_filter_clause = (
        f"{{{{ Dimension('{USER_FILTER_DIMENSION}') }}}} = '{current_member_email}'"
    )
    if user_filter_clause not in where_clauses:
        where_clauses.append(user_filter_clause)
    limit_value = response.get("limit")
    if isinstance(limit_value, str):
        limit_value = int(limit_value) if limit_value.isdigit() else None

    if not metrics:
        st.warning("I need at least one metric to build a query. Please specify a metric.")
        st.stop()

    group_by_inputs = []
    for dimension in dimensions:
        if dimension not in DIMENSIONS:
            continue
        if dimension.endswith("__day"):
            name = dimension.rsplit("__", 1)[0]
            group_by_inputs.append({"name": name, "grain": "DAY"})
            continue
        if dimension.endswith("__week"):
            name = dimension.rsplit("__", 1)[0]
            group_by_inputs.append({"name": name, "grain": "WEEK"})
            continue
        if dimension.endswith("__month"):
            name = dimension.rsplit("__", 1)[0]
            group_by_inputs.append({"name": name, "grain": "MONTH"})
            continue
        if dimension.endswith("__quarter"):
            name = dimension.rsplit("__", 1)[0]
            group_by_inputs.append({"name": name, "grain": "QUARTER"})
            continue
        if dimension.endswith("__year"):
            name = dimension.rsplit("__", 1)[0]
            group_by_inputs.append({"name": name, "grain": "YEAR"})
            continue
        group_by_inputs.append({"name": dimension})

    query_dict = {
        "metrics": [{"name": metric} for metric in metrics if metric in METRICS],
        "groupBy": group_by_inputs,
        "where": [{"sql": clause} for clause in where_clauses],
    }

    if limit_value:
        query_dict["limit"] = limit_value

    try:
        query = Query(**query_dict)
    except Exception as exc:
        st.error(f"Unable to build query from response: {exc}")
        st.stop()

    payload = {"query": query.gql, "variables": query.variables}

    with st.spinner("Running semantic layer query..."):
        try:
            data = get_query_results(payload, source="streamlit-openai", progress=False)
        except Exception as exc:
            st.error(f"Semantic layer query failed: {exc}")
            st.stop()

    arrow_bytes = data.get("arrowResult")
    if not arrow_bytes:
        st.warning("Query executed but returned no data.")
        st.stop()

    df = to_arrow_table(arrow_bytes)
    df.columns = [col.lower() for col in df.columns]

    run_id = f"llm_{len(st.session_state.chat)}"
    setattr(st.session_state, f"query_{run_id}", query)
    setattr(st.session_state, f"df_{run_id}", df)
    setattr(st.session_state, f"compiled_sql_{run_id}", data["sql"])

    st.chat_message("assistant").write(
        f"{restated}\n\nPreviewing {len(df)} rows filtered to {current_member_email}."
    )
    st.session_state.chat.append(
        {
            "role": "assistant",
            "content": f"{restated}\n\nPreviewing {len(df)} rows filtered to {current_member_email}.",
        }
    )
    create_tabs(st.session_state, run_id)


if st.button("Clear chat"):
    st.session_state.chat = []
    st.rerun()
