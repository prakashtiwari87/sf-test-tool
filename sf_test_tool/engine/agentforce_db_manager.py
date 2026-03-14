"""
agentforce_db_manager.py — Database Manager for Agentforce Testing
Phase 3 Enterprise

FUNCTIONS:
  • init_agentforce_database() - Initialize all tables
  • Agent management (CRUD)
  • Test script management
  • Execution tracking
  • Results storage
"""

import sqlite3
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
from config.settings_manager import DB_PATH

# ══════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ══════════════════════════════════════════════════════════════

def init_agentforce_database():
    """Initialize all Agentforce testing tables."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Agents table
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
    
    # Agent configurations table
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
    
    # Test scripts table
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
    
    # Test executions table
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
    
    # Test results table
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
    
    # Conversation tests table
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
    
    # UI test sessions table
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
    
    conn.commit()
    conn.close()


# ══════════════════════════════════════════════════════════════
# AGENT MANAGEMENT
# ══════════════════════════════════════════════════════════════

def save_agent(
    agent_id: str,
    agent_name: str,
    org_domain: str,
    agent_description: Optional[str] = None,
    **kwargs
) -> bool:
    """Save or update agent."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT OR REPLACE INTO agents
            (agent_id, agent_name, agent_description, org_domain,
             supports_chat, supports_email, supports_sms, supports_voice, supports_slack,
             api_endpoint, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_id,
            agent_name,
            agent_description,
            org_domain,
            kwargs.get('supports_chat', 1),
            kwargs.get('supports_email', 0),
            kwargs.get('supports_sms', 0),
            kwargs.get('supports_voice', 0),
            kwargs.get('supports_slack', 0),
            kwargs.get('api_endpoint', ''),
            'active',
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving agent: {e}")
        return False
    finally:
        conn.close()


def get_all_agents(org_domain: Optional[str] = None) -> List[Dict]:
    """Get all agents, optionally filtered by org."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    if org_domain:
        cur.execute("SELECT * FROM agents WHERE org_domain = ? AND status = 'active'", (org_domain,))
    else:
        cur.execute("SELECT * FROM agents WHERE status = 'active'")
    
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    
    return [dict(zip(cols, row)) for row in rows]


def get_agent(agent_id: str) -> Optional[Dict]:
    """Get single agent by ID."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
    row = cur.fetchone()
    
    if row:
        cols = [desc[0] for desc in cur.description]
        conn.close()
        return dict(zip(cols, row))
    
    conn.close()
    return None


# ══════════════════════════════════════════════════════════════
# AGENT CONFIGURATION
# ══════════════════════════════════════════════════════════════

def save_agent_configuration(
    agent_id: str,
    agent_description: str,
    agent_role: str,
    business_functions: List[str],
    topics: List[str],
    topic_instructions: str,
    preferred_llm_model: str,
    selected_test_types: List[str],
    selected_personas: List[str],
    additional_config: Optional[Dict] = None
) -> bool:
    """Save agent configuration."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT OR REPLACE INTO agent_configurations
            (agent_id, agent_description, agent_role, business_functions,
             topics, topic_instructions, additional_config, preferred_llm_model,
             selected_test_types, selected_personas, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_id,
            agent_description,
            agent_role,
            json.dumps(business_functions),
            json.dumps(topics),
            topic_instructions,
            json.dumps(additional_config or {}),
            preferred_llm_model,
            json.dumps(selected_test_types),
            json.dumps(selected_personas),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving configuration: {e}")
        return False
    finally:
        conn.close()


def get_agent_configuration(agent_id: str) -> Optional[Dict]:
    """Get agent configuration."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM agent_configurations WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1", (agent_id,))
    row = cur.fetchone()
    
    if row:
        cols = [desc[0] for desc in cur.description]
        config = dict(zip(cols, row))
        
        # Parse JSON fields
        config['business_functions'] = json.loads(config.get('business_functions', '[]'))
        config['topics'] = json.loads(config.get('topics', '[]'))
        config['additional_config'] = json.loads(config.get('additional_config', '{}'))
        config['selected_test_types'] = json.loads(config.get('selected_test_types', '[]'))
        config['selected_personas'] = json.loads(config.get('selected_personas', '[]'))
        
        conn.close()
        return config
    
    conn.close()
    return None


# ══════════════════════════════════════════════════════════════
# TEST SCRIPTS
# ══════════════════════════════════════════════════════════════

def save_test_scripts(scripts: List[Dict]) -> bool:
    """Save multiple test scripts."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        for script in scripts:
            cur.execute("""
                INSERT OR REPLACE INTO test_scripts
                (script_id, agent_id, test_type, persona, utterance,
                 expected_intent, expected_entities, expected_response,
                 script_source, generation_model, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                script.get('script_id'),
                script.get('agent_id'),
                script.get('test_type'),
                script.get('persona'),
                script.get('utterance'),
                script.get('expected_intent'),
                json.dumps(script.get('expected_entities', [])),
                script.get('expected_response'),
                script.get('script_source', 'generated'),
                script.get('generation_model'),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving scripts: {e}")
        return False
    finally:
        conn.close()


def get_test_scripts(agent_id: str) -> List[Dict]:
    """Get all test scripts for an agent."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM test_scripts WHERE agent_id = ? ORDER BY created_at DESC", (agent_id,))
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    
    scripts = []
    for row in rows:
        script = dict(zip(cols, row))
        script['expected_entities'] = json.loads(script.get('expected_entities', '[]'))
        scripts.append(script)
    
    return scripts


# ══════════════════════════════════════════════════════════════
# TEST EXECUTION
# ══════════════════════════════════════════════════════════════

def create_test_execution(
    execution_id: str,
    agent_id: str,
    execution_type: str,
    test_config: Dict
) -> bool:
    """Create new test execution."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO test_executions
            (execution_id, agent_id, execution_type, status, test_config, started_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            execution_id,
            agent_id,
            execution_type,
            'pending',
            json.dumps(test_config),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error creating execution: {e}")
        return False
    finally:
        conn.close()


def update_test_execution(
    execution_id: str,
    **kwargs
) -> bool:
    """Update test execution status."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    updates = []
    values = []
    
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        values.append(value)
    
    if 'updated_at' not in kwargs:
        updates.append("updated_at = ?")
        values.append(datetime.now().isoformat())
    
    values.append(execution_id)
    
    try:
        cur.execute(
            f"UPDATE test_executions SET {', '.join(updates)} WHERE execution_id = ?",
            values
        )
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating execution: {e}")
        return False
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
# TEST RESULTS
# ══════════════════════════════════════════════════════════════

def save_test_result(result: Dict) -> bool:
    """Save single test result."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO test_results_agentforce
            (result_id, execution_id, script_id, agent_id, test_type, persona,
             user_utterance, actual_response, expected_response,
             detected_intent, expected_intent, extracted_entities,
             judge_verdict, judge_confidence, judge_reasoning, judge_models_used,
             status, executed_at, duration_sec, session_id, conversation_context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            result.get('result_id'),
            result.get('execution_id'),
            result.get('script_id'),
            result.get('agent_id'),
            result.get('test_type'),
            result.get('persona'),
            result.get('user_utterance'),
            result.get('actual_response'),
            result.get('expected_response'),
            result.get('detected_intent'),
            result.get('expected_intent'),
            json.dumps(result.get('extracted_entities', [])),
            result.get('judge_verdict'),
            result.get('judge_confidence'),
            result.get('judge_reasoning'),
            json.dumps(result.get('judge_models_used', [])),
            result.get('status'),
            datetime.now().isoformat(),
            result.get('duration_sec'),
            result.get('session_id'),
            json.dumps(result.get('conversation_context', {}))
        ))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error saving result: {e}")
        return False
    finally:
        conn.close()


def get_execution_results(execution_id: str) -> List[Dict]:
    """Get all results for an execution."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute(
        "SELECT * FROM test_results_agentforce WHERE execution_id = ? ORDER BY executed_at",
        (execution_id,)
    )
    rows = cur.fetchall()
    cols = [desc[0] for desc in cur.description]
    conn.close()
    
    results = []
    for row in rows:
        result = dict(zip(cols, row))
        result['extracted_entities'] = json.loads(result.get('extracted_entities', '[]'))
        result['judge_models_used'] = json.loads(result.get('judge_models_used', '[]'))
        result['conversation_context'] = json.loads(result.get('conversation_context', '{}'))
        results.append(result)
    
    return results