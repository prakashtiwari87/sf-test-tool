import streamlit as st
import pandas as pd
import json
from engine.sf_metadata_engine import (
    get_all_objects, get_object_fields, get_all_agents,
    get_sync_status, sync_full_org_metadata, search_objects
)
from config.settings_manager import get_active_salesforce_connection

st.set_page_config(page_title="Metadata Explorer",
                   page_icon="🔍", layout="wide", initial_sidebar_state = "collapsed")
st.title("🔍 Salesforce Metadata Explorer")
st.caption("Browse all objects, fields, agents and packages discovered from your org")
from config.page_init import page_init
sf, org = page_init()

active = get_active_salesforce_connection()
org_domain = active.get("domain", "") if active else ""

if not org_domain:
    st.error("No Salesforce org connected. Go to Settings first.")
    st.stop()

# Sync status bar
sync = get_sync_status(org_domain)
if sync.get("status") == "complete":
    col1,col2,col3,col4,col5 = st.columns(5)
    col1.metric("Objects",  sync.get("total_objects", 0))
    col2.metric("Fields",   sync.get("total_fields",  0))
    col3.metric("Agents",   sync.get("total_agents",  0))
    col4.metric("Packages", sync.get("total_packages",0))
    col5.metric("Sync Time",sync.get("sync_duration", ""))
    st.caption(f"Last synced: {sync.get('last_sync','')[:19]}")
else:
    st.warning("Metadata not yet synced for this org.")

# Re-sync button
col1, col2 = st.columns([1, 5])
with col1:
    if st.button("🔄 Re-Sync Metadata", type="primary"):
        if st.session_state.get("sf_connection"):
            progress = st.empty()
            def cb(msg): progress.info(f"🔄 {msg}")
            summary = sync_full_org_metadata(
                sf=st.session_state.sf_connection,
                org_domain=org_domain,
                progress_callback=cb,
                objects_to_detail=60
            )
            progress.success(
                f"Sync complete: {summary['objects']} objects, "
                f"{summary['fields']} fields"
            )
            st.rerun()
        else:
            st.error("Reconnect Salesforce in Settings first")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📦 Objects",
    "🏷️ Fields",
    "🤖 Agents",
    "📱 Apps & Packages",
    "🔎 Search"
])

with tab1:
    st.subheader("All Objects in This Org")
    objects = get_all_objects(org_domain)
    if objects:
        df = pd.DataFrame(objects)
        df["Type"] = df["is_custom"].apply(
            lambda x: "🔧 Custom" if x else "📋 Standard"
        )
        st.dataframe(
            df[["object_name","object_label","Type","is_createable","is_queryable"]],
            use_container_width=True,
            column_config={
                "object_name":   "API Name",
                "object_label":  "Label",
                "Type":          "Type",
                "is_createable": st.column_config.CheckboxColumn("Createable"),
                "is_queryable":  st.column_config.CheckboxColumn("Queryable")
            }
        )
        st.caption(f"Total: {len(df)} objects")
    else:
        st.info("No objects synced yet. Click Re-Sync Metadata above.")

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
                    df[["field_name","field_label","field_type",
                        "Required","Custom","max_length"]],
                    use_container_width=True
                )
                st.caption(f"{len(df)} fields on {selected_obj}")

                # Show picklist fields
                picklist_fields = [
                    f for f in fields if f.get("picklist_values")
                ]
                if picklist_fields:
                    st.markdown("**Picklist Fields:**")
                    for pf in picklist_fields:
                        try:
                            vals = json.loads(pf["picklist_values"])
                            st.write(
                                f"**{pf['field_name']}**: "
                                + " | ".join(vals[:8])
                                + (" ..." if len(vals) > 8 else "")
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

with tab3:
    st.subheader("Agentforce & AI Agents")
    agents = get_all_agents(org_domain)
    if agents:
        df = pd.DataFrame(agents)
        st.dataframe(df, use_container_width=True)
    else:
        st.info(
            "No agents found. This org may not have Agentforce enabled, "
            "or agents haven't been created yet."
        )

with tab4:
    st.subheader("Installed Packages & Custom Apps")
    import sqlite3
    from config.settings_manager import DB_PATH

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Installed Packages**")
        conn = sqlite3.connect(DB_PATH)
        pkgs = pd.read_sql(
            "SELECT package_name, namespace, version, package_type "
            "FROM sf_packages WHERE org_domain = ?",
            conn, params=(org_domain,)
        )
        conn.close()
        if not pkgs.empty:
            st.dataframe(pkgs, use_container_width=True)
        else:
            st.info("No managed packages found")

    with col2:
        st.markdown("**Custom Apps**")
        conn = sqlite3.connect(DB_PATH)
        apps = pd.read_sql(
            "SELECT app_label, app_name, app_type, is_default "
            "FROM sf_apps WHERE org_domain = ?",
            conn, params=(org_domain,)
        )
        conn.close()
        if not apps.empty:
            st.dataframe(apps, use_container_width=True)
        else:
            st.info("No apps found")

with tab5:
    st.subheader("Search Metadata")
    search_term = st.text_input(
        "Search for any object, field, or agent:",
        placeholder="e.g. Account, Email, Agent, Custom__c"
    )
    if search_term:
        results = search_objects(org_domain, search_term)
        if results:
            st.write(f"**{len(results)} objects matching '{search_term}':**")
            for r in results:
                icon = "🔧" if r["is_custom"] else "📋"
                st.write(
                    f"{icon} **{r['object_name']}** "
                    f"({r['object_label']}) — {r['object_type']}"
                )
                fields = get_object_fields(org_domain, r["object_name"])
                matching_fields = [
                    f for f in fields
                    if search_term.lower() in f["field_name"].lower() or
                    search_term.lower() in (f["field_label"] or "").lower()
                ]
                if matching_fields:
                    for mf in matching_fields[:5]:
                        st.caption(
                            f"   └─ {mf['field_name']} "
                            f"({mf['field_type']})"
                        )
        else:
            st.info(f"No results for '{search_term}'")