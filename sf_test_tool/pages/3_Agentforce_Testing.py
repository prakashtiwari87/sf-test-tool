"""
3_Agentforce_Testing.py — Complete Agentforce Testing Page
Phase 3 Enterprise: CORRECTED VERSION

FIXED:
  • Uses correct theme imports (render_header, inject_css)
  • Matches existing page structure
  • Compatible with existing codebase
"""

import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(
    page_title="Agentforce Testing — AmplifyQA",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from config.page_init import page_init
from config.theme import render_header, inject_css
from config.settings_manager import (
    get_active_salesforce_connection,
    get_all_llm_keys
)

# Phase 3 Enterprise imports
try:
    from engine.agentforce_db_manager import (
        init_agentforce_database,
        get_all_agents,
        get_agent,
        get_agent_configuration,
        save_agent_configuration,
        get_test_scripts,
        save_test_scripts,
        get_execution_results
    )
    from engine.agent_discovery_engine import discover_agents_from_org
    from engine.test_script_generation_engine import (
        generate_test_scripts_for_agent,
        TEST_TYPES,
        PERSONAS
    )
    from engine.test_export_engine import export_test_results
    from connectors.salesforce_connector import connect_with_oauth
    AGENTFORCE_AVAILABLE = True
except ImportError as e:
    AGENTFORCE_AVAILABLE = False
    IMPORT_ERROR = str(e)

# ── BOOT ──────────────────────────────────────────────────────
init_agentforce_database() if AGENTFORCE_AVAILABLE else None
inject_css()

sf, org = page_init()

render_header(
    "Agentforce Testing", "🎯",
    org_name=org.get("org_name", ""),
    environment=org.get("org_type", ""),
)

# Check if Agentforce is available
if not AGENTFORCE_AVAILABLE:
    st.error("❌ **Agentforce Testing Not Available**")
    st.warning(f"Missing required components: {IMPORT_ERROR}")
    st.info("""
    **To enable Agentforce Testing:**
    
    1. Copy all engine files from `PHASE_3_ENTERPRISE/engine/` to your `engine/` directory
    2. Run the migration script: `python migrate_agentforce_database.py`
    3. Restart the application
    
    **Required files:**
    - `agentforce_db_manager.py`
    - `agent_discovery_engine.py`
    - `test_script_generation_engine.py`
    - `chat_api_testing_engine.py`
    - `test_export_engine.py`
    - And others...
    """)
    st.stop()

# Check prerequisites
if not sf:
    st.error("❌ Please configure Salesforce connection in Settings first.")
    st.stop()

# Main tabs
main_tabs = st.tabs([
    "🔍 Agent Discovery",
    "💬 Chat Agent Testing",
    "📊 Test Results",
    "📁 Export"
])

# ══════════════════════════════════════════════════════════════
# TAB 1: AGENT DISCOVERY
# ══════════════════════════════════════════════════════════════

with main_tabs[0]:
    st.markdown("### 🔍 Agent Discovery")
    st.caption("Discover and view Agentforce agents from your Salesforce org")
    
    active_sf = get_active_salesforce_connection()
    if not active_sf:
        st.warning("⚠️ No active Salesforce connection. Please configure in Settings.")
        st.stop()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.info(f"📡 Connected to: **{active_sf.get('domain', '')}**")
    
    with col2:
        if st.button("🔄 Refresh Agents", use_container_width=True):
            with st.spinner("Discovering agents..."):
                try:
                    sf, err = connect_with_oauth(
                        client_id=active_sf.get('client_id'),
                        client_secret=active_sf.get('client_secret'),
                        domain=active_sf.get('domain')
                    )
                    
                    if err:
                        st.error(f"❌ Connection failed: {err}")
                    else:
                        result = discover_agents_from_org(
                            sf_connection=sf,
                            org_domain=active_sf.get('domain'),
                            save_to_db=True
                        )
                        
                        st.success(f"✅ Found {result.get('discovered', 0)} agents!")
                        st.rerun()
                
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    st.markdown("---")
    
    # Get all agents
    agents = get_all_agents(org_domain=active_sf.get('domain'))
    
    if not agents:
        st.warning("⚠️ No agents found. Click 'Refresh Agents' to discover agents from Salesforce.")
    else:
        st.markdown(f"### Found {len(agents)} Agent(s)")
        
        # Display agents in a grid
        cols = st.columns(2)
        
        for idx, agent in enumerate(agents):
            with cols[idx % 2]:
                with st.container():
                    st.markdown(f"#### 🤖 {agent.get('agent_name')}")
                    st.caption(f"**Agent ID:** {agent.get('agent_id')}")
                    
                    if agent.get('agent_description'):
                        st.markdown(f"_{agent.get('agent_description')}_")
                    
                    # Channel support
                    channels = []
                    if agent.get('supports_chat'): channels.append("💬 Chat")
                    if agent.get('supports_email'): channels.append("📧 Email")
                    if agent.get('supports_sms'): channels.append("📱 SMS")
                    if agent.get('supports_voice'): channels.append("📞 Voice")
                    if agent.get('supports_slack'): channels.append("💼 Slack")
                    
                    if channels:
                        st.markdown("**Channels:** " + " · ".join(channels))
                    
                    # Status
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.success("✅ Active")
                    with col_b:
                        if st.button("🧪 Test", key=f"test_{agent.get('id')}", use_container_width=True):
                            st.session_state['selected_agent_id'] = agent.get('agent_id')
                            st.session_state['active_tab'] = 1  # Switch to testing tab
                            st.rerun()
                    
                    st.markdown("---")

# ══════════════════════════════════════════════════════════════
# TAB 2: CHAT AGENT TESTING
# ══════════════════════════════════════════════════════════════

with main_tabs[1]:
    st.markdown("### 💬 Chat Agent Testing")
    
    active_sf = get_active_salesforce_connection()
    if not active_sf:
        st.warning("⚠️ No active Salesforce connection.")
        st.stop()
    
    # Agent selection
    agents = get_all_agents(org_domain=active_sf.get('domain'))
    
    if not agents:
        st.warning("⚠️ No agents available. Please discover agents first.")
        st.stop()
    
    # Agent selector
    agent_options = {f"{a.get('agent_name')} ({a.get('agent_id')})": a.get('agent_id') for a in agents}
    
    selected_agent_display = st.selectbox(
        "Select Agent to Test",
        options=list(agent_options.keys()),
        key="agent_selector"
    )
    
    selected_agent_id = agent_options[selected_agent_display]
    selected_agent = get_agent(selected_agent_id)
    
    if not selected_agent:
        st.error("❌ Agent not found")
        st.stop()
    
    st.success(f"Testing: **{selected_agent.get('agent_name')}**")
    
    # Testing mode sub-tabs
    test_tabs = st.tabs([
        "🔌 API Testing",
        "🌐 UI Testing",
        "💭 Conversational Testing"
    ])
    
    # ─────────────────────────────────────────────────────────
    # SUB-TAB 1: API TESTING
    # ─────────────────────────────────────────────────────────
    
    with test_tabs[0]:
        st.markdown("#### API Testing")
        st.caption("Test agent via Agentforce API with LLM-generated test scripts")
        
        # Testing method selection
        testing_method = st.selectbox(
            "Testing Method",
            options=["Agent API", "Agentforce DX", "Testing API"],
            help="Choose how to invoke the agent"
        )
        
        st.markdown("---")
        
        # Configuration wizard
        st.markdown("### Step 1: Agent Configuration")
        
        with st.form("agent_config_form"):
            st.markdown("**Agent Description**")
            agent_description = st.text_area(
                "What does this agent do?",
                value="Deliver personalized customer interactions, understand who is calling, and determine the assistance required.",
                height=100,
                label_visibility="collapsed"
            )
            
            st.markdown("**Agent Role**")
            agent_role = st.text_area(
                "What role does the agent play?",
                value="Insurance service assistant helping customers by gathering essential information.",
                label_visibility="collapsed"
            )
            
            st.markdown("**Business Functions**")
            business_functions = st.multiselect(
                "Select applicable business functions",
                options=["Sales", "Claims", "Services", "Refunds", "Escalations", "Support", "Billing"],
                default=["Sales", "Claims", "Services"],
                label_visibility="collapsed"
            )
            
            st.markdown("**Topics**")
            topics = st.multiselect(
                "Key topics the agent handles",
                options=["Caller Verification", "Escalation", "Product Info", "Order Status", "Returns", "Technical Support"],
                default=["Caller Verification", "Escalation"],
                label_visibility="collapsed"
            )
            
            config_submitted = st.form_submit_button("💾 Save Configuration & Continue", use_container_width=True)
            
            if config_submitted:
                # Save configuration
                save_agent_configuration(
                    agent_id=selected_agent_id,
                    agent_description=agent_description,
                    agent_role=agent_role,
                    business_functions=business_functions,
                    topics=topics,
                    topic_instructions="",
                    preferred_llm_model="",
                    selected_test_types=[],
                    selected_personas=[]
                )
                
                st.success("✅ Configuration saved!")
                st.session_state['config_saved'] = True
        
        # Only show Step 2 if config is saved
        if st.session_state.get('config_saved', False):
            st.markdown("---")
            st.markdown("### Step 2: Test Generation Configuration")
            
            with st.form("test_generation_form"):
                # LLM Model selection
                llm_keys = get_all_llm_keys()
                working_models = [
                    model
                    for provider, data in llm_keys.items()
                    if data.get('status') == 'WORKING'
                    for model in data.get('models', [])
                ]
                
                if not working_models:
                    st.error("❌ No working LLM models found. Please configure LLM keys in Settings.")
                    st.stop()
                
                selected_llm = st.selectbox(
                    "Preferred LLM Model",
                    options=working_models
                )
                
                # Test types selection
                st.markdown("**Testing Types** (Select one or more)")
                
                test_type_cols = st.columns(3)
                selected_test_types = []
                
                for idx, test_type in enumerate(TEST_TYPES):
                    with test_type_cols[idx % 3]:
                        if st.checkbox(test_type, key=f"test_type_{idx}"):
                            selected_test_types.append(test_type)
                
                # Personas selection
                st.markdown("**Communication Styles / Personas** (Select one or more)")
                
                persona_cols = st.columns(3)
                selected_personas = []
                
                for idx, persona in enumerate(PERSONAS):
                    with persona_cols[idx % 3]:
                        if st.checkbox(persona, key=f"persona_{idx}"):
                            selected_personas.append(persona)
                
                # Scripts per combination
                scripts_per_combo = st.number_input(
                    "Test Scripts per Combination",
                    min_value=1,
                    max_value=50,
                    value=5,
                    help="Number of test scripts to generate for each test type + persona combination"
                )
                
                # Calculate total
                total_scripts = len(selected_test_types) * len(selected_personas) * scripts_per_combo
                
                if selected_test_types and selected_personas:
                    st.info(f"📊 Will generate **{total_scripts}** test scripts")
                
                generate_submitted = st.form_submit_button("🎯 Generate Test Scripts", use_container_width=True, type="primary")
                
                if generate_submitted:
                    if not selected_test_types:
                        st.error("❌ Please select at least one test type")
                    elif not selected_personas:
                        st.error("❌ Please select at least one persona")
                    else:
                        # Generate test scripts
                        with st.spinner(f"Generating {total_scripts} test scripts..."):
                            try:
                                # Get agent config
                                config = get_agent_configuration(selected_agent_id)
                                
                                if not config:
                                    config = {
                                        'agent_id': selected_agent_id,
                                        'agent_description': agent_description,
                                        'agent_role': agent_role,
                                        'business_functions': business_functions,
                                        'topics': topics
                                    }
                                
                                # Generate scripts
                                scripts = generate_test_scripts_for_agent(
                                    agent_config=config,
                                    test_types=selected_test_types,
                                    personas=selected_personas,
                                    scripts_per_combination=scripts_per_combo,
                                    llm_model=selected_llm
                                )
                                
                                if scripts:
                                    # Save to database
                                    save_test_scripts(scripts)
                                    
                                    st.success(f"✅ Generated and saved {len(scripts)} test scripts!")
                                    st.balloons()
                                    
                                    st.session_state['scripts_generated'] = True
                                    st.session_state['generated_scripts_count'] = len(scripts)
                                else:
                                    st.error("❌ Failed to generate test scripts")
                            
                            except Exception as e:
                                st.error(f"❌ Error: {str(e)}")
        
        # Show Step 3 if scripts generated
        if st.session_state.get('scripts_generated', False):
            st.markdown("---")
            st.markdown("### Step 3: Review & Execute Tests")
            
            # Get generated scripts
            scripts = get_test_scripts(selected_agent_id)
            
            if scripts:
                st.info(f"📋 **{len(scripts)}** test scripts ready")
                
                # Preview scripts
                with st.expander("👀 Preview Test Scripts"):
                    scripts_df = pd.DataFrame([
                        {
                            'Test Type': s.get('test_type'),
                            'Persona': s.get('persona'),
                            'Utterance': s.get('utterance')[:50] + '...',
                            'Expected Intent': s.get('expected_intent')
                        }
                        for s in scripts[:20]
                    ])
                    st.dataframe(scripts_df, use_container_width=True)
                
                # Export option
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("📥 Download Scripts (Excel)", use_container_width=True):
                        excel_bytes = export_test_results(
                            test_scripts=scripts,
                            format="xlsx"
                        )
                        
                        st.download_button(
                            label="💾 Download Excel File",
                            data=excel_bytes,
                            file_name=f"test_scripts_{selected_agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                
                with col2:
                    if st.button("📥 Download Scripts (CSV)", use_container_width=True):
                        csv_bytes = export_test_results(
                            test_scripts=scripts,
                            format="csv"
                        )
                        
                        st.download_button(
                            label="💾 Download CSV File",
                            data=csv_bytes,
                            file_name=f"test_scripts_{selected_agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                
                st.markdown("---")
                
                # Execute tests
                st.markdown("### Execute Tests")
                
                st.warning("⚠️ **Note:** Test execution requires valid Agentforce API credentials.")
                
                if st.button("▶️ Execute All Tests", use_container_width=True, type="primary"):
                    st.info("🚧 Test execution will be available once you configure Agentforce API credentials in Settings.")
    
    # ─────────────────────────────────────────────────────────
    # SUB-TAB 2: UI TESTING
    # ─────────────────────────────────────────────────────────
    
    with test_tabs[1]:
        st.markdown("#### UI Testing")
        st.caption("Test agent deployed on web pages using Playwright automation")
        
        st.info("🚧 UI Testing coming soon! This will use Playwright to automate browser-based agent testing.")
    
    # ─────────────────────────────────────────────────────────
    # SUB-TAB 3: CONVERSATIONAL TESTING
    # ─────────────────────────────────────────────────────────
    
    with test_tabs[2]:
        st.markdown("#### Conversational Testing")
        st.caption("Multi-turn conversations with Salesforce data validation")
        
        st.info("🚧 Conversational Testing coming soon! This will test multi-turn dialogues with SOQL validation.")

# ══════════════════════════════════════════════════════════════
# TAB 3: TEST RESULTS
# ══════════════════════════════════════════════════════════════

with main_tabs[2]:
    st.markdown("### 📊 Test Results")
    st.info("🚧 Test results viewer coming soon!")

# ══════════════════════════════════════════════════════════════
# TAB 4: EXPORT
# ══════════════════════════════════════════════════════════════

with main_tabs[3]:
    st.markdown("### 📁 Export")
    st.info("🚧 Export functionality coming soon!")

st.markdown("---")
st.caption("AmplifyQA - Enterprise Agentforce Testing Platform v3.0")