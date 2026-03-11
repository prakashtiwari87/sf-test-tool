"""
agentforce_testing_engine.py — Agentforce Multi-Channel Testing Engine
Phase 3: Agentforce & Multi-Channel Testing

FEATURES:
  • Chat testing (conversational flows)
  • Email testing (case routing & responses)
  • SMS testing (text message flows)
  • Slack testing (bot interactions)
  • Multi-turn conversations
  • Intent validation
  • Entity extraction testing
  • Response quality evaluation
  • Context maintenance testing
"""

import time
import json
from typing import List, Dict, Optional, Any
from datetime import datetime

class AgentforceTestingEngine:
    """
    Comprehensive Agentforce testing across all channels.
    Supports Chat, Email, SMS, Slack with multi-turn conversations.
    """
    
    def __init__(
        self,
        sf_connection: object,
        org_domain: str,
        agent_id: Optional[str] = None
    ):
        """
        Initialize Agentforce testing engine.
        
        Args:
            sf_connection: Salesforce connection
            org_domain: Org domain
            agent_id: Optional Agentforce agent ID
        """
        self.sf = sf_connection
        self.org_domain = org_domain
        self.agent_id = agent_id
        self.conversation_history = []
    
    # ══════════════════════════════════════════════════════════
    # CHAT TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_chat_message(
        self,
        user_message: str,
        expected_intent: Optional[str] = None,
        expected_entities: Optional[List[str]] = None,
        expected_response_contains: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Test single chat message to Agentforce.
        
        Args:
            user_message: User's input message
            expected_intent: Expected intent to be detected
            expected_entities: Expected entities to be extracted
            expected_response_contains: Keywords that should be in response
            session_id: Session ID for multi-turn conversations
        
        Returns:
            Test result with response and validation
        """
        start_time = time.time()
        
        try:
            # Call Agentforce chat API
            response = self._call_agentforce_chat(
                message=user_message,
                session_id=session_id or self._generate_session_id()
            )
            
            # Store in conversation history
            self.conversation_history.append({
                "user_message": user_message,
                "agent_response": response.get("response"),
                "timestamp": datetime.now().isoformat()
            })
            
            # Validate response
            validation_results = self._validate_chat_response(
                response=response,
                expected_intent=expected_intent,
                expected_entities=expected_entities,
                expected_response_contains=expected_response_contains
            )
            
            # Determine overall status
            all_passed = all(
                v.get("passed", True) 
                for v in validation_results.values()
            )
            
            return {
                "test_type": "AGENTFORCE_CHAT",
                "channel": "chat",
                "status": "PASS" if all_passed else "FAIL",
                "user_message": user_message,
                "agent_response": response.get("response"),
                "detected_intent": response.get("intent"),
                "extracted_entities": response.get("entities", []),
                "confidence": response.get("confidence", 0),
                "validation": validation_results,
                "duration_sec": time.time() - start_time,
                "session_id": session_id
            }
        
        except Exception as e:
            return {
                "test_type": "AGENTFORCE_CHAT",
                "channel": "chat",
                "status": "ERROR",
                "user_message": user_message,
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_chat_conversation(
        self,
        conversation_flow: List[Dict],
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Test multi-turn chat conversation.
        
        Args:
            conversation_flow: List of conversation turns with expectations
                Example: [
                    {
                        "user_message": "I need help with my order",
                        "expected_intent": "order_inquiry"
                    },
                    {
                        "user_message": "Order number 12345",
                        "expected_entities": ["order_number"]
                    }
                ]
            session_id: Session ID for conversation continuity
        
        Returns:
            Conversation test results
        """
        session_id = session_id or self._generate_session_id()
        turn_results = []
        
        for i, turn in enumerate(conversation_flow):
            result = self.test_chat_message(
                user_message=turn.get("user_message"),
                expected_intent=turn.get("expected_intent"),
                expected_entities=turn.get("expected_entities"),
                expected_response_contains=turn.get("expected_response_contains"),
                session_id=session_id
            )
            
            result["turn_number"] = i + 1
            turn_results.append(result)
        
        # Overall conversation metrics
        passed_turns = sum(1 for r in turn_results if r["status"] == "PASS")
        total_turns = len(turn_results)
        
        return {
            "test_type": "AGENTFORCE_CONVERSATION",
            "channel": "chat",
            "status": "PASS" if passed_turns == total_turns else "PARTIAL" if passed_turns > 0 else "FAIL",
            "total_turns": total_turns,
            "passed_turns": passed_turns,
            "failed_turns": total_turns - passed_turns,
            "conversation_success_rate": round((passed_turns / total_turns) * 100, 1) if total_turns > 0 else 0,
            "turn_results": turn_results,
            "session_id": session_id
        }
    
    # ══════════════════════════════════════════════════════════
    # EMAIL TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_email_to_case(
        self,
        email_subject: str,
        email_body: str,
        from_address: str,
        expected_case_created: bool = True,
        expected_priority: Optional[str] = None,
        expected_category: Optional[str] = None
    ) -> Dict:
        """
        Test email-to-case functionality.
        
        Args:
            email_subject: Email subject line
            email_body: Email body content
            from_address: Sender email
            expected_case_created: Should a case be created?
            expected_priority: Expected case priority
            expected_category: Expected case category
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            # Simulate email-to-case (in production, would send actual email)
            result = self._process_email_to_case(
                subject=email_subject,
                body=email_body,
                from_email=from_address
            )
            
            # Validate results
            case_created = result.get("case_created", False)
            case_id = result.get("case_id")
            
            validations = {}
            
            # Check if case created as expected
            validations["case_created"] = {
                "expected": expected_case_created,
                "actual": case_created,
                "passed": case_created == expected_case_created
            }
            
            # If case created, validate details
            if case_created and case_id:
                case_details = self._get_case_details(case_id)
                
                if expected_priority:
                    validations["priority"] = {
                        "expected": expected_priority,
                        "actual": case_details.get("Priority"),
                        "passed": case_details.get("Priority") == expected_priority
                    }
                
                if expected_category:
                    validations["category"] = {
                        "expected": expected_category,
                        "actual": case_details.get("Category__c"),
                        "passed": case_details.get("Category__c") == expected_category
                    }
            
            all_passed = all(v.get("passed", True) for v in validations.values())
            
            return {
                "test_type": "AGENTFORCE_EMAIL",
                "channel": "email",
                "status": "PASS" if all_passed else "FAIL",
                "email_subject": email_subject,
                "from_address": from_address,
                "case_created": case_created,
                "case_id": case_id,
                "validations": validations,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "AGENTFORCE_EMAIL",
                "channel": "email",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_email_response(
        self,
        case_id: str,
        expected_response_time_minutes: Optional[int] = None,
        expected_response_contains: Optional[List[str]] = None
    ) -> Dict:
        """
        Test automated email response to case.
        
        Args:
            case_id: Case ID to check for response
            expected_response_time_minutes: Max expected response time
            expected_response_contains: Keywords in response
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            # Get case and check for email response
            case_details = self._get_case_details(case_id)
            email_response = self._get_case_email_response(case_id)
            
            validations = {}
            
            # Check if response was sent
            validations["response_sent"] = {
                "expected": True,
                "actual": email_response is not None,
                "passed": email_response is not None
            }
            
            if email_response:
                # Check response time
                if expected_response_time_minutes:
                    response_time = email_response.get("response_time_minutes", 0)
                    validations["response_time"] = {
                        "expected": f"<= {expected_response_time_minutes} min",
                        "actual": f"{response_time} min",
                        "passed": response_time <= expected_response_time_minutes
                    }
                
                # Check response content
                if expected_response_contains:
                    response_body = email_response.get("body", "")
                    contains_all = all(
                        keyword.lower() in response_body.lower()
                        for keyword in expected_response_contains
                    )
                    validations["response_content"] = {
                        "expected": f"Contains: {expected_response_contains}",
                        "actual": "All found" if contains_all else "Some missing",
                        "passed": contains_all
                    }
            
            all_passed = all(v.get("passed", True) for v in validations.values())
            
            return {
                "test_type": "AGENTFORCE_EMAIL_RESPONSE",
                "channel": "email",
                "status": "PASS" if all_passed else "FAIL",
                "case_id": case_id,
                "response_sent": email_response is not None,
                "response_body": email_response.get("body") if email_response else None,
                "validations": validations,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "AGENTFORCE_EMAIL_RESPONSE",
                "channel": "email",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    # ══════════════════════════════════════════════════════════
    # SMS TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_sms_message(
        self,
        from_number: str,
        message_body: str,
        expected_response_contains: Optional[List[str]] = None,
        expected_creates_case: bool = False
    ) -> Dict:
        """
        Test SMS message to Agentforce.
        
        Args:
            from_number: Phone number sending SMS
            message_body: SMS message content
            expected_response_contains: Keywords in response
            expected_creates_case: Should create a case?
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            # Send SMS to Agentforce
            result = self._send_sms_to_agent(
                from_number=from_number,
                body=message_body
            )
            
            validations = {}
            
            # Check response
            response_received = result.get("response_body") is not None
            validations["response_received"] = {
                "expected": True,
                "actual": response_received,
                "passed": response_received
            }
            
            # Check response content
            if response_received and expected_response_contains:
                response_body = result.get("response_body", "")
                contains_all = all(
                    keyword.lower() in response_body.lower()
                    for keyword in expected_response_contains
                )
                validations["response_content"] = {
                    "expected": f"Contains: {expected_response_contains}",
                    "actual": "All found" if contains_all else "Some missing",
                    "passed": contains_all
                }
            
            # Check case creation
            case_created = result.get("case_created", False)
            validations["case_creation"] = {
                "expected": expected_creates_case,
                "actual": case_created,
                "passed": case_created == expected_creates_case
            }
            
            all_passed = all(v.get("passed", True) for v in validations.values())
            
            return {
                "test_type": "AGENTFORCE_SMS",
                "channel": "sms",
                "status": "PASS" if all_passed else "FAIL",
                "from_number": from_number,
                "message_body": message_body,
                "response_body": result.get("response_body"),
                "case_created": case_created,
                "case_id": result.get("case_id"),
                "validations": validations,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "AGENTFORCE_SMS",
                "channel": "sms",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    # ══════════════════════════════════════════════════════════
    # SLACK TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_slack_message(
        self,
        channel: str,
        user_id: str,
        message_text: str,
        expected_bot_response: bool = True,
        expected_response_contains: Optional[List[str]] = None
    ) -> Dict:
        """
        Test Slack message to Agentforce bot.
        
        Args:
            channel: Slack channel ID
            user_id: User ID sending message
            message_text: Message content
            expected_bot_response: Should bot respond?
            expected_response_contains: Keywords in response
        
        Returns:
            Test result
        """
        start_time = time.time()
        
        try:
            # Send Slack message to bot
            result = self._send_slack_message(
                channel=channel,
                user_id=user_id,
                text=message_text
            )
            
            validations = {}
            
            # Check bot response
            bot_responded = result.get("bot_response") is not None
            validations["bot_response"] = {
                "expected": expected_bot_response,
                "actual": bot_responded,
                "passed": bot_responded == expected_bot_response
            }
            
            # Check response content
            if bot_responded and expected_response_contains:
                bot_response = result.get("bot_response", "")
                contains_all = all(
                    keyword.lower() in bot_response.lower()
                    for keyword in expected_response_contains
                )
                validations["response_content"] = {
                    "expected": f"Contains: {expected_response_contains}",
                    "actual": "All found" if contains_all else "Some missing",
                    "passed": contains_all
                }
            
            all_passed = all(v.get("passed", True) for v in validations.values())
            
            return {
                "test_type": "AGENTFORCE_SLACK",
                "channel": "slack",
                "status": "PASS" if all_passed else "FAIL",
                "slack_channel": channel,
                "user_message": message_text,
                "bot_response": result.get("bot_response"),
                "validations": validations,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "AGENTFORCE_SLACK",
                "channel": "slack",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    # ══════════════════════════════════════════════════════════
    # INTENT & ENTITY TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_intent_recognition(
        self,
        test_utterances: List[Dict]
    ) -> Dict:
        """
        Test intent recognition across multiple utterances.
        
        Args:
            test_utterances: List of {utterance, expected_intent} dicts
        
        Returns:
            Intent recognition accuracy results
        """
        results = []
        
        for item in test_utterances:
            utterance = item.get("utterance")
            expected_intent = item.get("expected_intent")
            
            # Get intent from agent
            response = self._call_agentforce_chat(utterance)
            detected_intent = response.get("intent")
            confidence = response.get("confidence", 0)
            
            passed = detected_intent == expected_intent
            
            results.append({
                "utterance": utterance,
                "expected_intent": expected_intent,
                "detected_intent": detected_intent,
                "confidence": confidence,
                "passed": passed
            })
        
        # Calculate accuracy
        total = len(results)
        correct = sum(1 for r in results if r["passed"])
        accuracy = (correct / total) * 100 if total > 0 else 0
        
        return {
            "test_type": "INTENT_RECOGNITION",
            "total_utterances": total,
            "correct": correct,
            "incorrect": total - correct,
            "accuracy": round(accuracy, 2),
            "status": "PASS" if accuracy >= 80 else "FAIL",
            "results": results
        }
    
    def test_entity_extraction(
        self,
        test_utterances: List[Dict]
    ) -> Dict:
        """
        Test entity extraction accuracy.
        
        Args:
            test_utterances: List of {utterance, expected_entities} dicts
        
        Returns:
            Entity extraction results
        """
        results = []
        
        for item in test_utterances:
            utterance = item.get("utterance")
            expected_entities = set(item.get("expected_entities", []))
            
            # Get entities from agent
            response = self._call_agentforce_chat(utterance)
            extracted_entities = set(response.get("entities", []))
            
            # Calculate metrics
            correct_entities = expected_entities & extracted_entities
            missing_entities = expected_entities - extracted_entities
            extra_entities = extracted_entities - expected_entities
            
            precision = len(correct_entities) / len(extracted_entities) if extracted_entities else 0
            recall = len(correct_entities) / len(expected_entities) if expected_entities else 0
            f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
            
            results.append({
                "utterance": utterance,
                "expected_entities": list(expected_entities),
                "extracted_entities": list(extracted_entities),
                "correct": list(correct_entities),
                "missing": list(missing_entities),
                "extra": list(extra_entities),
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "f1": round(f1, 3)
            })
        
        # Overall metrics
        avg_f1 = sum(r["f1"] for r in results) / len(results) if results else 0
        
        return {
            "test_type": "ENTITY_EXTRACTION",
            "total_utterances": len(results),
            "average_f1": round(avg_f1, 3),
            "status": "PASS" if avg_f1 >= 0.8 else "FAIL",
            "results": results
        }
    
    # ══════════════════════════════════════════════════════════
    # HELPER METHODS
    # ══════════════════════════════════════════════════════════
    
    def _call_agentforce_chat(
        self,
        message: str,
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Call Agentforce chat API.
        In production, this would call the actual Agentforce REST API.
        """
        # PLACEHOLDER: Replace with actual Agentforce API call
        # This is a simulation for demonstration
        
        return {
            "response": f"I understand you said: {message}. How can I help?",
            "intent": "general_inquiry",
            "entities": [],
            "confidence": 0.85,
            "session_id": session_id
        }
    
    def _validate_chat_response(
        self,
        response: Dict,
        expected_intent: Optional[str],
        expected_entities: Optional[List[str]],
        expected_response_contains: Optional[List[str]]
    ) -> Dict:
        """Validate chat response against expectations."""
        validations = {}
        
        # Validate intent
        if expected_intent:
            detected_intent = response.get("intent")
            validations["intent"] = {
                "expected": expected_intent,
                "actual": detected_intent,
                "passed": detected_intent == expected_intent
            }
        
        # Validate entities
        if expected_entities:
            extracted = set(response.get("entities", []))
            expected = set(expected_entities)
            validations["entities"] = {
                "expected": list(expected),
                "actual": list(extracted),
                "passed": expected.issubset(extracted)
            }
        
        # Validate response content
        if expected_response_contains:
            response_text = response.get("response", "")
            contains_all = all(
                keyword.lower() in response_text.lower()
                for keyword in expected_response_contains
            )
            validations["response_content"] = {
                "expected": expected_response_contains,
                "passed": contains_all
            }
        
        return validations
    
    def _process_email_to_case(
        self,
        subject: str,
        body: str,
        from_email: str
    ) -> Dict:
        """
        Process email-to-case.
        PLACEHOLDER: Replace with actual implementation.
        """
        # In production, would actually create case
        return {
            "case_created": True,
            "case_id": "5001234567890ABC"
        }
    
    def _get_case_details(self, case_id: str) -> Dict:
        """Get case details from Salesforce."""
        try:
            case = self.sf.Case.get(case_id)
            return case
        except:
            return {}
    
    def _get_case_email_response(self, case_id: str) -> Optional[Dict]:
        """Get automated email response for case."""
        # PLACEHOLDER: Query EmailMessage related to case
        return None
    
    def _send_sms_to_agent(
        self,
        from_number: str,
        body: str
    ) -> Dict:
        """Send SMS to Agentforce."""
        # PLACEHOLDER: Replace with actual SMS API
        return {
            "response_body": "Thanks for contacting us!",
            "case_created": False
        }
    
    def _send_slack_message(
        self,
        channel: str,
        user_id: str,
        text: str
    ) -> Dict:
        """Send Slack message to bot."""
        # PLACEHOLDER: Replace with actual Slack API
        return {
            "bot_response": "I can help you with that!"
        }
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        import uuid
        return str(uuid.uuid4())
    
    def clear_conversation_history(self):
        """Clear conversation history."""
        self.conversation_history = []


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def test_chat_flow(
    sf_connection: object,
    conversation_flow: List[Dict]
) -> Dict:
    """
    Quick chat conversation test.
    
    Usage:
        flow = [
            {"user_message": "Hello", "expected_intent": "greeting"},
            {"user_message": "I need help", "expected_intent": "help_request"}
        ]
        
        result = test_chat_flow(sf, flow)
    """
    engine = AgentforceTestingEngine(sf_connection, "test.salesforce.com")
    return engine.test_chat_conversation(conversation_flow)