"""
llm_connector.py
Comprehensive LLM connector supporting every major provider.
🟢 Free  🟡 Limited Free  🔴 Paid
"""

import os
import litellm
from dotenv import load_dotenv

load_dotenv()
litellm.suppress_debug_info = True


# ─────────────────────────────────────────────────────────────
# COMPREHENSIVE MODEL REGISTRY
# ─────────────────────────────────────────────────────────────

ALL_MODELS = {

    # ══════════════════════════════════════════════════════════
    # 🟢 COMPLETELY FREE — No credit card needed
    # ══════════════════════════════════════════════════════════

    "── 🟢 GROQ  (Free · console.groq.com) ──────────────────": None,
    "Groq · Llama 3.3 70B Versatile":         "groq/llama-3.3-70b-versatile",
    "Groq · Llama 3.1 8B Instant":            "groq/llama-3.1-8b-instant",
    "Groq · Llama 4 Scout 17B":               "groq/meta-llama/llama-4-scout-17b-16e-instruct",
    "Groq · Llama 4 Maverick 17B":            "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
    "Groq · Compound Beta":                   "groq/compound-beta",
    "Groq · Compound Beta Mini":              "groq/compound-beta-mini",

    "── 🟢 MISTRAL AI  (Free · console.mistral.ai) ──────────": None,
    "Mistral · Mistral Small":                "mistral/mistral-small-latest",
    "Mistral · Open Mistral 7B":              "mistral/open-mistral-7b",
    "Mistral · Open Mixtral 8x7B":            "mistral/open-mixtral-8x7b",
    "Mistral · Codestral":                    "mistral/codestral-latest",

    "── 🟢 CEREBRAS  (Free · cloud.cerebras.ai) ─────────────": None,
    "Cerebras · Llama 3.3 70B":               "cerebras/llama3.3-70b",
    "Cerebras · Llama 3.1 8B":                "cerebras/llama3.1-8b",

    "── 🟢 OPENROUTER Free Models  (openrouter.ai) ──────────": None,
    "OpenRouter · Llama 3.3 70B (free)":      "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "OpenRouter · Llama 3.1 8B (free)":       "openrouter/meta-llama/llama-3.1-8b-instruct:free",
    "OpenRouter · Gemma 2 9B (free)":         "openrouter/google/gemma-2-9b-it:free",
    "OpenRouter · Mistral 7B (free)":         "openrouter/mistralai/mistral-7b-instruct:free",
    "OpenRouter · Phi-3 Medium (free)":       "openrouter/microsoft/phi-3-medium-128k-instruct:free",
    "OpenRouter · Qwen2 7B (free)":           "openrouter/qwen/qwen-2-7b-instruct:free",

    "── 🟢 COHERE  (Free trial · dashboard.cohere.com) ──────": None,
    "Cohere · Command R":                     "cohere/command-r",
    "Cohere · Command Light":                 "cohere/command-light",

    "── 🟢 TOGETHER AI  (Free $25 credit · api.together.ai) ─": None,
    "Together · Llama 3.3 70B":               "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "Together · Llama 3.1 8B":                "together_ai/meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "Together · Mistral 7B":                  "together_ai/mistralai/Mistral-7B-Instruct-v0.3",
    "Together · Gemma 2 27B":                 "together_ai/google/gemma-2-27b-it",
    "Together · Qwen 2.5 72B":                "together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo",

    "── 🟢 FIREWORKS AI  (Free $1 credit · fireworks.ai) ────": None,
    "Fireworks · Llama 3.1 405B":             "fireworks_ai/accounts/fireworks/models/llama-v3p1-405b-instruct",
    "Fireworks · Llama 3.3 70B":              "fireworks_ai/accounts/fireworks/models/llama-v3p3-70b-instruct",
    "Fireworks · Qwen 2.5 72B":               "fireworks_ai/accounts/fireworks/models/qwen2p5-72b-instruct",

    "── 🟢 HUGGING FACE  (Free · huggingface.co) ────────────": None,
    "HuggingFace · Zephyr 7B Beta":           "huggingface/HuggingFaceH4/zephyr-7b-beta",
    "HuggingFace · Mistral 7B Instruct":      "huggingface/mistralai/Mistral-7B-Instruct-v0.3",
    "HuggingFace · Llama 3.1 8B":             "huggingface/meta-llama/Meta-Llama-3.1-8B-Instruct",

    # ══════════════════════════════════════════════════════════
    # 🟡 LIMITED FREE TIER — Free quota, may run out
    # ══════════════════════════════════════════════════════════

    "── 🟡 GOOGLE GEMINI  (Limited · aistudio.google.com) ───": None,
    "Gemini · 2.0 Flash Lite":                "gemini/gemini-2.0-flash-lite",
    "Gemini · 2.0 Flash":                     "gemini/gemini-2.0-flash",
    "Gemini · 1.5 Flash":                     "gemini/gemini-1.5-flash",
    "Gemini · 1.5 Pro":                       "gemini/gemini-1.5-pro",
    "Gemini · 2.5 Pro Preview":               "gemini/gemini-2.5-pro-preview-03-25",

    "── 🟡 PERPLEXITY  (Limited · perplexity.ai) ────────────": None,
    "Perplexity · Sonar":                     "perplexity/sonar",
    "Perplexity · Sonar Pro":                 "perplexity/sonar-pro",
    "Perplexity · Sonar Reasoning":           "perplexity/sonar-reasoning",

    "── 🟡 AI21 LABS  (Free trial · studio.ai21.com) ────────": None,
    "AI21 · Jamba 1.5 Large":                 "ai21/jamba-1.5-large",
    "AI21 · Jamba 1.5 Mini":                  "ai21/jamba-1.5-mini",

    "── 🟡 NVIDIA NIM  (Free credits · build.nvidia.com) ────": None,
    "NVIDIA · Llama 3.1 70B":                 "nvidia_nim/meta/llama-3.1-70b-instruct",
    "NVIDIA · Llama 3.1 8B":                  "nvidia_nim/meta/llama-3.1-8b-instruct",
    "NVIDIA · Mistral 7B":                    "nvidia_nim/mistralai/mistral-7b-instruct-v0.3",
    "NVIDIA · Gemma 2 9B":                    "nvidia_nim/google/gemma-2-9b-it",

    # ══════════════════════════════════════════════════════════
    # 🔴 PAID ONLY — Requires billing setup
    # ══════════════════════════════════════════════════════════

    "── 🔴 OPENAI  (Paid · platform.openai.com) ─────────────": None,
    "OpenAI · GPT-4o":                        "gpt-4o",
    "OpenAI · GPT-4o Mini":                   "gpt-4o-mini",
    "OpenAI · GPT-4 Turbo":                   "gpt-4-turbo",
    "OpenAI · O1 Preview":                    "o1-preview",
    "OpenAI · O1 Mini":                       "o1-mini",
    "OpenAI · O3 Mini":                       "o3-mini",

    "── 🔴 ANTHROPIC CLAUDE  (Paid · console.anthropic.com) ─": None,
    "Claude · 3.7 Sonnet":                    "anthropic/claude-3-7-sonnet-20250219",
    "Claude · 3.5 Sonnet":                    "anthropic/claude-3-5-sonnet-20241022",
    "Claude · 3.5 Haiku":                     "anthropic/claude-3-5-haiku-20241022",
    "Claude · 3 Opus":                        "anthropic/claude-3-opus-20240229",
    "Claude · 3 Haiku":                       "anthropic/claude-3-haiku-20240307",

    "── 🔴 DEEPSEEK  (Paid · platform.deepseek.com) ─────────": None,
    "Deepseek · V3 Chat":                     "deepseek/deepseek-chat",
    "Deepseek · R1 Reasoning":                "deepseek/deepseek-reasoner",

    "── 🔴 MISTRAL AI Paid  (console.mistral.ai) ────────────": None,
    "Mistral · Large":                        "mistral/mistral-large-latest",
    "Mistral · Medium":                       "mistral/mistral-medium-latest",

    "── 🔴 OPENROUTER Paid  (openrouter.ai) ─────────────────": None,
    "OpenRouter · GPT-4o":                    "openrouter/openai/gpt-4o",
    "OpenRouter · Claude 3.5 Sonnet":         "openrouter/anthropic/claude-3.5-sonnet",
    "OpenRouter · Gemini 1.5 Pro":            "openrouter/google/gemini-pro-1.5",
    "OpenRouter · Llama 3.1 405B":            "openrouter/meta-llama/llama-3.1-405b-instruct",
}


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────

def get_selectable_models(saved_keys: dict = None) -> dict:
    """
    If called with no args (or None): return all real models from registry.
    If called with saved_keys dict: return models for providers with working keys.
    """
    if saved_keys is None:
        # Original behaviour — return full registry minus section headers
        return {k: v for k, v in ALL_MODELS.items() if v is not None}

    # New behaviour — filter by working provider keys
    MODEL_MAP = {
        "GROQ": [
            {"model_id": "groq/llama-3.3-70b-versatile",  "model_name": "llama-3.3-70b"},
            {"model_id": "groq/llama-3.1-8b-instant",     "model_name": "llama-3.1-8b"},
            {"model_id": "groq/compound-beta",             "model_name": "compound-beta"},
        ],
        "MISTRAL": [
            {"model_id": "mistral/open-mistral-7b",        "model_name": "open-mistral-7b"},
            {"model_id": "mistral/mistral-small-latest",   "model_name": "mistral-small"},
        ],
        "GEMINI": [
            {"model_id": "gemini/gemini-1.5-flash",        "model_name": "gemini-1.5-flash"},
            {"model_id": "gemini/gemini-1.5-pro",          "model_name": "gemini-1.5-pro"},
        ],
        "OPENAI": [
            {"model_id": "gpt-4o-mini",                    "model_name": "gpt-4o-mini"},
            {"model_id": "gpt-4o",                         "model_name": "gpt-4o"},
        ],
        "ANTHROPIC": [
            {"model_id": "claude-3-5-haiku-20241022",      "model_name": "claude-3-5-haiku"},
            {"model_id": "claude-3-5-sonnet-20241022",     "model_name": "claude-3-5-sonnet"},
        ],
        "COHERE": [
            {"model_id": "cohere/command-r",               "model_name": "command-r"},
        ],
        "CEREBRAS": [
            {"model_id": "cerebras/llama3.3-70b",          "model_name": "cerebras-llama3.3-70b"},
        ],
        "DEEPSEEK": [
            {"model_id": "deepseek/deepseek-chat",         "model_name": "deepseek-chat"},
        ],
    }
    models = []
    for provider, data in saved_keys.items():
        if data.get("status") == "WORKING" and provider in MODEL_MAP:
            models.extend(MODEL_MAP[provider])
    return models


def get_models_by_tier() -> dict:
    """Return models split into free / limited / paid groups"""
    selectable = {k: v for k, v in ALL_MODELS.items() if v is not None}
    free_prefixes = [
        "groq/", "mistral/open-", "mistral/codestral",
        "cerebras/", "openrouter/meta-llama/llama-3",
        "openrouter/google/gemma", "openrouter/mistralai/mistral-7b",
        "openrouter/microsoft/phi", "openrouter/qwen/qwen-2-7b",
        "cohere/command-r", "cohere/command-light",
        "together_ai/", "fireworks_ai/", "huggingface/",
    ]
    limited_prefixes = ["gemini/", "perplexity/", "ai21/", "nvidia_nim/"]

    free, limited, paid = {}, {}, {}
    for name, mid in selectable.items():
        if any(mid.startswith(p) for p in free_prefixes):
            free[name]    = mid
        elif any(mid.startswith(p) for p in limited_prefixes):
            limited[name] = mid
        else:
            paid[name]    = mid
    return {"free": free, "limited": limited, "paid": paid}


def update_llm_key_status(provider: str, status: str):
    """Update the working/failed status of an LLM provider key in the DB"""
    import sqlite3
    from datetime import datetime as _dt
    try:
        from config.settings_manager import DB_PATH
        conn = sqlite3.connect(DB_PATH)
        cur  = conn.cursor()
        cur.execute(
            "UPDATE llm_keys SET status=?, updated_at=? WHERE provider=?",
            (status, _dt.now().isoformat(), provider)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"update_llm_key_status error: {e}")


def get_provider_from_model(model_id: str) -> str:
    """Extract provider name from model ID"""
    mapping = {
        "groq/":          "GROQ",
        "mistral/":       "MISTRAL",
        "cerebras/":      "CEREBRAS",
        "openrouter/":    "OPENROUTER",
        "cohere/":        "COHERE",
        "together_ai/":   "TOGETHER",
        "fireworks_ai/":  "FIREWORKS",
        "huggingface/":   "HUGGINGFACE",
        "gemini/":        "GEMINI",
        "perplexity/":    "PERPLEXITY",
        "ai21/":          "AI21",
        "nvidia_nim/":    "NVIDIA",
        "anthropic/":     "ANTHROPIC",
        "deepseek/":      "DEEPSEEK",
    }
    for prefix, provider in mapping.items():
        if model_id.startswith(prefix):
            return provider
    if model_id.startswith(("gpt", "o1", "o3")):
        return "OPENAI"
    return "UNKNOWN"


# Confirmed working Groq models as safe default
DEFAULT_JUDGE_MODELS = [
    "groq/llama-3.3-70b-versatile",
    "groq/llama-3.1-8b-instant",
    "groq/meta-llama/llama-4-scout-17b-16e-instruct",
    "groq/meta-llama/llama-4-maverick-17b-128e-instruct",
    "groq/compound-beta",
    "groq/compound-beta-mini",
]

# Backwards compatibility
SUPPORTED_MODELS = {k: v for k, v in ALL_MODELS.items() if v is not None}


# ─────────────────────────────────────────────────────────────
# API KEY MANAGEMENT
# ─────────────────────────────────────────────────────────────

def set_api_keys(keys: dict):
    """Save API keys to both database and environment"""
    try:
        from config.settings_manager import save_llm_key
        save_to_db = True
    except Exception:
        save_to_db = False

    provider_map = {
        "GROQ_API_KEY":        ("GROQ",        "GROQ_API_KEY"),
        "MISTRAL_API_KEY":     ("MISTRAL",      "MISTRAL_API_KEY"),
        "CEREBRAS_API_KEY":    ("CEREBRAS",     "CEREBRAS_API_KEY"),
        "OPENROUTER_API_KEY":  ("OPENROUTER",   "OPENROUTER_API_KEY"),
        "COHERE_API_KEY":      ("COHERE",       "COHERE_API_KEY"),
        "TOGETHER_API_KEY":    ("TOGETHER",     "TOGETHERAI_API_KEY"),
        "FIREWORKS_API_KEY":   ("FIREWORKS",    "FIREWORKS_AI_API_KEY"),
        "HUGGINGFACE_API_KEY": ("HUGGINGFACE",  "HUGGINGFACE_API_KEY"),
        "GEMINI_API_KEY":      ("GEMINI",       "GEMINI_API_KEY"),
        "PERPLEXITY_API_KEY":  ("PERPLEXITY",   "PERPLEXITYAI_API_KEY"),
        "AI21_API_KEY":        ("AI21",         "AI21_API_KEY"),
        "NVIDIA_API_KEY":      ("NVIDIA",       "NVIDIA_NIM_API_KEY"),
        "OPENAI_API_KEY":      ("OPENAI",       "OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY":   ("ANTHROPIC",    "ANTHROPIC_API_KEY"),
        "DEEPSEEK_API_KEY":    ("DEEPSEEK",     "DEEPSEEK_API_KEY"),
    }
    for input_key, value in keys.items():
        if value and value.strip():
            if input_key in provider_map:
                provider, env_key = provider_map[input_key]
                os.environ[env_key] = value.strip()
                if save_to_db:
                    save_llm_key(provider, value.strip())


# ─────────────────────────────────────────────────────────────
# CORE LLM CALL
# ─────────────────────────────────────────────────────────────

def get_llm_response(prompt, model="groq/llama-3.3-70b-versatile",
                     system_prompt=None, max_tokens=2000):
    """Send a prompt to any LLM and get a response"""
    try:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = litellm.completion(
            model=model,
            messages=messages,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content, None
    except Exception as e:
        return None, f"LLM Error ({model}): {str(e)}"


# ─────────────────────────────────────────────────────────────
# SINGLE MODEL JUDGE
# ─────────────────────────────────────────────────────────────

def llm_judge(test_name, expected_result, actual_result,
              model="groq/llama-3.3-70b-versatile"):
    """Single LLM-as-Judge — returns PASS or FAIL with reason"""
    judge_prompt = f"""
You are an expert Salesforce Test Automation Judge.

Test Name: {test_name}
Expected Result: {expected_result}
Actual Result: {actual_result}

Compare carefully. Consider partial matches and semantic equivalence.
Respond in EXACTLY this format and nothing else:

STATUS: PASS
REASON: One sentence explanation.
"""
    response, error = get_llm_response(judge_prompt, model=model)
    if error:
        return {"status": "ERROR", "reason": error, "model": model}

    status = "UNKNOWN"
    reason = "Could not parse response"
    for line in response.strip().split("\n"):
        if line.startswith("STATUS:"):
            status = line.replace("STATUS:", "").strip()
        elif line.startswith("REASON:"):
            reason = line.replace("REASON:", "").strip()

    return {"status": status, "reason": reason, "model": model}


# ─────────────────────────────────────────────────────────────
# AUTO-HEAL — SKIP DEAD MODELS
# ─────────────────────────────────────────────────────────────

def get_working_models(models: list) -> list:
    """Test each model and skip any that are decommissioned"""
    working = []
    for model in models:
        try:
            litellm.completion(
                model=model,
                messages=[{"role": "user", "content": "OK"}],
                max_tokens=3
            )
            working.append(model)
        except Exception as e:
            err = str(e).lower()
            if "decommissioned" in err or "not found" in err or "404" in err:
                print(f"Skipping decommissioned model: {model}")
            else:
                working.append(model)
    return working if working else models


def _get_available_models() -> list:
    """Return models whose API keys are set in environment"""
    available = []
    key_model_map = {
        "GROQ_API_KEY": [
            "groq/llama-3.3-70b-versatile",
            "groq/llama-3.1-8b-instant",
        ],
        "MISTRAL_API_KEY":      ["mistral/mistral-small-latest"],
        "CEREBRAS_API_KEY":     ["cerebras/llama3.3-70b"],
        "OPENROUTER_API_KEY":   ["openrouter/meta-llama/llama-3.3-70b-instruct:free"],
        "COHERE_API_KEY":       ["cohere/command-r"],
        "GEMINI_API_KEY":       ["gemini/gemini-1.5-flash"],
        "OPENAI_API_KEY":       ["gpt-4o-mini"],
        "ANTHROPIC_API_KEY":    ["anthropic/claude-3-haiku-20240307"],
        "DEEPSEEK_API_KEY":     ["deepseek/deepseek-chat"],
        "TOGETHERAI_API_KEY":   ["together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo"],
        "FIREWORKS_AI_API_KEY": ["fireworks_ai/accounts/fireworks/models/llama-v3p3-70b-instruct"],
    }
    for env_key, models in key_model_map.items():
        if os.getenv(env_key):
            available.extend(models)
    return available


# ─────────────────────────────────────────────────────────────
# MULTI-MODEL JUDGE WITH CONFIDENCE SCORING
# ─────────────────────────────────────────────────────────────

def multi_model_judge(test_name, expected_result, actual_result,
                      models: list = None):
    """
    Judge a test using multiple LLM models simultaneously.
    Calculates confidence score based on how many models agree.
    """
    try:
        from config.settings_manager import get_selected_judge_models
        if not models:
            db_models = get_selected_judge_models()
            models    = db_models if db_models else _get_available_models()
    except Exception:
        if not models:
            models = _get_available_models()

    if not models:
        models = ["groq/llama-3.3-70b-versatile"]

    individual_results = []
    pass_count  = 0
    fail_count  = 0
    error_count = 0

    for model in models:
        result = llm_judge(test_name, expected_result, actual_result, model)
        individual_results.append(result)
        if   result["status"] == "PASS":  pass_count  += 1
        elif result["status"] == "FAIL":  fail_count  += 1
        else:                             error_count += 1

    total_valid  = pass_count + fail_count
    total_models = len(models)

    if total_valid == 0:
        confidence   = 0
        final_status = "ERROR"
        consensus    = "All models errored"
    elif pass_count >= fail_count:
        final_status = "PASS"
        confidence   = round((pass_count / total_valid) * 100, 1)
        consensus    = ("Unanimous PASS" if confidence == 100 else
                        "Strong PASS"    if confidence >= 75  else
                        "Weak PASS")
    else:
        final_status = "FAIL"
        confidence   = round((fail_count / total_valid) * 100, 1)
        consensus    = ("Unanimous FAIL" if confidence == 100 else
                        "Strong FAIL"    if confidence >= 75  else
                        "Weak FAIL")

    return {
        "final_status":       final_status,
        "confidence":         confidence,
        "pass_count":         pass_count,
        "fail_count":         fail_count,
        "error_count":        error_count,
        "total_models":       total_models,
        "consensus":          consensus,
        "individual_results": individual_results,
        "summary": (f"{pass_count} of {total_models} say PASS, "
                    f"{fail_count} say FAIL, "
                    f"{error_count} errored "
                    f"-> {confidence}% confidence")
    }


# ─────────────────────────────────────────────────────────────
# TEST DATA GENERATION
# ─────────────────────────────────────────────────────────────

def generate_test_data(object_name, fields, context="",
                       model="groq/llama-3.3-70b-versatile"):
    prompt = f"""Generate realistic test data for Salesforce {object_name}.
Fields needed: {', '.join(fields)}
Context: {context or 'Standard test scenario'}
Rules: use realistic but fake data, @testcompany.com emails, 555-XXXX phones.
Return ONLY a valid JSON object. No markdown. No explanation."""
    response, error = get_llm_response(prompt, model=model)
    if error:
        return {}, error
    try:
        import json
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean), None
    except Exception as e:
        return {}, f"Parse error: {str(e)}"


# ─────────────────────────────────────────────────────────────
# PROMPT TO TEST STEPS
# ─────────────────────────────────────────────────────────────

def parse_prompt_to_test_steps(user_prompt,
                                model="groq/llama-3.3-70b-versatile"):
    system = "You are a Salesforce test expert. Return ONLY valid JSON array."
    prompt = f"""Convert this to structured test steps: "{user_prompt}"
Each step needs: step_number, action (navigate/click/type/verify/api_call/soql_query/agent_message),
target, input_data (null if none), expected_outcome.
Return a JSON array only."""
    response, error = get_llm_response(prompt, model=model, system_prompt=system)
    if error:
        return [], error
    try:
        import json
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean), None
    except Exception as e:
        return [], f"Parse error: {str(e)}"


# ─────────────────────────────────────────────────────────────
# QUICK TEST
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Testing Multi-Model LLM Judge with 6 confirmed live Groq models\n")

    result = multi_model_judge(
        test_name="Account Creation Test",
        expected_result="Account named Test Corp created successfully",
        actual_result="Record saved: Account Test Corp was created with ID 001XX000003GYn2",
        models=DEFAULT_JUDGE_MODELS
    )

    print(f"Final Status:  {result['final_status']}")
    print(f"Confidence:    {result['confidence']}%")
    print(f"Consensus:     {result['consensus']}")
    print(f"Summary:       {result['summary']}")
    print(f"\nIndividual Results:")
    for r in result["individual_results"]:
        icon = ("PASS"  if r["status"] == "PASS"  else
                "FAIL"  if r["status"] == "FAIL"  else "ERROR")
        print(f"  [{icon}] {r['model']}")
        print(f"         {r['reason']}")