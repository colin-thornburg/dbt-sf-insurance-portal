# dbt Snowflake Insurance Portal

A production-grade, multi-tenant insurance member portal built with **dbt Semantic Layer**, **Snowflake**, and **Streamlit**. This app demonstrates secure AI-powered analytics with row-level security, company-scoped tokens, and comprehensive audit logging.

## 🏗️ Architecture

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
                    │   Snowflake DWH    │
                    │ (Row-Level Security)│
                    └────────────────────┘
```

## ✨ Features

### 🔐 Multi-Layered Security
- **Row-level security** via member email filtering injected into every query
- **Company-scoped service tokens** (DBT_TECHCORP_TOKEN, DBT_RETAILPLUS_TOKEN, DBT_MANUFACTURINGCO_TOKEN)
- **Audit logging** with security violation detection
- **Query validation** to ensure proper filters are applied

### 📊 Member Dashboard
- Personalized claims analytics
- Spend tracking and provider breakdowns
- All metrics automatically filtered to the selected member's data

### 🌌 Query Builder
- Interactive metric exploration
- GraphQL query generation
- Python SDK code snippets
- CLI command examples

### 🧠 LLM-Powered Analytics
- RAG-based conversational analytics using plan documents
- Natural language queries over member data
- Powered by **GPT-4o-mini**

### 🩺 Benefits Coach (AI Agent)
- Agentic AI using **OpenAI Agents SDK** with **dbt MCP**
- Direct access to live Snowflake data via Semantic Layer
- Combines plan documents (RAG) with real-time metrics
- Tool calling for dynamic data retrieval

### 🔍 Audit Log
- Track all queries with member context
- Validate security filters are applied
- Detect and flag security violations
- Query performance metrics

### 🎨 Modern UI
- Glassmorphic design with company-specific theming
- **TechCorp**: Indigo/Violet gradient
- **RetailPlus**: Orange/Red gradient
- **ManufacturingCo**: Sky Blue gradient
- Smooth animations and responsive layout

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- dbt Cloud account with Semantic Layer enabled
- Snowflake warehouse
- OpenAI API key (for LLM features)

### 1. Clone the Repository
```bash
git clone <repo-url>
cd dbt-sf-insurance-portal
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

**Option A: Using `uv` (recommended)**
```bash
pip install uv && uv pip install -r requirements.txt
```

**Option B: Using `pip`**
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# dbt Semantic Layer Configuration
DBT_HOST=https://semantic-layer.cloud.getdbt.com
DBT_ENVIRONMENT_ID=your_environment_id

# Company-Scoped Service Tokens (for multi-tenant security)
DBT_TECHCORP_TOKEN=your_techcorp_token
DBT_RETAILPLUS_TOKEN=your_retailplus_token
DBT_MANUFACTURINGCO_TOKEN=your_manufacturingco_token

# Fallback token (optional)
DBT_TOKEN=your_default_token

# OpenAI Configuration (for LLM features)
OPENAI_API_KEY=your_openai_api_key
```

### 5. Run the Application

```bash
streamlit run app.py
```

The app will be available at `http://localhost:8501`

## 📁 Project Structure

```
dbt-sf-insurance-portal/
├── app.py                      # 🔐 Authentication & member selection
├── pages/
│   ├── 01_📊_Member_Dashboard.py    # Member claims & spend analytics
│   ├── 02_🌌_Query_Builder.py       # Interactive query builder
│   ├── 03_🧠_LLM.py                 # RAG-based conversational analytics
│   ├── 04_🩺_Benefits_Coach.py      # AI agent with MCP access
│   ├── 05_🔍_Audit_Log.py           # Security & query audit log
│   └── 06_🏗️_Architecture.py        # Technical documentation
├── audit_logger.py             # Audit logging & security validation
├── client.py                   # dbt Semantic Layer client
├── helpers.py                  # Utility functions
├── styles.py                   # Glassmorphic theme with company colors
├── queries.py                  # GraphQL query templates
├── schema.py                   # Query schema definitions
├── chart.py                    # Visualization utilities
└── llm/
    └── semantic_layer_docs.py  # RAG setup for plan documents
```

## 🔒 Security Architecture

### Row-Level Security
Every query automatically includes a filter based on the selected member's email:
```sql
WHERE {{ Dimension('member__email') }} = 'john.doe@techcorp.com'
```

### Company-Scoped Tokens
The app automatically selects the appropriate service token based on email domain:
- `@techcorp.com` → `DBT_TECHCORP_TOKEN`
- `@retailplus.com` → `DBT_RETAILPLUS_TOKEN`
- `@manufacturingco.com` → `DBT_MANUFACTURINGCO_TOKEN`

### Audit Logging
All queries are logged with:
- Member email
- Filters applied
- Query type (dashboard, builder, LLM, agent)
- Row count returned
- Success/failure status
- Security validation results

## 🎯 Key Use Cases

### 1. Member Self-Service Analytics
Members can view their personalized claims, spending, and provider data through an intuitive dashboard.

### 2. Conversational Insights (LLM)
Ask questions like:
- "Show me my claims for the last 6 months"
- "How much has insurance paid this year?"
- "What providers have I visited?"

### 3. Benefits Guidance (AI Agent)
Get intelligent answers combining plan details with live data:
- "How much of my deductible have I met?"
- "What's my out-of-pocket maximum progress?"
- "Which providers are in my network?"

### 4. Security Compliance
Demonstrate proper data isolation and audit trails for regulatory compliance.

## 🛠️ Development

### Adding New Metrics
1. Define metrics in your dbt project
2. Run a production job in dbt Cloud
3. Metrics automatically appear in the app

### Customizing Themes
Edit `styles.py` to modify company-specific colors:
```python
themes = {
    "YourCompany": {
        "gradient_start": "#HEX_COLOR",
        "gradient_end": "#HEX_COLOR",
        "primary": "#HEX_COLOR",
    }
}
```

### Extending AI Capabilities
- Add plan documents to `llm/plan_details/`
- Modify agent instructions in `pages/04_🩺_Benefits_Coach.py`
- Adjust MCP tool filtering for security

## 📊 Tech Stack

- **Frontend**: Streamlit
- **Data Layer**: dbt Semantic Layer (GraphQL API)
- **AI/ML**: OpenAI (GPT-4o-mini), OpenAI Agents SDK
- **Agent Protocol**: Model Context Protocol (MCP)
- **Data Warehouse**: Snowflake
- **Authentication**: Session-based member context
- **Styling**: Custom glassmorphic CSS

## 📝 License

See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

This is a demo application showcasing dbt Semantic Layer capabilities. For production use, consider additional authentication, authorization, and infrastructure hardening.

---

Built with ❤️ using [dbt Semantic Layer](https://www.getdbt.com/product/semantic-layer) and [Streamlit](https://streamlit.io)
