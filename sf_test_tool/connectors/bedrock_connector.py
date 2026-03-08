"""
bedrock_connector.py
Amazon Bedrock AgentCore connector.
Supports: Bedrock Agents, Amazon Lex, Amazon Connect,
          Transcribe, Polly, Lambda, DynamoDB.
"""

import json
import time
import boto3
from datetime import datetime
from typing import Optional


def get_bedrock_client(access_key: str, secret_key: str,
                       region: str, service: str = "bedrock-agent-runtime"):
    """Create an authenticated boto3 client for any AWS service"""
    try:
        client = boto3.client(
            service,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        return client, None
    except Exception as e:
        return None, str(e)


def test_bedrock_connection(access_key: str, secret_key: str,
                             region: str) -> tuple:
    """Test AWS credentials by listing Bedrock agents"""
    try:
        client = boto3.client(
            "bedrock-agent",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        resp = client.list_agents(maxResults=5)
        agents = resp.get("agentSummaries", [])
        return {
            "connected": True,
            "region":    region,
            "agents":    agents,
            "agent_count": len(agents),
            "message": (
                f"Connected to AWS {region}. "
                f"Found {len(agents)} Bedrock agent(s)."
            )
        }, None
    except Exception as e:
        return None, f"AWS connection failed: {str(e)}"


def invoke_bedrock_agent(access_key: str, secret_key: str,
                          region: str, agent_id: str,
                          agent_alias_id: str, session_id: str,
                          prompt: str) -> tuple:
    """
    Invoke a Bedrock AgentCore agent with a prompt.
    Returns the agent's response text.
    """
    try:
        client = boto3.client(
            "bedrock-agent-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=prompt
        )
        # Stream the response
        full_response = ""
        for event in response.get("completion", []):
            chunk = event.get("chunk", {})
            if "bytes" in chunk:
                full_response += chunk["bytes"].decode("utf-8")

        return {
            "response":    full_response,
            "session_id":  session_id,
            "agent_id":    agent_id,
            "prompt":      prompt,
            "timestamp":   datetime.now().isoformat()
        }, None
    except Exception as e:
        return None, f"Agent invocation error: {str(e)}"


def run_conversation_flow(access_key: str, secret_key: str,
                           region: str, agent_id: str,
                           agent_alias_id: str,
                           conversation: list) -> tuple:
    """
    Run a multi-turn conversation flow against a Bedrock agent.

    conversation = [
        {"role": "user", "content": "Hello"},
        {"role": "user", "content": "What is my balance?"},
    ]
    Returns list of turn results.
    """
    import uuid
    session_id = f"test-{uuid.uuid4().hex[:12]}"
    results    = []

    for i, turn in enumerate(conversation):
        if turn.get("role") != "user":
            continue

        prompt   = turn.get("content","")
        t_start  = time.time()

        result, err = invoke_bedrock_agent(
            access_key, secret_key, region,
            agent_id, agent_alias_id, session_id, prompt
        )

        elapsed = round(time.time() - t_start, 2)

        results.append({
            "turn":       i + 1,
            "prompt":     prompt,
            "response":   result.get("response","") if result else "",
            "error":      err,
            "duration_s": elapsed,
            "success":    result is not None
        })

        # Brief pause between turns
        time.sleep(0.5)

    return results, None


def list_bedrock_agents(access_key: str, secret_key: str,
                         region: str) -> tuple:
    """List all Bedrock agents in the account"""
    try:
        client = boto3.client(
            "bedrock-agent",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        resp   = client.list_agents(maxResults=100)
        agents = resp.get("agentSummaries", [])
        return agents, None
    except Exception as e:
        return [], str(e)


def get_agent_details(access_key: str, secret_key: str,
                       region: str, agent_id: str) -> tuple:
    """Get details of a specific Bedrock agent"""
    try:
        client = boto3.client(
            "bedrock-agent",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        resp  = client.get_agent(agentId=agent_id)
        agent = resp.get("agent", {})
        return agent, None
    except Exception as e:
        return None, str(e)


def invoke_lambda(access_key: str, secret_key: str,
                   region: str, function_name: str,
                   payload: dict) -> tuple:
    """Invoke an AWS Lambda function for test validation"""
    try:
        client = boto3.client(
            "lambda",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        response = client.invoke(
            FunctionName=function_name,
            InvocationType="RequestResponse",
            Payload=json.dumps(payload)
        )
        result = json.loads(
            response["Payload"].read().decode("utf-8")
        )
        return result, None
    except Exception as e:
        return None, str(e)


def test_lex_bot(access_key: str, secret_key: str,
                  region: str, bot_id: str,
                  bot_alias_id: str, locale_id: str,
                  session_id: str, text: str) -> tuple:
    """Test an Amazon Lex V2 bot with a text input"""
    try:
        client = boto3.client(
            "lexv2-runtime",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        response = client.recognize_text(
            botId=bot_id,
            botAliasId=bot_alias_id,
            localeId=locale_id,
            sessionId=session_id,
            text=text
        )
        messages = [
            m.get("content","")
            for m in response.get("messages",[])
        ]
        intent      = response.get("sessionState",{}).get(
            "intent",{}
        )
        intent_name = intent.get("name","")
        confidence  = intent.get("nluConfidence",{}).get(
            "score", 0
        )
        return {
            "messages":    messages,
            "intent":      intent_name,
            "confidence":  confidence,
            "session_id":  session_id,
            "session_state": response.get("sessionState",{})
        }, None
    except Exception as e:
        return None, str(e)


def simulate_connect_contact_flow(access_key: str, secret_key: str,
                                   region: str, instance_id: str,
                                   contact_flow_id: str,
                                   test_params: dict) -> tuple:
    """
    Simulate an Amazon Connect contact flow test.
    Uses the Connect test API to simulate IVR interactions.
    """
    try:
        client = boto3.client(
            "connect",
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        # Start a test contact flow execution
        response = client.start_contact_evaluation(
            InstanceId=instance_id,
            ExistingContactId=test_params.get("contact_id",""),
            EvaluationFormId=contact_flow_id
        )
        return {
            "evaluation_id": response.get(
                "EvaluationId",""
            ),
            "evaluation_arn": response.get(
                "EvaluationArn",""
            ),
            "status": "started"
        }, None
    except Exception as e:
        return None, f"Connect flow test error: {str(e)}"