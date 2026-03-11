"""
voice_sms_engine.py — Voice & SMS Testing Engine
Phase 3: Agentforce & Multi-Channel Testing

FEATURES:
  • Voice call testing (IVR flows)
  • Speech recognition validation
  • DTMF (keypad) input testing
  • SMS message testing
  • Call flow navigation
  • Voice quality metrics
  • Response time testing
  • Transcription accuracy
"""

import time
from typing import List, Dict, Optional, Any
from datetime import datetime

class VoiceSMSEngine:
    """
    Voice and SMS testing engine for telephony channels.
    """
    
    def __init__(
        self,
        provider: str = "twilio",
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None
    ):
        """
        Initialize Voice/SMS testing engine.
        
        Args:
            provider: Telephony provider (twilio, amazon_connect, etc.)
            account_sid: Provider account SID
            auth_token: Provider auth token
        """
        self.provider = provider
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.call_history = []
        self.sms_history = []
    
    # ══════════════════════════════════════════════════════════
    # VOICE CALL TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_ivr_flow(
        self,
        phone_number: str,
        ivr_steps: List[Dict],
        timeout_seconds: int = 30
    ) -> Dict:
        """
        Test Interactive Voice Response (IVR) flow.
        
        Args:
            phone_number: Phone number to call
            ivr_steps: List of IVR navigation steps
                Example: [
                    {"action": "listen", "expected_prompt": "press 1 for sales"},
                    {"action": "dtmf", "keys": "1"},
                    {"action": "speak", "text": "I need sales help"},
                    {"action": "listen", "expected_response": "agent"}
                ]
            timeout_seconds: Max time to wait for responses
        
        Returns:
            IVR flow test results
        """
        start_time = time.time()
        call_id = self._initiate_call(phone_number)
        
        step_results = []
        
        try:
            for i, step in enumerate(ivr_steps):
                step_start = time.time()
                action = step.get("action")
                
                if action == "listen":
                    # Wait for and validate prompt
                    result = self._listen_for_prompt(
                        call_id=call_id,
                        expected_text=step.get("expected_prompt"),
                        timeout=timeout_seconds
                    )
                    
                elif action == "dtmf":
                    # Send DTMF tones (keypad input)
                    result = self._send_dtmf(
                        call_id=call_id,
                        keys=step.get("keys")
                    )
                    
                elif action == "speak":
                    # Send speech input
                    result = self._send_speech(
                        call_id=call_id,
                        text=step.get("text")
                    )
                    
                else:
                    result = {"status": "ERROR", "error": f"Unknown action: {action}"}
                
                result["step_number"] = i + 1
                result["step_duration"] = time.time() - step_start
                step_results.append(result)
            
            # End call
            self._end_call(call_id)
            
            # Calculate overall results
            passed_steps = sum(1 for r in step_results if r.get("status") == "PASS")
            total_steps = len(step_results)
            
            return {
                "test_type": "VOICE_IVR",
                "channel": "voice",
                "status": "PASS" if passed_steps == total_steps else "PARTIAL" if passed_steps > 0 else "FAIL",
                "phone_number": phone_number,
                "call_id": call_id,
                "total_steps": total_steps,
                "passed_steps": passed_steps,
                "failed_steps": total_steps - passed_steps,
                "step_results": step_results,
                "total_duration": time.time() - start_time
            }
        
        except Exception as e:
            self._end_call(call_id)
            return {
                "test_type": "VOICE_IVR",
                "channel": "voice",
                "status": "ERROR",
                "error": str(e),
                "step_results": step_results,
                "total_duration": time.time() - start_time
            }
    
    def test_speech_recognition(
        self,
        phone_number: str,
        test_phrases: List[Dict]
    ) -> Dict:
        """
        Test speech recognition accuracy.
        
        Args:
            phone_number: Phone number to call
            test_phrases: List of {spoken_text, expected_transcription} dicts
        
        Returns:
            Speech recognition test results
        """
        start_time = time.time()
        call_id = self._initiate_call(phone_number)
        
        results = []
        
        try:
            for phrase in test_phrases:
                spoken = phrase.get("spoken_text")
                expected = phrase.get("expected_transcription")
                
                # Send speech
                self._send_speech(call_id, spoken)
                
                # Get transcription
                transcription = self._get_transcription(call_id)
                
                # Calculate accuracy
                accuracy = self._calculate_transcription_accuracy(
                    expected, transcription
                )
                
                results.append({
                    "spoken_text": spoken,
                    "expected": expected,
                    "transcribed": transcription,
                    "accuracy": accuracy,
                    "passed": accuracy >= 90  # 90% threshold
                })
            
            self._end_call(call_id)
            
            # Overall metrics
            avg_accuracy = sum(r["accuracy"] for r in results) / len(results) if results else 0
            
            return {
                "test_type": "VOICE_SPEECH_RECOGNITION",
                "channel": "voice",
                "status": "PASS" if avg_accuracy >= 90 else "FAIL",
                "total_phrases": len(results),
                "average_accuracy": round(avg_accuracy, 2),
                "results": results,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            self._end_call(call_id)
            return {
                "test_type": "VOICE_SPEECH_RECOGNITION",
                "channel": "voice",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_dtmf_input(
        self,
        phone_number: str,
        dtmf_sequence: str,
        expected_route: str
    ) -> Dict:
        """
        Test DTMF (keypad) input routing.
        
        Args:
            phone_number: Phone number to call
            dtmf_sequence: Sequence of keys to press (e.g., "1234")
            expected_route: Expected destination/action
        
        Returns:
            DTMF test results
        """
        start_time = time.time()
        
        try:
            call_id = self._initiate_call(phone_number)
            
            # Send DTMF sequence
            self._send_dtmf(call_id, dtmf_sequence)
            
            # Wait for routing
            time.sleep(2)
            
            # Get current state
            actual_route = self._get_call_state(call_id)
            
            passed = actual_route == expected_route
            
            self._end_call(call_id)
            
            return {
                "test_type": "VOICE_DTMF",
                "channel": "voice",
                "status": "PASS" if passed else "FAIL",
                "dtmf_sequence": dtmf_sequence,
                "expected_route": expected_route,
                "actual_route": actual_route,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "VOICE_DTMF",
                "channel": "voice",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_call_quality(
        self,
        phone_number: str,
        duration_seconds: int = 10
    ) -> Dict:
        """
        Test voice call quality metrics.
        
        Args:
            phone_number: Phone number to call
            duration_seconds: How long to test
        
        Returns:
            Call quality metrics
        """
        start_time = time.time()
        
        try:
            call_id = self._initiate_call(phone_number)
            
            # Monitor call for specified duration
            time.sleep(duration_seconds)
            
            # Get quality metrics
            metrics = self._get_call_quality_metrics(call_id)
            
            self._end_call(call_id)
            
            # Evaluate quality
            quality_score = metrics.get("quality_score", 0)
            passed = quality_score >= 4.0  # MOS score >= 4.0
            
            return {
                "test_type": "VOICE_QUALITY",
                "channel": "voice",
                "status": "PASS" if passed else "FAIL",
                "quality_score": quality_score,  # MOS (Mean Opinion Score)
                "latency_ms": metrics.get("latency_ms"),
                "jitter_ms": metrics.get("jitter_ms"),
                "packet_loss_pct": metrics.get("packet_loss_pct"),
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "VOICE_QUALITY",
                "channel": "voice",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    # ══════════════════════════════════════════════════════════
    # SMS TESTING
    # ══════════════════════════════════════════════════════════
    
    def test_sms_send(
        self,
        to_number: str,
        from_number: str,
        message_body: str,
        expected_delivery: bool = True
    ) -> Dict:
        """
        Test SMS message sending.
        
        Args:
            to_number: Recipient phone number
            from_number: Sender phone number
            message_body: SMS message content
            expected_delivery: Should message be delivered?
        
        Returns:
            SMS send test results
        """
        start_time = time.time()
        
        try:
            # Send SMS
            result = self._send_sms(
                to=to_number,
                from_=from_number,
                body=message_body
            )
            
            message_sid = result.get("message_sid")
            
            # Wait for delivery status
            time.sleep(2)
            status = self._get_sms_status(message_sid)
            
            delivered = status in ["delivered", "sent"]
            passed = delivered == expected_delivery
            
            return {
                "test_type": "SMS_SEND",
                "channel": "sms",
                "status": "PASS" if passed else "FAIL",
                "to_number": to_number,
                "from_number": from_number,
                "message_sid": message_sid,
                "delivery_status": status,
                "delivered": delivered,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "SMS_SEND",
                "channel": "sms",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_sms_receive(
        self,
        from_number: str,
        to_number: str,
        message_body: str,
        expected_auto_response: bool = False,
        expected_response_contains: Optional[List[str]] = None
    ) -> Dict:
        """
        Test receiving and responding to SMS.
        
        Args:
            from_number: Sender phone number
            to_number: Receiver phone number
            message_body: SMS message content
            expected_auto_response: Should get auto-response?
            expected_response_contains: Keywords in response
        
        Returns:
            SMS receive test results
        """
        start_time = time.time()
        
        try:
            # Simulate incoming SMS
            result = self._simulate_incoming_sms(
                from_=from_number,
                to=to_number,
                body=message_body
            )
            
            # Check for auto-response
            time.sleep(3)  # Wait for auto-response
            auto_response = self._check_for_auto_response(from_number)
            
            validations = {}
            
            # Check if auto-response received
            validations["auto_response"] = {
                "expected": expected_auto_response,
                "actual": auto_response is not None,
                "passed": (auto_response is not None) == expected_auto_response
            }
            
            # Check response content
            if auto_response and expected_response_contains:
                contains_all = all(
                    keyword.lower() in auto_response.lower()
                    for keyword in expected_response_contains
                )
                validations["response_content"] = {
                    "expected": expected_response_contains,
                    "passed": contains_all
                }
            
            all_passed = all(v.get("passed", True) for v in validations.values())
            
            return {
                "test_type": "SMS_RECEIVE",
                "channel": "sms",
                "status": "PASS" if all_passed else "FAIL",
                "from_number": from_number,
                "to_number": to_number,
                "auto_response_received": auto_response is not None,
                "auto_response_text": auto_response,
                "validations": validations,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "SMS_RECEIVE",
                "channel": "sms",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    def test_sms_conversation(
        self,
        phone_number: str,
        conversation_flow: List[Dict]
    ) -> Dict:
        """
        Test multi-message SMS conversation.
        
        Args:
            phone_number: Phone number for conversation
            conversation_flow: List of message exchanges
                Example: [
                    {"send": "HELP", "expect_response": True},
                    {"send": "STATUS", "expect_contains": ["order", "shipped"]}
                ]
        
        Returns:
            SMS conversation test results
        """
        start_time = time.time()
        message_results = []
        
        try:
            for i, exchange in enumerate(conversation_flow):
                # Send message
                send_result = self.test_sms_send(
                    to_number=phone_number,
                    from_number="+1234567890",  # Test number
                    message_body=exchange.get("send")
                )
                
                # Check for response if expected
                if exchange.get("expect_response"):
                    time.sleep(2)
                    response = self._check_for_auto_response(phone_number)
                    
                    result = {
                        "exchange_number": i + 1,
                        "sent_message": exchange.get("send"),
                        "received_response": response is not None,
                        "response_text": response,
                        "status": "PASS" if response else "FAIL"
                    }
                else:
                    result = {
                        "exchange_number": i + 1,
                        "sent_message": exchange.get("send"),
                        "status": send_result.get("status")
                    }
                
                message_results.append(result)
            
            passed = sum(1 for r in message_results if r.get("status") == "PASS")
            
            return {
                "test_type": "SMS_CONVERSATION",
                "channel": "sms",
                "status": "PASS" if passed == len(message_results) else "PARTIAL" if passed > 0 else "FAIL",
                "total_exchanges": len(message_results),
                "passed_exchanges": passed,
                "message_results": message_results,
                "duration_sec": time.time() - start_time
            }
        
        except Exception as e:
            return {
                "test_type": "SMS_CONVERSATION",
                "channel": "sms",
                "status": "ERROR",
                "error": str(e),
                "duration_sec": time.time() - start_time
            }
    
    # ══════════════════════════════════════════════════════════
    # HELPER METHODS
    # ══════════════════════════════════════════════════════════
    
    def _initiate_call(self, phone_number: str) -> str:
        """Initiate voice call. Returns call ID."""
        # PLACEHOLDER: Replace with actual telephony API
        call_id = f"CALL_{int(time.time())}"
        self.call_history.append({"call_id": call_id, "number": phone_number})
        return call_id
    
    def _end_call(self, call_id: str):
        """End voice call."""
        # PLACEHOLDER: Replace with actual API call
        pass
    
    def _listen_for_prompt(
        self,
        call_id: str,
        expected_text: Optional[str],
        timeout: int
    ) -> Dict:
        """Listen for IVR prompt."""
        # PLACEHOLDER: Replace with actual speech-to-text
        time.sleep(1)
        
        # Simulate hearing prompt
        heard_prompt = "press 1 for sales, press 2 for support"
        
        if expected_text:
            passed = expected_text.lower() in heard_prompt.lower()
        else:
            passed = True
        
        return {
            "status": "PASS" if passed else "FAIL",
            "heard_prompt": heard_prompt,
            "expected": expected_text
        }
    
    def _send_dtmf(self, call_id: str, keys: str) -> Dict:
        """Send DTMF tones."""
        # PLACEHOLDER: Replace with actual DTMF API
        return {"status": "PASS", "keys_sent": keys}
    
    def _send_speech(self, call_id: str, text: str) -> Dict:
        """Send speech input."""
        # PLACEHOLDER: Replace with text-to-speech API
        return {"status": "PASS", "text_spoken": text}
    
    def _get_transcription(self, call_id: str) -> str:
        """Get speech transcription."""
        # PLACEHOLDER: Replace with actual transcription API
        return "sample transcription"
    
    def _calculate_transcription_accuracy(
        self,
        expected: str,
        actual: str
    ) -> float:
        """Calculate transcription accuracy (0-100)."""
        # Simple word-level accuracy
        expected_words = expected.lower().split()
        actual_words = actual.lower().split()
        
        if not expected_words:
            return 100.0
        
        correct = sum(1 for w in expected_words if w in actual_words)
        return (correct / len(expected_words)) * 100
    
    def _get_call_state(self, call_id: str) -> str:
        """Get current call state/route."""
        # PLACEHOLDER
        return "sales_queue"
    
    def _get_call_quality_metrics(self, call_id: str) -> Dict:
        """Get call quality metrics."""
        # PLACEHOLDER: Replace with actual quality monitoring
        return {
            "quality_score": 4.2,  # MOS score
            "latency_ms": 45,
            "jitter_ms": 8,
            "packet_loss_pct": 0.5
        }
    
    def _send_sms(self, to: str, from_: str, body: str) -> Dict:
        """Send SMS message."""
        # PLACEHOLDER: Replace with Twilio/provider API
        message_sid = f"SM{int(time.time())}"
        self.sms_history.append({
            "message_sid": message_sid,
            "to": to,
            "from": from_,
            "body": body
        })
        return {"message_sid": message_sid}
    
    def _get_sms_status(self, message_sid: str) -> str:
        """Get SMS delivery status."""
        # PLACEHOLDER
        return "delivered"
    
    def _simulate_incoming_sms(
        self,
        from_: str,
        to: str,
        body: str
    ) -> Dict:
        """Simulate incoming SMS."""
        # PLACEHOLDER
        return {"received": True}
    
    def _check_for_auto_response(self, phone_number: str) -> Optional[str]:
        """Check for auto-response SMS."""
        # PLACEHOLDER
        return "Thank you for contacting us!"


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def test_ivr_navigation(
    phone_number: str,
    navigation_steps: List[Dict]
) -> Dict:
    """
    Quick IVR flow test.
    
    Usage:
        steps = [
            {"action": "listen", "expected_prompt": "main menu"},
            {"action": "dtmf", "keys": "1"},
            {"action": "speak", "text": "I need help"}
        ]
        
        result = test_ivr_navigation("+1234567890", steps)
    """
    engine = VoiceSMSEngine()
    return engine.test_ivr_flow(phone_number, navigation_steps)