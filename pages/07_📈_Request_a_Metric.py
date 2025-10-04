# stdlib
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

# third party
import streamlit as st
from openai import OpenAI

# first party
from helpers import ensure_member_context, get_portal_title
from init_app import initialize_app
from styles import apply_glassmorphic_theme

st.set_page_config(
    page_title="AI Benefits Portal - Request a Metric",
    page_icon="📈",
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
    from agents.mcp.server import MCPServerStdio
except ImportError:
    st.error(
        "The OpenAI Agents SDK is not installed. Install it with `pip install openai-agents` (or `pip install dbt-mcp[agents]`) and restart the app."
    )
    st.stop()

logger = logging.getLogger("request_metric")
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
company_name = current_member.get("company_display")
portal_title = get_portal_title(company_name)

# Apply glassmorphic theme with company-specific colors
apply_glassmorphic_theme(company_name)

st.title(f"{portal_title} · Request a Metric")

st.markdown(
    """
    ### 🎯 What This Does
    
    This tool empowers you to request new metrics for your insurance data without writing any code. 
    Simply describe what you want to measure in plain English, and AI will:
    
    1. **Analyze** your existing dbt semantic models
    2. **Generate** the required YAML code (metrics and measures)
    3. **Create** a pull request in your dbt project repository
    4. **Document** everything clearly for your data team to review
    
    Once the PR is approved and merged, your new metric will automatically be available in this portal!
    """
)

st.divider()

st.markdown(
    """
    ### 📚 How It Works
    
    **Step 1: Describe Your Metric**  
    Tell us what you want to measure in plain language. Be specific about:
    - What you're measuring (e.g., "average", "total", "ratio")
    - What data you're measuring (e.g., "claim amounts", "approval rates")
    - Any groupings or filters (e.g., "per member", "by claim type")
    
    **Step 2: AI Generates YAML**  
    OpenAI analyzes your request and your existing semantic models to generate:
    - New measures (if needed)
    - The metric definition
    - Clear documentation
    
    **Step 3: Review & Approve**  
    You'll see the generated YAML code and can review it before creating a PR.
    
    **Step 4: Pull Request Created**  
    A new branch is created, changes are committed, and a PR is opened for your data team to review.
    
    **Step 5: Deploy to Production**  
    Once the PR is merged and your dbt job runs, the metric becomes available in this portal!
    """
)

st.divider()

# Environment configuration
DBT_MCP_ENV_FILE = os.getenv(
    "DBT_MCP_ENV_FILE",
    str(Path(__file__).resolve().parents[1] / ".env"),
)
DBT_MCP_COMMAND = os.getenv("DBT_MCP_COMMAND", "uvx")
DBT_MCP_ENTRY = os.getenv("DBT_MCP_ENTRY", "dbt-mcp")
MCP_CLIENT_TIMEOUT = int(os.getenv("DBT_MCP_CLIENT_TIMEOUT", "20"))
DBT_PROJECT_DIR = os.getenv("DBT_PROJECT_DIR")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# GitHub configuration
EMBEDDED_APP_REPO = "https://github.com/colin-thornburg/embedded-app.git"
EMBEDDED_APP_DIR = "/Users/colinthornburg/snow_dcwt/embedded-app"
SEMANTIC_MODELS_FILE = "models/semantic/semantic_models.yml"


def validate_environment() -> bool:
    """Validate required environment variables and directories."""
    # DBT_PROJECT_DIR is only needed for local development, not for Streamlit Cloud
    required_env = [
        "DBT_HOST",
        "DBT_TOKEN",
        "DBT_PROD_ENV_ID",
        "OPENAI_API_KEY",
    ]
    missing = [env for env in required_env if not os.getenv(env)]
    if missing:
        st.error(
            "Missing required environment variables: " + ", ".join(missing)
        )
        return False
    
    # Only validate local paths if DBT_PROJECT_DIR is set (local development)
    if DBT_PROJECT_DIR:
        if not Path(DBT_MCP_ENV_FILE).exists():
            st.error(
                f"MCP environment file not found at `{DBT_MCP_ENV_FILE}`. Set `DBT_MCP_ENV_FILE` or create the file."
            )
            return False
        if not Path(EMBEDDED_APP_DIR).exists():
            st.error(
                f"dbt project directory not found at `{EMBEDDED_APP_DIR}`. Clone the repository first."
            )
            return False
    else:
        # Running in Streamlit Cloud - this feature requires local setup
        st.info(
            """
            ℹ️ **Request a Metric** requires a local dbt project setup.
            
            This feature creates pull requests in your dbt repository, which requires:
            - Local clone of your dbt project
            - GitHub CLI installed and authenticated
            - Write access to the repository
            
            This feature is currently only available when running locally.
            """
        )
        return False
    
    return True


def validate_git_state() -> tuple[bool, str]:
    """Validate git repository state before creating PR."""
    import subprocess

    try:
        # Check if gh CLI is available
        result = subprocess.run(
            ["gh", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, "GitHub CLI (gh) is not installed. Install it with: `brew install gh`"

        # Check if gh is authenticated
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, "GitHub CLI is not authenticated. Run: `gh auth login`"

        # For demo purposes: automatically switch to main if not already on it
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=EMBEDDED_APP_DIR,
            capture_output=True,
            text=True,
            check=True
        )

        current_branch = result.stdout.strip()
        if current_branch != "main":
            logger.info(f"Currently on branch '{current_branch}', switching to main...")
            try:
                # Switch to main branch
                subprocess.run(
                    ["git", "checkout", "main"],
                    cwd=EMBEDDED_APP_DIR,
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info("Successfully switched to main branch")
            except subprocess.CalledProcessError as e:
                return False, f"Failed to switch to main branch: {e.stderr if e.stderr else str(e)}"

        # Check for uncommitted changes (but be lenient for demo)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=EMBEDDED_APP_DIR,
            capture_output=True,
            text=True,
            check=True
        )

        if result.stdout.strip():
            # For demo: try to stash changes automatically
            logger.info("Found uncommitted changes, attempting to stash...")
            try:
                subprocess.run(
                    ["git", "stash", "-u"],
                    cwd=EMBEDDED_APP_DIR,
                    capture_output=True,
                    text=True,
                    check=True
                )
                logger.info("Successfully stashed uncommitted changes")
            except subprocess.CalledProcessError as e:
                return False, f"The dbt project has uncommitted changes. Please commit or stash them first.\n\nUncommitted files:\n{result.stdout}"

        # Fetch and pull latest from origin
        subprocess.run(
            ["git", "fetch", "origin"],
            cwd=EMBEDDED_APP_DIR,
            capture_output=True,
            check=True
        )

        # Pull latest main
        subprocess.run(
            ["git", "pull", "origin", "main"],
            cwd=EMBEDDED_APP_DIR,
            capture_output=True,
            check=True
        )

        return True, "Git state is ready"

    except subprocess.CalledProcessError as e:
        logger.error(f"Git validation error: {e.stderr if e.stderr else str(e)}")
        return False, f"Git command failed: {e.stderr if e.stderr else str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during git validation: {e}")
        return False, f"Unexpected error: {str(e)}"


async def read_semantic_models_via_mcp() -> Optional[str]:
    """Read existing semantic models using dbt MCP."""
    try:
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
        ) as server:
            # List available resources
            logger.info("Listing dbt resources via MCP...")
            tools = await server.client.list_tools()
            logger.info(f"Available MCP tools: {[t.name for t in tools.tools]}")

            # For now, we'll read the file directly since MCP doesn't expose file reading
            # In the future, we could use get_resource if it provides YAML content
            return None
    except Exception as e:
        logger.error(f"Error reading via MCP: {e}")
        return None


def read_semantic_models_file() -> str:
    """Read the semantic models YAML file directly."""
    file_path = Path(EMBEDDED_APP_DIR) / SEMANTIC_MODELS_FILE
    if not file_path.exists():
        raise FileNotFoundError(f"Semantic models file not found at {file_path}")
    return file_path.read_text()


def generate_metric_yaml(user_request: str, existing_models: str) -> Dict:
    """Use OpenAI to analyze the request and generate metric YAML."""
    client = OpenAI(api_key=OPENAI_API_KEY)

    system_prompt = f"""You are a dbt Semantic Layer expert. Analyze the user's metric request and generate the appropriate YAML code.

Current semantic models:
```yaml
{existing_models}
```

Your task:
1. Determine if the requested metric already exists (if so, explain that)
2. Determine if new measures need to be added to semantic models
3. Generate the complete YAML code for the new metric (and measures if needed)
4. Provide a clear explanation of what you're adding

Return your response as JSON with this structure:
{{
    "metric_exists": true/false,
    "requires_new_measures": true/false,
    "new_measures_yaml": "YAML code for new measures (if needed)",
    "new_metric_yaml": "YAML code for the new metric",
    "explanation": "Clear explanation of what you're adding and why",
    "metric_name": "suggested_metric_name",
    "commit_message": "Brief commit message for the PR"
}}

Guidelines:
- Follow dbt Semantic Layer best practices
- Use appropriate metric types (simple, ratio, derived, cumulative)
- Include clear descriptions
- Match the existing YAML structure and indentation
- For ratio metrics, ensure both numerator and denominator measures exist
- Use snake_case for metric names
"""

    user_prompt = f"""I need a metric for: {user_request}

Please analyze the existing semantic models and generate the appropriate YAML code."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        logger.info(f"Generated metric analysis: {result}")
        return result
    except Exception as e:
        logger.error(f"Error generating metric: {e}")
        raise


def create_git_branch(metric_name: str) -> str:
    """Create a new git branch for the metric."""
    import subprocess

    branch_name = f"metric/{metric_name.replace('_', '-')}"

    try:
        # Create and checkout new branch (we already validated we're on main)
        result = subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=EMBEDDED_APP_DIR,
            check=True,
            capture_output=True,
            text=True
        )

        logger.info(f"Created branch: {branch_name}")
        st.info(f"✅ Created branch: `{branch_name}`")
        return branch_name
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        logger.error(f"Git branch creation failed: {error_msg}")
        st.error(f"Failed to create git branch: {error_msg}")
        raise


def update_semantic_models_file(new_measures_yaml: Optional[str], new_metric_yaml: str):
    """Update the semantic models YAML file with new content."""
    file_path = Path(EMBEDDED_APP_DIR) / SEMANTIC_MODELS_FILE
    current_content = file_path.read_text()

    updated_content = current_content

    # Add new measures if needed (insert before metrics section)
    if new_measures_yaml and new_measures_yaml.strip():
        # Find the measures section and add to it
        # This is a simple append - in production you'd want more sophisticated YAML parsing
        metrics_index = updated_content.find("\nmetrics:")
        if metrics_index != -1:
            updated_content = updated_content[:metrics_index] + "\n" + new_measures_yaml.strip() + updated_content[metrics_index:]

    # Add new metric at the end
    updated_content += "\n" + new_metric_yaml.strip() + "\n"

    file_path.write_text(updated_content)
    logger.info(f"Updated {file_path}")


def commit_and_push(branch_name: str, commit_message: str):
    """Commit changes and push to remote."""
    import subprocess

    try:
        # Add the semantic models file
        result = subprocess.run(
            ["git", "add", SEMANTIC_MODELS_FILE],
            cwd=EMBEDDED_APP_DIR,
            check=True,
            capture_output=True,
            text=True
        )

        # Commit
        full_message = f"""{commit_message}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

        result = subprocess.run(
            ["git", "commit", "-m", full_message],
            cwd=EMBEDDED_APP_DIR,
            check=True,
            capture_output=True,
            text=True
        )
        st.info(f"✅ Committed changes")

        # Push
        result = subprocess.run(
            ["git", "push", "-u", "origin", branch_name],
            cwd=EMBEDDED_APP_DIR,
            check=True,
            capture_output=True,
            text=True
        )
        st.info(f"✅ Pushed to remote: `{branch_name}`")

        logger.info(f"Committed and pushed to {branch_name}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        logger.error(f"Git commit/push failed: {error_msg}")
        st.error(f"Failed to commit/push: {error_msg}")
        raise


def create_pull_request(branch_name: str, metric_name: str, explanation: str) -> str:
    """Create a pull request using gh CLI."""
    import subprocess

    pr_title = f"Add metric: {metric_name}"
    pr_body = f"""## Summary
- Added new metric: `{metric_name}`

## Details
{explanation}

## Test Plan
- [ ] Run `dbt parse` to validate YAML syntax
- [ ] Run `dbt build` to ensure models compile
- [ ] Query the new metric via Semantic Layer to verify it works
- [ ] Check that the metric appears in downstream applications

🤖 Generated with [Claude Code](https://claude.com/claude-code)
"""

    try:
        result = subprocess.run(
            [
                "gh", "pr", "create",
                "--title", pr_title,
                "--body", pr_body,
                "--base", "main",
                "--head", branch_name
            ],
            cwd=EMBEDDED_APP_DIR,
            check=True,
            capture_output=True,
            text=True
        )

        pr_url = result.stdout.strip()
        logger.info(f"Created PR: {pr_url}")
        st.success(f"✅ Pull request created!")
        
        # Switch back to main branch for future requests
        try:
            subprocess.run(
                ["git", "checkout", "main"],
                cwd=EMBEDDED_APP_DIR,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("Switched back to main branch")
            st.info("✅ Switched back to main branch")
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to switch to main branch: {e.stderr if e.stderr else str(e)}")
            # Don't fail the whole operation if we can't switch branches
            pass
        
        return pr_url
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr if e.stderr else str(e)
        logger.error(f"PR creation failed: {error_msg}")
        st.error(f"Failed to create PR: {error_msg}")
        raise


# Main UI

st.markdown("### ✨ Step 1: Describe Your Metric")

st.info(
    """
    **💡 Tips for Great Metric Requests:**
    
    **Be Specific:** Instead of "claims data", say "average claim amount per member"
    
    **Include Calculations:** For ratios, specify both parts (e.g., "approved claims divided by total claims")
    
    **Mention Time Periods:** If relevant, include time context (e.g., "claims in the last 30 days")
    
    **Use Business Language:** Describe what the business needs, not technical SQL
    """
)

with st.expander("📋 Example Metric Requests", expanded=False):
    st.markdown(
        """
        **Simple Aggregations:**
        - "Average claim amount per member"
        - "Total claims count by claim type"
        - "Sum of member responsibility amounts"
        
        **Ratios:**
        - "Claim approval rate (approved claims divided by total claims)"
        - "Out-of-pocket ratio (member responsibility divided by total claim amount)"
        - "Claim denial rate by provider"
        
        **Time-Based Metrics:**
        - "Average days to claim settlement"
        - "Claims submitted in the last 30 days"
        - "Month-over-month claim growth"
        
        **Advanced Metrics:**
        - "Average claim amount per member by claim type"
        - "Percentage of claims over $1000"
        - "Member with highest total claim amount"
        """
    )

user_request = st.text_area(
    "📝 Describe your metric in plain English:",
    placeholder="Example: I want to track the average claim amount for each claim type, showing how much members typically pay versus what insurance covers.",
    height=120,
    help="Be as specific as possible. Include what you're measuring, how to calculate it, and any groupings or filters."
)

# Show git repository status
with st.expander("🔧 System Status (Advanced)", expanded=False):
    st.caption("Check that your local dbt project and GitHub connection are properly configured.")
    git_valid, git_message = validate_git_state()
    if git_valid:
        st.success(f"✅ {git_message}")
        st.info(f"**Repository:** {EMBEDDED_APP_REPO}\n\n**Local Path:** `{EMBEDDED_APP_DIR}`")
    else:
        st.error(f"❌ {git_message}")
        st.warning("⚠️ Please fix the issues above before creating a metric PR.")

# Initialize session state
if "generated_metric" not in st.session_state:
    st.session_state.generated_metric = None
if "pr_created" not in st.session_state:
    st.session_state.pr_created = False

# Step 1: Generate the metric YAML
if st.button("🚀 Generate Metric YAML", type="primary", disabled=not user_request):
    if not validate_environment():
        st.stop()

    # Validate git state early
    git_valid, git_message = validate_git_state()
    if not git_valid:
        st.error(f"❌ Git Repository Issue\n\n{git_message}")
        st.info("💡 Fix the issue above and try again.")
        st.stop()

    with st.spinner("Analyzing your request..."):
        try:
            # Read existing semantic models
            with st.status("Reading current semantic models...") as status:
                existing_models = read_semantic_models_file()
                status.update(label="✅ Read semantic models", state="complete")

            # Generate metric YAML using OpenAI
            with st.status("Generating metric YAML with OpenAI...") as status:
                result = generate_metric_yaml(user_request, existing_models)
                status.update(label="✅ Generated metric YAML", state="complete")

            # Check if metric already exists
            if result.get("metric_exists"):
                st.warning(f"⚠️ {result.get('explanation')}")
                st.session_state.generated_metric = None
                st.stop()

            # Store in session state
            st.session_state.generated_metric = result
            st.session_state.pr_created = False

        except Exception as e:
            logger.exception("Error in metric request workflow")
            st.error(f"❌ An error occurred: {str(e)}")
            st.session_state.generated_metric = None

# Step 2: Display generated metric if available
if st.session_state.generated_metric and not st.session_state.pr_created:
    result = st.session_state.generated_metric

    st.divider()
    st.markdown("### ✅ Step 2: Review Generated Code")
    
    st.success("🎉 AI successfully generated your metric definition!")
    
    with st.expander("📝 What This Metric Does", expanded=True):
        st.markdown(result.get("explanation"))
        st.caption(f"**Metric Name:** `{result.get('metric_name')}`")

    if result.get("requires_new_measures") and result.get("new_measures_yaml"):
        with st.expander("🔧 New Measures (Building Blocks)", expanded=False):
            st.markdown(
                """
                These are new **measures** that need to be added to your semantic models. 
                Measures are the raw aggregations (like `sum`, `count`, `avg`) that metrics are built from.
                """
            )
            st.code(result.get("new_measures_yaml"), language="yaml")

    with st.expander("📊 New Metric Definition", expanded=True):
        st.markdown(
            """
            This is the **metric** definition that will be added to your dbt project. 
            Once merged and deployed, this metric will be queryable through the Semantic Layer.
            """
        )
        st.code(result.get("new_metric_yaml"), language="yaml")

    # Step 3: Confirm and create PR
    st.divider()
    st.markdown("### 🚀 Step 3: Create Pull Request")
    
    st.info(
        """
        **What happens next:**
        1. A new Git branch will be created (e.g., `metric/your-metric-name`)
        2. The YAML code will be added to your semantic models file
        3. Changes will be committed and pushed to GitHub
        4. A pull request will be opened for your data team to review
        5. Once approved and merged, run a dbt job to make the metric available
        """
    )
    
    col1, col2, col3 = st.columns([2, 2, 3])
    
    with col1:
        if st.button("✅ Create Pull Request", type="primary", use_container_width=True):
            with st.spinner("Creating pull request..."):
                try:
                    # Create git branch
                    with st.status("Creating git branch...") as status:
                        branch_name = create_git_branch(result.get("metric_name"))
                        status.update(label=f"✅ Created branch: {branch_name}", state="complete")

                    # Update file
                    with st.status("Updating semantic models file...") as status:
                        update_semantic_models_file(
                            result.get("new_measures_yaml"),
                            result.get("new_metric_yaml")
                        )
                        status.update(label="✅ Updated semantic models", state="complete")

                    # Commit and push
                    with st.status("Committing and pushing changes...") as status:
                        commit_and_push(branch_name, result.get("commit_message"))
                        status.update(label="✅ Pushed to GitHub", state="complete")

                    # Create PR
                    with st.status("Creating pull request...") as status:
                        pr_url = create_pull_request(
                            branch_name,
                            result.get("metric_name"),
                            result.get("explanation")
                        )
                        status.update(label="✅ Pull request created!", state="complete")

                    st.success(f"🎉 Pull request created successfully!")
                    st.markdown(f"### [🔗 View Pull Request on GitHub]({pr_url})")
                    st.info(
                        """
                        **Next Steps:**
                        1. Review the PR on GitHub
                        2. Request review from your data team
                        3. Once approved, merge the PR
                        4. Run your dbt production job
                        5. The metric will be available in this portal!
                        """
                    )
                    st.balloons()

                    st.session_state.pr_created = True

                except Exception as e:
                    logger.exception("Error creating PR")
                    st.error(f"❌ Failed to create PR: {str(e)}")
                    st.info("💡 Check the System Status section above to troubleshoot.")

    with col2:
        if st.button("❌ Cancel", use_container_width=True):
            st.session_state.generated_metric = None
            st.rerun()
    
    with col3:
        st.caption("Review the generated code before creating a PR")


st.divider()

# Show recent PRs (optional)
with st.expander("📋 Recent Metric Pull Requests", expanded=False):
    st.caption("View recent metric PRs from your team")
    try:
        import subprocess
        result = subprocess.run(
            ["gh", "pr", "list", "--limit", "10", "--json", "number,title,url,state"],
            cwd=EMBEDDED_APP_DIR,
            capture_output=True,
            text=True,
            check=True
        )
        prs = json.loads(result.stdout)

        if prs:
            for pr in prs:
                status_emoji = "✅" if pr['state'] == "MERGED" else "🔄" if pr['state'] == "OPEN" else "❌"
                st.markdown(f"{status_emoji} **[#{pr['number']} - {pr['title']}]({pr['url']})** ({pr['state']})")
        else:
            st.info("No recent pull requests found in this repository.")
    except Exception as e:
        st.warning("Unable to fetch recent PRs. Make sure GitHub CLI (`gh`) is installed and authenticated.")
        st.caption(f"Error: {str(e)}")

# Help section
with st.expander("❓ Need Help?", expanded=False):
    st.markdown(
        """
        ### Common Questions
        
        **Q: How long does it take for my metric to appear?**  
        A: Once the PR is merged, you need to run a dbt production job. After that job completes, 
        refresh this portal and your metric will be available.
        
        **Q: Can I edit the generated YAML?**  
        A: Yes! After the PR is created, you can edit the files directly on GitHub before merging.
        
        **Q: What if the AI gets it wrong?**  
        A: Review the generated code carefully. If it's not quite right, you can either:
        - Try rephrasing your request
        - Edit the PR directly on GitHub
        - Close the PR and start over
        
        **Q: Who reviews the PR?**  
        A: Your data team or dbt project maintainers should review it to ensure:
        - The metric logic is correct
        - It follows your team's naming conventions
        - It doesn't duplicate existing metrics
        
        **Q: What if I don't have permission to create PRs?**  
        A: You'll need write access to the dbt repository. Contact your data team to request access.
        
        ### Prerequisites
        - GitHub CLI (`gh`) installed and authenticated
        - Write access to the dbt repository
        - Local clone of the dbt project
        - OpenAI API key configured
        - dbt Cloud credentials configured
        """
    )
