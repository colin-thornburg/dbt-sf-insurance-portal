# stdlib
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Dict

# third party
import streamlit as st

# first party
from audit_logger import log_query_execution
from helpers import (
    USER_FILTER_DIMENSION,
    ensure_member_context,
    get_portal_title,
    load_plan_documents,
)
from init_app import initialize_app
from styles import apply_glassmorphic_theme

st.set_page_config(
    page_title="AI Benefits Portal - Benefits Coach",
    page_icon="🩺",
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

try:
    from agents import Agent, Runner, trace
    from agents.mcp import create_static_tool_filter
    from agents.mcp.server import MCPServerStdio
except ImportError:
    st.error(
        "The OpenAI Agents SDK is not installed. Install it with `pip install openai-agents` (or `pip install dbt-mcp[agents]`) and restart the app to use the Benefits Coach tab."
    )
    st.stop()

logger = logging.getLogger("benefits_coach")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Initialize app (loads metrics automatically if needed)
initialize_app(show_spinner=True)

current_member = ensure_member_context()
member_email = current_member.get("email")
if not member_email:
    st.error("Selected member does not have an email address configured.")
    st.stop()

company_name = current_member.get("company_display")
portal_title = get_portal_title(company_name)

# Apply glassmorphic theme with company-specific colors
apply_glassmorphic_theme(company_name)

st.title(f"{portal_title} · Benefits Coach")

st.markdown(
    """
    Ask benefit-related questions and the coach will query the dbt Semantic Layer using the
    dbt MCP. Responses are automatically scoped to the member selected on the Home page.
    """
)

st.sidebar.caption(
    f"{portal_title} · {current_member.get('first_name', '')} {current_member.get('last_name', '')} ({member_email})."
)
st.sidebar.write("Switch members from the Home page.")

DBT_MCP_ENV_FILE = os.getenv(
    "DBT_MCP_ENV_FILE",
    str(Path(__file__).resolve().parents[1] / ".env"),
)
DBT_MCP_COMMAND = os.getenv("DBT_MCP_COMMAND", "uvx")
DBT_MCP_ENTRY = os.getenv("DBT_MCP_ENTRY", "dbt-mcp")
MCP_CLIENT_TIMEOUT = int(os.getenv("DBT_MCP_CLIENT_TIMEOUT", "20"))

instructions = f"""You are a benefits coaching assistant.
Use the available tools to answer questions about member benefits and claims.

IMPORTANT: Every query must include this exact filter: Dimension('{USER_FILTER_DIMENSION}') = '{member_email}'

Available tools:
- list_metrics: See what metrics are available
- query_metrics: Query specific metrics with filters

Plan documentation snippets are included in the conversation context. Use them when metric data lacks a deductible value.

When asked about deductible progress:
1. Call `query_metrics` for `ytd_member_responsibility` (with the member filter) to get the year-to-date spend.
2. Call `query_metrics` for `total_member_responsibility` grouped by plan details (e.g., `plan_details__plan_id`, `plan_details__plan_type`, `plan_details__annual_deductible`).
3. If `plan_details__annual_deductible` is missing or null, parse the deductible from the plan documentation provided in the context (for example, the TechCorp PPO document specifies an annual deductible of $500.00).
4. Compute `remaining_deductible = max(plan_deductible - ytd_member_responsibility, 0)`.
5. If plan data and documentation both fail, politely ask the user to provide the deductible once. If the user supplies it, store and reuse that value; otherwise respond with an apology and recommend contacting support.
6. After performing at most one query per tool, if you still cannot answer, respond with an apology instead of looping on the tools.
7. Explain the calculation and cite the values you used.

Response formatting guidelines:
- Write in full sentences (avoid character-by-character output).
- Format money as `$X.XX`.
- Avoid code blocks unless the user explicitly requests them.

Return concise, friendly answers.
"""

ALLOWED_TOOLS = [
    "list_metrics",
    "query_metrics",
]


def build_context_block() -> str:
    metrics = st.session_state.metric_dict
    dimensions = st.session_state.dimension_dict

    metrics_info = [
        {
            "name": name,
            "description": details.get("description"),
            "dimensions": details.get("dimensions"),
        }
        for name, details in metrics.items()
    ]
    dimensions_info = [
        {
            "name": name,
            "type": details.get("type"),
            "description": details.get("description"),
        }
        for name, details in dimensions.items()
    ]

    plan_docs = load_plan_documents()
    company_key = (company_name or "").lower()
    doc_snippets = []
    if plan_docs:
        if company_key:
            for name, content in plan_docs.items():
                if company_key in name:
                    doc_snippets.append((name, content))
        if not doc_snippets:
            for name, content in plan_docs.items():
                doc_snippets.append((name, content))

    doc_text = "\n".join(
        [f"Plan document `{name}`:\n{content}" for name, content in doc_snippets]
    ) if doc_snippets else "No plan documents available."

    return (
        "You have access to the following metrics and dimensions from the dbt Semantic Layer.\n"
        + f"Current member email: {member_email}. You must always include the filter `Dimension('{USER_FILTER_DIMENSION}') = '{member_email}'`.\n"
        + f"Metrics: {metrics_info}\n"
        + f"Dimensions: {dimensions_info}\n"
        + f"Plan documentation excerpts:\n{doc_text}"
    )


def validate_environment() -> bool:
    required_env = [
        "DBT_HOST",
        "DBT_TOKEN",
        "DBT_PROD_ENV_ID",
        "DBT_PROJECT_DIR",
    ]
    missing = [env for env in required_env if not os.getenv(env)]
    if missing:
        st.error(
            "Missing required environment variables for dbt MCP: " + ", ".join(missing)
        )
        return False
    if not Path(DBT_MCP_ENV_FILE).exists():
        st.error(
            f"MCP environment file not found at `{DBT_MCP_ENV_FILE}`. Set `DBT_MCP_ENV_FILE` or create the file."
        )
        return False
    return True


def run_agent(conversation: List[Dict[str, str]]) -> str:
    async def _run() -> str:
        context_block = build_context_block()
        full_conversation = [{"role": "system", "content": context_block}] + conversation

        async with MCPServerStdio(
            name="dbt",
            params={
                "command": DBT_MCP_COMMAND,
                "args": [
                    "--env-file",
                    DBT_MCP_ENV_FILE,
                    DBT_MCP_ENTRY,
                ],
            },
            client_session_timeout_seconds=MCP_CLIENT_TIMEOUT,
            cache_tools_list=True,
            tool_filter=create_static_tool_filter(
                allowed_tool_names=ALLOWED_TOOLS,
            ),
        ) as server:
            agent = Agent(
                name="Benefits Coach",
                instructions=instructions,
                mcp_servers=[server],
            )
            with trace(workflow_name="Benefits Coaching Conversation"):
                logger.info("Starting agent run with %d messages", len(full_conversation))
                logger.debug("Conversation payload: %s", full_conversation)
                # Add this right before the try block in run_agent()
                logger.info("Full conversation being sent to agent: %s", full_conversation)
                try:
                    result = await Runner.run(agent, full_conversation, max_turns=6)
                except Exception as e:
                    logger.exception("Agent run failed with detailed error")
                    logger.error(f"Error type: {type(e).__name__}")
                    logger.error(f"Error message: {str(e)}")
                    # Log the last few tool calls if available
                    raise
                logger.info("Agent run completed")

                # Extract tool calls from the conversation messages
                tool_calls = []
                conversation_list = result.to_input_list()

                # Extract tool calls from the conversation
                for msg in conversation_list:
                    if isinstance(msg, dict):
                        # OpenAI Agents SDK stores tool calls with type='function_call'
                        if "name" in msg and "arguments" in msg and msg.get("type") == "function_call":
                            tool_name = msg.get("name", "")

                            if tool_name == "query_metrics":
                                # Parse the arguments
                                import json
                                args = msg.get("arguments", {})

                                if isinstance(args, str):
                                    try:
                                        args = json.loads(args)
                                    except json.JSONDecodeError:
                                        logger.warning(f"Could not parse tool arguments: {args}")
                                        args = {}

                                tool_calls.append({
                                    "tool_name": tool_name,
                                    "tool_input": args,
                                    "tool_call_id": msg.get("call_id", "")
                                })
                                logger.info(f"Captured query_metrics tool call for audit log")

                if tool_calls:
                    logger.info(f"Found {len(tool_calls)} tool call(s) to log")
            return result.final_output, result.to_input_list(), tool_calls

    final_output, updated_conversation, tool_results = asyncio.run(_run())
    # remove initial system context before saving back to state
    trimmed_conversation = [msg for msg in updated_conversation if msg.get("role") != "system"]
    return final_output, trimmed_conversation, tool_results


def normalize_response(text: str) -> str:
    """
    Fix malformed agent responses where text is separated by spaces or newlines.
    Detects character-by-character output and rejoins it properly.
    """
    lines = text.splitlines()
    significant = [line for line in lines if line.strip()]
    
    # Case 1: ALL lines are single characters (classic character-by-character streaming)
    if significant and len(significant) > 10 and all(len(line.strip()) == 1 for line in significant):
        return "".join(line.strip() for line in significant)
    
    # Case 2: Lines have single-character words separated by spaces (new issue)
    # Check if the text has unusual spacing (many single-char words)
    words = text.split()
    single_char_words = [w for w in words if len(w) == 1 and w.isalpha()]
    
    # If more than 40% of words are single characters, it's likely malformed
    if len(words) > 5 and len(single_char_words) / len(words) > 0.4:
        # Try to reconstruct: remove spaces between single characters
        result = []
        i = 0
        while i < len(words):
            word = words[i]
            if len(word) == 1 and word.isalpha():
                # Collect consecutive single-character words
                chars = [word]
                i += 1
                while i < len(words) and len(words[i]) == 1 and words[i].isalpha():
                    chars.append(words[i])
                    i += 1
                result.append("".join(chars))
            else:
                result.append(word)
                i += 1
        return " ".join(result)
    
    # For normal text, preserve the original formatting
    return text


if "benefits_display" not in st.session_state:
    st.session_state.benefits_display = [
        {
            "role": "assistant",
            "content": "Hi! I'm your benefits coach. How can I help you today?",
        }
    ]

if "benefits_conversation" not in st.session_state:
    st.session_state.benefits_conversation = []

if "last_benefits_tool_results" not in st.session_state:
    st.session_state.last_benefits_tool_results = []

for message in st.session_state.benefits_display:
    st.chat_message(message["role"]).write(message["content"])

question = st.chat_input("Ask about your benefits, claims, or coverage...")

if question:
    if not validate_environment():
        st.stop()

    st.chat_message("user").write(question)
    st.session_state.benefits_display.append({"role": "user", "content": question})

    conversation = st.session_state.benefits_conversation.copy()
    conversation.append({"role": "user", "content": question})

    with st.spinner("Consulting the benefits coach..."):
        try:
            final_output, updated_conversation, tool_results = run_agent(conversation)
        except Exception as exc:
            logger.exception("Benefits coach encountered an error during execution")
            st.error(f"The benefits coach encountered an error: {exc}")
        else:
            st.session_state.benefits_conversation = updated_conversation
            normalized_output = normalize_response(final_output)
            st.session_state.benefits_display.append(
                {"role": "assistant", "content": normalized_output}
            )
            logger.info("Benefits coach response: %s", final_output)
            logger.debug(
                "Updated conversation state: %s", st.session_state.benefits_conversation
            )
            st.chat_message("assistant").write(normalized_output)

            # Log tool results to audit
            if tool_results:
                st.session_state.last_benefits_tool_results = tool_results

                # Log each tool call to audit log
                for tool in tool_results:
                    tool_name = tool.get("tool_name", "")

                    if tool_name == "query_metrics":
                        # Extract metrics from tool call
                        tool_input = tool.get("tool_input", {})

                        metrics = tool_input.get("metrics", [])
                        dimensions = tool_input.get("group_by", [])
                        where_filters = tool_input.get("where", [])

                        # Ensure lists
                        if isinstance(metrics, str):
                            metrics = [metrics]
                        if isinstance(dimensions, str):
                            dimensions = [dimensions]
                        if isinstance(where_filters, str):
                            where_filters = [where_filters]

                        log_query_execution(
                            query_type="benefits_coach",
                            member_email=member_email,
                            filters_applied=where_filters or [],
                            metrics=metrics or [],
                            dimensions=dimensions or [],
                            row_count=None,  # Agent doesn't return row count directly
                            status="success",
                            error_message=None,
                            page="Benefits Coach",
                        )
                        logger.info("Logged benefits coach query to audit log")
            else:
                st.session_state.last_benefits_tool_results = []


if st.session_state.get("last_benefits_tool_results"):
    with st.expander("Coach Tool Calls", expanded=False):
        for idx, tool in enumerate(st.session_state.last_benefits_tool_results):
            st.markdown(f"**Tool #{idx + 1}: {tool.get('tool_name', 'unknown')}**")
            st.json(tool)
logger = logging.getLogger("benefits_coach")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s %(name)s - %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
