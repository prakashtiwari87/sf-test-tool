"""
settings_manager.py
Handles all persistent storage using SQLite.
All settings entered in the browser UI are saved here permanently.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "settings.db")


# ─────────────────────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────────────────────

def init_database():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS llm_keys (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            provider    TEXT NOT NULL UNIQUE,
            api_key     TEXT NOT NULL,
            is_active   INTEGER DEFAULT 1,
            added_at    TEXT,
            last_tested TEXT,
            test_status TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS salesforce_connections (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_name TEXT NOT NULL,
            org_type        TEXT,
            domain          TEXT NOT NULL,
            auth_method     TEXT NOT NULL,
            client_id       TEXT,
            client_secret   TEXT,
            username        TEXT,
            password        TEXT,
            security_token  TEXT,
            is_active       INTEGER DEFAULT 0,
            last_connected  TEXT,
            org_name        TEXT,
            org_id          TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS email_connections (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_name TEXT NOT NULL,
            provider        TEXT NOT NULL,
            email_address   TEXT NOT NULL,
            auth_method     TEXT,
            client_id       TEXT,
            client_secret   TEXT,
            refresh_token   TEXT,
            smtp_server     TEXT,
            smtp_port       INTEGER,
            imap_server     TEXT,
            is_active       INTEGER DEFAULT 0,
            last_tested     TEXT,
            test_status     TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS slack_connections (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_name TEXT NOT NULL,
            workspace_name  TEXT,
            bot_token       TEXT NOT NULL,
            app_token       TEXT,
            default_channel TEXT,
            is_active       INTEGER DEFAULT 0,
            last_tested     TEXT,
            test_status     TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS judge_model_selection (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            model_id    TEXT NOT NULL UNIQUE,
            model_name  TEXT NOT NULL,
            provider    TEXT NOT NULL,
            is_selected INTEGER DEFAULT 0,
            sort_order  INTEGER DEFAULT 0
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
# Amazon Bedrock AgentCore Connections
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bedrock_connections (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            connection_name TEXT NOT NULL,
            region          TEXT NOT NULL,
            access_key      TEXT,
            secret_key      TEXT,
            agent_id        TEXT,
            agent_alias_id  TEXT,
            bot_id          TEXT,
            bot_alias_id    TEXT,
            locale_id       TEXT DEFAULT 'en_US',
            instance_id     TEXT,
            environment     TEXT DEFAULT 'Development',
            is_active       INTEGER DEFAULT 0,
            last_connected  TEXT,
            created_at      TEXT
        )
    """)
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# LLM KEY OPERATIONS
# ─────────────────────────────────────────────────────────────

def save_llm_key(provider: str, api_key: str):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO llm_keys (provider, api_key, is_active, added_at)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(provider) DO UPDATE SET
        api_key = ?, is_active = 1, added_at = ?
    """, (provider, api_key, datetime.now().isoformat(),
          api_key, datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_llm_key(provider: str) -> str:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT api_key FROM llm_keys
        WHERE provider = ? AND is_active = 1
        LIMIT 1
    """, (provider,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else os.getenv(f"{provider.upper()}_API_KEY", "")


def get_all_llm_keys() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT provider, api_key, test_status
        FROM llm_keys WHERE is_active = 1
    """)
    rows = cur.fetchall()
    conn.close()
    return {row[0]: {"key": row[1], "status": row[2]} for row in rows}


def update_llm_key_status(provider: str, status: str):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        UPDATE llm_keys SET test_status = ?, last_tested = ?
        WHERE provider = ?
    """, (status, datetime.now().isoformat(), provider))
    conn.commit()
    conn.close()


def delete_llm_key(provider: str):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("DELETE FROM llm_keys WHERE provider = ?", (provider,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# SALESFORCE CONNECTION OPERATIONS
# ─────────────────────────────────────────────────────────────

def save_salesforce_connection(name, domain, auth_method,
                                client_id="", client_secret="",
                                username="", password="",
                                security_token="", org_type="",
                                org_name="", org_id=""):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("UPDATE salesforce_connections SET is_active = 0")
    cur.execute("""
        INSERT INTO salesforce_connections
        (connection_name, org_type, domain, auth_method,
         client_id, client_secret, username, password,
         security_token, is_active, last_connected, org_name, org_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?)
    """, (name, org_type, domain, auth_method,
          client_id, client_secret, username, password,
          security_token, datetime.now().isoformat(), org_name, org_id))
    conn.commit()
    conn.close()


def get_active_salesforce_connection() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT * FROM salesforce_connections
        WHERE is_active = 1 ORDER BY id DESC LIMIT 1
    """)
    row  = cur.fetchone()
    conn.close()
    if not row:
        return {}
    cols = ["id","connection_name","org_type","domain","auth_method",
            "client_id","client_secret","username","password",
            "security_token","is_active","last_connected","org_name","org_id"]
    return dict(zip(cols, row))


def get_all_salesforce_connections() -> list:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, connection_name, org_type, domain,
               auth_method, is_active, last_connected, org_name
        FROM salesforce_connections ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    cols = ["id","connection_name","org_type","domain",
            "auth_method","is_active","last_connected","org_name"]
    return [dict(zip(cols, r)) for r in rows]


def set_active_salesforce_connection(conn_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("UPDATE salesforce_connections SET is_active = 0")
    cur.execute("UPDATE salesforce_connections SET is_active = 1 WHERE id = ?",
                (conn_id,))
    conn.commit()
    conn.close()


def delete_salesforce_connection(conn_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("DELETE FROM salesforce_connections WHERE id = ?", (conn_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# EMAIL CONNECTION OPERATIONS
# ─────────────────────────────────────────────────────────────

def save_email_connection(name, provider, email_address,
                           client_id="", client_secret="",
                           smtp_server="", smtp_port=587,
                           imap_server=""):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("UPDATE email_connections SET is_active = 0")
    cur.execute("""
        INSERT INTO email_connections
        (connection_name, provider, email_address,
         client_id, client_secret,
         smtp_server, smtp_port, imap_server,
         is_active, last_tested)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
    """, (name, provider, email_address,
          client_id, client_secret,
          smtp_server, smtp_port, imap_server,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_active_email_connection() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT * FROM email_connections
        WHERE is_active = 1 ORDER BY id DESC LIMIT 1
    """)
    row  = cur.fetchone()
    conn.close()
    if not row:
        return {}
    cols = ["id","connection_name","provider","email_address",
            "auth_method","client_id","client_secret","refresh_token",
            "smtp_server","smtp_port","imap_server",
            "is_active","last_tested","test_status"]
    return dict(zip(cols, row))


def get_all_email_connections() -> list:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, connection_name, provider, email_address,
               is_active, last_tested, test_status
        FROM email_connections ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    cols = ["id","connection_name","provider","email_address",
            "is_active","last_tested","test_status"]
    return [dict(zip(cols, r)) for r in rows]


def delete_email_connection(conn_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("DELETE FROM email_connections WHERE id = ?", (conn_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# SLACK CONNECTION OPERATIONS
# ─────────────────────────────────────────────────────────────

def save_slack_connection(name, workspace_name,
                           bot_token, app_token="",
                           default_channel=""):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("UPDATE slack_connections SET is_active = 0")
    cur.execute("""
        INSERT INTO slack_connections
        (connection_name, workspace_name, bot_token,
         app_token, default_channel, is_active, last_tested)
        VALUES (?, ?, ?, ?, ?, 1, ?)
    """, (name, workspace_name, bot_token,
          app_token, default_channel,
          datetime.now().isoformat()))
    conn.commit()
    conn.close()


def get_active_slack_connection() -> dict:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT * FROM slack_connections
        WHERE is_active = 1 ORDER BY id DESC LIMIT 1
    """)
    row  = cur.fetchone()
    conn.close()
    if not row:
        return {}
    cols = ["id","connection_name","workspace_name",
            "bot_token","app_token","default_channel",
            "is_active","last_tested","test_status"]
    return dict(zip(cols, row))


def get_all_slack_connections() -> list:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT id, connection_name, workspace_name,
               default_channel, is_active, last_tested
        FROM slack_connections ORDER BY id DESC
    """)
    rows = cur.fetchall()
    conn.close()
    cols = ["id","connection_name","workspace_name",
            "default_channel","is_active","last_tested"]
    return [dict(zip(cols, r)) for r in rows]


def delete_slack_connection(conn_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("DELETE FROM slack_connections WHERE id = ?", (conn_id,))
    conn.commit()
    conn.close()


# ─────────────────────────────────────────────────────────────
# JUDGE MODEL SELECTION
# ─────────────────────────────────────────────────────────────

def save_selected_judge_models(model_list: list):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("UPDATE judge_model_selection SET is_selected = 0")
    for i, model in enumerate(model_list):
        cur.execute("""
            INSERT INTO judge_model_selection
            (model_id, model_name, provider, is_selected, sort_order)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(model_id) DO UPDATE SET
            is_selected = 1, sort_order = ?
        """, (model["model_id"], model["model_name"],
              model["provider"], i, i))
    conn.commit()
    conn.close()


def get_selected_judge_models() -> list:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        SELECT model_id FROM judge_model_selection
        WHERE is_selected = 1 ORDER BY sort_order
    """)
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]


# ─────────────────────────────────────────────────────────────
# APP SETTINGS
# ─────────────────────────────────────────────────────────────

def save_setting(key: str, value: str):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO app_settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = ?
    """, (key, value, value))
    conn.commit()
    conn.close()


def get_setting(key: str, default: str = "") -> str:
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else default


# ─────────────────────────────────────────────────────────────
# LOAD ALL SAVED KEYS INTO ENVIRONMENT AT STARTUP
# ─────────────────────────────────────────────────────────────

def load_all_keys_to_env():
    """Load all saved API keys from DB into environment variables"""
    try:
        keys = get_all_llm_keys()
        provider_env_map = {
            "GROQ":        "GROQ_API_KEY",
            "MISTRAL":     "MISTRAL_API_KEY",
            "CEREBRAS":    "CEREBRAS_API_KEY",
            "OPENROUTER":  "OPENROUTER_API_KEY",
            "COHERE":      "COHERE_API_KEY",
            "TOGETHER":    "TOGETHERAI_API_KEY",
            "FIREWORKS":   "FIREWORKS_AI_API_KEY",
            "HUGGINGFACE": "HUGGINGFACE_API_KEY",
            "GEMINI":      "GEMINI_API_KEY",
            "PERPLEXITY":  "PERPLEXITYAI_API_KEY",
            "AI21":        "AI21_API_KEY",
            "NVIDIA":      "NVIDIA_NIM_API_KEY",
            "OPENAI":      "OPENAI_API_KEY",
            "ANTHROPIC":   "ANTHROPIC_API_KEY",
            "DEEPSEEK":    "DEEPSEEK_API_KEY",
        }
        for provider, data in keys.items():
            env_key = provider_env_map.get(provider.upper())
            if env_key and data.get("key"):
                os.environ[env_key] = data["key"]
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# RUN ON IMPORT
# ─────────────────────────────────────────────────────────────
init_database()
load_all_keys_to_env()

# ─────────────────────────────────────────────────────────────
# BEDROCK CONNECTIONS
# ─────────────────────────────────────────────────────────────

def save_bedrock_connection(name: str, region: str,
                             access_key: str, secret_key: str,
                             agent_id: str = "",
                             agent_alias_id: str = "",
                             bot_id: str = "",
                             bot_alias_id: str = "",
                             instance_id: str = "",
                             environment: str = "Development") -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        # Deactivate all others
        cur.execute(
            "UPDATE bedrock_connections SET is_active = 0"
        )
        cur.execute("""
            INSERT INTO bedrock_connections
            (connection_name, region, access_key, secret_key,
             agent_id, agent_alias_id, bot_id, bot_alias_id,
             instance_id, environment, is_active, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,1,?)
        """, (
            name, region, access_key, secret_key,
            agent_id, agent_alias_id, bot_id, bot_alias_id,
            instance_id, environment,
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"save_bedrock_connection error: {e}")
        return False


def get_active_bedrock_connection() -> dict:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, connection_name, region, access_key,
                   secret_key, agent_id, agent_alias_id,
                   bot_id, bot_alias_id, instance_id,
                   environment, is_active
            FROM bedrock_connections
            WHERE is_active = 1
            LIMIT 1
        """)
        row = cur.fetchone()
        conn.close()
        if not row:
            return {}
        cols = [
            "id","connection_name","region","access_key",
            "secret_key","agent_id","agent_alias_id",
            "bot_id","bot_alias_id","instance_id",
            "environment","is_active"
        ]
        return dict(zip(cols, row))
    except Exception:
        return {}


def get_all_bedrock_connections() -> list:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, connection_name, region, agent_id,
                   environment, is_active, created_at
            FROM bedrock_connections
            ORDER BY created_at DESC
        """)
        rows = cur.fetchall()
        conn.close()
        cols = [
            "id","connection_name","region","agent_id",
            "environment","is_active","created_at"
        ]
        return [dict(zip(cols,r)) for r in rows]
    except Exception:
        return []


def delete_bedrock_connection(conn_id: int) -> bool:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute(
            "DELETE FROM bedrock_connections WHERE id=?",
            (conn_id,)
        )
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False