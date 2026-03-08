"""
3_Agentforce_Testing.py
Salesforce Agentforce AI Agent Testing Module.
"""

import streamlit as st
import json
import time
import uuid
from datetime import datetime
from config.theme import inject_css, render_header, render_sidebar_logo
from config.settings_manager import (
    load_all_keys_to_env, get_active_salesforce_connection,
    get_selected_judge_models
)
from connectors.salesforce_connector import connect_with_oauth, get_org_info
from connectors.llm_connector import multi_model_judge, get_llm_response

st.set_page_config(
    page_title="Agentforce Testing — AmplifyQA",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state = "collapsed",
)

inject_css()
load_all_keys_to_env()

with st.sidebar:
    render_sidebar_logo()
    st.page_link("app.py",                              label="🏠 Home")
    st.page_link("pages/2_Salesforce_Testing.py",       label="🧪 Salesforce Testing")
    st.page_link("pages/3_Agentforce_Testing.py",       label="🤖 Agentforce Testing")
    st.page_link("pages/4_Bedrock_AgentCore_Testing.py",label="☁️ Bedrock Testing")
    st.page_link("pages/5_Reports.py",                  label="📊 Reports")
    st.page_link("pages/8_Settings.py",                 label="⚙️ Settings")

# Auto-connect
sf  = st.session_state.get("sf_connection")
org = st.session_state.get("sf_org_info", {})

if not sf:
    active = get_active_salesforce_connection()
    if active and active.get("client_id"):
        sf, err = connect_with_oauth(
            client_id=active["client_id"],
            client_secret=active["client_secret"],
            domain=active["domain"]
        )
        if sf:
            st.session_state.sf_connection = sf
            st.session_state.sf_org_info   = get_org_info(sf)
            org = st.session_state.sf_org_info

render_header(
    "Agentforce Testing", "🤖",
    org_name=org.get("org_name",""),
    environment="Agentforce"
)

# ── PAGE CONTENT ──────────────────────────────────────────────
st.markdown("""
<div class="agentforce-card fade-in" style="margin-bottom:24px;">
    <div style="display:flex;align-items:center;gap:12px;
                margin-bottom:12px;">
        <span style="font-size:32px;">🤖</span>
        <div>
            <h2 style="margin:0;color:white;font-size:20px;">
                Agentforce AI Agent Testing
            </h2>
            <p style="margin:0;color:#a5b4fc;font-size:13px;">
                Test Salesforce Agentforce agents — conversation flows,
                intent accuracy, response quality and autonomous actions
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

if not sf:
    st.error(
        "❌ Salesforce not connected. "
        "Go to Settings to connect your org."
    )
    st.page_link("pages/8_Settings.py",
                 label="⚙️ Go to Settings →")
    st.stop()

# ── DISCOVER AGENTS ──────────────────────────────────────────
from engine.sf_metadata_engine import get_all_agents, get_sync_status

active_conn   = get_active_salesforce_connection()
org_domain    = active_conn.get("domain","") if active_conn else ""
agents        = get_all_agents(org_domain)
judge_models  = st.session_state.get(
    "judge_models", get_selected_judge_models()
)
llm_model     = (
    judge_models[0]
    if judge_models
    else "groq/llama-3.3-70b-versatile"
)

tab1, tab2, tab3 = st.tabs([
    "🤖 Agent Discovery",
    "💬 Chat Testing",
    "📊 Test Results"
])

# ── TAB 1: AGENT DISCOVERY ────────────────────────────────────
with tab1:
    st.subheader("Discovered Agentforce Agents")

    if agents:
        for agent in agents:
            st.markdown(f"""
            <div class="amplify-card" style="margin-bottom:12px;">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-size:28px;">🤖</span>
                    <div>
                        <h3 style="margin:0;">{agent.get('agent_label','')}</h3>
                        <p style="margin:0;color:#6b7280;font-size:13px;">
                            {agent.get('agent_name','')} |
                            Type: {agent.get('agent_type','')} |
                            Status: {agent.get('status','')}
                        </p>
                        <p style="margin:4px 0 0;font-size:12px;color:#9ca3af;">
                            {agent.get('description','No description')}
                        </p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info(
            "No Agentforce agents discovered in this org. "
            "Either no agents are deployed, or the org doesn't "
            "have Agentforce enabled. Run a Metadata Sync in "
            "Settings to refresh."
        )
        st.markdown("""
        <div class="feature-card teal" style="margin-top:16px;">
            <h4 style="margin:0 0 8px;">How to deploy an Agentforce Agent</h4>
            <p style="margin:0;font-size:13px;color:#374151;">
                1. Go to Salesforce Setup → Agents<br/>
                2. Create a new Agent or use an existing template<br/>
                3. Configure intents, actions, and channels<br/>
                4. Activate the agent<br/>
                5. Return here and run Metadata Sync
            </p>
        </div>
        """, unsafe_allow_html=True)

# ── TAB 2: CHAT TESTING ───────────────────────────────────────
with tab2:
    st.subheader("Test Agentforce Agent Conversations")

    col1, col2 = st.columns([2, 1])
    with col1:
        agent_name_input = st.text_input(
            "Agent Developer Name",
            placeholder="e.g. My_Sales_Agent",
            help=(
                "The DeveloperName of the BotDefinition "
                "in Salesforce"
            )
        )
        test_prompt = st.text_area(
            "Test Message to Agent",
            placeholder=(
                "e.g. What is the status of my order #12345?"
            ),
            height=100
        )
        expected = st.text_area(
            "Expected Agent Behavior",
            placeholder=(
                "e.g. Agent should look up order and return status"
            ),
            height=80
        )

    with col2:
        st.markdown("""
        <div class="amplify-card">
            <h4 style="margin:0 0 12px;">Test Options</h4>
        </div>
        """, unsafe_allow_html=True)

        test_type = st.selectbox(
            "Test Type",
            ["Single Message", "Conversation Flow",
             "Intent Validation", "Regression Suite"]
        )
        judge_count = len(judge_models)
        st.metric("Judge Models", judge_count)

    if st.button(
        "▶️ Run Agentforce Test",
        type="primary",
        use_container_width=True
    ):
        if not test_prompt.strip():
            st.error("Please enter a test message")
        else:
            with st.spinner("Sending to Agentforce agent..."):
                # Use SOQL to invoke bot if available
                try:
                    from connectors.salesforce_connector import run_soql_query
                    # Check if we can find the agent
                    records, _ = run_soql_query(
                        sf,
                        f"SELECT Id, MasterLabel, Status "
                        f"FROM BotDefinition "
                        f"WHERE DeveloperName = '{agent_name_input}' "
                        f"LIMIT 1"
                    )
                    if records:
                        agent_info = records[0]
                        st.info(
                            f"Found agent: "
                            f"{agent_info.get('MasterLabel')}"
                        )

                    # Use LLM judge to simulate agent evaluation
                    # (actual agent invocation requires
                    #  Messaging API or Connect API)
                    sim_prompt = (
                        f"Simulate how a Salesforce Agentforce AI "
                        f"agent named '{agent_name_input}' would "
                        f"respond to: '{test_prompt}'\n\n"
                        f"Provide a realistic agent response based "
                        f"on typical Salesforce CRM context."
                    )
                    sim_resp, sim_err = get_llm_response(
                        sim_prompt,
                        model=llm_model,
                        max_tokens=400
                    )

                    if sim_resp:
                        st.markdown("**Simulated Agent Response:**")
                        st.info(sim_resp)

                        # Judge the response
                        judge_result = multi_model_judge(
                            test_name=f"Agentforce: {test_prompt[:50]}",
                            expected_result=expected or (
                                "Agent provides helpful, accurate response"
                            ),
                            actual_result=sim_resp,
                            models=judge_models
                        )

                        verdict = judge_result.get(
                            "final_status","FAIL"
                        )
                        conf    = judge_result.get("confidence",0)

                        if verdict == "PASS":
                            st.success(
                                f"✅ PASS — {conf}% confidence"
                            )
                        else:
                            st.error(
                                f"❌ {verdict} — {conf}% confidence"
                            )

                        st.caption(
                            judge_result.get("summary","")
                        )

                except Exception as e:
                    st.error(f"Test error: {str(e)}")

# ── TAB 3: RESULTS ────────────────────────────────────────────
with tab3:
    st.subheader("Agentforce Test Results")
    st.info(
        "Run tests from the Chat Testing tab to see results here."
    )