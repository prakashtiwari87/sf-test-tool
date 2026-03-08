"""
app.py — AmplifyQA Home
Marketing landing page + guided onboarding wizard.
"""

import streamlit as st
import os

st.set_page_config(
    page_title="AmplifyQA — AI-Augmented Testing Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from config.theme import inject_css, render_header
from config.settings_manager import (
    init_database, load_all_keys_to_env,
    get_active_salesforce_connection,
    get_all_llm_keys, get_selected_judge_models,
    save_salesforce_connection, save_llm_key,
    save_selected_judge_models
)
from connectors.salesforce_connector import connect_with_oauth, get_org_info
from connectors.llm_connector import (
    get_llm_response, DEFAULT_JUDGE_MODELS,
    update_llm_key_status, get_selectable_models
)

# ── BOOT ──────────────────────────────────────────────────────
init_database()
load_all_keys_to_env()

# ── AUTO-CONNECT SALESFORCE ───────────────────────────────────
sf  = st.session_state.get("sf_connection")
org = st.session_state.get("sf_org_info", {})
if not sf:
    active = get_active_salesforce_connection()
    if active and active.get("client_id"):
        sf_try, _ = connect_with_oauth(
            client_id=active["client_id"],
            client_secret=active["client_secret"],
            domain=active["domain"]
        )
        if sf_try:
            st.session_state.sf_connection = sf_try
            st.session_state.sf_org_info   = get_org_info(sf_try)
            sf  = sf_try
            org = st.session_state.sf_org_info

# ── INJECT CSS + TOP NAVBAR (with live connection status) ─────
inject_css(
    org_name     = org.get("org_name", ""),
    sf_connected = bool(sf)
)

# ── SESSION STATE ─────────────────────────────────────────────
for k, v in [("wizard_step", "hero"), ("wizard_target", None)]:
    if k not in st.session_state:
        st.session_state[k] = v


# ══════════════════════════════════════════════════════════════
# HERO LANDING PAGE
# ══════════════════════════════════════════════════════════════
if st.session_state.wizard_step == "hero":

    render_header("Home", "🏠",
                  org_name=org.get("org_name", ""),
                  environment=org.get("org_type", ""))

    # Main hero
    st.markdown("""
    <div class="hero-wrap fade-in">
        <div class="hero-badge">✨ Next-Generation AI Testing Platform</div>
        <h1>Welcome to the<br/>Future of Testing</h1>
        <p class="hero-sub">
            Introducing a next-generation <strong>AI-Augmented Testing
            Platform</strong> that seamlessly blends Human Intelligence
            with Autonomous AI Automation to redefine how enterprises
            deliver quality software.
        </p>
        <br/>
        <p class="hero-sub">
            In a world where speed and quality determine competitive
            advantage, traditional testing slows innovation.
            <strong>AmplifyQA changes the game.</strong>
            We let AI handle the repetitive, time-consuming testing
            work — from test creation and execution to analysis and
            reporting — while human QA experts focus on what truly
            matters: validating business quality, user experience,
            and strategic outcomes.
        </p>
        <br/>
        <p class="hero-sub" style="font-size:18px;font-weight:700;opacity:1;">
            Think of it as your 24/7 AI Testing Assistant.
        </p>
        <p class="hero-sub">
            An assistant that never gets tired. Never misses edge cases.
            Continuously tests your systems 365 days a year.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Stats row
    s1, s2, s3, s4 = st.columns(4)
    for col, icon, val, lbl in [
        (s1, "🚀", "10x",       "Faster Releases"),
        (s2, "✅", "100%",      "Test Coverage"),
        (s3, "🧠", "Real-time", "AI Precision"),
        (s4, "🔒", "Full",      "Audit Trail"),
    ]:
        col.markdown(
            '<div class="hero-stat">'
            '<span style="font-size:24px;">' + icon + '</span>'
            '<span class="snum">' + val + '</span>'
            '<span class="slbl">' + lbl + '</span>'
            '</div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

    # Results callout
    st.markdown("""
    <div class="aqa-card fade-in" style="margin-bottom:24px;">
        <h3 style="font-size:18px;margin:0 0 18px;">The result:</h3>
        <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:14px;">
            <div style="text-align:center;padding:18px;background:#eef2ff;border-radius:12px;">
                <div style="font-size:26px;">🚀</div>
                <div style="font-weight:700;color:#4338ca;margin-top:8px;font-size:14px;">Faster releases</div>
            </div>
            <div style="text-align:center;padding:18px;background:#f0fdf4;border-radius:12px;">
                <div style="font-size:26px;">✅</div>
                <div style="font-weight:700;color:#059669;margin-top:8px;font-size:14px;">Higher coverage</div>
            </div>
            <div style="text-align:center;padding:18px;background:#fdf4ff;border-radius:12px;">
                <div style="font-size:26px;">🎯</div>
                <div style="font-weight:700;color:#7c3aed;margin-top:8px;font-size:14px;">AI-driven precision</div>
            </div>
            <div style="text-align:center;padding:18px;background:#fff7ed;border-radius:12px;">
                <div style="font-size:26px;">🧑‍💼</div>
                <div style="font-weight:700;color:#c2410c;margin-top:8px;font-size:14px;">Human-guided QA</div>
            </div>
        </div>
        <p style="font-size:16px;font-weight:800;color:#4f46e5;text-align:center;margin:20px 0 0;">
            This is AI-Augmented Quality Engineering.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Feature cards
    st.markdown("""
    <div class="sec-head"><span>Platform Capabilities</span><hr/></div>
    """, unsafe_allow_html=True)

    fc1, fc2, fc3 = st.columns(3)
    for col, icon, colour, title, desc in [
        (fc1, "☁️", "#4f46e5",
         "Salesforce Testing",
         "Test any Salesforce implementation — standard objects, custom apps, "
         "flows, validation rules and complex business logic with AI-generated test data."),
        (fc2, "🤖", "#7c3aed",
         "Agentforce Testing",
         "Validate Salesforce Agentforce AI agents — test conversation flows, "
         "intent accuracy, response quality and autonomous action execution."),
        (fc3, "⚡", "#f59e0b",
         "Amazon Bedrock AgentCore",
         "Test Amazon Bedrock AgentCore agents — chat simulation, IVR voice testing, "
         "intent validation, conversation scoring and full regression suites."),
    ]:
        col.markdown(
            '<div class="aqa-card">'
            '<div style="width:40px;height:40px;border-radius:10px;'
            'background:' + colour + '18;display:flex;align-items:center;'
            'justify-content:center;font-size:22px;">' + icon + '</div>'
            '<h3>' + title + '</h3>'
            '<p>' + desc + '</p>'
            '</div>',
            unsafe_allow_html=True
        )

    st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)

    # CTA
    _, cta_col, _ = st.columns([1, 2, 1])
    with cta_col:
        if st.button(
            "🚀 Get Started — Set Up Your First Test",
            type="primary", use_container_width=True
        ):
            st.session_state.wizard_step = "choose_target"
            st.rerun()
        if sf:
            st.markdown(
                "<p style='text-align:center;font-size:12px;color:#9ca3af;margin-top:8px;'>"
                "or use the navigation bar above ↑</p>",
                unsafe_allow_html=True
            )


# ══════════════════════════════════════════════════════════════
# WIZARD STEP 1 — CHOOSE TARGET
# ══════════════════════════════════════════════════════════════
elif st.session_state.wizard_step == "choose_target":

    render_header("Getting Started", "🚀")

    st.markdown("""
    <div class="wizard-box fade-in">
        <div class="wizard-step-label">Step 1 of 3</div>
        <div class="wizard-title">What do you want to test today?</div>
        <div class="wizard-sub">Choose your testing target to begin the guided setup</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns(3)
    for col, icon, title, desc, key, target in [
        (c1, "☁️",
         "Salesforce Implementation",
         "Test objects, flows, validation rules, data integrity and business logic",
         "sel_sf", "salesforce"),
        (c2, "🤖",
         "Agentforce Agents",
         "Test AI agents, conversation flows, intent accuracy and autonomous actions",
         "sel_af", "agentforce"),
        (c3, "⚡",
         "Amazon Bedrock AgentCore",
         "Test Bedrock AI agents, Lex bots, Connect IVR and voice interactions",
         "sel_br", "bedrock"),
    ]:
        col.markdown(
            '<div class="option-card">'
            '<div class="icon">' + icon + '</div>'
            '<h4>' + title + '</h4>'
            '<p>' + desc + '</p>'
            '</div>',
            unsafe_allow_html=True
        )
        if col.button("Select →", key=key,
                      use_container_width=True, type="primary"):
            st.session_state.wizard_target = target
            st.session_state.wizard_step   = (
                "connect_bedrock" if target == "bedrock"
                else "connect_sf"
            )
            st.rerun()

    if st.button("← Back to Home"):
        st.session_state.wizard_step = "hero"
        st.rerun()


# ══════════════════════════════════════════════════════════════
# WIZARD STEP 2a — SALESFORCE CONNECTION
# ══════════════════════════════════════════════════════════════
elif st.session_state.wizard_step == "connect_sf":

    render_header("Connect Salesforce", "☁️")
    target     = st.session_state.wizard_target
    target_lbl = ("Salesforce Agentforce Agents"
                  if target == "agentforce"
                  else "Salesforce Implementation")

    st.markdown(
        '<div class="wizard-box fade-in">'
        '<div class="wizard-step-label">Step 2 of 3</div>'
        '<div class="wizard-title">Connect Your Salesforce Org</div>'
        '<div class="wizard-sub">Testing target: ' + target_lbl + '</div>'
        '</div>',
        unsafe_allow_html=True
    )

    if sf:
        st.success(
            f"✅ Already connected: **{org.get('org_name','')}** "
            f"({org.get('org_type','')})"
        )
        st.info("Your Salesforce connection is active. Continue to configure AI Judge Models.")
        if st.button("Continue to AI Model Setup →",
                     type="primary", use_container_width=True):
            st.session_state.wizard_step = "setup_llm"
            st.rerun()
    else:
        with st.form("wiz_sf_form"):
            col1, col2 = st.columns(2)
            with col1:
                cn_name   = st.text_input("Connection Name *",  placeholder="e.g. Dev Sandbox")
                cn_domain = st.text_input("My Domain URL *",    placeholder="yourorg.develop.my.salesforce.com")
                cn_env    = st.selectbox("Environment",
                    ["Sandbox","Production","Developer Edition","Scratch Org"])
            with col2:
                cn_key = st.text_input("Consumer Key *",    type="password")
                cn_sec = st.text_input("Consumer Secret *", type="password")
                st.caption("💡 Salesforce Setup → App Manager → Your App → Manage Consumer Details")

            c_sub, c_skip = st.columns(2)
            with c_sub:
                submitted = st.form_submit_button(
                    "🔌 Connect & Continue", type="primary", use_container_width=True)
            with c_skip:
                skipped = st.form_submit_button("Configure Later →", use_container_width=True)

        if submitted:
            if not all([cn_name, cn_domain, cn_key, cn_sec]):
                st.error("All fields with * are required.")
            else:
                with st.spinner("Connecting to Salesforce..."):
                    sf_new, err = connect_with_oauth(
                        client_id=cn_key, client_secret=cn_sec, domain=cn_domain)
                if sf_new:
                    oi = get_org_info(sf_new)
                    save_salesforce_connection(
                        name=cn_name, domain=cn_domain, auth_method="OAuth 2.0",
                        client_id=cn_key, client_secret=cn_sec,
                        org_name=oi.get("org_name",""), org_id=oi.get("org_id",""),
                        org_type=cn_env)
                    st.session_state.sf_connection = sf_new
                    st.session_state.sf_org_info   = oi
                    st.success(f"✅ Connected: {oi.get('org_name','')}")
                    st.balloons()
                    st.session_state.wizard_step = "setup_llm"
                    st.rerun()
                else:
                    st.error(f"Connection failed: {err}")
        if skipped:
            st.session_state.wizard_step = "setup_llm"
            st.rerun()

    if st.button("← Back"):
        st.session_state.wizard_step = "choose_target"
        st.rerun()


# ══════════════════════════════════════════════════════════════
# WIZARD STEP 2b — BEDROCK CONNECTION
# ══════════════════════════════════════════════════════════════
elif st.session_state.wizard_step == "connect_bedrock":

    render_header("Connect AWS Bedrock", "⚡")

    st.markdown("""
    <div class="wizard-box fade-in">
        <div class="wizard-step-label">Step 2 of 3</div>
        <div class="wizard-title">Connect Amazon Bedrock AgentCore</div>
        <div class="wizard-sub">Configure your AWS credentials and agent endpoint</div>
    </div>
    """, unsafe_allow_html=True)

    with st.form("wiz_br_form"):
        col1, col2 = st.columns(2)
        with col1:
            br_region = st.selectbox("AWS Region *",
                ["us-east-1","us-west-2","eu-west-1","ap-southeast-1","ap-northeast-1"])
            br_access = st.text_input("AWS Access Key ID *",    type="password", placeholder="AKIA...")
            br_secret = st.text_input("AWS Secret Access Key *", type="password")
        with col2:
            br_agent = st.text_input("Bedrock Agent ID",   placeholder="e.g. AGENTID123")
            br_alias = st.text_input("Agent Alias ID",     placeholder="e.g. TSTALIASID")
            br_env   = st.selectbox("Environment", ["Development","Staging","Production"])

        b_sub, b_skip = st.columns(2)
        with b_sub:
            br_submitted = st.form_submit_button(
                "🔌 Connect Bedrock →", type="primary", use_container_width=True)
        with b_skip:
            br_skipped = st.form_submit_button("Configure Later →", use_container_width=True)

    if br_submitted:
        if br_access and br_secret:
            from config.settings_manager import save_bedrock_connection
            save_bedrock_connection(
                name="Bedrock " + br_env, region=br_region,
                access_key=br_access, secret_key=br_secret,
                agent_id=br_agent, agent_alias_id=br_alias, environment=br_env)
            st.success("✅ Bedrock credentials saved")
            st.session_state.wizard_step = "setup_llm"
            st.rerun()
        else:
            st.error("AWS Access Key and Secret Key are required")
    if br_skipped:
        st.session_state.wizard_step = "setup_llm"
        st.rerun()

    if st.button("← Back"):
        st.session_state.wizard_step = "choose_target"
        st.rerun()


# ══════════════════════════════════════════════════════════════
# WIZARD STEP 3 — LLM SETUP
# ══════════════════════════════════════════════════════════════
elif st.session_state.wizard_step == "setup_llm":

    render_header("Configure AI Models", "🧠")

    st.markdown("""
    <div class="wizard-box fade-in">
        <div class="wizard-step-label">Step 3 of 3</div>
        <div class="wizard-title">Configure AI Judge Models</div>
        <div class="wizard-sub">
            At least one working model is required to run tests.
            Groq and Mistral offer free tiers — great to start.
        </div>
    </div>
    """, unsafe_allow_html=True)

    saved_keys = get_all_llm_keys()

    PROVIDERS = [
        ("GROQ",     "Groq",      "GROQ_API_KEY",
         "console.groq.com",          "groq/llama-3.3-70b-versatile",    "🟢 Free"),
        ("MISTRAL",  "Mistral",   "MISTRAL_API_KEY",
         "console.mistral.ai",         "mistral/open-mistral-7b",          "🟢 Free"),
        ("GEMINI",   "Google",    "GEMINI_API_KEY",
         "aistudio.google.com",        "gemini/gemini-1.5-flash",          "🟢 Free"),
        ("OPENAI",   "OpenAI",    "OPENAI_API_KEY",
         "platform.openai.com",        "gpt-4o-mini",                      "💰 Paid"),
        ("ANTHROPIC","Anthropic", "ANTHROPIC_API_KEY",
         "console.anthropic.com",      "claude-3-5-haiku-20241022",        "💰 Paid"),
    ]

    working = []

    for pid, pname, env_key, portal, test_model, tier in PROVIDERS:
        saved    = saved_keys.get(pid, {})
        curr_key = saved.get("key", os.getenv(env_key, ""))
        status   = saved.get("status", "")
        icon     = "✅" if status == "WORKING" else "❌" if status == "FAILED" else "⚪"

        with st.expander(f"{icon} {pname} — {tier}",
                         expanded=(status != "WORKING")):
            k1, k2, k3 = st.columns([5, 1, 1])
            with k1:
                new_key = st.text_input(
                    f"{pname} API Key", type="password",
                    value=curr_key, key=f"wk_{pid}",
                    placeholder=f"Get free at {portal}")
            with k2:
                if st.button("💾", key=f"ws_{pid}", help="Save"):
                    if new_key.strip():
                        save_llm_key(pid, new_key.strip())
                        os.environ[env_key] = new_key.strip()
                        st.success("Saved")
                        st.rerun()
            with k3:
                if st.button("🧪", key=f"wt_{pid}", help="Test"):
                    key_to_use = new_key.strip() or curr_key
                    if key_to_use:
                        os.environ[env_key] = key_to_use
                        with st.spinner("Testing..."):
                            resp, err = get_llm_response(
                                "Say OK", model=test_model, max_tokens=5)
                        if resp:
                            save_llm_key(pid, key_to_use)
                            update_llm_key_status(pid, "WORKING")
                            st.success("✅ Working!")
                        else:
                            update_llm_key_status(pid, "FAILED")
                            st.error(f"❌ {err}")
                        st.rerun()
                    else:
                        st.warning("Enter a key first")

        if status == "WORKING":
            working.append(test_model)

    st.markdown("---")

    if working:
        st.success(
            f"✅ {len(working)} model(s) ready: "
            + ", ".join(m.split("/")[-1] for m in working)
        )
        model_data = [
            {"model_id": m, "model_name": m.split("/")[-1],
             "provider": m.split("/")[0]}
            for m in working
        ]
        save_selected_judge_models(model_data)
        st.session_state.judge_models = working
        st.session_state.llm_model    = working[0]

        if st.button("🚀 Launch Testing Platform →",
                     type="primary", use_container_width=True):
            st.session_state.wizard_step = "complete"
            st.rerun()
    else:
        st.warning("⚠️ No working models yet. Save and test at least one key above.")
        if st.button("Continue Anyway →", use_container_width=True):
            st.session_state.wizard_step = "complete"
            st.rerun()

    if st.button("← Back"):
        st.session_state.wizard_step = (
            "connect_sf"
            if st.session_state.wizard_target != "bedrock"
            else "connect_bedrock"
        )
        st.rerun()


# ══════════════════════════════════════════════════════════════
# WIZARD COMPLETE
# ══════════════════════════════════════════════════════════════
elif st.session_state.wizard_step == "complete":

    render_header("Setup Complete", "🎉")
    st.balloons()

    st.markdown("""
    <div style="text-align:center;padding:48px 24px;" class="fade-in">
        <div style="font-size:72px;margin-bottom:16px;">🎉</div>
        <h1 style="font-size:32px;font-weight:900;color:#1e1b4b;
                   letter-spacing:-1px;margin-bottom:12px;">
            You're all set!
        </h1>
        <p style="font-size:16px;color:#6b7280;max-width:480px;
                  margin:0 auto 36px;line-height:1.6;">
            AmplifyQA is configured and ready.
            Use the navigation bar at the top to switch between modules.
        </p>
    </div>
    """, unsafe_allow_html=True)

    target   = st.session_state.wizard_target
    dest_map = {
        "salesforce": ("pages/2_Salesforce_Testing.py",        "🧪 Go to Salesforce Testing"),
        "agentforce": ("pages/3_Agentforce_Testing.py",        "🤖 Go to Agentforce Testing"),
        "bedrock":    ("pages/4_Bedrock_AgentCore_Testing.py", "☁️ Go to Bedrock Testing"),
    }
    dest_page, dest_label = dest_map.get(
        target, ("pages/2_Salesforce_Testing.py", "🧪 Go to Testing"))

    _, mc, _ = st.columns([1, 2, 1])
    with mc:
        st.page_link(dest_page,           label=dest_label)
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        st.page_link("pages/8_Settings.py", label="⚙️ Go to Settings")
        st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
        if st.button("🏠 Back to Home", use_container_width=True):
            st.session_state.wizard_step   = "hero"
            st.session_state.wizard_target = None
            st.rerun()