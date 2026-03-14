"""
agentforce_database_schema.sql — Database Schema for Agentforce Testing Platform
Phase 3 Enterprise: Complete rebuild

TABLES:
  • agents - Registered Agentforce agents
  • agent_configurations - Agent details, roles, topics
  • test_scripts - Generated/uploaded test scripts
  • test_executions - Test run executions
  • conversation_tests - Multi-turn conversation tests
  • test_results_agentforce - Detailed test results
"""

-- ══════════════════════════════════════════════════════════════
-- AGENTS TABLE
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    agent_name TEXT NOT NULL,
    agent_description TEXT,
    org_domain TEXT NOT NULL,
    salesforce_connection_id INTEGER,
    status TEXT DEFAULT 'active',
    
    -- Channel support
    supports_chat INTEGER DEFAULT 0,
    supports_email INTEGER DEFAULT 0,
    supports_sms INTEGER DEFAULT 0,
    supports_voice INTEGER DEFAULT 0,
    supports_slack INTEGER DEFAULT 0,
    
    -- API endpoints
    api_endpoint TEXT,
    dx_endpoint TEXT,
    testing_api_key TEXT,
    
    -- Metadata
    created_at TEXT,
    updated_at TEXT,
    last_tested_at TEXT,
    
    UNIQUE(agent_id, org_domain)
);

-- ══════════════════════════════════════════════════════════════
-- AGENT CONFIGURATIONS TABLE
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS agent_configurations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL,
    
    -- Agent details
    agent_description TEXT,
    agent_role TEXT,
    business_functions TEXT, -- JSON array
    topics TEXT, -- JSON array
    topic_instructions TEXT, -- Long text field
    
    -- Additional settings
    additional_config TEXT, -- JSON
    
    -- LLM settings
    preferred_llm_model TEXT,
    
    -- Testing configuration
    selected_test_types TEXT, -- JSON array
    selected_personas TEXT, -- JSON array
    
    created_at TEXT,
    updated_at TEXT,
    
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- ══════════════════════════════════════════════════════════════
-- TEST SCRIPTS TABLE
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS test_scripts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    script_id TEXT NOT NULL UNIQUE,
    agent_id TEXT NOT NULL,
    
    -- Script details
    test_type TEXT NOT NULL, -- Intent, Knowledge, Action, etc.
    persona TEXT NOT NULL, -- Direct, Friendly, etc.
    
    -- Test case
    utterance TEXT NOT NULL,
    expected_intent TEXT,
    expected_entities TEXT, -- JSON
    expected_response TEXT,
    
    -- Metadata
    script_source TEXT DEFAULT 'generated', -- generated, uploaded, manual
    generation_model TEXT,
    
    created_at TEXT,
    
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- ══════════════════════════════════════════════════════════════
-- TEST EXECUTIONS TABLE
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS test_executions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL UNIQUE,
    agent_id TEXT NOT NULL,
    
    -- Execution details
    execution_type TEXT NOT NULL, -- api, ui, conversation
    total_scripts INTEGER DEFAULT 0,
    executed_scripts INTEGER DEFAULT 0,
    passed_scripts INTEGER DEFAULT 0,
    failed_scripts INTEGER DEFAULT 0,
    error_scripts INTEGER DEFAULT 0,
    
    -- Status
    status TEXT DEFAULT 'pending', -- pending, running, completed, failed
    
    -- Timing
    started_at TEXT,
    completed_at TEXT,
    duration_sec REAL,
    
    -- Configuration
    test_config TEXT, -- JSON
    
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- ══════════════════════════════════════════════════════════════
-- TEST RESULTS (AGENTFORCE)
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS test_results_agentforce (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    result_id TEXT NOT NULL UNIQUE,
    execution_id TEXT NOT NULL,
    script_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    
    -- Test details
    test_type TEXT NOT NULL,
    persona TEXT NOT NULL,
    
    -- Input/Output
    user_utterance TEXT,
    actual_response TEXT,
    expected_response TEXT,
    
    -- Validation
    detected_intent TEXT,
    expected_intent TEXT,
    extracted_entities TEXT, -- JSON
    
    -- LLM Judge results
    judge_verdict TEXT, -- PASS, FAIL, ERROR
    judge_confidence REAL,
    judge_reasoning TEXT,
    judge_models_used TEXT, -- JSON array
    
    -- Status
    status TEXT DEFAULT 'pending', -- pending, pass, fail, error
    
    -- Timing
    executed_at TEXT,
    duration_sec REAL,
    
    -- Additional data
    session_id TEXT,
    conversation_context TEXT, -- JSON
    
    FOREIGN KEY (execution_id) REFERENCES test_executions(execution_id),
    FOREIGN KEY (script_id) REFERENCES test_scripts(script_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- ══════════════════════════════════════════════════════════════
-- CONVERSATION TESTS TABLE
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS conversation_tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL UNIQUE,
    execution_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    
    -- Conversation details
    total_turns INTEGER DEFAULT 0,
    passed_turns INTEGER DEFAULT 0,
    failed_turns INTEGER DEFAULT 0,
    
    -- Full transcript
    conversation_transcript TEXT, -- JSON array of turns
    
    -- Salesforce data validation
    soql_queries_executed TEXT, -- JSON array
    data_validations TEXT, -- JSON
    
    -- Status
    status TEXT DEFAULT 'pending',
    final_verdict TEXT, -- PASS, FAIL, ERROR
    
    -- Timing
    started_at TEXT,
    completed_at TEXT,
    duration_sec REAL,
    
    FOREIGN KEY (execution_id) REFERENCES test_executions(execution_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- ══════════════════════════════════════════════════════════════
-- UI TEST SESSIONS TABLE
-- ══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS ui_test_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    execution_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    
    -- UI details
    chat_url TEXT NOT NULL,
    browser TEXT DEFAULT 'chromium',
    
    -- Test details
    total_scenarios INTEGER DEFAULT 0,
    passed_scenarios INTEGER DEFAULT 0,
    failed_scenarios INTEGER DEFAULT 0,
    
    -- Screenshots/Videos
    evidence_paths TEXT, -- JSON array of file paths
    
    -- Status
    status TEXT DEFAULT 'pending',
    
    -- Timing
    started_at TEXT,
    completed_at TEXT,
    duration_sec REAL,
    
    FOREIGN KEY (execution_id) REFERENCES test_executions(execution_id),
    FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
);

-- ══════════════════════════════════════════════════════════════
-- INDEXES FOR PERFORMANCE
-- ══════════════════════════════════════════════════════════════

CREATE INDEX IF NOT EXISTS idx_agents_org ON agents(org_domain);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_test_scripts_agent ON test_scripts(agent_id);
CREATE INDEX IF NOT EXISTS idx_test_executions_agent ON test_executions(agent_id);
CREATE INDEX IF NOT EXISTS idx_test_results_execution ON test_results_agentforce(execution_id);
CREATE INDEX IF NOT EXISTS idx_conversation_tests_execution ON conversation_tests(execution_id);

-- ══════════════════════════════════════════════════════════════
-- SAMPLE DATA INSERTIONS (FOR TESTING)
-- ══════════════════════════════════════════════════════════════

-- Sample test types
-- Intent Recognition & NLP Testing
-- Knowledge Grounding Testing
-- Action / Automation Testing
-- Guardrails & Safety Testing
-- Context & Memory Testing
-- Performance & Load Testing
-- Prompt & Response Quality Testing
-- Multilingual Testing
-- Security & Access Testing

-- Sample personas
-- Direct / Straightforward
-- Friendly / Polite
-- Formal / Professional
-- Casual / Conversational
-- Frustrated / Angry
-- Confused
-- Curious / Exploratory
-- Impatient / Urgent
-- Hesitant / Unsure
-- Technical / Power User
-- Non-Native Speaker
-- Verbose / Storytelling
-- Multi-Intent User
-- Sarcastic / Passive Aggressive
-- Adversarial / Edge Case Testing