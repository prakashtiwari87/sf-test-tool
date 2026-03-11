"""
7_Metadata_Explorer.py — Enhanced Metadata Browser
FIXED VERSION - Phase 0

FIXES IN THIS VERSION:
  • Per-org collapsible sections for multi-org management
  • Better visual hierarchy
  • Quick metadata type counts in headers
  • Refresh button per org
  • Enhanced search across all metadata types
  • Better error handling and user feedback
"""

import streamlit as st
import pandas as pd
import json
from engine.sf_metadata_engine import (
    get_all_objects, get_object_fields, get_all_agents,
    get_sync_status, sync_full_org_metadata,
    search_all_metadata,
    get_org_flows, get_org_triggers, get_org_components,
    get_org_apps, get_org_packages, get_org_validation_rules
)
from config.settings_manager import (
    get_active_salesforce_connection,
    get_all_salesforce_connections,
    DB_PATH
)
from connectors.salesforce_connector import connect_with_oauth

st.set_page_config(
    page_title="Metadata Explorer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from config.theme import inject_css, render_header
inject_css()

render_header("Salesforce Metadata Explorer", "🔍")

st.markdown("""
<div class="page-subtitle">
    Browse all objects, fields, agents, flows, and packages discovered from your Salesforce orgs.
    Each org's metadata is stored separately for easy comparison and reference.
</div>
""", unsafe_allow_html=True)

# ── GET ALL CONNECTED ORGS ────────────────────────────────────
all_orgs = get_all_salesforce_connections()

if not all_orgs:
    st.warning("⚠️ No Salesforce orgs connected. Go to **Settings** to connect an org first.")
    st.stop()

# ── GLOBAL SEARCH ─────────────────────────────────────────────
st.markdown("### 🔍 Global Search")
search_col1, search_col2 = st.columns([3, 1])
with search_col1:
    global_search = st.text_input(
        "Search across all orgs and metadata types",
        placeholder="e.g. Account, Contact, AgentCore, etc.",
        label_visibility="collapsed"
    )
with search_col2:
    if st.button("🔍 Search All Orgs", type="primary", use_container_width=True):
        if global_search:
            st.session_state.search_query = global_search
        else:
            st.warning("Enter a search term first.")

# Show search results if query exists
if st.session_state.get("search_query"):
    st.markdown(f"**Search results for:** `{st.session_state.search_query}`")
    
    # Search across all orgs
    all_results = []
    for org in all_orgs:
        org_domain = org.get("domain", "")
        results = search_all_metadata(st.session_state.search_query, org_domain)
        for r in results:
            r["org_name"] = org.get("org_name", org_domain)
        all_results.extend(results)
    
    if all_results:
        st.success(f"✅ Found {len(all_results)} results across {len(set(r['org_name'] for r in all_results))} org(s)")
        df = pd.DataFrame(all_results)
        st.dataframe(
            df[["org_name", "metadata_type", "name", "label"]],
            use_container_width=True,
            height=300
        )
    else:
        st.info("No results found. Try a different search term.")
    
    if st.button("Clear Search"):
        del st.session_state.search_query
        st.rerun()
    
    st.markdown("---")

# ── PER-ORG METADATA VIEW ─────────────────────────────────────
st.markdown("### 📚 Metadata by Organization")

for org in all_orgs:
    org_domain = org.get("domain", "")
    org_name = org.get("org_name", "Unknown Org")
    org_type = org.get("org_type", "")
    is_active = org.get("is_active", 0)
    
    # Get sync status for this org
    sync = get_sync_status(org_domain)
    
    # Build header with counts
    header_parts = [f"{'🟢' if is_active else '⚪'} **{org_name}**"]
    
    if sync and sync.get("last_sync"):
        counts = []
        if sync.get("total_objects"): counts.append(f"{sync.get('total_objects')} Objects")
        if sync.get("total_agents"): counts.append(f"{sync.get('total_agents')} Agents")
        if sync.get("total_flows"): counts.append(f"{sync.get('total_flows')} Flows")
        if sync.get("total_apps"): counts.append(f"{sync.get('total_apps')} Apps")
        
        if counts:
            header_parts.append(" | ".join(counts))
        header_parts.append(f"Last synced: {sync.get('last_sync', '')[:16].replace('T', ' ')}")
    else:
        header_parts.append("⚠️ Not yet synced")
    
    header_parts.append(org_type)
    
    with st.expander(" — ".join(header_parts), expanded=is_active):
        
        # Sync button for this org
        sync_col1, sync_col2, sync_col3 = st.columns([2, 1, 1])
        with sync_col1:
            if sync and sync.get("last_sync"):
                st.caption(f"📅 Last synced: {sync.get('last_sync', '')[:19].replace('T', ' ')}")
            else:
                st.caption("⚠️ Metadata not yet synced for this org")
        
        with sync_col2:
            if st.button(
                "🔄 Sync Metadata",
                key=f"sync_{org['id']}",
                use_container_width=True
            ):
                with st.spinner(f"Syncing metadata from {org_name}..."):
                    # Connect to org
                    sf, err = connect_with_oauth(
                        client_id=org.get("client_id"),
                        client_secret=org.get("client_secret"),
                        domain=org_domain
                    )
                    
                    if sf:
                        try:
                            # Run full sync
                            result = sync_full_org_metadata(sf, org_domain)
                            st.success(f"✅ Synced {result.get('total_items', 0)} items!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Sync failed: {str(e)}")
                    else:
                        st.error(f"Connection failed: {err}")
        
        with sync_col3:
            if st.button(
                "ℹ️ Sync Status",
                key=f"status_{org['id']}",
                use_container_width=True
            ):
                if sync:
                    st.json(sync)
                else:
                    st.info("No sync data available")
        
        st.markdown("---")
        
        # Metadata tabs for this org
        tab_obj, tab_agents, tab_flows, tab_apps, tab_other = st.tabs([
            "📦 Objects",
            "🤖 Agentforce",
            "🔄 Flows",
            "📱 Apps",
            "⚙️ Other"
        ])
        
        # OBJECTS TAB
        with tab_obj:
            objects = get_all_objects(org_domain)
            if objects:
                st.caption(f"**{len(objects)} objects found**")
                
                # Filter controls
                obj_filter = st.text_input(
                    "Filter objects",
                    placeholder="Search by name or label...",
                    key=f"obj_filter_{org['id']}"
                )
                
                if obj_filter:
                    objects = [
                        o for o in objects 
                        if obj_filter.lower() in o.get("object_name", "").lower()
                        or obj_filter.lower() in o.get("object_label", "").lower()
                    ]
                
                # Create DataFrame
                df_objects = pd.DataFrame(objects)
                
                # Display
                if not df_objects.empty:
                    display_cols = ["object_name", "object_label", "object_type", 
                                    "is_custom", "record_count"]
                    available_cols = [c for c in display_cols if c in df_objects.columns]
                    
                    st.dataframe(
                        df_objects[available_cols],
                        use_container_width=True,
                        height=300
                    )
                else:
                    st.info("No objects match your filter.")
            else:
                st.info("No objects synced yet. Click 'Sync Metadata' above.")
        
        # AGENTFORCE TAB
        with tab_agents:
            agents = get_all_agents(org_domain)
            if agents:
                st.caption(f"**{len(agents)} Agentforce agents found**")
                
                for agent in agents:
                    agent_name = agent.get("agent_name", "Unknown Agent")
                    agent_type = agent.get("agent_type", "")
                    status = agent.get("status", "")
                    
                    with st.expander(
                        f"🤖 {agent_name} ({agent_type}) — {status}",
                        expanded=False
                    ):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Label:** {agent.get('agent_label', '—')}")
                            st.write(f"**Type:** {agent_type}")
                            st.write(f"**Channel:** {agent.get('channel', '—')}")
                        with col2:
                            st.write(f"**Status:** {status}")
                            st.write(f"**API Name:** {agent_name}")
                            st.write(f"**Synced:** {agent.get('synced_at', '—')[:16]}")
            else:
                st.info("No Agentforce agents found. They may not be enabled in this org.")
        
        # FLOWS TAB
        with tab_flows:
            flows = get_org_flows(org_domain)
            if flows:
                st.caption(f"**{len(flows)} flows found**")
                
                df_flows = pd.DataFrame(flows)
                if not df_flows.empty:
                    display_cols = ["flow_name", "flow_label", "flow_type", 
                                    "status", "description"]
                    available_cols = [c for c in display_cols if c in df_flows.columns]
                    
                    st.dataframe(
                        df_flows[available_cols],
                        use_container_width=True,
                        height=300
                    )
            else:
                st.info("No flows synced yet.")
        
        # APPS TAB
        with tab_apps:
            apps = get_org_apps(org_domain)
            packages = get_org_packages(org_domain)
            
            if apps:
                st.markdown("**Lightning Apps**")
                df_apps = pd.DataFrame(apps)
                if not df_apps.empty:
                    st.dataframe(
                        df_apps[["app_name", "app_label", "app_type"]],
                        use_container_width=True,
                        height=200
                    )
            
            if packages:
                st.markdown("**Installed Packages**")
                df_packages = pd.DataFrame(packages)
                if not df_packages.empty:
                    st.dataframe(
                        df_packages[["package_name", "namespace", "version"]],
                        use_container_width=True,
                        height=200
                    )
            
            if not apps and not packages:
                st.info("No apps or packages synced yet.")
        
        # OTHER METADATA TAB
        with tab_other:
            triggers = get_org_triggers(org_domain)
            components = get_org_components(org_domain)
            
            st.markdown("**Apex Triggers**")
            if triggers:
                st.caption(f"{len(triggers)} triggers found")
                df_triggers = pd.DataFrame(triggers)
                if not df_triggers.empty:
                    st.dataframe(
                        df_triggers[["trigger_name", "object_name", "status"]],
                        use_container_width=True,
                        height=150
                    )
            else:
                st.info("No triggers synced yet.")
            
            st.markdown("**Lightning Components**")
            if components:
                st.caption(f"{len(components)} components found")
                df_components = pd.DataFrame(components)
                if not df_components.empty:
                    st.dataframe(
                        df_components[["component_name", "component_type"]],
                        use_container_width=True,
                        height=150
                    )
            else:
                st.info("No components synced yet.")

st.markdown("---")
st.caption(
    "💡 **Tip:** Click 'Sync Metadata' for each org to fetch the latest metadata. "
    "Use the search bar at the top to find specific items across all orgs."
)