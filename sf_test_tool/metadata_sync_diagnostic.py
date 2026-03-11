"""
detailed_sync_diagnostic.py - Deep dive into sync issues

Run this to see exactly where the sync is failing:
    streamlit run detailed_sync_diagnostic.py
"""

import streamlit as st
import traceback
from datetime import datetime

st.set_page_config(page_title="Sync Diagnostic", layout="wide")
st.title("🔍 Detailed Metadata Sync Diagnostic")

# Import everything we need
try:
    from config.page_init import page_init
    from config.settings_manager import get_active_salesforce_connection, DB_PATH
    from engine.sf_metadata_engine import sync_objects_and_fields
    import sqlite3
    
    st.success("✅ All imports successful")
except Exception as e:
    st.error(f"❌ Import failed: {e}")
    st.stop()

# Get connection
sf, org = page_init()
active = get_active_salesforce_connection()
org_domain = active.get("domain", "") if active else ""

st.write("---")
st.subheader("Connection Status")
col1, col2, col3 = st.columns(3)
col1.metric("SF Connection", "✅ Yes" if sf else "❌ No")
col2.metric("Org Domain", org_domain or "None")
col3.metric("Org Name", org.get("org_name", "None"))

if not sf:
    st.error("No Salesforce connection! Go to Settings and connect first.")
    st.stop()

st.write("---")
st.subheader("Step-by-Step Sync Test")

# Test 1: Can we describe?
with st.expander("TEST 1: Can we call sf.describe()?", expanded=True):
    try:
        describe = sf.describe()
        sobjects = describe.get('sobjects', [])
        st.success(f"✅ Describe successful! Found {len(sobjects)} objects")
        
        # Show first 10
        st.write("**First 10 objects:**")
        for obj in sobjects[:10]:
            st.write(f"- {obj.get('name')} ({obj.get('label')})")
    except Exception as e:
        st.error(f"❌ Describe failed: {e}")
        st.code(traceback.format_exc())

# Test 2: Can we describe Account object?
with st.expander("TEST 2: Can we describe Account object fields?", expanded=True):
    try:
        account_desc = sf.Account.describe()
        fields = account_desc.get('fields', [])
        st.success(f"✅ Account describe successful! Found {len(fields)} fields")
        
        # Show first 10 fields
        st.write("**First 10 Account fields:**")
        for field in fields[:10]:
            st.write(f"- {field.get('name')} ({field.get('type')})")
    except Exception as e:
        st.error(f"❌ Account describe failed: {e}")
        st.code(traceback.format_exc())

# Test 3: Database write test
with st.expander("TEST 3: Can we write to database?", expanded=True):
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Try to insert a test object
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO sf_objects 
            (org_domain, api_name, label, is_custom, is_queryable, is_createable, key_prefix, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (org_domain, "TEST_Object__c", "Test Object", 1, 1, 1, "a00", now))
        conn.commit()
        
        # Read it back
        cursor.execute(
            "SELECT * FROM sf_objects WHERE org_domain=? AND api_name=?",
            (org_domain, "TEST_Object__c")
        )
        result = cursor.fetchone()
        
        if result:
            st.success("✅ Database write successful!")
            st.write("Wrote and read back test object:", dict(zip([d[0] for d in cursor.description], result)))
            
            # Clean up
            cursor.execute(
                "DELETE FROM sf_objects WHERE org_domain=? AND api_name=?",
                (org_domain, "TEST_Object__c")
            )
            conn.commit()
        else:
            st.error("❌ Could not read back test data")
        
        conn.close()
    except Exception as e:
        st.error(f"❌ Database test failed: {e}")
        st.code(traceback.format_exc())

# Test 4: Manual sync of just Account
with st.expander("TEST 4: Manual sync of Account object", expanded=True):
    if st.button("🔄 Run Manual Account Sync"):
        progress = st.empty()
        result_area = st.empty()
        
        def progress_cb(msg, pct):
            progress.info(f"[{int(pct)}%] {msg}")
        
        try:
            # Import the sync function
            from engine.sf_metadata_engine import sync_objects_and_fields
            
            st.write("**Starting sync of Account object only...**")
            
            count = sync_objects_and_fields(
                sf=sf,
                org_domain=org_domain,
                progress_callback=progress_cb,
                selected_objects=['Account']
            )
            
            progress.empty()
            result_area.success(f"✅ Sync returned count: {count}")
            
            # Check database
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT COUNT(*) FROM sf_objects WHERE org_domain=? AND api_name='Account'",
                (org_domain,)
            )
            obj_count = cursor.fetchone()[0]
            
            cursor.execute(
                "SELECT COUNT(*) FROM sf_fields WHERE org_domain=? AND object_name='Account'",
                (org_domain,)
            )
            field_count = cursor.fetchone()[0]
            
            conn.close()
            
            st.write(f"**Database check:**")
            st.write(f"- Objects in DB: {obj_count}")
            st.write(f"- Account fields in DB: {field_count}")
            
            if obj_count == 0 and field_count == 0:
                st.error("⚠️ Sync returned success but nothing was saved to database!")
                st.write("This suggests the sync function is not working correctly.")
            
        except Exception as e:
            progress.empty()
            result_area.error(f"❌ Manual sync failed: {e}")
            st.code(traceback.format_exc())

# Test 5: Check what's currently in database
with st.expander("TEST 5: What's currently in the database?", expanded=True):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Count records in each table for this org
        tables_to_check = [
            'sf_objects', 'sf_fields', 'sf_agents', 'sf_flows',
            'sf_apex_triggers', 'sf_lightning_components', 'sf_lightning_apps',
            'sf_installed_packages', 'sf_validation_rules'
        ]
        
        st.write(f"**Records for org: {org_domain}**")
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE org_domain=?", (org_domain,))
                count = cursor.fetchone()[0]
                st.write(f"- {table}: **{count}** records")
            except Exception as e:
                st.write(f"- {table}: ❌ Error - {e}")
        
        # Check sync status
        cursor.execute("SELECT * FROM sf_sync_status WHERE org_domain=?", (org_domain,))
        sync_status = cursor.fetchone()
        if sync_status:
            st.write("**Sync Status Record:**")
            cols = [d[0] for d in cursor.description]
            status_dict = dict(zip(cols, sync_status))
            st.json(status_dict)
        else:
            st.write("No sync status record found")
        
        conn.close()
    except Exception as e:
        st.error(f"❌ Database query failed: {e}")
        st.code(traceback.format_exc())

# Test 6: Try calling the actual sync function with detailed logging
with st.expander("TEST 6: Full sync with detailed logging", expanded=True):
    if st.button("🔄 Run Full Sync with Logging"):
        progress = st.empty()
        log_area = st.empty()
        logs = []
        
        def log_cb(msg, pct):
            log_msg = f"[{int(pct)}%] {msg}"
            logs.append(log_msg)
            progress.info(log_msg)
            log_area.code("\n".join(logs[-20:]))  # Show last 20 log lines
        
        try:
            from engine.sf_metadata_engine import sync_full_org_metadata
            
            st.write("**Starting full sync...**")
            
            summary = sync_full_org_metadata(
                sf=sf,
                org_domain=org_domain,
                progress_callback=log_cb
            )
            
            progress.empty()
            st.success("✅ Sync function completed!")
            st.write("**Summary returned:**")
            st.json(summary)
            
            # Show all logs
            with st.expander("View full sync log"):
                st.code("\n".join(logs))
            
        except Exception as e:
            progress.empty()
            st.error(f"❌ Full sync failed: {e}")
            st.code(traceback.format_exc())
            
            # Show logs up to failure
            with st.expander("View log up to failure"):
                st.code("\n".join(logs))

st.write("---")
st.info("💡 **Tip:** Run these tests in order. If any test fails, that's where the issue is!")