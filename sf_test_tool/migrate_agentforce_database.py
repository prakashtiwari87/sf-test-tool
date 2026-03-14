"""
migrate_agentforce_database.py — Database Migration Script
Phase 3 Enterprise: Full Implementation

Run this script to initialize all Agentforce testing tables.

Usage:
    python migrate_agentforce_database.py
"""

import sqlite3
from config.settings_manager import DB_PATH
from datetime import datetime

def run_migration():
    """Run database migration to create Agentforce tables."""
    
    print("="*60)
    print("AGENTFORCE DATABASE MIGRATION")
    print("="*60)
    print(f"\nDatabase: {DB_PATH}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        # Table 1: Agents
        print("Creating table: agents...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                agent_description TEXT,
                org_domain TEXT NOT NULL,
                salesforce_connection_id INTEGER,
                status TEXT DEFAULT 'active',
                supports_chat INTEGER DEFAULT 0,
                supports_email INTEGER DEFAULT 0,
                supports_sms INTEGER DEFAULT 0,
                supports_voice INTEGER DEFAULT 0,
                supports_slack INTEGER DEFAULT 0,
                api_endpoint TEXT,
                dx_endpoint TEXT,
                testing_api_key TEXT,
                created_at TEXT,
                updated_at TEXT,
                last_tested_at TEXT,
                UNIQUE(agent_id, org_domain)
            )
        """)
        print("✅ agents table created")
        
        # Table 2: Agent Configurations
        print("Creating table: agent_configurations...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS agent_configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                agent_description TEXT,
                agent_role TEXT,
                business_functions TEXT,
                topics TEXT,
                topic_instructions TEXT,
                additional_config TEXT,
                preferred_llm_model TEXT,
                selected_test_types TEXT,
                selected_personas TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        print("✅ agent_configurations table created")
        
        # Table 3: Test Scripts
        print("Creating table: test_scripts...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_scripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                script_id TEXT NOT NULL UNIQUE,
                agent_id TEXT NOT NULL,
                test_type TEXT NOT NULL,
                persona TEXT NOT NULL,
                utterance TEXT NOT NULL,
                expected_intent TEXT,
                expected_entities TEXT,
                expected_response TEXT,
                script_source TEXT DEFAULT 'generated',
                generation_model TEXT,
                created_at TEXT
            )
        """)
        print("✅ test_scripts table created")
        
        # Table 4: Test Executions
        print("Creating table: test_executions...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT NOT NULL UNIQUE,
                agent_id TEXT NOT NULL,
                execution_type TEXT NOT NULL,
                total_scripts INTEGER DEFAULT 0,
                executed_scripts INTEGER DEFAULT 0,
                passed_scripts INTEGER DEFAULT 0,
                failed_scripts INTEGER DEFAULT 0,
                error_scripts INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                duration_sec REAL,
                test_config TEXT
            )
        """)
        print("✅ test_executions table created")
        
        # Table 5: Test Results
        print("Creating table: test_results_agentforce...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS test_results_agentforce (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                result_id TEXT NOT NULL UNIQUE,
                execution_id TEXT NOT NULL,
                script_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                test_type TEXT NOT NULL,
                persona TEXT NOT NULL,
                user_utterance TEXT,
                actual_response TEXT,
                expected_response TEXT,
                detected_intent TEXT,
                expected_intent TEXT,
                extracted_entities TEXT,
                judge_verdict TEXT,
                judge_confidence REAL,
                judge_reasoning TEXT,
                judge_models_used TEXT,
                status TEXT DEFAULT 'pending',
                executed_at TEXT,
                duration_sec REAL,
                session_id TEXT,
                conversation_context TEXT
            )
        """)
        print("✅ test_results_agentforce table created")
        
        # Table 6: Conversation Tests
        print("Creating table: conversation_tests...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS conversation_tests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL UNIQUE,
                execution_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                total_turns INTEGER DEFAULT 0,
                passed_turns INTEGER DEFAULT 0,
                failed_turns INTEGER DEFAULT 0,
                conversation_transcript TEXT,
                soql_queries_executed TEXT,
                data_validations TEXT,
                status TEXT DEFAULT 'pending',
                final_verdict TEXT,
                started_at TEXT,
                completed_at TEXT,
                duration_sec REAL
            )
        """)
        print("✅ conversation_tests table created")
        
        # Table 7: UI Test Sessions
        print("Creating table: ui_test_sessions...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ui_test_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL UNIQUE,
                execution_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                chat_url TEXT NOT NULL,
                browser TEXT DEFAULT 'chromium',
                total_scenarios INTEGER DEFAULT 0,
                passed_scenarios INTEGER DEFAULT 0,
                failed_scenarios INTEGER DEFAULT 0,
                evidence_paths TEXT,
                status TEXT DEFAULT 'pending',
                started_at TEXT,
                completed_at TEXT,
                duration_sec REAL
            )
        """)
        print("✅ ui_test_sessions table created")
        
        # Create indexes
        print("\nCreating indexes...")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agents_org ON agents(org_domain)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_test_scripts_agent ON test_scripts(agent_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_test_executions_agent ON test_executions(agent_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_test_results_execution ON test_results_agentforce(execution_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_conversation_tests_execution ON conversation_tests(execution_id)")
        print("✅ Indexes created")
        
        # Commit changes
        conn.commit()
        
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("="*60)
        print(f"\n7 tables created:")
        print("  1. agents")
        print("  2. agent_configurations")
        print("  3. test_scripts")
        print("  4. test_executions")
        print("  5. test_results_agentforce")
        print("  6. conversation_tests")
        print("  7. ui_test_sessions")
        print(f"\n6 indexes created for performance")
        print(f"\nDatabase ready at: {DB_PATH}\n")
        
        return True
    
    except Exception as e:
        print(f"\n❌ MIGRATION FAILED!")
        print(f"Error: {str(e)}\n")
        conn.rollback()
        return False
    
    finally:
        conn.close()


def verify_migration():
    """Verify migration was successful."""
    
    print("\n" + "="*60)
    print("VERIFYING MIGRATION")
    print("="*60 + "\n")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Get all tables
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cur.fetchall()]
    
    expected_tables = [
        'agents',
        'agent_configurations',
        'test_scripts',
        'test_executions',
        'test_results_agentforce',
        'conversation_tests',
        'ui_test_sessions'
    ]
    
    print("Checking tables...")
    all_exist = True
    
    for table in expected_tables:
        exists = table in tables
        status = "✅" if exists else "❌"
        print(f"  {status} {table}")
        
        if exists:
            # Count rows
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"      ({count} rows)")
        
        all_exist = all_exist and exists
    
    conn.close()
    
    if all_exist:
        print("\n✅ All tables verified successfully!\n")
        return True
    else:
        print("\n❌ Some tables are missing!\n")
        return False


if __name__ == "__main__":
    print("\n🚀 Starting Agentforce database migration...\n")
    
    # Run migration
    success = run_migration()
    
    if success:
        # Verify
        verify_migration()
        
        print("="*60)
        print("🎉 DATABASE MIGRATION COMPLETE!")
        print("="*60)
        print("\nYou can now:")
        print("  • Register Agentforce agents")
        print("  • Generate test scripts")
        print("  • Execute tests")
        print("  • View results")
        print("\nNext steps:")
        print("  1. Go to Settings page")
        print("  2. Register or discover your Agentforce agents")
        print("  3. Start testing!")
        print()
    else:
        print("="*60)
        print("❌ MIGRATION FAILED - Please check errors above")
        print("="*60)
        print()