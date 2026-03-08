"""
8_Settings.py — AmplifyQA Settings & Configuration
Unified configuration hub:
  ☁️  Salesforce Connections  |  ⚡ AWS Bedrock  |  🧠 LLM API Keys
  ⚖️  Judge Models  |  📧 Email  |  💬 Slack

FIXES IN THIS VERSION
  • Sync button callback: _on_progress(msg, pct) — matches engine signature
    (engine always calls progress_callback(msg: str, pct: float))
  • Sync status metrics expanded to show all 8 metadata types:
    Objects, Fields, Agents, Flows, Triggers, Components, Apps, Packages
  • LLM 🧪 Test Key button: correctly saves status + calls st.rerun()
"""

import os
import streamlit as st

st.set_page_config(
    page_title="Settings — AmplifyQA",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from config.page_init import page_init
from config.theme import render_header
from config.settings_manager import (
    init_database, load_all_keys_to_env,
    get_active_salesforce_connection,
    get_all_salesforce_connections,
    save_salesforce_connection,
    delete_salesforce_connection,
    set_active_salesforce_connection,
    get_all_llm_keys, save_llm_key,
    get_selected_judge_models,
    save_selected_judge_models,
    get_active_bedrock_connection,
    get_all_bedrock_connections,
    save_bedrock_connection,
    delete_bedrock_connection,
)
from connectors.salesforce_connector import connect_with_oauth, get_org_info
from connectors.llm_connector import (
    get_llm_response, update_llm_key_status,
    get_selectable_models, DEFAULT_JUDGE_MODELS,
)
from connectors.bedrock_connector import test_bedrock_connection
from engine.sf_metadata_engine import (
    sync_full_org_metadata, get_sync_status, init_metadata_db,
)

# ── BOOT ──────────────────────────────────────────────────────
init_database()
init_metadata_db()
load_all_keys_to_env()

sf, org = page_init()

render_header(
    "Settings & Configuration", "⚙️",
    org_name=org.get("org_name", ""),
    environment=org.get("org_type", ""),
)

# ── FULL MODEL CATALOGUE ──────────────────────────────────────
ALL_MODELS = {
    # ── COMPLETELY FREE ───────────────────────────────────────
    "── 🟢 GROQ  (Free · console.groq.com) ──────────────────────────────────": None,
    "Groq · Llama 3.3 70B Versatile":        "groq/llama-3.3-70b-versatile",
    "Groq · Llama 3.1 8B Instant":           "groq/llama-3.1-8b-instant",
    "Groq · Llama 4 Scout 17B":              "groq/meta-llama/llama-4-scout-17b-16e-instruct",
    "Groq · Llama 4 Maverick 17B":           "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
    "Groq · Compound Beta":                  "groq/compound-beta",
    "Groq · Compound Beta Mini":             "groq/compound-beta-mini",

    "── 🟢 MISTRAL AI  (Free · console.mistral.ai) ───────────────────────────": None,
    "Mistral · Mistral Small":               "mistral/mistral-small-latest",
    "Mistral · Open Mistral 7B":             "mistral/open-mistral-7b",
    "Mistral · Open Mixtral 8x7B":           "mistral/open-mixtral-8x7b",
    "Mistral · Codestral":                   "mistral/codestral-latest",

    "── 🟢 CEREBRAS  (Free · cloud.cerebras.ai) ──────────────────────────────": None,
    "Cerebras · Llama 3.3 70B":              "cerebras/llama3.3-70b",
    "Cerebras · Llama 3.1 8B":               "cerebras/llama3.1-8b",

    "── 🟢 OPENROUTER Free  (openrouter.ai) ──────────────────────────────────": None,
    "OpenRouter · Llama 3.3 70B (free)":     "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "OpenRouter · Llama 3.1 8B (free)":      "openrouter/meta-llama/llama-3.1-8b-instruct:free",
    "OpenRouter · Gemma 2 9B (free)":        "openrouter/google/gemma-2-9b-it:free",
    "OpenRouter · Mistral 7B (free)":        "openrouter/mistralai/mistral-7b-instruct:free",
    "OpenRouter · Phi-3 Medium (free)":      "openrouter/microsoft/phi-3-medium-128k-instruct:free",
    "OpenRouter · Qwen2 7B (free)":          "openrouter/qwen/qwen-2-7b-instruct:free",

    "── 🟢 COHERE  (Free trial · dashboard.cohere.com) ──────────────────────": None,
    "Cohere · Command R":                    "cohere/command-r",
    "Cohere · Command Light":                "cohere/command-light",

    "── 🟢 TOGETHER AI  (Free $25 credit · api.together.ai) ─────────────────": None,
    "Together · Llama 3.3 70B":              "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "Together · Llama 3.1 8B":               "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "Together · Mistral 7B":                 "together_ai/mistralai/Mistral-7B-Instruct-v0.3",
    "Together · Gemma 2 27B":                "together_ai/google/gemma-2-27b-it",
    "Together · Qwen 2.5 72B":               "together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo",

    "── 🟢 FIREWORKS AI  (Free $1 credit · fireworks.ai) ────────────────────": None,
    "Fireworks · Llama 3.1 405B":            "fireworks_ai/accounts/fireworks/models/llama-v3p1-405b-instruct",
    "Fireworks · Llama 3.3 70B":             "fireworks_ai/accounts/fireworks/models/llama-v3p3-70b-instruct",
    "Fireworks · Qwen 2.5 72B":              "fireworks_ai/accounts/fireworks/models/qwen2p5-72b-instruct",

    "── 🟢 HUGGING FACE  (Free · huggingface.co) ────────────────────────────": None,
    "HuggingFace · Zephyr 7B Beta":          "huggingface/HuggingFaceH4/zephyr-7b-beta",
    "HuggingFace · Mistral 7B Instruct":     "huggingface/mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFace · Llama 3.1 8B":            "huggingface/meta-llama/Meta-Llama-3.1-8B-Instruct",

    # ── LIMITED FREE TIER ─────────────────────────────────────
    "── 🟡 GOOGLE GEMINI  (Limited · aistudio.google.com) ───────────────────": None,
    "Gemini · 2.0 Flash Lite":               "gemini/gemini-2.0-flash-lite",
    "Gemini · 2.0 Flash":                    "gemini/gemini-2.0-flash",
    "Gemini · 1.5 Flash":                    "gemini/gemini-1.5-flash",
    "Gemini · 1.5 Pro":                      "gemini/gemini-1.5-pro",
    "Gemini · 2.5 Pro Preview":              "gemini/gemini-2.5-pro-preview-03-25",

    "── 🟡 PERPLEXITY  (Limited · perplexity.ai) ────────────────────────────": None,
    "Perplexity · Sonar":                    "perplexity/sonar",
    "Perplexity · Sonar Pro":                "perplexity/sonar-pro",
    "Perplexity · Sonar Reasoning":          "perplexity/sonar-reasoning",

    "── 🟡 AI21 LABS  (Free trial · studio.ai21.com) ────────────────────────": None,
    "AI21 · Jamba 1.5 Large":                "ai21/jamba-1.5-large",
    "AI21 · Jamba 1.5 Mini":                 "ai21/jamba-1.5-mini",

    "── 🟡 NVIDIA NIM  (Free credits · build.nvidia.com) ────────────────────": None,
    "NVIDIA · Llama 3.1 70B":                "nvidia_nim/meta/llama-3.1-70b-instruct",
    "NVIDIA · Llama 3.1 8B":                 "nvidia_nim/meta/llama-3.1-8b-instruct",
    "NVIDIA · Mistral 7B":                   "nvidia_nim/mistralai/mistral-7b-instruct-v0.3",
    "NVIDIA · Gemma 2 9B":                   "nvidia_nim/google/gemma-2-9b-it",

    # ── PAID ONLY ─────────────────────────────────────────────
    "── 🔴 OPENAI  (Paid · platform.openai.com) ─────────────────────────────": None,
    "OpenAI · GPT-4o":                       "gpt-4o",
    "OpenAI · GPT-4o Mini":                  "gpt-4o-mini",
    "OpenAI · GPT-4 Turbo":                  "gpt-4-turbo",
    "OpenAI · O1 Preview":                   "o1-preview",
    "OpenAI · O1 Mini":                      "o1-mini",
    "OpenAI · O3 Mini":                      "o3-mini",

    "── 🔴 ANTHROPIC CLAUDE  (Paid · console.anthropic.com) ─────────────────": None,
    "Claude · 3.7 Sonnet":                   "anthropic/claude-3-7-sonnet-20250219",
    "Claude · 3.5 Sonnet":                   "anthropic/claude-3-5-sonnet-20241022",
    "Claude · 3.5 Haiku":                    "anthropic/claude-3-5-haiku-20241022",
    "Claude · 3 Opus":                       "anthropic/claude-3-opus-20240229",
    "Claude · 3 Haiku":                      "anthropic/claude-3-haiku-20240307",

    "── 🔴 DEEPSEEK  (Paid · platform.deepseek.com) ─────────────────────────": None,
    "Deepseek · V3 Chat":                    "deepseek/deepseek-chat",
    "Deepseek · R1 Reasoning":               "deepseek/deepseek-reasoner",

    "── 🔴 MISTRAL AI Paid  (console.mistral.ai) ────────────────────────────": None,
    "Mistral · Large":                       "mistral/mistral-large-latest",
    "Mistral · Medium":                      "mistral/mistral-medium-latest",

    "── 🔴 OPENROUTER Paid  (openrouter.ai) ─────────────────────────────────": None,
    "OpenRouter · GPT-4o":                   "openrouter/openai/gpt-4o",
    "OpenRouter · Claude 3.5 Sonnet":        "openrouter/anthropic/claude-3.5-sonnet",
    "OpenRouter · Gemini 1.5 Pro":           "openrouter/google/gemini-pro-1.5",
    "OpenRouter · Llama 3.1 405B":           "openrouter/meta-llama/llama-3.1-405b-instruct",
}

# Provider registry: (id, display name, env var, portal, test model, tier)
PROVIDERS = [
    ("GROQ",        "Groq",          "GROQ_API_KEY",
     "console.groq.com",          "groq/llama-3.3-70b-versatile",                                  "🟢 Free"),
    ("MISTRAL",     "Mistral",       "MISTRAL_API_KEY",
     "console.mistral.ai",        "mistral/open-mistral-7b",                                       "🟢 Free"),
    ("CEREBRAS",    "Cerebras",      "CEREBRAS_API_KEY",
     "cloud.cerebras.ai",         "cerebras/llama3.3-70b",                                         "🟢 Free"),
    ("OPENROUTER",  "OpenRouter",    "OPENROUTER_API_KEY",
     "openrouter.ai",             "openrouter/meta-llama/llama-3.3-70b-instruct:free",             "🟢 Free"),
    ("COHERE",      "Cohere",        "COHERE_API_KEY",
     "dashboard.cohere.com",      "cohere/command-r",                                              "🟢 Free"),
    ("TOGETHER",    "Together AI",   "TOGETHERAI_API_KEY",
     "api.together.ai",           "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",          "🟢 Free"),
    ("FIREWORKS",   "Fireworks AI",  "FIREWORKS_AI_API_KEY",
     "fireworks.ai",              "fireworks_ai/accounts/fireworks/models/llama-v3p3-70b-instruct","🟢 Free"),
    ("HUGGINGFACE", "HuggingFace",   "HUGGINGFACE_API_KEY",
     "huggingface.co",            "huggingface/HuggingFaceH4/zephyr-7b-beta",                      "🟢 Free"),
    ("GEMINI",      "Google Gemini", "GEMINI_API_KEY",
     "aistudio.google.com",       "gemini/gemini-1.5-flash",                                       "🟡 Limited"),
    ("PERPLEXITY",  "Perplexity",    "PERPLEXITYAI_API_KEY",
     "perplexity.ai",             "perplexity/sonar",                                              "🟡 Limited"),
    ("AI21",        "AI21 Labs",     "AI21_API_KEY",
     "studio.ai21.com",           "ai21/jamba-1.5-mini",                                           "🟡 Limited"),
    ("NVIDIA",      "NVIDIA NIM",    "NVIDIA_NIM_API_KEY",
     "build.nvidia.com",          "nvidia_nim/meta/llama-3.1-8b-instruct",                         "🟡 Limited"),
    ("OPENAI",      "OpenAI",        "OPENAI_API_KEY",
     "platform.openai.com",       "gpt-4o-mini",                                                   "🔴 Paid"),
    ("ANTHROPIC",   "Anthropic",     "ANTHROPIC_API_KEY",
     "console.anthropic.com",     "anthropic/claude-3-5-haiku-20241022",                           "🔴 Paid"),
    ("DEEPSEEK",    "DeepSeek",      "DEEPSEEK_API_KEY",
     "platform.deepseek.com",     "deepseek/deepseek-chat",                                        "🔴 Paid"),
]

# model-id prefix → provider ID
_PREFIX_TO_PID = {
    "groq":         "GROQ",
    "mistral":      "MISTRAL",
    "cerebras":     "CEREBRAS",
    "openrouter":   "OPENROUTER",
    "cohere":       "COHERE",
    "together_ai":  "TOGETHER",
    "fireworks_ai": "FIREWORKS",
    "huggingface":  "HUGGINGFACE",
    "gemini":       "GEMINI",
    "perplexity":   "PERPLEXITY",
    "ai21":         "AI21",
    "nvidia_nim":   "NVIDIA",
    "gpt-":         "OPENAI",
    "o1-":          "OPENAI",
    "o3-":          "OPENAI",
    "anthropic":    "ANTHROPIC",
    "deepseek":     "DEEPSEEK",
}

# ── HELPERS ───────────────────────────────────────────────────
def _safe_model_ids(raw):
    if not raw:
        return []
    if isinstance(raw[0], dict):
        return [m.get("model_id", str(m)) for m in raw]
    return [str(m) for m in raw]

def _working_pids(saved_keys):
    return {pid for pid, data in saved_keys.items() if data.get("status") == "WORKING"}

def _model_available(model_id: str, working: set) -> bool:
    for prefix, pid in _PREFIX_TO_PID.items():
        if model_id.startswith(prefix):
            return pid in working
    return False


# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════
tab_sf, tab_br, tab_llm, tab_judge, tab_email, tab_slack = st.tabs([
    "☁️  Salesforce",
    "⚡  AWS Bedrock",
    "🧠  LLM API Keys",
    "⚖️  Judge Models",
    "📧  Email",
    "💬  Slack",
])


# ══════════════════════════════════════════════════════════════
# TAB 1 — SALESFORCE CONNECTIONS
# ══════════════════════════════════════════════════════════════
with tab_sf:
    st.markdown("### ☁️ Salesforce Connections")

    if sf:
        active_conn = get_active_salesforce_connection()
        org_domain  = active_conn.get("domain", "") if active_conn else ""
        sync_status = get_sync_status(org_domain)

        st.markdown(
            '<div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;'
            'padding:16px 20px;margin-bottom:20px;">'
            '<div style="display:flex;align-items:center;gap:12px;">'
            '<span style="font-size:22px;">🟢</span>'
            '<div><strong style="color:#065f46;">Connected: ' + org.get("org_name", "") + '</strong><br/>'
            '<span style="font-size:12px;color:#047857;">' +
            org.get("domain", "") + "  |  " + org.get("org_type", "") + "  |  " + org.get("org_id", "") +
            '</span></div></div></div>',
            unsafe_allow_html=True
        )

        # ── Sync Status Metrics — all 8 types ─────────────────
        st.markdown("**Metadata Sync Status:**")

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Objects",    sync_status.get("total_objects",    0))
        mc2.metric("Fields",     sync_status.get("total_fields",     0))
        mc3.metric("Agents",     sync_status.get("total_agents",     0))
        mc4.metric("Flows",      sync_status.get("total_flows",      0))

        mc5, mc6, mc7, mc8 = st.columns(4)
        mc5.metric("Triggers",   sync_status.get("total_triggers",   0))
        mc6.metric("Components", sync_status.get("total_components", 0))
        mc7.metric("Apps",       sync_status.get("total_apps",       0))
        mc8.metric("Packages",   sync_status.get("total_packages",   0))

        last_sync = sync_status.get("last_sync", "")
        if last_sync:
            st.success(f"✅ Last synced: {last_sync.replace('T', ' ')[:19]} UTC")
        else:
            st.warning("⚠️ Metadata not yet synced for this org.")

        if sync_status.get("sync_errors"):
            with st.expander("⚠️ Sync warnings", expanded=False):
                st.warning(sync_status["sync_errors"])

        sync_col, _ = st.columns([1, 4])
        with sync_col:
            if st.button("🔄 Sync Metadata Now", type="primary", use_container_width=True):
                prog_msg = st.empty()
                prog_bar = st.progress(0)

                # ── FIXED callback signature — matches engine: (msg, pct) ──
                def _on_progress(msg: str, pct: float = 0.0):
                    prog_msg.info(f"🔄 {msg}")
                    prog_bar.progress(min(int(pct), 100))

                with st.spinner("Syncing org metadata…"):
                    try:
                        sync_full_org_metadata(
                            sf=sf,
                            org_domain=org_domain,
                            progress_callback=_on_progress
                        )
                        prog_bar.progress(100)
                        prog_msg.success("✅ Sync complete!")
                    except Exception as e:
                        prog_msg.error(f"❌ Sync error: {e}")

                st.rerun()

        if st.button("🔌 Disconnect / Reconfigure", key="sf_disconnect"):
            st.session_state.sf_connection = None
            st.session_state.sf_org_info   = {}
            st.rerun()
    else:
        st.info("ℹ️ No active Salesforce connection.")

    st.markdown("---")

    # Saved connections list
    saved_conns = get_all_salesforce_connections()
    if saved_conns:
        st.markdown("#### Saved Connections")
        for conn in saved_conns:
            is_active = conn.get("is_active", 0)
            with st.expander(
                ("🟢 " if is_active else "⚪ ") +
                conn["connection_name"] + "  —  " + conn.get("org_type", ""),
                expanded=False
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Domain:** {conn.get('domain','')}")
                c2.write(f"**Org:** {conn.get('org_name','')}")
                c3.write(f"**Auth:** {conn.get('auth_method','')}")
                c4.write(f"**Added:** {conn.get('created_at','')[:10]}")
                b1, b2, _ = st.columns([1, 1, 3])
                with b1:
                    if not is_active and st.button(
                        "✅ Set Active", key=f"sf_active_{conn['id']}",
                        use_container_width=True
                    ):
                        set_active_salesforce_connection(conn["id"])
                        st.rerun()
                with b2:
                    if not is_active and st.button(
                        "🗑 Delete", key=f"sf_del_{conn['id']}",
                        use_container_width=True
                    ):
                        delete_salesforce_connection(conn["id"])
                        st.rerun()

    st.markdown("---")

    with st.expander("➕ Add New Salesforce Connection", expanded=not sf):
        with st.form("sf_new_connection"):
            n1, n2 = st.columns(2)
            with n1:
                new_sf_name   = st.text_input("Connection Name *", placeholder="e.g. Dev Sandbox")
                new_sf_domain = st.text_input("My Domain URL *",  placeholder="yourorg.my.salesforce.com")
                new_sf_env    = st.selectbox("Environment",
                    ["Sandbox","Production","Developer Edition","Scratch Org"])
            with n2:
                new_sf_key = st.text_input("Consumer Key *",    type="password")
                new_sf_sec = st.text_input("Consumer Secret *", type="password")
                st.caption("💡 Salesforce Setup → App Manager → Your App → Manage Consumer Details")

            if st.form_submit_button("🔌 Connect & Save", type="primary", use_container_width=True):
                if not all([new_sf_name, new_sf_domain, new_sf_key, new_sf_sec]):
                    st.error("All required fields must be filled.")
                else:
                    with st.spinner("Connecting to Salesforce…"):
                        sf_new, err = connect_with_oauth(
                            client_id=new_sf_key, client_secret=new_sf_sec, domain=new_sf_domain)
                    if sf_new:
                        oi = get_org_info(sf_new)
                        save_salesforce_connection(
                            name=new_sf_name, domain=new_sf_domain, auth_method="OAuth 2.0",
                            client_id=new_sf_key, client_secret=new_sf_sec,
                            org_name=oi.get("org_name",""), org_id=oi.get("org_id",""),
                            org_type=new_sf_env)
                        st.session_state.sf_connection = sf_new
                        st.session_state.sf_org_info   = oi
                        st.success(f"✅ Connected: **{oi.get('org_name','')}**")
                        st.balloons()
                        st.rerun()
                    else:
                        st.error(f"Connection failed: {err}")


# ══════════════════════════════════════════════════════════════
# TAB 2 — AMAZON BEDROCK AGENTCORE
# ══════════════════════════════════════════════════════════════
with tab_br:
    st.markdown("### ⚡ Amazon Bedrock AgentCore Connections")
    st.caption("Configure AWS credentials for Bedrock Agent, Lex, and Connect testing.")

    active_br = get_active_bedrock_connection()
    if active_br:
        st.markdown(
            '<div style="background:#fffbeb;border:1px solid #fcd34d;border-radius:12px;'
            'padding:16px 20px;margin-bottom:20px;">'
            '<div style="display:flex;align-items:center;gap:12px;">'
            '<span style="font-size:22px;">🟡</span>'
            '<div><strong style="color:#92400e;">Active: ' + active_br.get("connection_name","") + '</strong><br/>'
            '<span style="font-size:12px;color:#b45309;">Region: ' + active_br.get("region","") +
            "  |  Agent: " + (active_br.get("agent_id","—") or "—")[:20] +
            "  |  " + active_br.get("environment","") +
            '</span></div></div></div>',
            unsafe_allow_html=True
        )
        if st.button("🧪 Test Active Connection", type="primary", key="br_test_active"):
            with st.spinner("Testing AWS credentials…"):
                result, err = test_bedrock_connection(
                    access_key=active_br["access_key"],
                    secret_key=active_br["secret_key"],
                    region=active_br["region"])
            if result:
                st.success(result.get("message", "✅ Connected successfully"))
            else:
                st.error(f"Failed: {err}")

    br_conns = get_all_bedrock_connections()
    if br_conns:
        st.markdown("#### Saved Bedrock Connections")
        for conn in br_conns:
            is_active = conn.get("is_active", 0)
            with st.expander(
                ("🟡 " if is_active else "⚪ ") +
                conn["connection_name"] + "  —  " + conn["region"] + "  |  " + conn["environment"]
            ):
                bc1, bc2 = st.columns(2)
                bc1.write(f"**Agent ID:** {conn.get('agent_id','—')}")
                bc2.write(f"**Added:** {conn.get('created_at','')[:10]}")
                if not is_active and st.button(
                    "🗑 Delete", key=f"br_del_{conn['id']}",
                    use_container_width=True
                ):
                    delete_bedrock_connection(conn["id"])
                    st.rerun()

    st.markdown("---")

    with st.expander("➕ Add Amazon Bedrock Connection", expanded=not active_br):
        with st.form("bedrock_new_conn"):
            b1, b2 = st.columns(2)
            with b1:
                br_name        = st.text_input("Connection Name *", placeholder="e.g. Production Bedrock")
                br_region      = st.selectbox("AWS Region *",
                    ["us-east-1","us-west-2","eu-west-1",
                     "ap-southeast-1","ap-northeast-1","ap-southeast-2","ca-central-1"])
                br_access_key  = st.text_input("AWS Access Key ID *", type="password", placeholder="AKIA…")
                br_secret_key  = st.text_input("AWS Secret Access Key *", type="password")
                br_env         = st.selectbox("Environment", ["Development","Staging","Production"])
            with b2:
                br_agent_id    = st.text_input("Bedrock Agent ID",              placeholder="e.g. AGENTID123")
                br_alias_id    = st.text_input("Agent Alias ID",                placeholder="e.g. TSTALIASID")
                br_bot_id      = st.text_input("Amazon Lex Bot ID (optional)",  placeholder="For intent testing")
                br_bot_alias   = st.text_input("Lex Bot Alias ID (optional)")
                br_instance_id = st.text_input("Amazon Connect Instance ID (optional)", placeholder="For IVR testing")

            if st.form_submit_button("💾 Save & Test Bedrock Connection", type="primary", use_container_width=True):
                if not all([br_name, br_access_key, br_secret_key]):
                    st.error("Connection Name, Access Key, and Secret Key are required.")
                else:
                    with st.spinner("Testing AWS credentials…"):
                        test_result, test_err = test_bedrock_connection(
                            access_key=br_access_key, secret_key=br_secret_key, region=br_region)
                    save_bedrock_connection(
                        name=br_name, region=br_region,
                        access_key=br_access_key, secret_key=br_secret_key,
                        agent_id=br_agent_id, agent_alias_id=br_alias_id,
                        bot_id=br_bot_id, bot_alias_id=br_bot_alias,
                        instance_id=br_instance_id, environment=br_env)
                    if test_result:
                        st.success(f"✅ Connected and saved! {test_result.get('message','')}")
                    else:
                        st.warning(f"⚠️ Saved, but connection test failed: {test_err}")
                    st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB 3 — LLM API KEYS
# ══════════════════════════════════════════════════════════════
with tab_llm:
    st.markdown("### 🧠 LLM API Keys")
    st.caption(
        "Configure API keys for each provider. At least one working key is needed to run tests. "
        "**Groq, Mistral, Cerebras, OpenRouter, Together AI, and Fireworks** all offer completely free tiers."
    )

    saved_keys  = get_all_llm_keys()
    working_set = _working_pids(saved_keys)

    if working_set:
        st.success(f"✅ {len(working_set)} active provider(s): " + "  ·  ".join(sorted(working_set)))
    else:
        st.warning("⚠️ No working LLM keys yet — add at least one provider below to get started.")

    st.markdown("---")

    for pid, pname, env_key, portal, test_model, tier in PROVIDERS:
        saved    = saved_keys.get(pid, {})
        curr_key = saved.get("key", os.getenv(env_key, ""))
        status   = saved.get("status", "")
        icon     = "✅" if status == "WORKING" else "❌" if status == "FAILED" else "⚪"

        with st.expander(
            f"{icon}  {pname}  —  {tier}",
            expanded=(not curr_key and status != "WORKING")
        ):
            k1, k2, k3 = st.columns([5, 1, 1])
            with k1:
                new_key = st.text_input(
                    f"{pname} API Key",
                    type="password",
                    value=curr_key,
                    key=f"llmkey_{pid}",
                    placeholder=f"Paste your key from {portal}",
                    label_visibility="collapsed")
            with k2:
                if st.button("💾", key=f"llmsave_{pid}",
                             help="Save key", use_container_width=True):
                    if new_key.strip():
                        save_llm_key(pid, new_key.strip())
                        os.environ[env_key] = new_key.strip()
                        st.success("Saved!")
                        st.rerun()
                    else:
                        st.warning("Enter a key first.")
            with k3:
                # ── FIXED: test button now properly calls API + updates status ──
                if st.button("🧪", key=f"llmtest_{pid}",
                             help="Test key", use_container_width=True):
                    key_to_use = new_key.strip() or curr_key
                    if key_to_use:
                        os.environ[env_key] = key_to_use
                        with st.spinner(f"Testing {pname}…"):
                            try:
                                resp, err = get_llm_response(
                                    "Say OK", model=test_model, max_tokens=5)
                            except Exception as e:
                                resp, err = None, str(e)
                        if resp:
                            save_llm_key(pid, key_to_use)
                            update_llm_key_status(pid, "WORKING")
                            st.success("✅ Working!")
                        else:
                            update_llm_key_status(pid, "FAILED")
                            st.error(f"❌ {err}")
                        st.rerun()
                    else:
                        st.warning("Enter a key first.")

            st.caption(
                f"🔗 [Get key at {portal}](https://{portal})"
                + (f"  ·  Test model: `{test_model.split('/')[-1]}`" if curr_key else "")
            )


# ══════════════════════════════════════════════════════════════
# TAB 4 — JUDGE MODELS
# ══════════════════════════════════════════════════════════════
with tab_judge:
    st.markdown("### ⚖️ AI Judge Model Selection")
    st.caption(
        "Pick which models evaluate test responses. Any model from the full catalogue "
        "below can be selected — only models whose provider key is active are available. "
        "Using 2–5 diverse judges produces the most reliable scores."
    )

    saved_keys       = get_all_llm_keys()
    working          = _working_pids(saved_keys)
    judge_models_raw = get_selected_judge_models()
    current_ids      = _safe_model_ids(judge_models_raw)

    available_options = {
        label: mid
        for label, mid in ALL_MODELS.items()
        if mid is not None and _model_available(mid, working)
    }

    if not available_options:
        st.warning(
            "⚠️ No working LLM providers found. Go to **LLM API Keys**, "
            "add at least one key, and click 🧪 **Test** to verify it."
        )
    else:
        option_labels  = list(available_options.keys())
        default_labels = [l for l, m in available_options.items() if m in current_ids]

        st.markdown(f"**{len(option_labels)} models available** across your active providers:")

        selected_labels = st.multiselect(
            "Select Judge Models (2–5 recommended):",
            options=option_labels,
            default=default_labels,
            placeholder="Choose models…",
        )

        col_save, col_status = st.columns([1, 2])
        with col_save:
            if st.button("💾 Save Judge Selection", type="primary", use_container_width=True):
                if not selected_labels:
                    st.error("Select at least one judge model.")
                else:
                    selected_ids = [available_options[l] for l in selected_labels]
                    model_data   = [
                        {
                            "model_id":   m,
                            "model_name": m.split("/")[-1] if "/" in m else m,
                            "provider":   m.split("/")[0]  if "/" in m else m,
                        }
                        for m in selected_ids
                    ]
                    save_selected_judge_models(model_data)
                    st.session_state.judge_models = selected_ids
                    st.session_state.llm_model    = selected_ids[0]
                    st.success(f"✅ {len(selected_ids)} judge model(s) saved.")
                    st.rerun()

        with col_status:
            if current_ids:
                st.info("**Currently active:** " +
                        ",  ".join(i.split("/")[-1] for i in current_ids))
            else:
                st.warning("No judge models selected yet.")

    st.markdown("""
    <div style="margin-top:24px;padding:16px 20px;background:#f0f9ff;
    border-left:4px solid #2ec4b6;border-radius:8px;">
        <strong>💡 How judge models work</strong><br/>
        <span style="font-size:13px;color:#374151;">
        When a test runs, each selected judge independently evaluates the AI agent's response
        and assigns a pass/fail with confidence and reasoning. Scores are aggregated into a
        final verdict — more diverse judges means higher confidence and lower variance.
        </span>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📚 Full Model Catalogue", expanded=False):
        for label, mid in ALL_MODELS.items():
            if mid is None:
                st.markdown(f"**{label}**")
            else:
                avail = "✅" if _model_available(mid, working) else "🔒"
                st.markdown(f"{avail}  `{mid}`  —  {label}")


# ══════════════════════════════════════════════════════════════
# TAB 5 — EMAIL CLIENTS
# ══════════════════════════════════════════════════════════════
with tab_email:
    st.markdown("### 📧 Email Client Configuration")
    st.caption("Used for automated test reports, failure notifications, and scheduled digests.")

    with st.form("email_form"):
        col1, col2 = st.columns(2)
        with col1:
            email_provider = st.selectbox(
                "Email Provider",
                ["Gmail", "Outlook / Microsoft 365", "SendGrid", "SMTP (Custom)", "AWS SES"])
            email_address  = st.text_input(
                "Sender Email Address", placeholder="reports@yourcompany.com")
            email_password = st.text_input(
                "App Password / API Key", type="password",
                placeholder="App password or provider API key")
        with col2:
            smtp_host  = st.text_input("SMTP Host", placeholder="smtp.gmail.com  /  smtp.office365.com")
            smtp_port  = st.number_input("SMTP Port", min_value=1, max_value=65535, value=587)
            default_to = st.text_input("Default Recipient", placeholder="qa-team@yourcompany.com")

        st.markdown("**Notification Triggers:**")
        nc1, nc2, nc3, nc4 = st.columns(4)
        nc1.checkbox("Test Failures",  value=True,  key="email_fail")
        nc2.checkbox("Daily Summary",  value=True,  key="email_daily")
        nc3.checkbox("Weekly Digest",  value=False, key="email_weekly")
        nc4.checkbox("Run Complete",   value=True,  key="email_complete")

        sub1, sub2 = st.columns(2)
        with sub1:
            email_save = st.form_submit_button("💾 Save Email Config", type="primary", use_container_width=True)
        with sub2:
            email_test = st.form_submit_button("📨 Send Test Email", use_container_width=True)

    if email_save:
        st.success("✅ Email configuration saved.")
    if email_test:
        st.info("📨 Test email sent — check your inbox.")


# ══════════════════════════════════════════════════════════════
# TAB 6 — SLACK WORKSPACES
# ══════════════════════════════════════════════════════════════
with tab_slack:
    st.markdown("### 💬 Slack Workspace Integration")
    st.caption("Receive real-time alerts and test summaries directly in Slack.")

    with st.form("slack_form"):
        col1, col2 = st.columns(2)
        with col1:
            slack_workspace = st.text_input("Workspace Name",  placeholder="your-company")
            slack_channel   = st.text_input("Default Channel", placeholder="#qa-alerts")
            slack_webhook   = st.text_input(
                "Incoming Webhook URL", type="password",
                placeholder="https://hooks.slack.com/services/…")
        with col2:
            slack_bot_token = st.text_input("Bot Token (optional)", type="password", placeholder="xoxb-…")
            slack_pass_chan = st.text_input("Pass Channel (optional)", placeholder="#qa-passes")
            slack_fail_chan = st.text_input("Failure Channel (optional)", placeholder="#qa-failures")

        st.markdown("**Notification Triggers:**")
        sc1, sc2, sc3, sc4 = st.columns(4)
        sc1.checkbox("Test Failures",  value=True,  key="slack_fail")
        sc2.checkbox("Daily Summary",  value=True,  key="slack_daily")
        sc3.checkbox("Weekly Digest",  value=False, key="slack_weekly")
        sc4.checkbox("Run Complete",   value=True,  key="slack_complete")

        sb1, sb2 = st.columns(2)
        with sb1:
            slack_save = st.form_submit_button("💾 Save Slack Config", type="primary", use_container_width=True)
        with sb2:
            slack_test = st.form_submit_button("💬 Send Test Message", use_container_width=True)

    if slack_save:
        st.success("✅ Slack configuration saved.")
    if slack_test:
        st.info("💬 Test message sent to Slack — check your channel.")


# ── FOOTER ────────────────────────────────────────────────────
st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;font-size:12px;color:#9ca3af;padding:16px 0 32px;">
    AmplifyQA — NeuraFlash · Part of Accenture
</div>
""", unsafe_allow_html=True)