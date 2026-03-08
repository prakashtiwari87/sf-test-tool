"""
4_Bedrock_AgentCore_Testing.py
Amazon Bedrock AgentCore AI Agent Testing Module.
Supports: chat, conversation flows, Lex intent testing,
          Connect IVR simulation, response scoring, regression.
"""

import streamlit as st
import json
import time
import uuid
import pandas as pd
import io
from datetime import datetime
from config.theme import inject_css, render_header, render_sidebar_logo
from config.settings_manager import (
    load_all_keys_to_env, get_active_bedrock_connection,
    get_selected_judge_models, get_all_bedrock_connections
)
from connectors.bedrock_connector import (
    test_bedrock_connection, invoke_bedrock_agent,
    run_conversation_flow, list_bedrock_agents,
    test_lex_bot
)
from engine.bedrock_test_engine import (
    run_chat_test, run_conversation_test,
    run_intent_validation_test, run_regression_suite,
    score_agent_response
)

st.set_page_config(
    page_title="Bedrock AgentCore Testing — AmplifyQA",
    page_icon="☁️",
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

# Load active Bedrock config
bedrock_config = get_active_bedrock_connection()
judge_models   = st.session_state.get(
    "judge_models", get_selected_judge_models()
)
llm_model = (
    judge_models[0]
    if judge_models
    else "groq/llama-3.3-70b-versatile"
)

render_header(
    "Amazon Bedrock AgentCore Testing", "☁️",
    org_name=bedrock_config.get("connection_name",""),
    environment=bedrock_config.get("environment","AWS")
)

# Hero
st.markdown("""
<div class="bedrock-card fade-in" style="margin-bottom:24px;">
    <div style="display:flex;align-items:center;gap:16px;">
        <span style="font-size:40px;">☁️</span>
        <div>
            <div class="bedrock-badge">
                ⚡ Amazon Bedrock AgentCore
            </div>
            <h2 style="margin:8px 0 4px;color:white;font-size:22px;">
                AI Agent Testing Platform
            </h2>
            <p style="margin:0;color:#94a3b8;font-size:13px;">
                Test Amazon Bedrock Agents · Amazon Lex Bots ·
                Amazon Connect IVR · Lambda Functions ·
                Voice and Chat Interactions
            </p>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Connection check
if not bedrock_config:
    st.warning(
        "⚠️ No Amazon Bedrock connection configured. "
        "Go to Settings → Amazon Bedrock AgentCore Connections."
    )
    st.page_link(
        "pages/8_Settings.py",
        label="⚙️ Configure Bedrock Connection →"
    )

    # Still allow demo/preview mode
    st.markdown("---")
    st.info(
        "You can still explore the testing interface below. "
        "Configure your AWS credentials in Settings to "
        "run live tests."
    )

# Tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔌 Connection",
    "💬 Chat Testing",
    "🔄 Conversation Flows",
    "🎯 Intent Validation",
    "📞 IVR / Voice Testing",
    "📊 Regression Suite"
])

# ── TAB 1: CONNECTION ─────────────────────────────────────────
with tab1:
    st.subheader("Amazon Bedrock Connection Status")

    if bedrock_config:
        col1, col2, col3 = st.columns(3)
        col1.metric("Region",       bedrock_config.get("region","—"))
        col2.metric("Agent ID",     bedrock_config.get("agent_id","—")[:12] + "...")
        col3.metric("Environment",  bedrock_config.get("environment","—"))

        if st.button(
            "🔌 Test Connection",
            type="primary"
        ):
            with st.spinner("Testing AWS connection..."):
                result, err = test_bedrock_connection(
                    access_key=bedrock_config["access_key"],
                    secret_key=bedrock_config["secret_key"],
                    region=bedrock_config["region"]
                )
            if result:
                st.success(result.get("message","Connected"))
                agents = result.get("agents",[])
                if agents:
                    st.markdown("**Discovered Bedrock Agents:**")
                    for agent in agents:
                        st.write(
                            f"• {agent.get('agentName','')} "
                            f"({agent.get('agentStatus','')})"
                        )
            else:
                st.error(f"Connection failed: {err}")
    else:
        st.error(
            "No Bedrock connection configured. "
            "Go to Settings to add your AWS credentials."
        )

    st.markdown("---")
    st.subheader("Saved Connections")
    connections = get_all_bedrock_connections()
    if connections:
        for conn in connections:
            badge = "🟢 ACTIVE" if conn["is_active"] else "⚪ inactive"
            st.markdown(
                f"{badge} **{conn['connection_name']}** | "
                f"Region: {conn['region']} | "
                f"Agent: {conn.get('agent_id','—')[:10]}... | "
                f"{conn['environment']}"
            )
    else:
        st.info(
            "No connections saved yet. "
            "Add one in Settings → Amazon Bedrock AgentCore Connections."
        )

# ── TAB 2: CHAT TESTING ───────────────────────────────────────
with tab2:
    st.subheader("Chat / Prompt Testing")
    st.caption(
        "Send a single message to your Bedrock agent "
        "and validate the response with AI judges."
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        chat_prompt  = st.text_area(
            "Test Prompt",
            placeholder=(
                "e.g. What is the weather in Seattle today?"
                "e.g. What is the return policy for damaged items?"
            ),
            height=120,
            key="chat_prompt"
        )
        chat_expected = st.text_area(
            "Expected Behavior",
            placeholder=(
                "e.g. Agent should explain the return policy "
                "clearly and offer next steps"
            ),
            height=80,
            key="chat_expected"
        )

    with col2:
        st.markdown("""
        <div class="amplify-card" style="padding:16px;">
            <h4 style="margin:0 0 12px;font-size:14px;">
                Test Configuration
            </h4>
        </div>
        """, unsafe_allow_html=True)
        chat_scenario_id = st.text_input(
            "Scenario ID",
            value=f"CHAT-{datetime.now().strftime('%H%M%S')}",
            key="chat_sid"
        )
        st.metric("Judge Models", len(judge_models))
        st.caption(
            "Response is scored on:\n"
            "Relevance · Accuracy · Completeness · Safety"
        )

    if st.button(
        "▶️ Run Chat Test",
        type="primary",
        use_container_width=True,
        key="run_chat"
    ):
        if not chat_prompt.strip():
            st.error("Please enter a test prompt")
        elif not bedrock_config:
            st.error(
                "No Bedrock connection. Configure in Settings."
            )
        else:
            test_case = {
                "test_id":       chat_scenario_id,
                "test_name":     chat_prompt[:60],
                "input_data":    chat_prompt,
                "expected_output": chat_expected,
                "test_type":     "chat"
            }
            with st.spinner("Invoking Bedrock agent..."):
                result = run_chat_test(
                    bedrock_config, test_case, llm_model
                )

            status = result.get("status","ERROR")
            icon   = (
                "✅" if status == "PASS" else
                "❌" if status == "FAIL" else "⚠️"
            )

            st.markdown(f"### {icon} Result: {status}")

            rc1, rc2, rc3, rc4 = st.columns(4)
            score = result.get("score", {})
            rc1.metric(
                "Overall Score",
                f"{result.get('overall_score',0)}/10"
            )
            rc2.metric(
                "Relevance",
                f"{score.get('relevance',0)}/10"
            )
            rc3.metric(
                "Accuracy",
                f"{score.get('accuracy',0)}/10"
            )
            rc4.metric(
                "Duration",
                f"{result.get('duration_s',0)}s"
            )

            st.markdown("**Agent Response:**")
            st.info(result.get("response","No response"))

            st.markdown("**AI Judge Reasoning:**")
            st.write(score.get("reasoning","—"))

            if result.get("error"):
                st.error(f"Error: {result['error']}")

            if "chat_results" not in st.session_state:
                st.session_state.chat_results = []
            st.session_state.chat_results.append(result)

# ── TAB 3: CONVERSATION FLOWS ─────────────────────────────────
with tab3:
    st.subheader("Multi-Turn Conversation Flow Testing")
    st.caption(
        "Test complex multi-turn conversations with "
        "your Bedrock agent. Define a sequence of user messages "
        "and validate the complete conversation."
    )

    st.markdown("**Define Conversation Turns:**")

    if "conv_turns" not in st.session_state:
        st.session_state.conv_turns = [
            {"turn": 1, "message": ""},
            {"turn": 2, "message": ""}
        ]

    t1, t2 = st.columns([5, 1])
    with t2:
        if st.button("➕ Add Turn", use_container_width=True):
            turns = st.session_state.conv_turns
            turns.append({
                "turn":    len(turns) + 1,
                "message": ""
            })
            st.session_state.conv_turns = turns
            st.rerun()

    updated_turns = []
    for i, turn in enumerate(st.session_state.conv_turns):
        col_num, col_msg, col_del = st.columns([1, 8, 1])
        with col_num:
            st.markdown(
                f"<div style='background:#6366f1;color:white;"
                f"border-radius:50%;width:32px;height:32px;"
                f"display:flex;align-items:center;"
                f"justify-content:center;font-weight:700;"
                f"margin-top:28px;'>{i+1}</div>",
                unsafe_allow_html=True
            )
        with col_msg:
            msg = st.text_input(
                f"Turn {i+1} — User Message",
                value=turn.get("message",""),
                key=f"conv_turn_{i}",
                placeholder=f"e.g. Hi, I need help with my account"
            )
        with col_del:
            if st.button("🗑", key=f"del_turn_{i}") and len(st.session_state.conv_turns) > 1:
                new_turns = [
                    t for j, t in
                    enumerate(st.session_state.conv_turns)
                    if j != i
                ]
                st.session_state.conv_turns = new_turns
                st.rerun()
        updated_turns.append({"turn": i+1, "message": msg})

    st.session_state.conv_turns = updated_turns

    conv_expected = st.text_area(
        "Expected Final Outcome",
        placeholder=(
            "e.g. Agent should successfully resolve the "
            "customer's issue by the end of the conversation"
        ),
        height=80
    )

    if st.button(
        "▶️ Run Conversation Flow Test",
        type="primary",
        use_container_width=True,
        key="run_conv"
    ):
        if not bedrock_config:
            st.error("No Bedrock connection configured.")
        else:
            conversation = [
                {"role": "user", "content": t["message"]}
                for t in updated_turns
                if t.get("message","").strip()
            ]
            if not conversation:
                st.error("Add at least one conversation turn.")
            else:
                test_case = {
                    "test_id":      f"CONV-{datetime.now().strftime('%H%M%S')}",
                    "test_name":    "Conversation Flow Test",
                    "input_data":   json.dumps(conversation),
                    "expected_output": conv_expected,
                    "test_type":    "conversation"
                }
                with st.spinner("Running conversation flow..."):
                    result = run_conversation_test(
                        bedrock_config, test_case, llm_model
                    )

                status = result.get("status","ERROR")
                icon   = "✅" if status == "PASS" else "❌"
                st.markdown(f"### {icon} Result: {status}")

                rc1, rc2, rc3 = st.columns(3)
                rc1.metric(
                    "Total Turns",
                    result.get("total_turns",0)
                )
                rc2.metric(
                    "Successful",
                    result.get("successful_turns",0)
                )
                rc3.metric(
                    "Pass Rate",
                    f"{result.get('pass_rate',0)}%"
                )

                st.markdown("**Turn-by-Turn Results:**")
                for turn in result.get("turns",[]):
                    turn_icon = "✅" if turn.get("success") else "❌"
                    with st.expander(
                        f"{turn_icon} Turn {turn['turn']}: "
                        f"{turn.get('prompt','')[:60]}"
                    ):
                        st.write(
                            "**Response:**",
                            turn.get("response","No response")
                        )
                        if turn.get("error"):
                            st.error(turn["error"])

# ── TAB 4: INTENT VALIDATION ──────────────────────────────────
with tab4:
    st.subheader("Intent Validation Testing")
    st.caption(
        "Validate that your Amazon Lex bot or Bedrock agent "
        "correctly identifies user intents."
    )

    col1, col2 = st.columns(2)
    with col1:
        intent_test_cases = st.text_area(
            "Test Cases (one per line: prompt | expected_intent)",
            height=200,
            placeholder=(
                "What is my balance? | CheckBalance\n"
                "I want to cancel my subscription | CancelAccount\n"
                "Where is my order? | TrackOrder\n"
                "Help me reset my password | PasswordReset"
            ),
            key="intent_cases"
        )

    with col2:
        st.markdown("""
        <div class="amplify-card">
            <h4 style="margin:0 0 12px;">Lex Bot Configuration</h4>
        </div>
        """, unsafe_allow_html=True)
        lex_bot_id   = st.text_input(
            "Lex Bot ID (optional)",
            value=bedrock_config.get("bot_id","") if bedrock_config else "",
            placeholder="e.g. ABCDEFGH12"
        )
        lex_alias_id = st.text_input(
            "Lex Alias ID (optional)",
            value=bedrock_config.get("bot_alias_id","") if bedrock_config else "",
            placeholder="e.g. TSTALIASID"
        )
        locale_id    = st.selectbox(
            "Locale",
            ["en_US","en_GB","fr_FR","de_DE","es_ES","ja_JP"]
        )

    if st.button(
        "▶️ Run Intent Validation",
        type="primary",
        use_container_width=True,
        key="run_intent"
    ):
        if not intent_test_cases.strip():
            st.error("Please add at least one test case")
        elif not bedrock_config:
            st.error("No Bedrock connection configured")
        else:
            lines = [
                l.strip() for l in
                intent_test_cases.strip().split("\n")
                if l.strip()
            ]
            test_cases = []
            for line in lines:
                parts = line.split("|")
                test_cases.append({
                    "test_id":       f"INTENT-{len(test_cases)+1:03d}",
                    "test_name":     parts[0].strip()[:60],
                    "input_data":    parts[0].strip(),
                    "expected_output": parts[1].strip() if len(parts)>1 else "",
                    "test_type":     "intent"
                })

            bc = dict(bedrock_config)
            if lex_bot_id:
                bc["bot_id"]      = lex_bot_id
                bc["bot_alias_id"] = lex_alias_id
                bc["locale_id"]   = locale_id

            passed = 0
            failed = 0
            for tc in test_cases:
                result = run_intent_validation_test(
                    bc, tc, llm_model
                )
                status = result.get("status","ERROR")
                icon   = "✅" if status=="PASS" else "❌"
                conf   = result.get("confidence",
                         result.get("score",{}).get("overall_score",0))
                st.markdown(
                    f"{icon} **{tc['test_name']}** → "
                    f"Expected: `{tc.get('expected_output','—')}` | "
                    f"Score: {conf}"
                )
                if status == "PASS":
                    passed += 1
                else:
                    failed += 1

            st.markdown("---")
            ic1, ic2, ic3 = st.columns(3)
            ic1.metric("Total",  len(test_cases))
            ic2.metric("✅ Pass", passed)
            ic3.metric("❌ Fail", failed)

# ── TAB 5: IVR / VOICE TESTING ───────────────────────────────
with tab5:
    st.subheader("IVR & Voice Testing — Amazon Connect")
    st.caption(
        "Simulate IVR call flows and voice interactions "
        "using Amazon Connect testing APIs."
    )

    st.markdown("""
    <div class="bedrock-card" style="margin-bottom:20px;">
        <h4 style="color:white;margin:0 0 8px;">
            📞 Amazon Connect IVR Testing
        </h4>
        <p style="color:#94a3b8;font-size:13px;margin:0;">
            This module maps out IVR call flows, simulates
            caller navigation, validates system prompts,
            and tests DTMF / voice inputs using
            Amazon Connect's dedicated testing APIs.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        connect_instance = st.text_input(
            "Amazon Connect Instance ID",
            value=bedrock_config.get("instance_id","") if bedrock_config else "",
            placeholder="e.g. xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        )
        contact_flow_id  = st.text_input(
            "Contact Flow ID",
            placeholder="e.g. xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
        )
        source_phone     = st.text_input(
            "Source Phone Number (E.164)",
            placeholder="e.g. +12025551234"
        )

    with col2:
        st.markdown("""
        <div class="amplify-card">
            <h4 style="margin:0 0 8px;">IVR Flow Configuration</h4>
        </div>
        """, unsafe_allow_html=True)
        ivr_scenario = st.text_area(
            "IVR Test Scenario",
            height=120,
            placeholder=(
                "Describe the IVR flow to test:\n"
                "1. Caller dials in\n"
                "2. Hears welcome message\n"
                "3. Presses 1 for Sales\n"
                "4. Expects agent pickup within 30s"
            )
        )

    expected_prompts = st.text_area(
        "Expected IVR Prompts (one per line)",
        placeholder=(
            "Thank you for calling, press 1 for Sales\n"
            "Please hold while we connect you\n"
            "Your estimated wait time is 2 minutes"
        ),
        height=80
    )

    if st.button(
        "📞 Run IVR Flow Test",
        type="primary",
        use_container_width=True,
        key="run_ivr"
    ):
        if not bedrock_config:
            st.error("No Bedrock/AWS connection configured.")
        elif not connect_instance.strip():
            st.warning(
                "Amazon Connect Instance ID required for live IVR testing. "
                "Running simulation mode..."
            )

        # Simulation mode using LLM
        if ivr_scenario.strip():
            sim_prompt = (
                f"Simulate an Amazon Connect IVR call flow test.\n\n"
                f"IVR Scenario: {ivr_scenario}\n\n"
                f"Expected Prompts:\n{expected_prompts}\n\n"
                f"Provide a step-by-step test execution report "
                f"with PASS/FAIL for each step. Include:\n"
                f"- Step number\n"
                f"- Expected prompt\n"
                f"- Simulated system response\n"
                f"- PASS or FAIL\n"
                f"- Any issues detected"
            )

            with st.spinner("Simulating IVR flow..."):
                sim_result, sim_err = get_llm_response(
                    sim_prompt,
                    model=llm_model,
                    max_tokens=600
                )

            if sim_result:
                st.success("✅ IVR Simulation Complete")
                st.markdown("**Simulation Report:**")
                st.write(sim_result)
            else:
                st.error(f"Simulation failed: {sim_err}")

    st.markdown("---")
    st.markdown("""
    <div class="feature-card" style="margin-top:8px;">
        <h4 style="margin:0 0 8px;">Voice Testing Pipeline</h4>
        <p style="margin:0;font-size:13px;color:#374151;">
            <strong>Supported test types:</strong><br/>
            • DTMF input simulation (keypad navigation)<br/>
            • Voice recognition testing (Amazon Transcribe)<br/>
            • TTS response validation (Amazon Polly)<br/>
            • Lex bot intent detection in voice context<br/>
            • Dynamic conversation branching validation<br/>
            • Wait time and queue behavior testing<br/>
            • Lambda-backed contact flow testing
        </p>
    </div>
    """, unsafe_allow_html=True)

# ── TAB 6: REGRESSION SUITE ───────────────────────────────────
with tab6:
    st.subheader("Automated Regression Suite")
    st.caption(
        "Run a full regression suite of Bedrock agent tests "
        "from an Excel template or UI-defined test cases."
    )

    from engine.excel_loader import (
        load_test_cases_from_excel,
        create_excel_template
    )

    col_dl, col_info = st.columns([1, 3])
    with col_dl:
        st.download_button(
            "⬇️ Download Test Template",
            data=create_excel_template(),
            file_name="bedrock_test_template.xlsx",
            mime=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            ),
            use_container_width=True
        )
    with col_info:
        st.info(
            "Use the same template format. "
            "Set 'Detailed Test Steps' to your agent prompts. "
            "Test types: chat · conversation · intent"
        )

    reg_file = st.file_uploader(
        "Upload Regression Test Excel",
        type=["xlsx","xls"],
        key="bedrock_regression"
    )

    if reg_file:
        test_cases, warning = load_test_cases_from_excel(reg_file)
        if test_cases:
            st.success(
                f"✅ Loaded {len(test_cases)} test cases"
            )
            if warning:
                st.warning(warning)

            rc1, rc2, rc3 = st.columns(3)
            rc1.metric("Total",    len(test_cases))
            rc2.metric("Est. Time",f"~{len(test_cases)*15//60}m")
            rc3.metric("Models",   len(judge_models))

            if st.button(
                f"▶️ Run All {len(test_cases)} Regression Tests",
                type="primary",
                use_container_width=True,
                key="run_regression"
            ):
                if not bedrock_config:
                    st.error("No Bedrock connection configured.")
                else:
                    progress_bar = st.progress(0)
                    status_ph    = st.empty()
                    results      = []

                    for i, tc in enumerate(test_cases):
                        pct = int((i/len(test_cases))*100)
                        progress_bar.progress(pct)
                        status_ph.info(
                            f"🔄 {i+1}/{len(test_cases)}: "
                            f"{tc.get('test_name','')[:60]}"
                        )

                        test_type = tc.get("tags","").lower()
                        if "conversation" in test_type:
                            r = run_conversation_test(
                                bedrock_config, tc, llm_model
                            )
                        elif "intent" in test_type:
                            r = run_intent_validation_test(
                                bedrock_config, tc, llm_model
                            )
                        else:
                            r = run_chat_test(
                                bedrock_config, tc, llm_model
                            )
                        results.append(r)

                    progress_bar.progress(100)
                    status_ph.empty()

                    passed = sum(
                        1 for r in results
                        if r.get("status")=="PASS"
                    )
                    failed = len(results) - passed

                    if passed == len(results):
                        st.success(
                            f"🎉 All {len(results)} tests PASSED"
                        )
                    else:
                        st.warning(
                            f"⚠️ {passed} passed, "
                            f"{failed} failed"
                        )

                    for r in results:
                        s = r.get("status","ERROR")
                        i = "✅" if s=="PASS" else "❌"
                        with st.expander(
                            f"{i} {r.get('test_name','')[:60]} — {s}"
                        ):
                            st.write(
                                "**Response:**",
                                r.get("response","")[:500]
                            )
                            score = r.get("score",{})
                            if score:
                                st.write(
                                    "**Reasoning:**",
                                    score.get("reasoning","")
                                )