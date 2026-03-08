import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────
# AGENTFORCE - CHAT AGENT
# ─────────────────────────────────────────

def test_chat_agent(sf, bot_id, message, session_id=None):
    """
    Send a message to an Agentforce/Einstein Chat bot and get the response.
    sf = connected Salesforce instance
    bot_id = your bot's API name or ID from Salesforce Setup
    message = the test message to send
    """
    try:
        headers = {
            "Authorization": f"Bearer {sf.session_id}",
            "Content-Type": "application/json"
        }

        # Start or continue a session
        if not session_id:
            session_url = f"{sf.sf_instance}/services/data/v59.0/einstein/ai-agent/sessions"
            session_payload = {
                "externalSessionKey": f"test_session_{int(__import__('time').time())}",
                "instanceConfig": {
                    "endpoint": sf.sf_instance
                },
                "streamingCapabilities": {
                    "chunkTypes": ["Text"]
                }
            }
            session_resp = requests.post(session_url, headers=headers, json=session_payload)
            session_data = session_resp.json()
            session_id = session_data.get("sessionId", "unknown")

        # Send message to agent
        message_url = f"{sf.sf_instance}/services/data/v59.0/einstein/ai-agent/sessions/{session_id}/messages"
        message_payload = {
            "message": {
                "role": "user",
                "content": [{"type": "text", "text": message}]
            },
            "variables": []
        }

        msg_resp = requests.post(message_url, headers=headers, json=message_payload)
        response_data = msg_resp.json()

        # Extract text response from agent
        agent_response = ""
        messages = response_data.get("messages", [])
        for msg in messages:
            if msg.get("role") == "assistant":
                for content in msg.get("content", []):
                    if content.get("type") == "text":
                        agent_response += content.get("text", "")

        return {
            "session_id": session_id,
            "user_message": message,
            "agent_response": agent_response,
            "raw_response": response_data,
            "success": bool(agent_response)
        }, None

    except Exception as e:
        return None, f"Chat Agent Error: {str(e)}"


# ─────────────────────────────────────────
# AGENTFORCE - EMAIL AGENT
# ─────────────────────────────────────────

def test_email_agent(sf, case_email_service_address, from_email, subject, body):
    """
    Test an Email Agent by simulating an inbound email via Salesforce Email-to-Case.
    The agent should auto-respond or create a Case.
    """
    try:
        headers = {
            "Authorization": f"Bearer {sf.session_id}",
            "Content-Type": "application/json"
        }

        # Simulate inbound email by creating an EmailMessage record
        email_payload = {
            "Subject": subject,
            "FromAddress": from_email,
            "ToAddress": case_email_service_address,
            "TextBody": body,
            "HtmlBody": f"<p>{body}</p>",
            "Incoming": True,
            "Status": "0"
        }

        url = f"{sf.sf_instance}/services/data/v59.0/sobjects/EmailMessage/"
        response = requests.post(url, headers=headers, json=email_payload)

        if response.status_code in [200, 201]:
            email_id = response.json().get("id")
            # Check if a Case was auto-created
            import time
            time.sleep(3)  # Wait for automation to trigger

            case_check = sf.query(
                f"SELECT Id, CaseNumber, Subject, Status FROM Case "
                f"WHERE Subject = '{subject}' ORDER BY CreatedDate DESC LIMIT 1"
            )
            cases = case_check.get("records", [])

            return {
                "email_sent": True,
                "email_id": email_id,
                "case_created": bool(cases),
                "case_details": cases[0] if cases else None
            }, None
        else:
            return None, f"Email simulation failed: {response.text}"

    except Exception as e:
        return None, f"Email Agent Error: {str(e)}"


# ─────────────────────────────────────────
# AGENTFORCE - SMS AGENT
# ─────────────────────────────────────────

def test_sms_agent(sf, messaging_channel_id, phone_number, message_text):
    """
    Test an SMS/Messaging Agent via Salesforce Digital Engagement API.
    """
    try:
        headers = {
            "Authorization": f"Bearer {sf.session_id}",
            "Content-Type": "application/json"
        }

        # Create inbound messaging session
        session_url = f"{sf.sf_instance}/services/data/v59.0/messaging/sessions"
        session_payload = {
            "MessagingChannelId": messaging_channel_id,
            "MessagingEndUserId": phone_number,
        }

        session_resp = requests.post(session_url, headers=headers, json=session_payload)
        session_data = session_resp.json()
        conversation_id = session_data.get("Id") or session_data.get("id")

        # Send inbound test message
        msg_url = f"{sf.sf_instance}/services/data/v59.0/messaging/sessions/{conversation_id}/messages"
        msg_payload = {
            "text": message_text,
            "direction": "Inbound"
        }

        msg_resp = requests.post(msg_url, headers=headers, json=msg_payload)

        return {
            "conversation_id": conversation_id,
            "message_sent": message_text,
            "api_response": msg_resp.json(),
            "success": msg_resp.status_code in [200, 201]
        }, None

    except Exception as e:
        return None, f"SMS Agent Error: {str(e)}"


# ─────────────────────────────────────────
# AGENTFORCE - SLACK AGENT
# ─────────────────────────────────────────

def test_slack_agent(slack_bot_token, channel_id, message_text):
    """
    Test an Agentforce Slack Agent by sending a message to a Slack channel
    and capturing the bot's response.
    slack_bot_token = your Slack Bot OAuth token (xoxb-...)
    channel_id = Slack channel ID where your bot is present
    """
    try:
        headers = {
            "Authorization": f"Bearer {slack_bot_token}",
            "Content-Type": "application/json"
        }

        # Send message to Slack channel
        post_url = "https://slack.com/api/chat.postMessage"
        payload = {
            "channel": channel_id,
            "text": message_text
        }
        response = requests.post(post_url, headers=headers, json=payload)
        response_data = response.json()

        if response_data.get("ok"):
            message_ts = response_data["message"]["ts"]

            # Wait briefly for bot to respond
            import time
            time.sleep(5)

            # Fetch conversation history to capture bot response
            history_url = "https://slack.com/api/conversations.history"
            params = {
                "channel": channel_id,
                "oldest": message_ts,
                "limit": 10
            }
            history_resp = requests.get(history_url, headers=headers, params=params)
            history_data = history_resp.json()

            bot_messages = [
                msg["text"] for msg in history_data.get("messages", [])
                if msg.get("bot_id")
            ]

            return {
                "message_sent": message_text,
                "bot_responses": bot_messages,
                "bot_responded": bool(bot_messages),
                "latest_response": bot_messages[-1] if bot_messages else "No response"
            }, None
        else:
            return None, f"Slack API Error: {response_data.get('error')}"

    except Exception as e:
        return None, f"Slack Agent Error: {str(e)}"