"""
Modern glassmorphic styling for the Streamlit app.
Provides a clean, modern UI with frosted glass effects.
"""

import streamlit as st


def hex_to_rgb(hex_color: str) -> str:
    """Convert hex color to RGB values for rgba() CSS"""
    hex_color = hex_color.lstrip('#')
    return f"{int(hex_color[0:2], 16)}, {int(hex_color[2:4], 16)}, {int(hex_color[4:6], 16)}"


def apply_glassmorphic_theme(company_name: str = None):
    """
    Apply modern glassmorphic theme to the app with company-specific colors.

    Args:
        company_name: Name of the company to apply theme for (TechCorp, RetailPlus, ManufacturingCo)
    """
    
    # Prevent flash of unstyled content (FOUC) by hiding content until styles load
    st.markdown("""
    <style>
    /* Prevent FOUC - set base styles immediately */
    .stApp {
        opacity: 1 !important;
        transition: opacity 0.3s ease-in !important;
    }
    </style>
    """, unsafe_allow_html=True)
    # Company-specific color schemes
    themes = {
        "TechCorp": {
            "gradient_start": "#4F46E5",  # Indigo
            "gradient_end": "#7C3AED",    # Violet
            "primary": "#4F46E5",
        },
        "RetailPlus": {
            "gradient_start": "#EA580C",  # Orange
            "gradient_end": "#DC2626",    # Red
            "primary": "#EA580C",
        },
        "ManufacturingCo": {
            "gradient_start": "#0EA5E9",  # Sky blue
            "gradient_end": "#0284C7",    # Blue
            "primary": "#0EA5E9",
        },
        "default": {
            "gradient_start": "#667eea",  # Purple
            "gradient_end": "#764ba2",    # Dark purple
            "primary": "#667eea",
        }
    }

    theme = themes.get(company_name, themes["default"])
    gradient_start = theme["gradient_start"]
    gradient_end = theme["gradient_end"]
    primary = theme["primary"]

    # Calculate RGB values for rgba() CSS
    primary_rgb = hex_to_rgb(primary)
    gradient_end_rgb = hex_to_rgb(gradient_end)

    st.markdown(f"""
    <style>
    /* CACHE BUST - Version 2.0 */
    /* Import modern font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* Global styles - prevent FOUC */
    * {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Main app background with gradient */
    .stApp {{
        background: linear-gradient(135deg, {gradient_start} 0%, {gradient_end} 100%);
        background-attachment: fixed;
    }}

    /* Sidebar glassmorphism */
    [data-testid="stSidebar"] {{
        background: rgba(255, 255, 255, 0.1) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.2) !important;
    }}

    /* Sidebar text - all white for visibility */
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}

    /* Sidebar captions and emails */
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] .caption {{
        color: white !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3) !important;
    }}

    /* Sidebar strong emphasis */
    [data-testid="stSidebar"] strong {{
        color: white !important;
        font-weight: 700 !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.4) !important;
    }}

    [data-testid="stSidebarNav"] {{
        background: transparent !important;
    }}

    /* Sidebar nav items */
    [data-testid="stSidebarNav"] a {{
        background: rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px !important;
        margin: 4px 0 !important;
        padding: 12px 16px !important;
        transition: all 0.3s ease !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }}

    [data-testid="stSidebarNav"] a:hover {{
        background: rgba(255, 255, 255, 0.2) !important;
        transform: translateX(4px);
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
    }}

    [data-testid="stSidebarNav"] a[aria-current="page"] {{
        background: rgba(255, 255, 255, 0.25) !important;
        border: 1px solid rgba(255, 255, 255, 0.4) !important;
        font-weight: 600 !important;
    }}

    /* Main content area */
    .main .block-container {{
        padding: 2rem !important;
        max-width: 1400px !important;
        background: transparent !important;
    }}

    /* Remove default stApp background in main area to prevent white boxes */
    .main {{
        background: transparent !important;
    }}

    /* AGGRESSIVE: All markdown and text elements WHITE by default */
    [data-testid="stMarkdown"] p,
    [data-testid="stMarkdown"] span,
    [data-testid="stMarkdown"] div,
    [data-testid="stText"],
    .main [data-testid="stMarkdown"] {{
        color: white !important;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.6) !important;
        font-weight: 600 !important;
    }}

    /* Dark text inside columns and cards */
    [data-testid="column"] [data-testid="stMarkdown"] p,
    [data-testid="column"] [data-testid="stMarkdown"] span,
    [data-testid="column"] [data-testid="stMarkdown"] div {{
        color: #1e293b !important;
        text-shadow: none !important;
        font-weight: 500 !important;
    }}

    /* Captions - white with strong shadow for contrast */
    .main [data-testid="stCaptionContainer"] {{
        color: white !important;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.6) !important;
        font-weight: 600 !important;
    }}

    [data-testid="column"] [data-testid="stCaptionContainer"] {{
        color: #475569 !important;
        text-shadow: none !important;
        font-weight: 500 !important;
    }}

    /* Links - white with strong contrast */
    [data-testid="stMarkdown"] a {{
        color: white !important;
        border-bottom: 2px solid rgba(255, 255, 255, 0.8) !important;
        font-weight: 700 !important;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.6) !important;
        text-decoration: none !important;
    }}

    [data-testid="stMarkdown"] a:hover {{
        background: rgba(255, 255, 255, 0.25) !important;
        border-bottom-color: white !important;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.7) !important;
    }}

    /* Links inside columns - dark */
    [data-testid="column"] [data-testid="stMarkdown"] a {{
        color: {primary} !important;
        text-shadow: none !important;
    }}

    /* Only apply glassmorphic cards to main content sections */
    section.main > div.block-container > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"] {{
        background: rgba(255, 255, 255, 0.85) !important;
        backdrop-filter: blur(20px) !important;
        -webkit-backdrop-filter: blur(20px) !important;
        border-radius: 20px !important;
        border: 1px solid rgba(255, 255, 255, 0.3) !important;
        padding: 24px !important;
        margin-bottom: 20px !important;
        box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1) !important;
    }}

    /* Remove background from certain containers to avoid double-layering */
    div[data-testid="column"] > div[data-testid="stVerticalBlock"] > div[data-testid="element-container"],
    div[data-testid="stHorizontalBlock"] > div[data-testid="element-container"] {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        box-shadow: none !important;
    }}

    /* Headers - WHITE by default (most appear on gradient background) */
    h1 {{
        color: white !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em;
        padding-top: 0 !important;
        margin-top: 0 !important;
        margin-bottom: 1rem !important;
        text-shadow: 0 2px 8px rgba(0, 0, 0, 0.5) !important;
    }}

    h2 {{
        color: white !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
        margin-top: 1.5rem !important;
        margin-bottom: 1rem !important;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.4) !important;
    }}

    h3 {{
        color: white !important;
        font-weight: 600 !important;
        letter-spacing: -0.01em;
        margin-top: 1rem !important;
        margin-bottom: 0.75rem !important;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4) !important;
    }}

    /* Headers INSIDE white cards should be dark */
    [data-testid="element-container"][style*="background"] h1,
    [data-testid="column"] h1,
    [data-testid="stExpander"] h1 {{
        color: #0f172a !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.05) !important;
    }}

    [data-testid="element-container"][style*="background"] h2,
    [data-testid="column"] h2,
    [data-testid="stExpander"] h2 {{
        color: #1e293b !important;
        text-shadow: none !important;
    }}

    [data-testid="element-container"][style*="background"] h3,
    [data-testid="column"] h3,
    [data-testid="stExpander"] h3 {{
        color: #334155 !important;
        text-shadow: none !important;
    }}

    /* Force ALL main content text to WHITE (on gradient background) */
    .main p,
    .main span,
    .main div {{
        color: white !important;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.5) !important;
        font-weight: 500 !important;
    }}

    /* But make text DARK inside white glassmorphic cards */
    [data-testid="column"] p,
    [data-testid="column"] span,
    [data-testid="column"] div,
    [data-testid="stExpander"] p,
    [data-testid="stExpander"] span,
    [data-testid="stExpander"] div {{
        color: #1e293b !important;
        text-shadow: none !important;
        font-weight: 500 !important;
    }}

    /* Paragraph and text spacing - white with strong shadow */
    p {{
        margin-bottom: 0.75rem !important;
        line-height: 1.6 !important;
        color: white !important;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.6) !important;
        font-weight: 600 !important;
    }}

    /* Dark paragraphs in columns */
    [data-testid="column"] p {{
        color: #1e293b !important;
        text-shadow: none !important;
        font-weight: 500 !important;
    }}

    /* Metric cards */
    [data-testid="stMetric"] {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid rgba({primary_rgb}, 0.25) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        backdrop-filter: blur(10px) !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
    }}

    [data-testid="stMetric"]:hover {{
        transform: translateY(-4px);
        box-shadow: 0 12px 24px rgba({primary_rgb}, 0.25) !important;
        border-color: rgba({primary_rgb}, 0.4) !important;
    }}

    [data-testid="stMetric"] label {{
        font-size: 13px !important;
        font-weight: 700 !important;
        color: #475569 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        opacity: 1 !important;
    }}

    [data-testid="stMetric"] [data-testid="stMetricValue"] {{
        font-size: 32px !important;
        font-weight: 700 !important;
        color: #1e293b !important;
    }}

    [data-testid="stMetric"] [data-testid="stMetricDelta"] {{
        color: #64748b !important;
        font-weight: 600 !important;
    }}

    /* Buttons */
    .stButton > button {{
        background: linear-gradient(135deg, {primary} 0%, {gradient_end} 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 28px !important;
        font-weight: 600 !important;
        font-size: 15px !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 15px rgba({primary_rgb}, 0.4) !important;
    }}

    .stButton > button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba({primary_rgb}, 0.5) !important;
    }}

    .stButton > button:active {{
        transform: translateY(0);
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 6px;
        background: rgba({primary_rgb}, 0.08) !important;
        padding: 8px !important;
        border-radius: 16px !important;
        border: 2px solid rgba({primary_rgb}, 0.15) !important;
        box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.05) !important;
    }}

    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        border: 2px solid transparent !important;
        color: #334155 !important;
    }}

    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba({primary_rgb}, 0.12) !important;
        border: 2px solid rgba({primary_rgb}, 0.2) !important;
        color: #1e293b !important;
    }}

    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background: linear-gradient(135deg, {primary} 0%, {gradient_end} 100%) !important;
        color: white !important;
        border: 2px solid transparent !important;
        box-shadow: 0 4px 12px rgba({primary_rgb}, 0.3) !important;
    }}

    /* Tab content */
    .stTabs [data-baseweb="tab-panel"] {{
        padding-top: 20px !important;
    }}

    /* Dataframes */
    [data-testid="stDataFrame"] {{
        border-radius: 16px !important;
        overflow: hidden !important;
        border: 2px solid rgba({primary_rgb}, 0.15) !important;
        background: rgba(255, 255, 255, 0.95) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
    }}

    [data-testid="stDataFrame"] thead tr th {{
        background: rgba(248, 250, 252, 0.98) !important;
        color: #334155 !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.1em;
        padding: 16px 12px !important;
        border-bottom: 2px solid rgba({primary_rgb}, 0.25) !important;
    }}

    [data-testid="stDataFrame"] tbody tr {{
        transition: all 0.2s ease !important;
    }}

    [data-testid="stDataFrame"] tbody tr:hover {{
        background: rgba({primary_rgb}, 0.06) !important;
        transform: scale(1.01);
    }}

    [data-testid="stDataFrame"] tbody td {{
        padding: 12px !important;
        font-size: 14px !important;
        border-bottom: 1px solid rgba({primary_rgb}, 0.08) !important;
        color: #1e293b !important;
        font-weight: 500 !important;
    }}

    /* Table styling */
    .stTable {{
        background: rgba(255, 255, 255, 0.95) !important;
        border-radius: 16px !important;
        overflow: hidden !important;
    }}

    /* Expanders */
    [data-testid="stExpander"] {{
        background: rgba(255, 255, 255, 0.75) !important;
        border: 2px solid rgba({primary_rgb}, 0.2) !important;
        border-radius: 16px !important;
        backdrop-filter: blur(10px) !important;
        margin: 12px 0 !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.3s ease !important;
    }}

    [data-testid="stExpander"]:hover {{
        border-color: rgba({primary_rgb}, 0.35) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1) !important;
    }}

    [data-testid="stExpander"] summary {{
        font-weight: 700 !important;
        color: #1e293b !important;
        padding: 16px 20px !important;
        font-size: 15px !important;
    }}

    [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        padding: 16px 20px !important;
    }}

    /* Text inputs and selectboxes */
    .stTextInput > div > div > input {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid rgba({primary_rgb}, 0.2) !important;
        border-radius: 12px !important;
        padding: 12px 16px !important;
        transition: all 0.3s ease !important;
        font-size: 15px !important;
        color: #1e293b !important;
        font-weight: 500 !important;
    }}

    .stTextInput > div > div > input:focus {{
        border-color: {primary} !important;
        box-shadow: 0 0 0 3px rgba({primary_rgb}, 0.15) !important;
    }}

    /* Selectbox styling - fix cut-off text */
    .stSelectbox > div > div {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid rgba({primary_rgb}, 0.2) !important;
        border-radius: 12px !important;
        transition: all 0.3s ease !important;
    }}

    .stSelectbox > div > div:focus-within {{
        border-color: {primary} !important;
        box-shadow: 0 0 0 3px rgba({primary_rgb}, 0.15) !important;
    }}

    .stSelectbox [data-baseweb="select"] {{
        min-height: 48px !important;
    }}

    .stSelectbox [data-baseweb="select"] > div {{
        padding: 10px 16px !important;
        font-size: 15px !important;
        line-height: 1.6 !important;
        min-height: 48px !important;
        display: flex !important;
        align-items: center !important;
        color: #1e293b !important;
        font-weight: 500 !important;
    }}

    /* Selectbox dropdown menu */
    [data-baseweb="popover"] {{
        background: rgba(255, 255, 255, 0.98) !important;
        backdrop-filter: blur(20px) !important;
        border-radius: 12px !important;
        border: 2px solid rgba({primary_rgb}, 0.2) !important;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2) !important;
        margin-top: 4px !important;
    }}

    [data-baseweb="menu"] {{
        background: transparent !important;
    }}

    [role="option"] {{
        padding: 12px 16px !important;
        font-size: 15px !important;
        line-height: 1.6 !important;
        min-height: 48px !important;
        display: flex !important;
        align-items: center !important;
        transition: all 0.2s ease !important;
        color: #1e293b !important;
        font-weight: 500 !important;
    }}

    [role="option"]:hover {{
        background: rgba({primary_rgb}, 0.1) !important;
        color: #0f172a !important;
        font-weight: 600 !important;
    }}

    [role="option"][aria-selected="true"] {{
        background: rgba({primary_rgb}, 0.15) !important;
        color: #0f172a !important;
        font-weight: 700 !important;
    }}

    /* MultiSelect */
    .stMultiSelect > div > div > div {{
        background: rgba(255, 255, 255, 0.95) !important;
        border: 2px solid rgba({primary_rgb}, 0.2) !important;
        border-radius: 12px !important;
        padding: 8px 12px !important;
        transition: all 0.3s ease !important;
        min-height: 48px !important;
    }}

    .stMultiSelect > div > div > div:focus {{
        border-color: {primary} !important;
        box-shadow: 0 0 0 3px rgba({primary_rgb}, 0.15) !important;
    }}

    /* ========================================
       PROFESSIONAL CHAT INTERFACE STYLING
       ======================================== */
    
    /* Chat messages - clean design without borders */
    [data-testid="stChatMessage"] {{
        background: rgba(255, 255, 255, 0.98) !important;
        border-radius: 16px !important;
        border: none !important;
        padding: 24px !important;
        margin-bottom: 16px !important;
        backdrop-filter: blur(10px) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06) !important;
        transition: all 0.2s ease !important;
    }}

    [data-testid="stChatMessage"]:hover {{
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1) !important;
    }}

    /* Remove ALL backgrounds from chat message content wrappers */
    [data-testid="stChatMessage"] > div,
    [data-testid="stChatMessage"] [data-testid="stChatMessageContent"],
    [data-testid="stChatMessage"] .stChatMessageContent {{
        background: none !important;
        background-color: transparent !important;
    }}

    /* User messages (questions) - gradient without border */
    [data-testid="stChatMessage"][data-testid*="user"],
    [data-testid="stChatMessageContent"] > div:has([data-testid="stMarkdown"]:first-child) {{
        background: linear-gradient(135deg, {primary} 0%, {gradient_end} 100%) !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba({primary_rgb}, 0.25) !important;
    }}

    /* User message text - CRISP WHITE with NO shadows */
    [data-testid="stChatMessage"][data-testid*="user"] p,
    [data-testid="stChatMessage"][data-testid*="user"] span:not(code),
    [data-testid="stChatMessage"][data-testid*="user"] div:not(pre),
    [data-testid="stChatMessage"][data-testid*="user"] strong,
    [data-testid="stChatMessage"][data-testid*="user"] li {{
        color: white !important;
        font-weight: 500 !important;
        line-height: 1.7 !important;
        text-shadow: none !important;
    }}

    /* Assistant messages (answers) - clean white without border */
    [data-testid="stChatMessage"]:not([data-testid*="user"]) {{
        background: rgba(255, 255, 255, 0.98) !important;
        border: none !important;
    }}

    /* Remove any colored backgrounds from assistant message content */
    [data-testid="stChatMessage"]:not([data-testid*="user"]) [data-testid="stMarkdown"],
    [data-testid="stChatMessage"]:not([data-testid*="user"]) [data-testid="stMarkdown"] > div,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) div,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) > div {{
        background: transparent !important;
    }}

    /* Assistant message text - CRISP DARK with NO shadows */
    [data-testid="stChatMessage"]:not([data-testid*="user"]) p,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) span:not(code),
    [data-testid="stChatMessage"]:not([data-testid*="user"]) div:not(pre),
    [data-testid="stChatMessage"]:not([data-testid*="user"]) strong,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) li,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) ul,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) ol,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) h1,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) h2,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) h3,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) h4 {{
        color: #1e293b !important;
        background: none !important;
        background-color: transparent !important;
        background-image: none !important;
        line-height: 1.7 !important;
        text-shadow: none !important;
        font-weight: 500 !important;
    }}

    /* NUCLEAR OPTION: Reset all background CSS variables and remove shadows */
    [data-testid="stChatMessage"]:not([data-testid*="user"]) * {{
        --background: transparent !important;
        --background-color: transparent !important;
        --bg-color: transparent !important;
        text-shadow: none !important;
    }}

    /* Force remove ALL text shadows from chat messages */
    [data-testid="stChatMessage"] p,
    [data-testid="stChatMessage"] span:not(code),
    [data-testid="stChatMessage"] div:not(pre),
    [data-testid="stChatMessage"] strong,
    [data-testid="stChatMessage"] li,
    [data-testid="stChatMessage"] a {{
        text-shadow: none !important;
    }}

    /* Chat input box - professional styling */
    [data-testid="stChatInput"] {{
        background: rgba(255, 255, 255, 0.98) !important;
        border: 2px solid rgba({primary_rgb}, 0.2) !important;
        border-radius: 16px !important;
        padding: 4px !important;
        box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08) !important;
        transition: all 0.3s ease !important;
    }}

    [data-testid="stChatInput"]:focus-within {{
        border-color: {primary} !important;
        box-shadow: 0 0 0 3px rgba({primary_rgb}, 0.1), 0 2px 12px rgba(0, 0, 0, 0.08) !important;
    }}

    [data-testid="stChatInput"] textarea {{
        color: #1e293b !important;
        font-weight: 500 !important;
        font-size: 15px !important;
        line-height: 1.6 !important;
    }}

    [data-testid="stChatInput"] textarea::placeholder {{
        color: #94a3b8 !important;
    }}

    /* Chat message avatars - professional appearance */
    [data-testid="stChatMessage"] img {{
        border-radius: 50% !important;
        width: 36px !important;
        height: 36px !important;
        border: 2px solid rgba({primary_rgb}, 0.3) !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1) !important;
    }}

    /* Lists in chat messages - better spacing and NO shadows */
    [data-testid="stChatMessage"] ul,
    [data-testid="stChatMessage"] ol {{
        padding-left: 24px !important;
        margin: 12px 0 !important;
    }}

    [data-testid="stChatMessage"] li {{
        margin-bottom: 8px !important;
        line-height: 1.6 !important;
        text-shadow: none !important;
    }}

    /* User message lists - white text, no shadow */
    [data-testid="stChatMessage"][data-testid*="user"] li {{
        color: white !important;
        text-shadow: none !important;
    }}

    /* Assistant message lists - dark text, no shadow */
    [data-testid="stChatMessage"]:not([data-testid*="user"]) li {{
        color: #1e293b !important;
        text-shadow: none !important;
    }}

    /* Emphasis in chat messages - clean and crisp */
    [data-testid="stChatMessage"] strong {{
        font-weight: 700 !important;
        text-shadow: none !important;
    }}

    [data-testid="stChatMessage"][data-testid*="user"] strong {{
        color: white !important;
        text-shadow: none !important;
    }}

    [data-testid="stChatMessage"]:not([data-testid*="user"]) strong {{
        color: #0f172a !important;
        text-shadow: none !important;
    }}

    /* Code blocks - general styling with bright text */
    .stCodeBlock, pre {{
        border-radius: 12px !important;
        border: 1px solid rgba({primary_rgb}, 0.3) !important;
        background: #1a202c !important;
        backdrop-filter: blur(10px) !important;
        padding: 16px !important;
        margin: 16px 0 !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15) !important;
    }}

    code {{
        font-family: 'Monaco', 'Menlo', 'Consolas', 'Courier New', monospace !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
        font-weight: 500 !important;
    }}

    /* Make code blocks text BRIGHT WHITE for maximum contrast */
    .stCodeBlock code,
    pre code,
    .stCodeBlock span,
    pre span {{
        color: #f7fafc !important;
    }}

    /* Syntax highlighting - bright colors on dark background */
    .stCodeBlock .hljs-keyword,
    .stCodeBlock .hljs-selector-tag,
    .stCodeBlock .hljs-built_in {{
        color: #fc8181 !important;  /* Bright red */
    }}

    .stCodeBlock .hljs-string,
    .stCodeBlock .hljs-attr {{
        color: #68d391 !important;  /* Bright green */
    }}

    .stCodeBlock .hljs-number,
    .stCodeBlock .hljs-literal {{
        color: #90cdf4 !important;  /* Bright blue */
    }}

    .stCodeBlock .hljs-function,
    .stCodeBlock .hljs-title {{
        color: #fbd38d !important;  /* Bright yellow */
    }}

    .stCodeBlock .hljs-comment {{
        color: #a0aec0 !important;  /* Medium gray - still readable */
    }}

    .stCodeBlock .hljs-variable,
    .stCodeBlock .hljs-name {{
        color: #b794f4 !important;  /* Bright purple */
    }}

    /* ULTRA AGGRESSIVE: Force remove ALL colored backgrounds and shadows from assistant messages */
    [data-testid="stChatMessage"]:not([data-testid*="user"]),
    [data-testid="stChatMessage"]:not([data-testid*="user"]) *,
    [data-testid="stChatMessage"]:not([data-testid*="user"]) *[style],
    [data-testid="stChatMessage"]:not([data-testid*="user"]) div[style*="background"],
    [data-testid="stChatMessage"]:not([data-testid*="user"]) span[style*="background"],
    [data-testid="stChatMessage"]:not([data-testid*="user"]) p[style*="background"],
    [data-testid="stChatMessage"]:not([data-testid*="user"]) *[style*="background"],
    [data-testid="stChatMessage"]:not([data-testid*="user"]) *[style*="Background"],
    [data-testid="stChatMessage"]:not([data-testid*="user"]) *[class*="background"],
    [data-testid="stChatMessage"]:not([data-testid*="user"]) > * {{
        background: none !important;
        background-color: transparent !important;
        background-image: none !important;
        text-shadow: none !important;
    }}

    /* Force override for assistant message container itself */
    [data-testid="stChatMessage"][data-testid*="assistant"] {{
        background: rgba(255, 255, 255, 0.98) !important;
    }}

    [data-testid="stChatMessage"][data-testid*="assistant"] * {{
        background: none !important;
        background-color: transparent !important;
        text-shadow: none !important;
    }}

    /* Code blocks in chat messages - bright text */
    [data-testid="stChatMessage"] pre {{
        background: #1a202c !important;
        border-radius: 8px !important;
        border: 1px solid rgba({primary_rgb}, 0.3) !important;
        padding: 16px !important;
        margin: 12px 0 !important;
        overflow-x: auto !important;
    }}

    [data-testid="stChatMessage"] pre code,
    [data-testid="stChatMessage"] pre code span {{
        background: transparent !important;
        color: #f7fafc !important;
        font-size: 14px !important;
        font-weight: 500 !important;
    }}

    /* Inline code in chat messages */
    [data-testid="stChatMessage"] code:not(pre code) {{
        background: rgba(79, 70, 229, 0.12) !important;
        padding: 2px 6px !important;
        border-radius: 4px !important;
        font-size: 13px !important;
        color: #1e293b !important;
        font-weight: 600 !important;
    }}

    /* Inline code in user messages */
    [data-testid="stChatMessage"][data-testid*="user"] code:not(pre code) {{
        background: rgba(255, 255, 255, 0.25) !important;
        color: white !important;
        font-weight: 700 !important;
    }}

    [data-testid="stChatMessage"][data-testid*="user"] pre code,
    [data-testid="stChatMessage"][data-testid*="user"] pre code span {{
        color: #f7fafc !important;
    }}

    /* Line numbers in code blocks - bright and readable */
    .stCodeBlock .line-number,
    pre .line-number {{
        color: #718096 !important;
        font-weight: 500 !important;
    }}

    /* Ensure all text in code blocks is bright */
    .stCodeBlock * {{
        color: #f7fafc !important;
    }}

    /* Override for specific syntax elements to use vibrant colors */
    .stCodeBlock .token {{
        font-weight: 500 !important;
    }}

    /* Chart containers */
    [data-testid="stArrowVegaLiteChart"], 
    [data-testid="stLineChart"],
    [data-testid="stBarChart"],
    [data-testid="stAreaChart"] {{
        background: rgba(255, 255, 255, 0.95) !important;
        border-radius: 16px !important;
        padding: 20px !important;
        border: 2px solid rgba({primary_rgb}, 0.15) !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08) !important;
        margin: 16px 0 !important;
    }}

    /* Remove spacing issues at page top */
    .main .block-container > div[data-testid="stVerticalBlock"]:first-child > div[data-testid="element-container"]:first-child {{
        margin-top: 0 !important;
        padding-top: 0 !important;
    }}

    /* Fix for blank sections - ensure no empty containers create white boxes */
    div[data-testid="element-container"]:empty,
    div[data-testid="stVerticalBlock"]:empty {{
        display: none !important;
    }}

    /* Alerts */
    .stAlert {{
        border-radius: 16px !important;
        backdrop-filter: blur(10px) !important;
        padding: 16px 20px !important;
        margin: 12px 0 !important;
        font-size: 14px !important;
        line-height: 1.6 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08) !important;
    }}

    div[data-baseweb="notification"] {{
        border-radius: 16px !important;
        backdrop-filter: blur(10px) !important;
    }}

    /* Success alert */
    .stSuccess, div[data-baseweb="notification"][kind="positive"] {{
        background: rgba(72, 187, 120, 0.12) !important;
        border: 2px solid rgba(72, 187, 120, 0.35) !important;
        color: #276749 !important;
    }}

    /* Info alert */
    .stInfo, div[data-baseweb="notification"][kind="info"] {{
        background: rgba(66, 153, 225, 0.12) !important;
        border: 2px solid rgba(66, 153, 225, 0.35) !important;
        color: #2C5282 !important;
    }}

    /* NO info/success styling inside chat messages */
    [data-testid="stChatMessage"] .stInfo,
    [data-testid="stChatMessage"] .stSuccess,
    [data-testid="stChatMessage"] [data-baseweb="notification"] {{
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
    }}

    /* Warning alert */
    .stWarning, div[data-baseweb="notification"][kind="warning"] {{
        background: rgba(237, 137, 54, 0.12) !important;
        border: 2px solid rgba(237, 137, 54, 0.35) !important;
        color: #7C2D12 !important;
    }}

    /* Error alert */
    .stError, div[data-baseweb="notification"][kind="negative"] {{
        background: rgba(245, 101, 101, 0.12) !important;
        border: 2px solid rgba(245, 101, 101, 0.35) !important;
        color: #991B1B !important;
    }}

    /* Progress bars */
    .stProgress > div > div {{
        background: linear-gradient(90deg, {primary} 0%, {gradient_end} 100%) !important;
        border-radius: 8px !important;
    }}

    /* Spinners */
    .stSpinner > div {{
        border-top-color: {primary} !important;
    }}

    /* Labels - WHITE by default (on gradient background) */
    label {{
        font-weight: 700 !important;
        color: white !important;
        font-size: 14px !important;
        margin-bottom: 8px !important;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.6) !important;
    }}

    /* Labels inside columns/cards - dark */
    [data-testid="column"] label,
    [data-testid="stExpander"] label {{
        color: #1e293b !important;
        text-shadow: none !important;
    }}


    /* Dividers */
    hr {{
        border-color: rgba({primary_rgb}, 0.2) !important;
        margin: 32px 0 !important;
        opacity: 0.6;
    }}

    /* Column spacing */
    [data-testid="column"] {{
        padding: 0 8px !important;
    }}

    [data-testid="column"]:first-child {{
        padding-left: 0 !important;
    }}

    [data-testid="column"]:last-child {{
        padding-right: 0 !important;
    }}

    /* Scrollbar */
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}

    ::-webkit-scrollbar-track {{
        background: rgba(255, 255, 255, 0.1);
        border-radius: 10px;
    }}

    ::-webkit-scrollbar-thumb {{
        background: rgba({primary_rgb}, 0.5);
        border-radius: 10px;
    }}

    ::-webkit-scrollbar-thumb:hover {{
        background: rgba({primary_rgb}, 0.7);
    }}

    /* Markdown content - white with strong shadows */
    .stMarkdown {{
        line-height: 1.7 !important;
    }}

    .stMarkdown strong {{
        font-weight: 700 !important;
        color: white !important;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.6) !important;
    }}

    .stMarkdown ul, .stMarkdown ol {{
        padding-left: 24px !important;
        margin-bottom: 1rem !important;
    }}

    .stMarkdown li {{
        margin-bottom: 0.5rem !important;
        color: white !important;
        text-shadow: 0 2px 6px rgba(0, 0, 0, 0.6) !important;
        font-weight: 600 !important;
    }}

    /* Dark markdown in columns */
    [data-testid="column"] .stMarkdown p,
    [data-testid="column"] .stMarkdown strong,
    [data-testid="column"] .stMarkdown li {{
        color: #1e293b !important;
        text-shadow: none !important;
        font-weight: 500 !important;
    }}

    [data-testid="column"] .stMarkdown strong {{
        font-weight: 700 !important;
        color: #0f172a !important;
    }}

    /* Improve metric card layout */
    [data-testid="stMetricLabel"] > div {{
        overflow: visible !important;
        white-space: normal !important;
    }}

    /* Animations */
    @keyframes fadeIn {{
        from {{
            opacity: 0;
            transform: translateY(10px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}

    .main .block-container > div {{
        animation: fadeIn 0.5s ease-out;
    }}

    /* Hide Streamlit branding for cleaner look */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Responsive adjustments */
    @media (max-width: 768px) {{
        .main .block-container {{
            padding: 1rem !important;
        }}
        
        h1 {{
            font-size: 1.8rem !important;
        }}
        
        h2 {{
            font-size: 1.4rem !important;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)
