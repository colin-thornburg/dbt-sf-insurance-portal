# third party
import streamlit as st

# first party
from helpers import (
    ensure_member_context,
    get_portal_title,
)
from init_app import initialize_app
from styles import apply_glassmorphic_theme

st.set_page_config(
    page_title="AI Benefits Portal - Architecture",
    page_icon="🏗️",
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

# Initialize app (loads metrics automatically if needed)
initialize_app(show_spinner=True)

current_member = ensure_member_context()
company_name = current_member.get("company_display")
portal_title = get_portal_title(company_name)

# Apply glassmorphic theme with company-specific colors
apply_glassmorphic_theme(company_name)

st.title(f"{portal_title} · Technical Architecture")

st.markdown("""
This page explains how dbt Semantic Layer, dbt MCP (Model Context Protocol), and Snowflake
work together to power this secure, multi-tenant insurance portal.
""")

# Architecture Overview
st.header("🏗️ Architecture Overview")

st.markdown("""
```
┌─────────────────────────────────────────────────────────────────┐
│                      Streamlit Frontend                         │
│  (Member Dashboard, Benefits Coach, Query Builder, Audit Log)   │
└────────────────┬────────────────────────────┬───────────────────┘
                 │                            │
                 │                            │
      ┌──────────▼──────────┐       ┌────────▼────────────┐
      │  dbt Semantic Layer │       │  dbt MCP Server     │
      │   (GraphQL API)     │       │  (Tool Provider)    │
      └──────────┬──────────┘       └─────────┬───────────┘
                 │                            │
                 └────────────┬───────────────┘
                              │
                    ┌─────────▼──────────┐
                    │   Snowflake DW     │
                    │  (Claims, Members) │
                    └────────────────────┘
```
""")

# Component Breakdown
st.header("🔧 Component Breakdown")

tab1, tab2, tab3, tab4 = st.tabs(["Snowflake", "dbt Semantic Layer", "dbt MCP", "Streamlit App"])

with tab1:
    st.subheader("❄️ Snowflake Data Warehouse")

    st.markdown("""
    **Role**: Source of truth for all insurance data

    **Data Model**:
    - **Seeds/Source Tables**: `members`, `claims`, `companies`, `plans`, `providers`, `prescriptions`
    - **Staging Layer** (`stg_*`): Clean, typed source data
    - **Intermediate Layer** (`int_*`): Business logic transformations
    - **Semantic Layer** (`fct_claims`, `dim_members`, `dim_plans`): Analytics-ready models

    **Key Tables**:
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.code("""
-- fct_claims (Fact Table)
SELECT
    claim_id,
    member_id,
    company_id,
    claim_date,
    claim_type,
    provider_name,
    claim_amount,
    paid_amount,
    member_responsibility,
    claim_status
FROM {{ ref('stg_claims') }}
        """, language="sql")

    with col2:
        st.code("""
-- dim_members (Dimension Table)
SELECT
    member_id,
    first_name,
    last_name,
    email,
    company_id,
    company_name,
    department,
    plan_type,
    enrollment_date
FROM {{ ref('stg_members') }}
        """, language="sql")

    st.markdown("""
    **Security**: Row-level security enforced at the Semantic Layer, not in Snowflake directly.
    """)

with tab2:
    st.subheader("📊 dbt Semantic Layer")

    st.markdown("""
    **Role**: Centralized metric definitions and governed data access

    **How It Works**:
    1. **Semantic Models** define entities, dimensions, and measures in YAML
    2. **Metrics** are built on top of measures with business logic
    3. **GraphQL API** exposes metrics with consistent definitions
    4. **Query Engine** generates optimized SQL and executes on Snowflake

    **Example Semantic Model**:
    """)

    st.code("""
semantic_models:
  - name: claims
    model: ref('fct_claims')
    entities:
      - name: claim
        type: primary
        expr: claim_id
      - name: member
        type: foreign
        expr: member_id

    dimensions:
      - name: claim_date
        type: time
        expr: claim_date
      - name: claim_type
        type: categorical

    measures:
      - name: total_claim_amount
        agg: sum
        expr: claim_amount
      - name: claim_count
        agg: count
        expr: claim_id
    """, language="yaml")

    st.markdown("""
    **Example Metric**:
    """)

    st.code("""
metrics:
  - name: ytd_member_responsibility
    description: "Member responsibility amount year-to-date"
    type: simple
    type_params:
      measure: member_responsibility
    filter: |
      {{ Dimension('claim__claim_date') }} >= '2024-01-01'
    """, language="yaml")

    st.markdown("""
    **Key Features in This App**:
    - ✅ **Governed Metrics**: `total_claim_amount`, `ytd_member_responsibility`, `total_claims_count`
    - ✅ **Row-Level Security**: Filters injected via `{{ Dimension('member__email') }} = '...'`
    - ✅ **Token Scoping**: Company-specific service tokens limit data access
    - ✅ **Consistent Definitions**: Same metric definitions across all pages
    - ✅ **Query Caching**: Semantic Layer caches results for performance
    """)

with tab3:
    st.subheader("🔌 dbt MCP (Model Context Protocol)")

    st.markdown("""
    **Role**: Provides AI agents secure access to dbt Semantic Layer as tools

    **What is MCP?**
    - Protocol created by Anthropic for connecting AI agents to external tools
    - dbt MCP implements MCP server that exposes Semantic Layer operations
    - AI agents can discover and call tools without hardcoded integration

    **Available Tools**:
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **`list_metrics`**
        - Lists all available metrics
        - Shows dimensions and descriptions
        - Used for agent planning
        """)

        st.code("""
# Agent calls this to discover metrics
{
  "tool": "list_metrics",
  "arguments": {}
}

# Returns:
[
  {
    "name": "total_claim_amount",
    "description": "Total dollar amount...",
    "dimensions": ["member__email", ...]
  }
]
        """, language="json")

    with col2:
        st.markdown("""
        **`query_metrics`**
        - Queries specific metrics with filters
        - Returns tabular results
        - Supports group_by, where, order_by
        """)

        st.code("""
# Agent calls this to get data
{
  "tool": "query_metrics",
  "arguments": {
    "metrics": ["total_claim_amount"],
    "where": "{{ Dimension('member__email') }} = '...'",
    "group_by": ["claim__claim_type"]
  }
}
        """, language="json")

    st.markdown("""
    **How Benefits Coach Uses MCP**:

    1. **User asks**: "What are my total claims?"
    2. **Agent calls** `query_metrics` with member email filter
    3. **dbt MCP** validates request and forwards to Semantic Layer
    4. **Semantic Layer** generates SQL: `SELECT SUM(claim_amount) FROM fct_claims WHERE member_email = '...'`
    5. **Snowflake** executes query and returns results
    6. **Agent** receives data and formats natural language response

    **Security in MCP**:
    - 🔒 Agent instructions **require** member email filter in every query
    - 🔒 Tool filter restricts agent to only `list_metrics` and `query_metrics`
    - 🔒 All queries logged to audit log for validation
    """)

with tab4:
    st.subheader("🖥️ Streamlit Application")

    st.markdown("""
    **Role**: User interface and orchestration layer

    **Pages & Data Flow**:
    """)

    # Member Dashboard
    st.markdown("### 📊 Member Dashboard")
    st.code("""
# 1. Get member email from session context
member_email = st.session_state.selected_member_email

# 2. Build filter clause
filter_clause = f"{{{{ Dimension('member__email') }}}} = '{member_email}'"

# 3. Query Semantic Layer via GraphQL
payload = {
    "query": "mutation CreateQuery { ... }",
    "variables": {
        "metrics": ["total_claim_amount", "ytd_member_responsibility"],
        "groupBy": [{"name": "claim__claim_date", "grain": "DAY"}],
        "where": [{"sql": filter_clause}]
    }
}

# 4. Execute query and render results
response = requests.post(SL_GRAPHQL_URL, json=payload)
df = parse_arrow_result(response.json())

# 5. Log to audit log
log_query_execution(
    member_email=member_email,
    filters_applied=[filter_clause],
    metrics=["total_claim_amount"],
    status="success"
)
    """, language="python")

    st.divider()

    # Benefits Coach
    st.markdown("### 🩺 Benefits Coach")
    st.code("""
# 1. Build agent context with member email
context = f"Current member email: {member_email}. " + \\
          "You must always include filter: Dimension('member__email') = '{member_email}'"

# 2. Start MCP server with dbt connection
async with MCPServerStdio(
    command="uvx",
    args=["--env-file", ".env", "dbt-mcp"],
    tool_filter=allow_only(["list_metrics", "query_metrics"])
) as mcp_server:

    # 3. Create agent with instructions
    agent = Agent(
        name="Benefits Coach",
        instructions="Use query_metrics with member filter...",
        mcp_servers=[mcp_server]
    )

    # 4. Run agent with user question
    result = await Runner.run(agent, conversation)

    # 5. Extract tool calls and log to audit
    for tool_call in extract_tool_calls(result):
        log_query_execution(
            query_type="benefits_coach",
            member_email=member_email,
            filters_applied=tool_call["where"],
            metrics=tool_call["metrics"]
        )
    """, language="python")

    st.divider()

    # Architecture patterns
    st.markdown("### 🔐 Security Patterns")

    st.markdown("""
    **1. Company-Scoped Service Tokens** 🆕
    - Each company has its own dbt Cloud service token
    - Token selected based on email domain:
      - `@techcorp.com` → `DBT_TECHCORP_TOKEN`
      - `@retailplus.com` → `DBT_RETAILPLUS_TOKEN`
      - `@manufacturingco.com` → `DBT_MANUFACTURINGCO_TOKEN`
    - Connection automatically switches when member changes
    - Provides defense-in-depth beyond row-level filters

    **2. Session-Based Member Context**
    - Member selected on Authentication page stored in `st.session_state`
    - All pages read from session state (cannot be manipulated via URL)
    - Context switching requires going through Authentication page

    **3. Row-Level Filter Injection**
    - Every query automatically injects `WHERE member__email = '...'`
    - Filter built server-side, not sent from client
    - Semantic Layer enforces at query execution time
    - Combined with company token for dual-layer security

    **4. Audit Trail**
    - All queries logged with filters, metrics, member context, and company
    - Security violations flagged if member filter missing
    - Immutable log (session-based in demo, would be database in production)
    """)

    st.code("""
# Example: Token scoping in action
member_email = "alice.chen@techcorp.com"
company = get_company_from_email(member_email)  # Returns "techcorp"
token = get_company_token(company)  # Gets DBT_TECHCORP_TOKEN

# Create connection with company-specific token
conn = ConnAttr(
    host="semantic-layer.cloud.getdbt.com",
    params={"environmentId": "123"},
    auth_header=f"Bearer {token}"  # TechCorp token
)

# If user switches to bob.smith@retailplus.com
# Connection automatically refreshes with DBT_RETAILPLUS_TOKEN
    """, language="python")

# Data Flow Example
st.header("🔄 End-to-End Data Flow Example")

st.markdown("""
**Scenario**: User asks Benefits Coach "What are my total claims?"
""")

col1, col2 = st.columns([1, 1])

with col1:
    st.markdown("""
    **Step 1: User Input**
    ```
    User: "What are my total claims?"
    Member Context: alice.chen@techcorp.com
    ```

    **Step 2: Agent Planning**
    ```
    Agent decides to call query_metrics tool
    ```

    **Step 3: MCP Tool Call**
    ```json
    {
      "tool": "query_metrics",
      "metrics": ["total_claims_count"],
      "where": "{{ Dimension('member__email') }} = 'alice.chen@techcorp.com'"
    }
    ```

    **Step 4: Semantic Layer Processing**
    ```
    - Validates metric exists
    - Parses where filter
    - Generates SQL with joins
    - Applies row-level filter
    ```
    """)

with col2:
    st.markdown("""
    **Step 5: SQL Generation**
    ```sql
    SELECT
        COUNT(c.claim_id) as total_claims_count
    FROM analytics.fct_claims c
    LEFT JOIN analytics.dim_members m
        ON c.member_id = m.member_id
    WHERE m.email = 'alice.chen@techcorp.com'
    ```

    **Step 6: Snowflake Execution**
    ```
    Query runs on Snowflake
    Returns: total_claims_count = 15
    ```

    **Step 7: Agent Response**
    ```
    "You have 15 total claims."
    ```

    **Step 8: Audit Log**
    ```json
    {
      "timestamp": "2025-10-03T05:33:26Z",
      "member_email": "alice.chen@techcorp.com",
      "filters_applied": ["{{ Dimension('member__email') }} = 'alice.chen@techcorp.com'"],
      "metrics": ["total_claims_count"],
      "page": "Benefits Coach"
    }
    ```
    """)

# Key Takeaways
st.header("💡 Key Takeaways")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 🎯 Centralized Metrics

    - **One source of truth** for metric definitions
    - Change in dbt YAML updates all consumers
    - No metric drift between dashboards
    - Consistent business logic
    """)

with col2:
    st.markdown("""
    ### 🔒 Multi-Layer Security

    - **Token scoping** by company
    - **Row-level filters** by member
    - Cannot be bypassed by client
    - Logged and auditable
    - Same pattern for human and AI users
    """)

with col3:
    st.markdown("""
    ### 🤖 AI-Ready Data

    - MCP enables secure AI access
    - Agent discovers metrics dynamically
    - Security enforced in instructions
    - Audit trail for all AI queries
    """)

# Production Considerations
st.header("🚀 Production Considerations")

st.markdown("""
**This is a demo app**. For production, you would add:

1. **Authentication**: OAuth2, SAML, or Snowflake OAuth instead of member selector
2. **Database Audit Log**: Write audit log to Snowflake table instead of session state
3. **Rate Limiting**: Throttle queries per user to prevent abuse
4. **Query Cost Tracking**: Monitor dbt Cloud credits per user/query
5. **Data Masking**: Mask PII fields (SSN, DOB) in UI
6. **Multi-Region**: Deploy Semantic Layer in same region as Snowflake
7. **Caching Strategy**: Use Redis for cross-session query caching
8. **Monitoring**: Alert on security violations, failed queries, high latency
9. **Role-Based Access**: Different metric sets for member vs. broker vs. admin
10. **Compliance**: HIPAA logging, data retention policies, breach notification

**Connection String Management**:
- Demo uses `JDBC_URL` in secrets or `.env` file
- Production should use environment-specific service tokens
- Rotate tokens regularly and never commit to git
""")

st.divider()

st.caption("""
This architecture demonstrates how dbt's Semantic Layer enables governed, secure analytics
for both human users and AI agents, with Snowflake as the performant data warehouse backend.
""")
