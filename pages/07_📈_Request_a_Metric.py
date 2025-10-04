# stdlib
import asyncio
import base64
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

# third party
import streamlit as st
from github import Github, GithubException
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# GitHub configuration (works with Streamlit Cloud)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO_OWNER = os.getenv("GITHUB_REPO_OWNER", "colin-thornburg")
GITHUB_REPO_NAME = os.getenv("GITHUB_REPO_NAME", "embedded-app")
GITHUB_DEFAULT_BRANCH = os.getenv("GITHUB_DEFAULT_BRANCH", "main")
GITHUB_SEMANTIC_MODELS_PATH = os.getenv("GITHUB_SEMANTIC_MODELS_PATH", "models/semantic/semantic_models.yml")


def validate_environment() -> bool:
    """Validate required environment variables."""
    required_env = {
        "OPENAI_API_KEY": "OpenAI API key for generating metrics",
        "GITHUB_TOKEN": "GitHub Personal Access Token for creating PRs",
        "GITHUB_REPO_OWNER": "GitHub repository owner (e.g., colin-thornburg)",
        "GITHUB_REPO_NAME": "GitHub repository name (e.g., embedded-app)",
    }
    
    missing = {k: v for k, v in required_env.items() if not os.getenv(k)}
    
    if missing:
        st.error("❌ Missing Required Environment Variables")
        st.markdown("The following environment variables need to be configured:")
        for env_var, description in missing.items():
            st.markdown(f"- **`{env_var}`**: {description}")
        
        with st.expander("🔧 How to Configure", expanded=False):
            st.markdown(
                """
                ### For Streamlit Cloud:
                1. Go to your app settings
                2. Click on "Secrets"
                3. Add these variables:
                
                ```toml
                OPENAI_API_KEY = "your_openai_key"
                GITHUB_TOKEN = "your_github_token"
                GITHUB_REPO_OWNER = "your_github_username"
                GITHUB_REPO_NAME = "your_repo_name"
                ```
                
                ### For Local Development:
                Add these to your `.streamlit/secrets.toml` file.
                
                ### Generate GitHub Token:
                1. Go to GitHub → Settings → Developer settings
                2. Personal access tokens → Tokens (classic)
                3. Generate new token with `repo` scope
                """
            )
        return False
    
    return True


def validate_github_access() -> tuple[bool, str]:
    """Validate GitHub API access and repository permissions."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        
        # Check if we have write access
        if not repo.permissions.push:
            return False, f"No write access to repository {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}"
        
        # Check if the semantic models file exists
        try:
            repo.get_contents(GITHUB_SEMANTIC_MODELS_PATH, ref=GITHUB_DEFAULT_BRANCH)
        except GithubException as e:
            return False, f"Semantic models file not found at {GITHUB_SEMANTIC_MODELS_PATH}"
        
        logger.info(f"Successfully validated access to {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        return True, f"GitHub repository access verified"
    
    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
        if e.status == 401:
            return False, "GitHub token is invalid. Please check your GITHUB_TOKEN"
        elif e.status == 404:
            return False, f"Repository {GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME} not found or no access"
        else:
            return False, f"GitHub API error: {e.data.get('message', str(e))}"
    except Exception as e:
        logger.error(f"Unexpected error validating GitHub access: {e}")
        return False, f"Unexpected error: {str(e)}"


def read_semantic_models_from_github() -> str:
    """Read the semantic models YAML file from GitHub."""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        
        # Get file from GitHub
        file_content = repo.get_contents(GITHUB_SEMANTIC_MODELS_PATH, ref=GITHUB_DEFAULT_BRANCH)
        
        # Decode base64 content
        content = base64.b64decode(file_content.content).decode('utf-8')
        logger.info(f"Successfully read {GITHUB_SEMANTIC_MODELS_PATH} from GitHub")
        return content
    
    except GithubException as e:
        logger.error(f"Failed to read semantic models from GitHub: {e}")
        raise FileNotFoundError(f"Could not read {GITHUB_SEMANTIC_MODELS_PATH} from GitHub: {e}")
    except Exception as e:
        logger.error(f"Unexpected error reading from GitHub: {e}")
        raise


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


def create_branch_and_update_file(metric_name: str, new_measures_yaml: Optional[str], new_metric_yaml: str, commit_message: str) -> str:
    """Create a new branch and update the semantic models file via GitHub API."""
    branch_name = f"metric/{metric_name.replace('_', '-')}"
    
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        
        # Get the current file from main branch
        file = repo.get_contents(GITHUB_SEMANTIC_MODELS_PATH, ref=GITHUB_DEFAULT_BRANCH)
        current_content = base64.b64decode(file.content).decode('utf-8')
        
        # Update content
        updated_content = current_content
        
        # Add new measures if needed
        if new_measures_yaml and new_measures_yaml.strip():
            metrics_index = updated_content.find("\nmetrics:")
            if metrics_index != -1:
                updated_content = updated_content[:metrics_index] + "\n" + new_measures_yaml.strip() + updated_content[metrics_index:]
        
        # Add new metric at the end
        updated_content += "\n" + new_metric_yaml.strip() + "\n"
        
        # Get the SHA of the main branch
        main_branch = repo.get_branch(GITHUB_DEFAULT_BRANCH)
        
        # Create new branch from main
        repo.create_git_ref(ref=f"refs/heads/{branch_name}", sha=main_branch.commit.sha)
        logger.info(f"Created branch: {branch_name}")
        st.info(f"✅ Created branch: `{branch_name}`")
        
        # Update file in new branch
        full_commit_message = f"""{commit_message}

🤖 Generated via AI Benefits Portal

Co-Authored-By: AI Agent <noreply@example.com>"""
        
        repo.update_file(
            path=GITHUB_SEMANTIC_MODELS_PATH,
            message=full_commit_message,
            content=updated_content,
            sha=file.sha,
            branch=branch_name
        )
        
        logger.info(f"Updated {GITHUB_SEMANTIC_MODELS_PATH} in branch {branch_name}")
        st.info(f"✅ Updated {GITHUB_SEMANTIC_MODELS_PATH}")
        
        return branch_name
    
    except GithubException as e:
        logger.error(f"GitHub API error: {e}")
        st.error(f"Failed to create branch or update file: {e.data.get('message', str(e))}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        st.error(f"Unexpected error: {str(e)}")
        raise


def create_pull_request_via_api(branch_name: str, metric_name: str, explanation: str) -> str:
    """Create a pull request using GitHub API."""
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

🤖 Generated via AI Benefits Portal
"""

    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        
        # Create pull request
        pr = repo.create_pull(
            title=pr_title,
            body=pr_body,
            head=branch_name,
            base=GITHUB_DEFAULT_BRANCH
        )
        
        pr_url = pr.html_url
        logger.info(f"Created PR: {pr_url}")
        st.success(f"✅ Pull request created!")
        
        return pr_url
    
    except GithubException as e:
        logger.error(f"Failed to create PR: {e}")
        st.error(f"Failed to create pull request: {e.data.get('message', str(e))}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error creating PR: {e}")
        st.error(f"Unexpected error: {str(e)}")
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

# Show GitHub repository status
with st.expander("🔧 System Status (Advanced)", expanded=False):
    st.caption("Check that GitHub connection is properly configured.")
    github_valid, github_message = validate_github_access()
    if github_valid:
        st.success(f"✅ {github_message}")
        st.info(f"**Repository:** `{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}`\n\n**Branch:** `{GITHUB_DEFAULT_BRANCH}`\n\n**File:** `{GITHUB_SEMANTIC_MODELS_PATH}`")
    else:
        st.error(f"❌ {github_message}")
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

    # Validate GitHub access early
    github_valid, github_message = validate_github_access()
    if not github_valid:
        st.error(f"❌ GitHub Access Issue\n\n{github_message}")
        st.info("💡 Fix the issue above and try again.")
        st.stop()

    with st.spinner("Analyzing your request..."):
        try:
            # Read existing semantic models from GitHub
            with st.status("Reading current semantic models from GitHub...") as status:
                existing_models = read_semantic_models_from_github()
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
                    # Create branch and update file via GitHub API
                    with st.status("Creating branch and updating file...") as status:
                        branch_name = create_branch_and_update_file(
                            result.get("metric_name"),
                            result.get("new_measures_yaml"),
                            result.get("new_metric_yaml"),
                            result.get("commit_message")
                        )
                        status.update(label=f"✅ Created branch and committed changes", state="complete")

                    # Create PR via GitHub API
                    with st.status("Creating pull request...") as status:
                        pr_url = create_pull_request_via_api(
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

# Show recent PRs via GitHub API
with st.expander("📋 Recent Metric Pull Requests", expanded=False):
    st.caption("View recent metric PRs from your team")
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(f"{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}")
        
        # Get recent PRs (limit to 10)
        pulls = repo.get_pulls(state='all', sort='created', direction='desc')
        prs = []
        for pr in pulls[:10]:
            prs.append({
                'number': pr.number,
                'title': pr.title,
                'url': pr.html_url,
                'state': pr.state.upper(),
                'merged': pr.merged
            })
        
        if prs:
            for pr in prs:
                # Determine status emoji
                if pr['merged']:
                    status_emoji = "✅"
                    state = "MERGED"
                elif pr['state'] == "OPEN":
                    status_emoji = "🔄"
                    state = "OPEN"
                else:
                    status_emoji = "❌"
                    state = "CLOSED"
                
                st.markdown(f"{status_emoji} **[#{pr['number']} - {pr['title']}]({pr['url']})** ({state})")
        else:
            st.info("No recent pull requests found in this repository.")
    except Exception as e:
        st.warning("Unable to fetch recent PRs via GitHub API.")
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
        
        **Q: How does this work without local git?**  
        A: This feature uses the GitHub API to create branches, commit changes, and open PRs 
        directly from the cloud. No local setup required!
        
        ### Prerequisites
        - GitHub Personal Access Token with `repo` scope
        - OpenAI API key
        - Write access to the dbt repository
        - Environment variables configured in Streamlit Cloud secrets
        """
    )
