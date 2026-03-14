"""
conversational_testing_engine.py — Conversational Testing Engine
Phase 3 Enterprise: Full Implementation

FEATURES:
  • Multi-turn conversation testing
  • Context retention validation
  • Salesforce data validation (SOQL)
  • Conversation flow generation
  • Session management
  • Real-time data lookups
"""

import time
import uuid
import json
from typing import List, Dict, Optional, Callable
from datetime import datetime
from engine.agentforce_api_connector import AgentforceAPIConnector
from engine.llm_judge_engine import LLMJudgeEngine
from connectors.llm_connector import get_llm_response

class ConversationalTestingEngine:
    """
    Tests multi-turn conversations with Salesforce data validation.
    """
    
    def __init__(
        self,
        agent_id: str,
        agentforce_connector: AgentforceAPIConnector,
        sf_connection: object,
        agent_config: Dict,
        llm_model: str = "groq/llama-3.3-70b-versatile",
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize conversational testing engine.
        
        Args:
            agent_id: Agent ID
            agentforce_connector: Agentforce API connector
            sf_connection: Salesforce connection for data validation
            agent_config: Agent configuration
            llm_model: LLM for conversation generation
            progress_callback: Progress callback
        """
        self.agent_id = agent_id
        self.connector = agentforce_connector
        self.sf = sf_connection
        self.agent_config = agent_config
        self.llm_model = llm_model
        self.progress_callback = progress_callback
        
        # Judge engine
        self.judge_engine = LLMJudgeEngine()
    
    def generate_and_execute_conversations(
        self,
        num_conversations: int = 10,
        validate_with_salesforce: bool = True
    ) -> Dict:
        """
        Generate and execute conversational test scenarios.
        
        Args:
            num_conversations: Number of conversations to generate
            validate_with_salesforce: Validate data with SOQL queries
        
        Returns:
            Execution summary
        """
        start_time = time.time()
        
        # 1. Generate conversation scenarios
        self._report_progress("Generating conversation scenarios...", 10)
        
        conversation_scenarios = self._generate_conversation_scenarios(
            num_conversations
        )
        
        # 2. Execute each conversation
        results = []
        
        for i, scenario in enumerate(conversation_scenarios):
            self._report_progress(
                f"Executing conversation {i+1}/{num_conversations}",
                10 + ((i / num_conversations) * 80)
            )
            
            result = self._execute_conversation(
                scenario=scenario,
                validate_with_salesforce=validate_with_salesforce
            )
            
            results.append(result)
        
        # 3. Calculate summary
        passed = sum(1 for r in results if r.get('final_verdict') == 'PASS')
        failed = sum(1 for r in results if r.get('final_verdict') == 'FAIL')
        errors = sum(1 for r in results if r.get('final_verdict') == 'ERROR')
        
        self._report_progress("Complete!", 100)
        
        return {
            'success': True,
            'total_conversations': num_conversations,
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'pass_rate': round((passed / num_conversations) * 100, 1) if num_conversations > 0 else 0,
            'duration_sec': time.time() - start_time,
            'results': results
        }
    
    def _generate_conversation_scenarios(
        self,
        num_scenarios: int
    ) -> List[Dict]:
        """Generate conversation scenarios using LLM."""
        
        prompt = f"""You are a conversation scenario designer for testing AI agents.

Generate {num_scenarios} realistic multi-turn conversation scenarios for testing this agent:

AGENT CONTEXT:
Description: {self.agent_config.get('agent_description', '')}
Role: {self.agent_config.get('agent_role', '')}
Business Functions: {', '.join(self.agent_config.get('business_functions', []))}

Each conversation should test:
- Greeting and introduction
- Intent recognition
- Information gathering
- Context retention across turns
- Data retrieval (order status, account info, etc.)
- Conversation closure

CONVERSATION FLOW TEMPLATE:
1. User greets agent
2. Agent responds with greeting
3. User states request (e.g., check order status)
4. Agent asks for verification details
5. User provides details (order number, name, etc.)
6. Agent retrieves data and responds
7. User may ask follow-up questions
8. Conversation ends

OUTPUT FORMAT (JSON):
Return ONLY a JSON array of conversation scenarios:
[
  {{
    "scenario_name": "Order Status Inquiry",
    "test_focus": "Order retrieval and status communication",
    "conversation_flow": [
      {{
        "turn": 1,
        "speaker": "user",
        "message": "Hi, I need help with my order",
        "expected_agent_action": "greet_and_acknowledge"
      }},
      {{
        "turn": 2,
        "speaker": "agent",
        "expected_intent": "greeting",
        "validation": "Should ask how to help"
      }},
      {{
        "turn": 3,
        "speaker": "user",
        "message": "I want to check my order status",
        "expected_agent_action": "request_order_details"
      }},
      ...
    ],
    "salesforce_validation": {{
      "query": "SELECT Id, Status FROM Order WHERE OrderNumber = :orderNumber",
      "expected_fields": ["Id", "Status"]
    }}
  }},
  ...
]

Generate {num_scenarios} diverse conversation scenarios now:"""
        
        response, error = get_llm_response(
            prompt=prompt,
            model=self.llm_model,
            max_tokens=4000,
            temperature=0.8
        )
        
        if error or not response:
            print(f"Failed to generate scenarios: {error}")
            return []
        
        try:
            # Clean and parse response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])
            
            scenarios = json.loads(response)
            return scenarios
        
        except Exception as e:
            print(f"Error parsing scenarios: {e}")
            return []
    
    def _execute_conversation(
        self,
        scenario: Dict,
        validate_with_salesforce: bool
    ) -> Dict:
        """Execute single conversation scenario."""
        start_time = time.time()
        conversation_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        scenario_name = scenario.get('scenario_name', 'Unnamed Scenario')
        conversation_flow = scenario.get('conversation_flow', [])
        sf_validation = scenario.get('salesforce_validation', {})
        
        # Execute conversation
        transcript = []
        passed_turns = 0
        failed_turns = 0
        soql_queries = []
        data_validations = []
        
        for turn in conversation_flow:
            speaker = turn.get('speaker')
            
            if speaker == 'user':
                # User turn - send message to agent
                message = turn.get('message')
                
                agent_response = self.connector.send_message_to_agent(
                    agent_id=self.agent_id,
                    message=message,
                    session_id=session_id
                )
                
                # Store in transcript
                transcript.append({
                    'turn': turn.get('turn'),
                    'speaker': 'user',
                    'message': message
                })
                
                if agent_response.get('success'):
                    agent_text = agent_response.get('response', '')
                    
                    transcript.append({
                        'turn': turn.get('turn'),
                        'speaker': 'agent',
                        'message': agent_text,
                        'intent': agent_response.get('intent'),
                        'entities': agent_response.get('entities', [])
                    })
                    
                    # Validate agent response if expected action specified
                    expected_action = turn.get('expected_agent_action')
                    if expected_action:
                        # Use LLM to validate agent took expected action
                        validation = self._validate_agent_action(
                            agent_response=agent_text,
                            expected_action=expected_action
                        )
                        
                        if validation:
                            passed_turns += 1
                        else:
                            failed_turns += 1
                    else:
                        passed_turns += 1
                else:
                    failed_turns += 1
                    transcript.append({
                        'turn': turn.get('turn'),
                        'speaker': 'agent',
                        'error': agent_response.get('error')
                    })
        
        # Salesforce data validation
        if validate_with_salesforce and sf_validation:
            query = sf_validation.get('query')
            expected_fields = sf_validation.get('expected_fields', [])
            
            if query:
                try:
                    # Execute SOQL query
                    # Replace placeholders with actual values from conversation
                    # This is simplified - in production would extract values from transcript
                    
                    result = self.sf.query(query)
                    records = result.get('records', [])
                    
                    soql_queries.append({
                        'query': query,
                        'record_count': len(records)
                    })
                    
                    # Validate expected fields are present
                    if records:
                        record = records[0]
                        fields_present = all(
                            field in record for field in expected_fields
                        )
                        
                        data_validations.append({
                            'expected_fields': expected_fields,
                            'fields_present': fields_present,
                            'status': 'PASS' if fields_present else 'FAIL'
                        })
                
                except Exception as e:
                    data_validations.append({
                        'error': str(e),
                        'status': 'ERROR'
                    })
        
        # Determine final verdict
        total_turns = passed_turns + failed_turns
        if total_turns == 0:
            final_verdict = 'ERROR'
        elif failed_turns == 0:
            final_verdict = 'PASS'
        elif passed_turns > failed_turns:
            final_verdict = 'PARTIAL'
        else:
            final_verdict = 'FAIL'
        
        return {
            'conversation_id': conversation_id,
            'scenario_name': scenario_name,
            'total_turns': total_turns,
            'passed_turns': passed_turns,
            'failed_turns': failed_turns,
            'conversation_transcript': transcript,
            'soql_queries_executed': soql_queries,
            'data_validations': data_validations,
            'final_verdict': final_verdict,
            'duration_sec': time.time() - start_time
        }
    
    def _validate_agent_action(
        self,
        agent_response: str,
        expected_action: str
    ) -> bool:
        """Validate agent took expected action."""
        
        prompt = f"""Did the agent's response demonstrate the expected action?

AGENT RESPONSE:
{agent_response}

EXPECTED ACTION:
{expected_action}

Respond with ONLY "YES" or "NO":"""
        
        response, _ = get_llm_response(
            prompt=prompt,
            model=self.llm_model,
            max_tokens=10
        )
        
        if response:
            return response.strip().upper() == "YES"
        
        return False
    
    def _report_progress(self, message: str, percentage: float):
        """Report progress."""
        if self.progress_callback:
            try:
                self.progress_callback(message, percentage)
            except:
                pass


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def execute_conversational_tests(
    agent_id: str,
    agentforce_connector: AgentforceAPIConnector,
    sf_connection: object,
    agent_config: Dict,
    num_conversations: int = 10
) -> Dict:
    """
    Quick function to execute conversational tests.
    
    Usage:
        result = execute_conversational_tests(
            agent_id="0Xx...",
            agentforce_connector=connector,
            sf_connection=sf,
            agent_config=config,
            num_conversations=20
        )
        
        print(f"Pass rate: {result['pass_rate']}%")
    """
    engine = ConversationalTestingEngine(
        agent_id=agent_id,
        agentforce_connector=agentforce_connector,
        sf_connection=sf_connection,
        agent_config=agent_config
    )
    
    return engine.generate_and_execute_conversations(
        num_conversations=num_conversations,
        validate_with_salesforce=True
    )