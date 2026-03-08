"""
bedrock_test_engine.py
Test execution engine for Amazon Bedrock AgentCore agents.
Supports: chat, conversation flows, intent validation,
          response scoring, IVR simulation, regression suites.
"""

import json
import time
import uuid
from datetime import datetime
from connectors.bedrock_connector import (
    invoke_bedrock_agent, run_conversation_flow,
    test_lex_bot
)
from connectors.llm_connector import get_llm_response


def score_agent_response(prompt: str, response: str,
                          expected: str,
                          llm_model: str) -> dict:
    """
    Use an LLM judge to score a Bedrock agent response.
    Returns score, pass/fail, and reasoning.
    """
    judge_prompt = (
        "You are an AI quality evaluator for enterprise AI agents.\n\n"
        "Evaluate this AI agent response:\n\n"
        f"User Prompt: {prompt}\n"
        f"Expected Behavior: {expected}\n"
        f"Agent Response: {response}\n\n"
        "Score the response on:\n"
        "1. Relevance (0-10): Does it address the prompt?\n"
        "2. Accuracy (0-10): Is the information correct?\n"
        "3. Completeness (0-10): Is it sufficiently detailed?\n"
        "4. Safety (0-10): Is it appropriate and safe?\n\n"
        "Return ONLY valid JSON:\n"
        '{"verdict":"PASS","relevance":8,"accuracy":9,'
        '"completeness":7,"safety":10,"overall_score":8.5,'
        '"reasoning":"Brief explanation"}'
    )

    resp, err = get_llm_response(
        judge_prompt, model=llm_model, max_tokens=300
    )
    if err or not resp:
        return {
            "verdict": "ERROR", "overall_score": 0,
            "reasoning": err or "No response"
        }

    try:
        clean = (
            resp.strip()
            .replace("```json","")
            .replace("```","")
            .strip()
        )
        result = json.loads(clean)
        return result
    except Exception:
        return {
            "verdict": "ERROR", "overall_score": 0,
            "reasoning": "Could not parse judge response"
        }


def run_chat_test(bedrock_config: dict, test_case: dict,
                   llm_model: str) -> dict:
    """
    Run a single chat test against a Bedrock agent.
    """
    start      = time.time()
    session_id = f"test-{uuid.uuid4().hex[:8]}"
    prompt     = test_case.get("input_data","")
    expected   = test_case.get("expected_output","")

    result, err = invoke_bedrock_agent(
        access_key=bedrock_config["access_key"],
        secret_key=bedrock_config["secret_key"],
        region=bedrock_config["region"],
        agent_id=bedrock_config["agent_id"],
        agent_alias_id=bedrock_config.get("agent_alias_id",""),
        session_id=session_id,
        prompt=prompt
    )

    duration = round(time.time() - start, 2)

    if err or not result:
        return {
            "test_id":     test_case.get("test_id",""),
            "test_name":   test_case.get("test_name",""),
            "status":      "ERROR",
            "error":       err,
            "duration_s":  duration,
            "prompt":      prompt,
            "response":    "",
            "score":       {},
            "timestamp":   datetime.now().isoformat()
        }

    response_text = result.get("response","")

    # Score the response
    score = score_agent_response(
        prompt, response_text, expected, llm_model
    )

    verdict = score.get("verdict","FAIL")
    overall = score.get("overall_score", 0)

    # PASS if score >= 7
    if isinstance(overall, (int,float)) and overall >= 7:
        verdict = "PASS"
    elif isinstance(overall, (int,float)) and overall < 5:
        verdict = "FAIL"

    return {
        "test_id":    test_case.get("test_id",""),
        "test_name":  test_case.get("test_name",""),
        "status":     verdict,
        "prompt":     prompt,
        "response":   response_text,
        "expected":   expected,
        "score":      score,
        "overall_score": overall,
        "duration_s": duration,
        "session_id": session_id,
        "timestamp":  datetime.now().isoformat(),
        "error":      ""
    }


def run_conversation_test(bedrock_config: dict,
                           test_case: dict,
                           llm_model: str) -> dict:
    """
    Run a multi-turn conversation test.
    test_case["input_data"] should be a JSON array of turns:
    [{"role":"user","content":"Hi"},...]
    """
    start    = time.time()
    raw_data = test_case.get("input_data","")

    try:
        if isinstance(raw_data, str):
            conversation = json.loads(raw_data)
        else:
            conversation = raw_data
    except Exception:
        conversation = [{"role":"user","content": raw_data}]

    turns, err = run_conversation_flow(
        access_key=bedrock_config["access_key"],
        secret_key=bedrock_config["secret_key"],
        region=bedrock_config["region"],
        agent_id=bedrock_config["agent_id"],
        agent_alias_id=bedrock_config.get("agent_alias_id",""),
        conversation=conversation
    )

    duration = round(time.time() - start, 2)

    if err:
        return {
            "test_id":   test_case.get("test_id",""),
            "test_name": test_case.get("test_name",""),
            "status":    "ERROR",
            "error":     err,
            "duration_s": duration,
            "turns":     [],
            "timestamp": datetime.now().isoformat()
        }

    successful_turns = sum(1 for t in turns if t.get("success"))
    total_turns      = len(turns)
    pass_rate        = (
        successful_turns / total_turns
        if total_turns else 0
    )

    # Score last response if expected outcome given
    expected    = test_case.get("expected_output","")
    last_resp   = turns[-1].get("response","") if turns else ""
    last_prompt = turns[-1].get("prompt","") if turns else ""

    score = {}
    if expected and last_resp:
        score = score_agent_response(
            last_prompt, last_resp, expected, llm_model
        )

    verdict = "PASS" if pass_rate >= 0.8 else "FAIL"
    if score.get("verdict") == "FAIL":
        verdict = "FAIL"

    return {
        "test_id":       test_case.get("test_id",""),
        "test_name":     test_case.get("test_name",""),
        "status":        verdict,
        "total_turns":   total_turns,
        "successful_turns": successful_turns,
        "pass_rate":     round(pass_rate*100,1),
        "turns":         turns,
        "final_score":   score,
        "duration_s":    duration,
        "timestamp":     datetime.now().isoformat(),
        "error":         ""
    }


def run_intent_validation_test(bedrock_config: dict,
                                test_case: dict,
                                llm_model: str) -> dict:
    """
    Validate that the agent correctly identifies intents.
    Uses Lex if configured, otherwise evaluates via LLM judge.
    """
    start  = time.time()
    prompt = test_case.get("input_data","")

    # Try Lex first if configured
    if bedrock_config.get("bot_id"):
        session_id = f"intent-test-{uuid.uuid4().hex[:8]}"
        result, err = test_lex_bot(
            access_key=bedrock_config["access_key"],
            secret_key=bedrock_config["secret_key"],
            region=bedrock_config["region"],
            bot_id=bedrock_config["bot_id"],
            bot_alias_id=bedrock_config.get("bot_alias_id",""),
            locale_id=bedrock_config.get("locale_id","en_US"),
            session_id=session_id,
            text=prompt
        )
        if result:
            expected_intent = test_case.get(
                "expected_intent",
                test_case.get("expected_output","")
            )
            detected_intent  = result.get("intent","")
            confidence_score = result.get("confidence",0)
            matched          = (
                expected_intent.lower() in
                detected_intent.lower()
            ) if expected_intent else True

            return {
                "test_id":         test_case.get("test_id",""),
                "test_name":       test_case.get("test_name",""),
                "status":          "PASS" if matched else "FAIL",
                "prompt":          prompt,
                "expected_intent": expected_intent,
                "detected_intent": detected_intent,
                "confidence":      confidence_score,
                "matched":         matched,
                "duration_s":      round(time.time()-start, 2),
                "timestamp":       datetime.now().isoformat(),
                "error":           err or ""
            }

    # Fallback — use Bedrock agent + LLM judge
    agent_result, err = invoke_bedrock_agent(
        access_key=bedrock_config["access_key"],
        secret_key=bedrock_config["secret_key"],
        region=bedrock_config["region"],
        agent_id=bedrock_config["agent_id"],
        agent_alias_id=bedrock_config.get("agent_alias_id",""),
        session_id=f"intent-{uuid.uuid4().hex[:8]}",
        prompt=prompt
    )

    response_text = (
        agent_result.get("response","") if agent_result else ""
    )
    expected = test_case.get("expected_output","")

    score   = score_agent_response(
        prompt, response_text, expected, llm_model
    )
    verdict = score.get("verdict","FAIL")

    return {
        "test_id":    test_case.get("test_id",""),
        "test_name":  test_case.get("test_name",""),
        "status":     verdict,
        "prompt":     prompt,
        "response":   response_text,
        "score":      score,
        "duration_s": round(time.time()-start,2),
        "timestamp":  datetime.now().isoformat(),
        "error":      err or ""
    }


def run_regression_suite(bedrock_config: dict,
                          test_cases: list,
                          llm_model: str,
                          progress_callback=None) -> list:
    """
    Run a full regression suite of Bedrock agent tests.
    """
    results = []

    for i, tc in enumerate(test_cases):
        if progress_callback:
            progress_callback(
                i, len(test_cases),
                tc.get("test_name","")
            )

        test_type = tc.get("test_type","chat").lower()

        if "conversation" in test_type or "flow" in test_type:
            result = run_conversation_test(
                bedrock_config, tc, llm_model
            )
        elif "intent" in test_type:
            result = run_intent_validation_test(
                bedrock_config, tc, llm_model
            )
        else:
            result = run_chat_test(
                bedrock_config, tc, llm_model
            )

        results.append(result)
        time.sleep(0.3)  # Rate limit protection

    return results