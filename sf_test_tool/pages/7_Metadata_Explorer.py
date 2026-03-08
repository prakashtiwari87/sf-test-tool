"""
7_Metadata_Explorer.py — Enhanced Metadata Browser with Selective Sync

FEATURES:
  • Browse all Salesforce metadata: Objects, Fields, Agents, Flows, etc.
  • Selective metadata sync (choose which types to download)
  • Advanced search across all metadata
  • Fixed database queries and function imports

FIXES IN THIS VERSION:
  • Fixed import names (get_all_objects, get_object_fields, get_all_agents)
  • Fixed progress callback signature (msg, pct)
  • Fixed database table names (sf_installed_packages, sf_lightning_apps)
  • Fixed column names to match actual schema
  • Added selective sync UI
"""

import streamlit as st
import pandas as pd
import json
import sqlite3
from engine.sf_metadata_engine import (
    get_all_objects, get_object_fields, get_all_agents,
    get_sync_status, sync_full_org_metadata, selective_sync_metadata,
    search_objects, search_all_metadata,
    get_org_flows, get_org_triggers, get_org_components,
    get_org_apps, get_org_packages, get_org_validation_rules
)
from config.settings_manager import get_active_salesforce_connection, DB_PATH

st.set_page_config(
    page_title="Metadata Explorer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.title("🔍 Salesforce Metadata Explorer")
st.caption("Browse all objects, fields, agents, flows, and packages discovered from your org")

from config.page_init import page_init
sf, org = page_init()

active = get_active_salesforce_connection()
org_domain = active.get("domain", "") if active else ""

if not org_domain:
    st.error("No Salesforce org connected. Go to Settings first.")
    st.stop()

# ─────────────────────────────────────────────────────────────
# SYNC STATUS BAR
# ─────────────────────────────────────────────────────────────

sync = get_sync_status(org_domain)
if sync and sync.get("last_sync"):
    # Display sync metrics
    cols = st.columns(9)
    metrics = [
        ("Objects", sync.get("total_objects", 0)),
        ("Fields", sync.get("total_fields", 0)),
        ("Agents", sync.get("total_agents", 0)),
        ("Flows", sync.get("total_flows", 0)),
        ("Triggers", sync.get("total_triggers", 0)),
        ("Components", sync.get("total_components", 0)),
        ("Apps", sync.get("total_apps", 0)),
        ("Packages", sync.get("total_packages", 0)),
        ("Duration", sync.get("sync_duration", "—"))
    ]
    
    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)
    
    st.caption(f"📅 Last synced: {sync.get('last_sync', '')[:19].replace('T', ' ')}")
    
    if sync.get("sync_errors"):
        with st.expander("⚠️ Sync Warnings"):
            st.warning(sync.get("sync_errors"))
else:
    st.warning("⚠️ Metadata not yet synced for this org. Use the sync button below to get started.")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# SYNC CONTROLS
# ─────────────────────────────────────────────────────────────

col1, col2 = st.columns([1, 3])

with col1:
    sync_mode = st.selectbox(
        "Sync Mode",
        ["Full Sync (All Metadata)", "Selective Sync (Choose Types)"],
        help="Choose whether to sync all metadata or select specific types"
    )

# Full Sync Button
if sync_mode == "Full Sync (All Metadata)":
    with col2:
        if st.button("🔄 Re-Sync All Metadata", type="primary", use_container_width=True):
            if st.session_state.get("sf_connection"):
                progress = st.empty()
                
                # Fixed callback signature: accepts both msg and pct
                def cb(msg, pct):
                    progress.info(f"🔄 {msg} ({int(pct)}%)")
                
                try:
                    summary = sync_full_org_metadata(
                        sf=st.session_state.sf_connection,
                        org_domain=org_domain,
                        progress_callback=cb
                    )
                    progress.success(
                        f"✅ Sync complete: {summary.get('total_objects', 0)} objects, "
                        f"{summary.get('total_fields', 0)} fields, "
                        f"{summary.get('total_agents', 0)} agents, "
                        f"{summary.get('total_flows', 0)} flows, "
                        f"{summary.get('total_triggers', 0)} triggers, "
                        f"{summary.get('total_components', 0)} components, "
                        f"{summary.get('total_apps', 0)} apps, "
                        f"{summary.get('total_packages', 0)} packages"
                    )
                    st.balloons()
                    st.rerun()
                except Exception as e:
                    progress.error(f"❌ Sync failed: {str(e)}")
            else:
                st.error("Reconnect Salesforce in Settings first")

# Selective Sync UI
else:
    st.markdown("### 🎯 Select Metadata Types to Sync")
    
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        sync_objects = st.checkbox("📦 Objects & Fields", value=True,
                                   help="Sync all objects and their fields")
        sync_agents = st.checkbox("🤖 Agentforce Agents",
                                  help="Sync AI agents and bots")
        sync_flows = st.checkbox("🌊 Flows",
                                help="Sync Flow definitions")
    
    with col_b:
        sync_triggers = st.checkbox("⚡ Apex Triggers",
                                    help="Sync Apex triggers")
        sync_components = st.checkbox("⚙️ Lightning Components",
                                      help="Sync LWC and Aura components")
        sync_apps = st.checkbox("📱 Lightning Apps",
                               help="Sync Lightning applications")
    
    with col_c:
        sync_packages = st.checkbox("📦 Installed Packages",
                                    help="Sync managed packages")
        sync_vr = st.checkbox("✅ Validation Rules",
                             help="Sync validation rules")
    
    # Object selection for selective sync
    selected_objects = None
    if sync_objects:
        with st.expander("🎯 Optionally select specific objects (leave empty for all)"):
            # Get existing objects to show options
            existing_objects = get_all_objects(org_domain)
            if existing_objects:
                obj_names = sorted([o["object_name"] for o in existing_objects])
                selected_objects = st.multiselect(
                    "Choose specific objects to sync (or leave empty for all queryable objects)",
                    options=obj_names,
                    help="Select specific objects to limit the sync scope"
                )
                if selected_objects:
                    st.info(f"📌 Will sync {len(selected_objects)} selected objects")
    
    # Selective sync button
    if st.button("🎯 Run Selective Sync", type="primary", use_container_width=True):
        # Build metadata types list
        metadata_types = []
        if sync_objects: metadata_types.append('objects')
        if sync_agents: metadata_types.append('agents')
        if sync_flows: metadata_types.append('flows')
        if sync_triggers: metadata_types.append('triggers')
        if sync_components: metadata_types.append('components')
        if sync_apps: metadata_types.append('apps')
        if sync_packages: metadata_types.append('packages')
        if sync_vr: metadata_types.append('validation_rules')
        
        if not metadata_types:
            st.error("⚠️ Please select at least one metadata type to sync")
        elif st.session_state.get("sf_connection"):
            progress = st.empty()
            
            # Fixed callback signature
            def cb(msg, pct):
                progress.info(f"🔄 {msg} ({int(pct)}%)")
            
            try:
                summary = selective_sync_metadata(
                    sf=st.session_state.sf_connection,
                    org_domain=org_domain,
                    metadata_types=metadata_types,
                    progress_callback=cb,
                    selected_objects=selected_objects if selected_objects else None
                )
                
                # Build success message
                parts = []
                if summary.get('total_objects'): parts.append(f"{summary['total_objects']} objects")
                if summary.get('total_fields'): parts.append(f"{summary['total_fields']} fields")
                if summary.get('total_agents'): parts.append(f"{summary['total_agents']} agents")
                if summary.get('total_flows'): parts.append(f"{summary['total_flows']} flows")
                if summary.get('total_triggers'): parts.append(f"{summary['total_triggers']} triggers")
                if summary.get('total_components'): parts.append(f"{summary['total_components']} components")
                if summary.get('total_apps'): parts.append(f"{summary['total_apps']} apps")
                if summary.get('total_packages'): parts.append(f"{summary['total_packages']} packages")
                if summary.get('total_vr'): parts.append(f"{summary['total_vr']} validation rules")
                
                progress.success(f"✅ Selective sync complete: {', '.join(parts)}")
                st.balloons()
                st.rerun()
            except Exception as e:
                progress.error(f"❌ Sync failed: {str(e)}")
        else:
            st.error("Reconnect Salesforce in Settings first")

st.markdown("---")

# ─────────────────────────────────────────────────────────────
# METADATA TABS
# ─────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📦 Objects",
    "🏷️ Fields",
    "🤖 Agents",
    "🌊 Flows & Automation",
    "📱 Apps & Packages",
    "⚡ Triggers & Components",
    "🔎 Search All"
])

# ── TAB 1: OBJECTS ────────────────────────────────────────────

with tab1:
    st.subheader("All Objects in This Org")
    objects = get_all_objects(org_domain)
    if objects:
        df = pd.DataFrame(objects)
        df["Type"] = df["is_custom"].apply(
            lambda x: "🔧 Custom" if x else "📋 Standard"
        )
        st.dataframe(
            df[["object_name", "object_label", "Type", "is_createable", "is_queryable"]],
            use_container_width=True,
            column_config={
                "object_name":   "API Name",
                "object_label":  "Label",
                "Type":          "Type",
                "is_createable": st.column_config.CheckboxColumn("Createable"),
                "is_queryable":  st.column_config.CheckboxColumn("Queryable")
            }
        )
        st.caption(f"Total: {len(df)} objects ({df['is_custom'].sum()} custom, {len(df) - df['is_custom'].sum()} standard)")
    else:
        st.info("No objects synced yet. Click Re-Sync Metadata above.")

# ── TAB 2: FIELDS ─────────────────────────────────────────────

with tab2:
    st.subheader("Fields by Object")
    objects = get_all_objects(org_domain)
    if objects:
        obj_names = [o["object_name"] for o in objects]
        selected_obj = st.selectbox(
            "Select Object:", obj_names,
            index=obj_names.index("Contact") if "Contact" in obj_names else 0
        )
        if selected_obj:
            fields = get_object_fields(org_domain, selected_obj)
            if fields:
                df = pd.DataFrame(fields)
                df["Required"] = df["is_required"].apply(
                    lambda x: "✅ Yes" if x else "No"
                )
                df["Custom"] = df["is_custom"].apply(
                    lambda x: "🔧 Yes" if x else "No"
                )
                st.dataframe(
                    df[["field_name", "field_label", "field_type",
                        "Required", "Custom", "max_length"]],
                    use_container_width=True
                )
                st.caption(f"Total: {len(df)} fields ({df['is_custom'].sum()} custom, {len(df) - df['is_custom'].sum()} standard)")

                # Show picklist fields
                picklist_fields = [
                    f for f in fields if f.get("picklist_values")
                ]
                if picklist_fields:
                    with st.expander(f"📋 Picklist Fields ({len(picklist_fields)})"):
                        for pf in picklist_fields:
                            try:
                                vals = json.loads(pf["picklist_values"])
                                st.write(
                                    f"**{pf['field_name']}** ({pf['field_label']}): "
                                    + " | ".join(vals[:10])
                                    + (f" ... (+{len(vals)-10} more)" if len(vals) > 10 else "")
                                )
                            except Exception:
                                pass
            else:
                st.info(
                    f"No fields synced for {selected_obj} yet. "
                    f"Re-sync metadata to include this object."
                )
    else:
        st.info("Sync metadata first")

# ── TAB 3: AGENTS ─────────────────────────────────────────────

with tab3:
    st.subheader("Agentforce & AI Agents")
    agents = get_all_agents(org_domain)
    if agents:
        df = pd.DataFrame(agents)
        st.dataframe(
            df[["agent_name", "agent_type", "description", "is_active"]],
            use_container_width=True,
            column_config={
                "agent_name": "Agent Name",
                "agent_type": "Type",
                "description": "Description",
                "is_active": st.column_config.CheckboxColumn("Active")
            }
        )
        st.caption(f"Total: {len(df)} agents ({df['is_active'].sum()} active)")
    else:
        st.info(
            "No agents found. This org may not have Agentforce enabled, "
            "or agents haven't been created yet."
        )

# ── TAB 4: FLOWS & AUTOMATION ─────────────────────────────────

with tab4:
    col_flows, col_vr = st.columns(2)
    
    with col_flows:
        st.markdown("### 🌊 Flows")
        flows = get_org_flows(org_domain)
        if flows:
            df = pd.DataFrame(flows)
            st.dataframe(
                df[["label", "process_type", "status", "is_active"]],
                use_container_width=True,
                column_config={
                    "label": "Flow Name",
                    "process_type": "Type",
                    "status": "Status",
                    "is_active": st.column_config.CheckboxColumn("Active")
                }
            )
            st.caption(f"Total: {len(df)} flows ({df['is_active'].sum()} active)")
        else:
            st.info("No flows synced yet")
    
    with col_vr:
        st.markdown("### ✅ Validation Rules")
        vr = get_org_validation_rules(org_domain)
        if vr:
            df = pd.DataFrame(vr)
            st.dataframe(
                df[["object_name", "name", "is_active"]],
                use_container_width=True,
                column_config={
                    "object_name": "Object",
                    "name": "Rule Name",
                    "is_active": st.column_config.CheckboxColumn("Active")
                }
            )
            st.caption(f"Total: {len(df)} rules ({df['is_active'].sum()} active)")
        else:
            st.info("No validation rules synced yet")

# ── TAB 5: APPS & PACKAGES ────────────────────────────────────

with tab5:
    col_packages, col_apps = st.columns(2)
    
    with col_packages:
        st.markdown("### 📦 Installed Packages")
        packages = get_org_packages(org_domain)
        if packages:
            df = pd.DataFrame(packages)
            st.dataframe(
                df[["name", "namespace_prefix", "version_number"]],
                use_container_width=True,
                column_config={
                    "name": "Package Name",
                    "namespace_prefix": "Namespace",
                    "version_number": "Version"
                }
            )
            st.caption(f"Total: {len(df)} packages")
        else:
            st.info("No managed packages found")
    
    with col_apps:
        st.markdown("### 📱 Lightning Apps")
        apps = get_org_apps(org_domain)
        if apps:
            df = pd.DataFrame(apps)
            st.dataframe(
                df[["label", "name", "form_factors"]],
                use_container_width=True,
                column_config={
                    "label": "App Label",
                    "name": "Developer Name",
                    "form_factors": "Form Factors"
                }
            )
            st.caption(f"Total: {len(df)} apps")
        else:
            st.info("No apps found")

# ── TAB 6: TRIGGERS & COMPONENTS ──────────────────────────────

with tab6:
    col_triggers, col_components = st.columns(2)
    
    with col_triggers:
        st.markdown("### ⚡ Apex Triggers")
        triggers = get_org_triggers(org_domain)
        if triggers:
            df = pd.DataFrame(triggers)
            st.dataframe(
                df[["name", "table_enum_or_id", "status", "is_active"]],
                use_container_width=True,
                column_config={
                    "name": "Trigger Name",
                    "table_enum_or_id": "Object",
                    "status": "Status",
                    "is_active": st.column_config.CheckboxColumn("Active")
                }
            )
            st.caption(f"Total: {len(df)} triggers ({df['is_active'].sum()} active)")
        else:
            st.info("No triggers synced yet")
    
    with col_components:
        st.markdown("### ⚙️ Lightning Components")
        components = get_org_components(org_domain)
        if components:
            df = pd.DataFrame(components)
            df["Component Type"] = df["is_aura"].apply(
                lambda x: "Aura" if x else "LWC"
            )
            st.dataframe(
                df[["name", "Component Type", "master_label"]],
                use_container_width=True,
                column_config={
                    "name": "Developer Name",
                    "Component Type": "Type",
                    "master_label": "Label"
                }
            )
            st.caption(f"Total: {len(df)} components ({(~df['is_aura']).sum()} LWC, {df['is_aura'].sum()} Aura)")
        else:
            st.info("No components synced yet")

# ── TAB 7: SEARCH ALL ─────────────────────────────────────────

with tab7:
    st.subheader("🔎 Search All Metadata")
    search_term = st.text_input(
        "Search for any object, field, agent, flow, or component:",
        placeholder="e.g. Account, Email, Agent, Custom__c, MyFlow",
        help="Search across all synced metadata types"
    )
    
    if search_term:
        # Use comprehensive search
        all_results = search_all_metadata(org_domain, search_term)
        
        total_found = sum(len(v) for v in all_results.values())
        
        if total_found > 0:
            st.success(f"Found {total_found} results matching '{search_term}'")
            
            # Objects
            if all_results.get('objects'):
                with st.expander(f"📦 Objects ({len(all_results['objects'])})"):
                    for obj in all_results['objects']:
                        icon = "🔧" if obj.get("is_custom") else "📋"
                        st.write(f"{icon} **{obj['api_name']}** ({obj['label']})")
            
            # Fields
            if all_results.get('fields'):
                with st.expander(f"🏷️ Fields ({len(all_results['fields'])})"):
                    for field in all_results['fields']:
                        st.write(
                            f"**{field['object_name']}.{field['api_name']}** "
                            f"({field['label']}) — {field['field_type']}"
                        )
            
            # Agents
            if all_results.get('agents'):
                with st.expander(f"🤖 Agents ({len(all_results['agents'])})"):
                    for agent in all_results['agents']:
                        st.write(f"**{agent['agent_name']}** ({agent['agent_type']})")
                        if agent.get('description'):
                            st.caption(f"   {agent['description']}")
            
            # Flows
            if all_results.get('flows'):
                with st.expander(f"🌊 Flows ({len(all_results['flows'])})"):
                    for flow in all_results['flows']:
                        st.write(f"**{flow['label']}** — {flow['process_type']} ({flow['status']})")
            
            # Triggers
            if all_results.get('triggers'):
                with st.expander(f"⚡ Triggers ({len(all_results['triggers'])})"):
                    for trigger in all_results['triggers']:
                        st.write(f"**{trigger['name']}** on {trigger['table_enum_or_id']} — {trigger['status']}")
            
            # Components
            if all_results.get('components'):
                with st.expander(f"⚙️ Components ({len(all_results['components'])})"):
                    for comp in all_results['components']:
                        st.write(f"**{comp['name']}** ({comp['master_label']})")
            
            # Apps
            if all_results.get('apps'):
                with st.expander(f"📱 Apps ({len(all_results['apps'])})"):
                    for app in all_results['apps']:
                        st.write(f"**{app['label']}** ({app['name']})")
            
            # Packages
            if all_results.get('packages'):
                with st.expander(f"📦 Packages ({len(all_results['packages'])})"):
                    for pkg in all_results['packages']:
                        st.write(f"**{pkg['name']}** ({pkg['namespace_prefix']}) v{pkg['version_number']}")
        else:
            st.info(f"No results found for '{search_term}'")