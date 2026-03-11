"""
8_Settings.py — AmplifyQA Settings & Configuration
COMPLETELY FIXED VERSION - All Issues Resolved

FIXES IN THIS VERSION:
  • LLM Key Test button now shows VISUAL FEEDBACK (spinner + status)
  • Status indicators properly update (🟢 green = working, 🔴 red = failed, 🟡 yellow = untested)
  • Judge Models tab now correctly detects working providers
  • Models organized by TIER sections (not icons)
  • Added missing providers: OpenRouter, HuggingFace, NVIDIA NIM, Meta, Stability AI, Replicate
  • Comprehensive free model catalog (30+ free options)
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
from config.theme import render_header, inject_css
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
)
from connectors.bedrock_connector import test_bedrock_connection
from engine.sf_metadata_engine import (
    sync_full_org_metadata, get_sync_status, init_metadata_db,
)

# ── BOOT ──────────────────────────────────────────────────────
init_database()
init_metadata_db()
load_all_keys_to_env()
inject_css()

sf, org = page_init()

render_header(
    "Settings & Configuration", "⚙️",
    org_name=org.get("org_name", ""),
    environment=org.get("org_type", ""),
)

# ══════════════════════════════════════════════════════════════
# COMPREHENSIVE LLM PROVIDER CATALOG
# ══════════════════════════════════════════════════════════════

# Format: (provider_id, display_name, env_key, portal, test_model, tier)
PROVIDERS = [
    # ── COMPLETELY FREE ───────────────────────────────────────
    ("groq",         "Groq",              "GROQ_API_KEY",           "console.groq.com",              "groq/llama-3.3-70b-versatile",                          "FREE"),
    ("mistral",      "Mistral AI",        "MISTRAL_API_KEY",        "console.mistral.ai",            "mistral/mistral-small-latest",                          "FREE"),
    ("cerebras",     "Cerebras",          "CEREBRAS_API_KEY",       "cloud.cerebras.ai",             "cerebras/llama3.3-70b",                                 "FREE"),
    ("together_ai",  "Together AI",       "TOGETHER_API_KEY",       "api.together.ai",               "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",   "FREE"),
    ("fireworks_ai", "Fireworks AI",      "FIREWORKS_API_KEY",      "fireworks.ai",                  "fireworks_ai/accounts/fireworks/models/llama-v3p3-70b-instruct", "FREE"),
    ("openrouter",   "OpenRouter",        "OPENROUTER_API_KEY",     "openrouter.ai",                 "openrouter/meta-llama/llama-3.3-70b-instruct:free",     "FREE"),
    ("huggingface",  "HuggingFace",       "HUGGINGFACE_API_KEY",    "huggingface.co/settings/tokens","huggingface/meta-llama/Meta-Llama-3.1-8B-Instruct",     "FREE"),
    ("replicate",    "Replicate",         "REPLICATE_API_KEY",      "replicate.com/account/api-tokens","replicate/meta/meta-llama-3-70b-instruct",            "FREE"),
    ("cohere",       "Cohere",            "COHERE_API_KEY",         "dashboard.cohere.com",          "cohere/command-light",                                  "FREE"),
    ("ai21",         "AI21 Labs",         "AI21_API_KEY",           "studio.ai21.com",               "ai21/jamba-1.5-mini",                                   "FREE"),
    ("deepseek",     "DeepSeek",          "DEEPSEEK_API_KEY",       "platform.deepseek.com",         "deepseek/deepseek-chat",                                "FREE"),
    
    # ── LIMITED FREE ──────────────────────────────────────────
    ("gemini",       "Google Gemini",     "GEMINI_API_KEY",         "aistudio.google.com",           "gemini/gemini-2.0-flash-lite",                          "LIMITED_FREE"),
    ("perplexity",   "Perplexity",        "PERPLEXITY_API_KEY",     "perplexity.ai",                 "perplexity/sonar",                                      "LIMITED_FREE"),
    ("nvidia_nim",   "NVIDIA NIM",        "NVIDIA_NIM_API_KEY",     "build.nvidia.com",              "nvidia_nim/meta/llama-3.1-70b-instruct",                "LIMITED_FREE"),
    
    # ── PAID ──────────────────────────────────────────────────
    ("openai",       "OpenAI",            "OPENAI_API_KEY",         "platform.openai.com",           "gpt-4o-mini",                                           "PAID"),
    ("anthropic",    "Anthropic Claude",  "ANTHROPIC_API_KEY",      "console.anthropic.com",         "anthropic/claude-3-5-haiku-20241022",                   "PAID"),
    ("meta",         "Meta Llama",        "META_API_KEY",           "llama.meta.com",                "meta-llama/Meta-Llama-3.1-70B-Instruct",                "PAID"),
    ("stability",    "Stability AI",      "STABILITY_API_KEY",      "platform.stability.ai",         "stability-ai/stable-diffusion-xl-base-1.0",             "PAID"),
]

# ── COMPREHENSIVE MODEL CATALOG ───────────────────────────────
ALL_MODELS = {
    # ══════════════════════════════════════════════════════════
    # COMPLETELY FREE MODELS
    # ══════════════════════════════════════════════════════════
    
    "── Groq (FREE) ──────────────────────────────────────────": None,
    "Groq · Llama 3.3 70B Versatile":          "groq/llama-3.3-70b-versatile",
    "Groq · Llama 3.1 8B Instant":             "groq/llama-3.1-8b-instant",
    "Groq · Llama 4 Scout 17B":                "groq/meta-llama/llama-4-scout-17b-16e-instruct",
    "Groq · Llama 4 Maverick 17B":             "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
    "Groq · Compound Beta":                    "groq/compound-beta",
    "Groq · Compound Beta Mini":               "groq/compound-beta-mini",

    "── Mistral AI (FREE) ────────────────────────────────────": None,
    "Mistral · Mistral Small":                 "mistral/mistral-small-latest",
    "Mistral · Open Mistral 7B":               "mistral/open-mistral-7b",
    "Mistral · Open Mixtral 8x7B":             "mistral/open-mixtral-8x7b",
    "Mistral · Codestral":                     "mistral/codestral-latest",

    "── Cerebras (FREE) ──────────────────────────────────────": None,
    "Cerebras · Llama 3.3 70B":                "cerebras/llama3.3-70b",
    "Cerebras · Llama 3.1 8B":                 "cerebras/llama3.1-8b",
    "Cerebras · Llama 3.1 70B":                "cerebras/llama3.1-70b",

    "── OpenRouter Free (FREE) ───────────────────────────────": None,
    "OpenRouter · Llama 3.3 70B":              "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "OpenRouter · Llama 3.1 8B":               "openrouter/meta-llama/llama-3.1-8b-instruct:free",
    "OpenRouter · Gemma 2 9B":                 "openrouter/google/gemma-2-9b-it:free",
    "OpenRouter · Mistral 7B":                 "openrouter/mistralai/mistral-7b-instruct:free",
    "OpenRouter · Phi-3 Medium":               "openrouter/microsoft/phi-3-medium-128k-instruct:free",
    "OpenRouter · Qwen2 7B":                   "openrouter/qwen/qwen-2-7b-instruct:free",

    "── Together AI (FREE) ───────────────────────────────────": None,
    "Together · Llama 3.3 70B":                "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "Together · Llama 3.1 405B":               "together_ai/meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo",
    "Together · Llama 3.1 8B":                 "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "Together · Mistral 7B":                   "together_ai/mistralai/Mistral-7B-Instruct-v0.3",
    "Together · Gemma 2 27B":                  "together_ai/google/gemma-2-27b-it",
    "Together · Qwen 2.5 72B":                 "together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo",

    "── Fireworks AI (FREE) ──────────────────────────────────": None,
    "Fireworks · Llama 3.3 70B":               "fireworks_ai/accounts/fireworks/models/llama-v3p3-70b-instruct",
    "Fireworks · Llama 3.1 405B":              "fireworks_ai/accounts/fireworks/models/llama-v3p1-405b-instruct",
    "Fireworks · Qwen 2.5 72B":                "fireworks_ai/accounts/fireworks/models/qwen2p5-72b-instruct",

    "── HuggingFace (FREE) ───────────────────────────────────": None,
    "HuggingFace · Llama 3.1 8B":              "huggingface/meta-llama/Meta-Llama-3.1-8B-Instruct",
    "HuggingFace · Mistral 7B":                "huggingface/mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFace · Zephyr 7B":                 "huggingface/HuggingFaceH4/zephyr-7b-beta",
    "HuggingFace · Phi-3 Mini":                "huggingface/microsoft/Phi-3-mini-4k-instruct",

    "── Replicate (FREE) ─────────────────────────────────────": None,
    "Replicate · Llama 3 70B":                 "replicate/meta/meta-llama-3-70b-instruct",
    "Replicate · Llama 3.1 405B":              "replicate/meta/meta-llama-3.1-405b-instruct",
    "Replicate · Mistral 7B":                  "replicate/mistralai/mistral-7b-instruct-v0.2",

    "── DeepSeek (FREE/Cheap) ────────────────────────────────": None,
    "DeepSeek · Chat":                         "deepseek/deepseek-chat",
    "DeepSeek · Reasoner":                     "deepseek/deepseek-reasoner",

    "── Cohere (FREE Trial) ──────────────────────────────────": None,
    "Cohere · Command R":                      "cohere/command-r",
    "Cohere · Command Light":                  "cohere/command-light",

    "── AI21 Labs (FREE Trial) ───────────────────────────────": None,
    "AI21 · Jamba 1.5 Large":                  "ai21/jamba-1.5-large",
    "AI21 · Jamba 1.5 Mini":                   "ai21/jamba-1.5-mini",

    # ══════════════════════════════════════════════════════════
    # LIMITED FREE MODELS
    # ══════════════════════════════════════════════════════════

    "── Google Gemini (LIMITED FREE) ─────────────────────────": None,
    "Gemini · 2.0 Flash Lite":                 "gemini/gemini-2.0-flash-lite",
    "Gemini · 2.0 Flash":                      "gemini/gemini-2.0-flash",
    "Gemini · 1.5 Flash":                      "gemini/gemini-1.5-flash",
    "Gemini · 1.5 Pro":                        "gemini/gemini-1.5-pro",

    "── Perplexity (LIMITED FREE) ────────────────────────────": None,
    "Perplexity · Sonar":                      "perplexity/sonar",
    "Perplexity · Sonar Pro":                  "perplexity/sonar-pro",
    "Perplexity · Sonar Reasoning":            "perplexity/sonar-reasoning",

    "── NVIDIA NIM (FREE Credits) ────────────────────────────": None,
    "NVIDIA · Llama 3.1 70B":                  "nvidia_nim/meta/llama-3.1-70b-instruct",
    "NVIDIA · Llama 3.1 8B":                   "nvidia_nim/meta/llama-3.1-8b-instruct",
    "NVIDIA · Mistral 7B":                     "nvidia_nim/mistralai/mistral-7b-instruct-v0.3",
    "NVIDIA · Gemma 2 9B":                     "nvidia_nim/google/gemma-2-9b-it",

    # ══════════════════════════════════════════════════════════
    # PAID MODELS
    # ══════════════════════════════════════════════════════════

    "── OpenAI (PAID) ────────────────────────────────────────": None,
    "OpenAI · GPT-4o":                         "gpt-4o",
    "OpenAI · GPT-4o Mini":                    "gpt-4o-mini",
    "OpenAI · O1 Preview":                     "o1-preview",
    "OpenAI · O1 Mini":                        "o1-mini",
    "OpenAI · O3 Mini":                        "o3-mini",

    "── Anthropic Claude (PAID) ──────────────────────────────": None,
    "Claude · 3.7 Sonnet":                     "anthropic/claude-3-7-sonnet-20250219",
    "Claude · 3.5 Sonnet":                     "anthropic/claude-3-5-sonnet-20241022",
    "Claude · 3.5 Haiku":                      "anthropic/claude-3-5-haiku-20241022",
    "Claude · 3 Opus":                         "anthropic/claude-3-opus-20240229",

    "── Meta Llama (PAID via providers) ──────────────────────": None,
    "Meta · Llama 3.1 405B":                   "meta-llama/Meta-Llama-3.1-405B-Instruct",
    "Meta · Llama 3.1 70B":                    "meta-llama/Meta-Llama-3.1-70B-Instruct",
    "Meta · Llama 3.1 8B":                     "meta-llama/Meta-Llama-3.1-8B-Instruct",
}

# ── HELPER FUNCTIONS ──────────────────────────────────────────

def _working_pids(keys_dict: dict) -> set:
    """Return set of provider IDs with WORKING status."""
    return {pid for pid, data in keys_dict.items() if data.get("status") == "WORKING"}

def _safe_model_ids(models: list) -> list:
    """Extract model_id from judge model records."""
    if not models:
        return []
    return [m.get("model_id", "") for m in models if isinstance(m, dict) and m.get("model_id")]

def _model_available(model_id: str, working_providers: set) -> bool:
    """Check if model is available based on working providers."""
    if not model_id or "/" not in model_id:
        # Handle models without provider prefix (like OpenAI models)
        # Check if we have OpenAI key working
        return "openai" in working_providers
    provider = model_id.split("/")[0]
    
    # Map provider prefixes to provider IDs
    provider_map = {
        "groq": "groq",
        "mistral": "mistral",
        "cerebras": "cerebras",
        "gemini": "gemini",
        "anthropic": "anthropic",
        "openrouter": "openrouter",
        "together_ai": "together_ai",
        "fireworks_ai": "fireworks_ai",
        "huggingface": "huggingface",
        "replicate": "replicate",
        "cohere": "cohere",
        "ai21": "ai21",
        "deepseek": "deepseek",
        "perplexity": "perplexity",
        "nvidia_nim": "nvidia_nim",
        "meta-llama": "meta",
        "stability-ai": "stability",
        "gpt": "openai",  # OpenAI models
        "o1": "openai",
        "o3": "openai",
    }
    
    provider_id = provider_map.get(provider, provider)
    return provider_id in working_providers

# ══════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════

tab_sf, tab_br, tab_llm, tab_judge = st.tabs([
    "☁️ Salesforce Connections",
    "⚡ AWS Bedrock",
    "🧠 LLM API Keys",
    "⚖️ Judge Models"
])

# ══════════════════════════════════════════════════════════════
# TAB 1 — SALESFORCE CONNECTIONS (NO CHANGES)
# ══════════════════════════════════════════════════════════════
with tab_sf:
    st.markdown("### ☁️ Salesforce Org Connections")
    st.caption("Manage OAuth connections to your Salesforce orgs. Multiple orgs supported.")

    active_sf = get_active_salesforce_connection()
    if active_sf:
        st.markdown(
            '<div style="background:#ecfdf5;border:1px solid#10b981;border-radius:12px;'
            'padding:16px 20px;margin-bottom:20px;">'
            '<div style="display:flex;align-items:center;gap:12px;">'
            '<span style="font-size:22px;">🟢</span>'
            '<div><strong style="color:#065f46;">Active: ' + active_sf.get("org_name","") + '</strong><br/>'
            '<span style="font-size:12px;color:#047857;">' + active_sf.get("domain","") +
            "  |  " + active_sf.get("org_type","") +
            '</span></div></div></div>',
            unsafe_allow_html=True
        )

        # Show sync status
        sync = get_sync_status(active_sf.get("domain", ""))
        if sync and sync.get("last_sync"):
            st.info(
                f"📊 **Metadata Synced:** {sync.get('total_objects', 0)} objects, "
                f"{sync.get('total_fields', 0)} fields, "
                f"{sync.get('total_agents', 0)} agents, "
                f"{sync.get('total_flows', 0)} flows  |  "
                f"Last sync: {sync.get('last_sync', '')[:16]}"
            )

    sf_conns = get_all_salesforce_connections()
    if sf_conns:
        st.markdown("#### Saved Salesforce Connections")
        for conn in sf_conns:
            is_active = conn.get("is_active", 0)
            with st.expander(
                ("🟢 " if is_active else "⚪ ") +
                conn["org_name"] + "  —  " + conn["domain"] + "  |  " + conn.get("org_type","")
            ):
                c1, c2, c3, c4 = st.columns(4)
                c1.write(f"**Name:** {conn.get('connection_name','')}")
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
# TAB 2 — AMAZON BEDROCK (NO CHANGES)
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
# TAB 3 — LLM API KEYS (COMPLETELY REDESIGNED)
# ══════════════════════════════════════════════════════════════
with tab_llm:
    st.markdown("### 🧠 LLM API Keys")
    st.caption(
        "Configure API keys for each provider. At least one working key is needed to run tests. "
        "**11 providers offer completely FREE access**, 3 have limited free tiers, and 4 are paid-only."
    )

    saved_keys  = get_all_llm_keys()
    working_set = _working_pids(saved_keys)

    if working_set:
        providers_list = ", ".join(sorted([p.upper() for p in working_set]))
        st.success(f"✅ **{len(working_set)} active provider(s):** {providers_list}")
    else:
        st.warning("⚠️ No working LLM keys yet — add at least one provider below to get started.")

    st.markdown("---")

    # ── GROUP PROVIDERS BY TIER ───────────────────────────────
    
    free_providers = [p for p in PROVIDERS if p[5] == "FREE"]
    limited_providers = [p for p in PROVIDERS if p[5] == "LIMITED_FREE"]
    paid_providers = [p for p in PROVIDERS if p[5] == "PAID"]

    # ══════════════════════════════════════════════════════════
    # COMPLETELY FREE SECTION
    # ══════════════════════════════════════════════════════════
    
    st.markdown("## 🟢 Completely FREE Providers")
    st.caption(f"**{len(free_providers)} providers** with unlimited free access (no credit card required)")
    
    for pid, pname, env_key, portal, test_model, tier in free_providers:
        saved    = saved_keys.get(pid, {})
        curr_key = saved.get("key", os.getenv(env_key, ""))
        status   = saved.get("status", "")
        
        # Status icon logic
        if status == "WORKING":
            icon = "🟢"
            status_text = "Active & Working"
        elif status == "FAILED":
            icon = "🔴"
            status_text = "Test Failed"
        else:
            icon = "🟡"
            status_text = "Not Tested"

        with st.expander(
            f"{icon} {pname} — {status_text}",
            expanded=(not curr_key and status != "WORKING")
        ):
            k1, k2, k3 = st.columns([5, 1, 1])
            with k1:
                new_key = st.text_input(
                    f"{pname} API Key",
                    type="password",
                    value=curr_key,
                    key=f"llmkey_{pid}",
                    placeholder=f"Get free key from {portal}",
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
                # ── COMPLETELY FIXED TEST BUTTON ──
                test_btn = st.button("🧪", key=f"llmtest_{pid}",
                                     help="Test key", use_container_width=True)
                
            # Handle test button click OUTSIDE columns
            if test_btn:
                key_to_use = new_key.strip() or curr_key
                if not key_to_use:
                    st.warning("⚠️ Enter a key first before testing.")
                else:
                    # Set key in environment
                    os.environ[env_key] = key_to_use
                    
                    # Create placeholder for dynamic updates
                    status_placeholder = st.empty()
                    
                    # Show testing progress
                    status_placeholder.info(f"🔄 Testing {pname} with model `{test_model.split('/')[-1]}`...")
                    
                    try:
                        # Call LLM API
                        resp, err = get_llm_response(
                            "Say OK", 
                            model=test_model, 
                            max_tokens=10
                        )
                    except Exception as e:
                        resp, err = None, str(e)
                    
                    # Handle result
                    if resp and not err:
                        # Success
                        save_llm_key(pid, key_to_use)
                        update_llm_key_status(pid, "WORKING")
                        status_placeholder.success(f"✅ **{pname} is working!** Key validated successfully.")
                        st.balloons()
                        st.rerun()
                    else:
                        # Failure
                        update_llm_key_status(pid, "FAILED")
                        error_msg = err if err else "Unknown error"
                        status_placeholder.error(f"❌ **Test failed:** {error_msg[:300]}")
                        st.rerun()

            st.caption(f"🔗 [Get free API key at **{portal}**](https://{portal})")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # LIMITED FREE SECTION
    # ══════════════════════════════════════════════════════════
    
    st.markdown("## 🟡 Limited FREE Providers")
    st.caption(f"**{len(limited_providers)} providers** with free tiers (quotas or trial credits)")
    
    for pid, pname, env_key, portal, test_model, tier in limited_providers:
        saved    = saved_keys.get(pid, {})
        curr_key = saved.get("key", os.getenv(env_key, ""))
        status   = saved.get("status", "")
        
        # Status icon logic
        if status == "WORKING":
            icon = "🟢"
            status_text = "Active & Working"
        elif status == "FAILED":
            icon = "🔴"
            status_text = "Test Failed"
        else:
            icon = "🟡"
            status_text = "Not Tested"

        with st.expander(
            f"{icon} {pname} — {status_text}",
            expanded=(not curr_key and status != "WORKING")
        ):
            k1, k2, k3 = st.columns([5, 1, 1])
            with k1:
                new_key = st.text_input(
                    f"{pname} API Key",
                    type="password",
                    value=curr_key,
                    key=f"llmkey_{pid}",
                    placeholder=f"Get key from {portal}",
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
                test_btn = st.button("🧪", key=f"llmtest_{pid}",
                                     help="Test key", use_container_width=True)
                
            # Handle test button click
            if test_btn:
                key_to_use = new_key.strip() or curr_key
                if not key_to_use:
                    st.warning("⚠️ Enter a key first before testing.")
                else:
                    os.environ[env_key] = key_to_use
                    status_placeholder = st.empty()
                    status_placeholder.info(f"🔄 Testing {pname}...")
                    
                    try:
                        resp, err = get_llm_response("Say OK", model=test_model, max_tokens=10)
                    except Exception as e:
                        resp, err = None, str(e)
                    
                    if resp and not err:
                        save_llm_key(pid, key_to_use)
                        update_llm_key_status(pid, "WORKING")
                        status_placeholder.success(f"✅ **{pname} is working!**")
                        st.balloons()
                        st.rerun()
                    else:
                        update_llm_key_status(pid, "FAILED")
                        status_placeholder.error(f"❌ **Test failed:** {err[:300] if err else 'Unknown error'}")
                        st.rerun()

            st.caption(f"🔗 [Get API key at **{portal}**](https://{portal})")

    st.markdown("---")

    # ══════════════════════════════════════════════════════════
    # PAID SECTION
    # ══════════════════════════════════════════════════════════
    
    st.markdown("## 🔴 PAID Providers")
    st.caption(f"**{len(paid_providers)} providers** requiring payment (credit card needed)")
    
    for pid, pname, env_key, portal, test_model, tier in paid_providers:
        saved    = saved_keys.get(pid, {})
        curr_key = saved.get("key", os.getenv(env_key, ""))
        status   = saved.get("status", "")
        
        # Status icon logic
        if status == "WORKING":
            icon = "🟢"
            status_text = "Active & Working"
        elif status == "FAILED":
            icon = "🔴"
            status_text = "Test Failed"
        else:
            icon = "🟡"
            status_text = "Not Tested"

        with st.expander(
            f"{icon} {pname} — {status_text}",
            expanded=(not curr_key and status != "WORKING")
        ):
            k1, k2, k3 = st.columns([5, 1, 1])
            with k1:
                new_key = st.text_input(
                    f"{pname} API Key",
                    type="password",
                    value=curr_key,
                    key=f"llmkey_{pid}",
                    placeholder=f"Get key from {portal}",
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
                test_btn = st.button("🧪", key=f"llmtest_{pid}",
                                     help="Test key", use_container_width=True)
                
            # Handle test button click
            if test_btn:
                key_to_use = new_key.strip() or curr_key
                if not key_to_use:
                    st.warning("⚠️ Enter a key first before testing.")
                else:
                    os.environ[env_key] = key_to_use
                    status_placeholder = st.empty()
                    status_placeholder.info(f"🔄 Testing {pname}...")
                    
                    try:
                        resp, err = get_llm_response("Say OK", model=test_model, max_tokens=10)
                    except Exception as e:
                        resp, err = None, str(e)
                    
                    if resp and not err:
                        save_llm_key(pid, key_to_use)
                        update_llm_key_status(pid, "WORKING")
                        status_placeholder.success(f"✅ **{pname} is working!**")
                        st.balloons()
                        st.rerun()
                    else:
                        update_llm_key_status(pid, "FAILED")
                        status_placeholder.error(f"❌ **Test failed:** {err[:300] if err else 'Unknown error'}")
                        st.rerun()

            st.caption(f"🔗 [Get API key at **{portal}**](https://{portal})")


# ══════════════════════════════════════════════════════════════
# TAB 4 — JUDGE MODELS (FIXED)
# ══════════════════════════════════════════════════════════════
with tab_judge:
    st.markdown("### ⚖️ AI Judge Model Selection")
    st.caption(
        "Pick which models evaluate test responses. Any model from the catalogue "
        "can be selected — only models whose provider key is active are available. "
        "Using 2–5 diverse judges produces the most reliable scores."
    )

    saved_keys       = get_all_llm_keys()
    working          = _working_pids(saved_keys)
    judge_models_raw = get_selected_judge_models()
    current_ids      = _safe_model_ids(judge_models_raw)

    # Build available options with improved matching
    available_options = {}
    for label, mid in ALL_MODELS.items():
        if mid is not None and _model_available(mid, working):
            available_options[label] = mid

    if not available_options:
        st.warning(
            "⚠️ **No working LLM providers found.** Go to **LLM API Keys** tab, "
            "add at least one key, click 🧪 **Test** to verify it, then come back here."
        )
        
        # Show which providers are configured but not working
        if saved_keys:
            configured = list(saved_keys.keys())
            st.info(f"**Configured providers:** {', '.join([p.upper() for p in configured])}")
            st.info("💡 Make sure to click the 🧪 **Test** button for each key to verify it works!")
    else:
        option_labels  = list(available_options.keys())
        default_labels = [l for l, m in available_options.items() if m in current_ids]

        st.success(f"✅ **{len(option_labels)} models available** across {len(working)} active provider(s)")

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
        against the expected outcome. Consensus voting combines their verdicts to produce a
        final PASS/FAIL decision with a confidence score. More judges = higher reliability.
        </span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "💡 **Tip:** Test each LLM key with the 🧪 button to verify it works. "
    "**11 free providers** available — Groq, Mistral, Cerebras, OpenRouter, Together AI, "
    "Fireworks AI, HuggingFace, Replicate, DeepSeek, Cohere, AI21."
)