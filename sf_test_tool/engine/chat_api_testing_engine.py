"""
chat_api_testing_engine.py — Chat API Testing Engine
Phase 3 Enterprise: Full Implementation

FEATURES:
  • Execute test scripts via Agent API
  • LLM-as-Judge evaluation
  • Multi-model judge voting
  • Real-time execution tracking
  • Results storage
  • Progress callbacks
"""

import time
import uuid
from typing import List, Dict, Optional, Callable
from datetime import datetime
from engine.agentforce_api_connector import AgentforceAPIConnector
from engine.llm_judge_engine import LLMJudgeEngine
from engine.agentforce_db_manager import (
    create_test_execution,
    update_test_execution,
    save_test_result,
    get_test_scripts
)

class ChatAPITestingEngine:
    """
    Executes chat test scripts and evaluates results using LLM judges.
    """
    
    def __init__(
        self,
        agent_id: str,
        agentforce_connector: AgentforceAPIConnector,
        judge_models: Optional[List[str]] = None,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize chat API testing engine.
        
        Args:
            agent_id: Agent ID to test
            agentforce_connector: Agentforce API connector
            judge_models: List of LLM models for judging (defaults to configured models)
            progress_callback: Optional callback for progress updates
        """
        self.agent_id = agent_id
        self.connector = agentforce_connector
        self.judge_engine = LLMJudgeEngine(judge_models=judge_models)
        self.progress_callback = progress_callback
        
        # Execution state
        self.execution_id = None
        self.total_scripts = 0
        self.executed_scripts = 0
        self.passed_scripts = 0
        self.failed_scripts = 0
        self.error_scripts = 0
    
    def execute_test_scripts(
        self,
        test_scripts: Optional[List[Dict]] = None,
        script_ids: Optional[List[str]] = None
    ) -> Dict:
        """
        Execute test scripts.
        
        Args:
            test_scripts: List of test script dictionaries (if already loaded)
            script_ids: List of script IDs to execute (will load from DB)
        
        Returns:
            Execution summary
        """
        # Load scripts if not provided
        if not test_scripts:
            if script_ids:
                # Load specific scripts by ID
                all_scripts = get_test_scripts(self.agent_id)
                test_scripts = [
                    s for s in all_scripts 
                    if s.get('script_id') in script_ids
                ]
            else:
                # Load all scripts for agent
                test_scripts = get_test_scripts(self.agent_id)
        
        if not test_scripts:
            return {
                'success': False,
                'error': 'No test scripts found'
            }
        
        # Initialize execution
        self.execution_id = str(uuid.uuid4())
        self.total_scripts = len(test_scripts)
        self.executed_scripts = 0
        self.passed_scripts = 0
        self.failed_scripts = 0
        self.error_scripts = 0
        
        # Create execution record
        create_test_execution(
            execution_id=self.execution_id,
            agent_id=self.agent_id,
            execution_type='api',
            test_config={
                'total_scripts': self.total_scripts,
                'judge_models': self.judge_engine.judge_models
            }
        )
        
        # Update execution status
        update_test_execution(
            execution_id=self.execution_id,
            status='running',
            total_scripts=self.total_scripts
        )
        
        start_time = time.time()
        
        # Execute each script
        for i, script in enumerate(test_scripts):
            try:
                # Execute single script
                result = self._execute_single_script(script)
                
                # Update counters
                self.executed_scripts += 1
                
                if result.get('status') == 'pass':
                    self.passed_scripts += 1
                elif result.get('status') == 'fail':
                    self.failed_scripts += 1
                else:
                    self.error_scripts += 1
                
                # Report progress
                self._report_progress(
                    f"Executed {self.executed_scripts}/{self.total_scripts} scripts",
                    (self.executed_scripts / self.total_scripts) * 100
                )
            
            except Exception as e:
                self.error_scripts += 1
                self.executed_scripts += 1
                print(f"Error executing script {script.get('script_id')}: {e}")
        
        duration = time.time() - start_time
        
        # Update execution as completed
        update_test_execution(
            execution_id=self.execution_id,
            status='completed',
            executed_scripts=self.executed_scripts,
            passed_scripts=self.passed_scripts,
            failed_scripts=self.failed_scripts,
            error_scripts=self.error_scripts,
            completed_at=datetime.now().isoformat(),
            duration_sec=duration
        )
        
        return {
            'success': True,
            'execution_id': self.execution_id,
            'total_scripts': self.total_scripts,
            'executed': self.executed_scripts,
            'passed': self.passed_scripts,
            'failed': self.failed_scripts,
            'errors': self.error_scripts,
            'pass_rate': round((self.passed_scripts / self.total_scripts) * 100, 1) if self.total_scripts > 0 else 0,
            'duration_sec': duration
        }
    
    def _execute_single_script(self, script: Dict) -> Dict:
        """Execute a single test script."""
        script_start = time.time()
        
        # Get script details
        utterance = script.get('utterance')
        expected_intent = script.get('expected_intent')
        expected_response = script.get('expected_response')
        script_id = script.get('script_id')
        test_type = script.get('test_type')
        persona = script.get('persona')
        
        try:
            # 1. Send message to agent
            agent_response = self.connector.send_message_to_agent(
                agent_id=self.agent_id,
                message=utterance
            )
            
            if not agent_response.get('success'):
                # Agent API call failed
                result = {
                    'result_id': str(uuid.uuid4()),
                    'execution_id': self.execution_id,
                    'script_id': script_id,
                    'agent_id': self.agent_id,
                    'test_type': test_type,
                    'persona': persona,
                    'user_utterance': utterance,
                    'actual_response': None,
                    'expected_response': expected_response,
                    'expected_intent': expected_intent,
                    'status': 'error',
                    'judge_verdict': 'ERROR',
                    'judge_confidence': 0,
                    'judge_reasoning': f"Agent API failed: {agent_response.get('error')}",
                    'duration_sec': time.time() - script_start
                }
                
                save_test_result(result)
                return result
            
            # 2. Get actual response
            actual_response = agent_response.get('response', '')
            detected_intent = agent_response.get('intent')
            
            # 3. Evaluate with LLM judge
            judge_result = self.judge_engine.evaluate_response(
                test_input=utterance,
                expected_output=expected_response,
                actual_output=actual_response,
                context=f"Expected Intent: {expected_intent}\nDetected Intent: {detected_intent}"
            )
            
            # 4. Determine status
            judge_verdict = judge_result.get('status')  # PASS or FAIL
            
            if judge_verdict == 'PASS':
                status = 'pass'
            elif judge_verdict == 'FAIL':
                status = 'fail'
            else:
                status = 'error'
            
            # 5. Create result record
            result = {
                'result_id': str(uuid.uuid4()),
                'execution_id': self.execution_id,
                'script_id': script_id,
                'agent_id': self.agent_id,
                'test_type': test_type,
                'persona': persona,
                'user_utterance': utterance,
                'actual_response': actual_response,
                'expected_response': expected_response,
                'detected_intent': detected_intent,
                'expected_intent': expected_intent,
                'extracted_entities': agent_response.get('entities', []),
                'judge_verdict': judge_verdict,
                'judge_confidence': judge_result.get('confidence', 0),
                'judge_reasoning': judge_result.get('judge_summary', ''),
                'judge_models_used': self.judge_engine.judge_models,
                'status': status,
                'duration_sec': time.time() - script_start,
                'session_id': agent_response.get('session_id')
            }
            
            # 6. Save result to database
            save_test_result(result)
            
            return result
        
        except Exception as e:
            # Unexpected error
            result = {
                'result_id': str(uuid.uuid4()),
                'execution_id': self.execution_id,
                'script_id': script_id,
                'agent_id': self.agent_id,
                'test_type': test_type,
                'persona': persona,
                'user_utterance': utterance,
                'expected_response': expected_response,
                'expected_intent': expected_intent,
                'status': 'error',
                'judge_verdict': 'ERROR',
                'judge_confidence': 0,
                'judge_reasoning': f"Unexpected error: {str(e)}",
                'duration_sec': time.time() - script_start
            }
            
            save_test_result(result)
            return result
    
    def _report_progress(self, message: str, percentage: float):
        """Report progress to callback."""
        if self.progress_callback:
            try:
                self.progress_callback(message, percentage)
            except:
                pass


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def execute_agent_tests(
    agent_id: str,
    agentforce_connector: AgentforceAPIConnector,
    test_scripts: Optional[List[Dict]] = None,
    judge_models: Optional[List[str]] = None,
    progress_callback: Optional[Callable] = None
) -> Dict:
    """
    Quick function to execute agent tests.
    
    Usage:
        from engine.agentforce_api_connector import create_agentforce_connector
        
        connector = create_agentforce_connector(sf)
        
        result = execute_agent_tests(
            agent_id="0Xx...",
            agentforce_connector=connector,
            test_scripts=[...]  # or None to load from DB
        )
        
        print(f"Pass rate: {result['pass_rate']}%")
    """
    engine = ChatAPITestingEngine(
        agent_id=agent_id,
        agentforce_connector=agentforce_connector,
        judge_models=judge_models,
        progress_callback=progress_callback
    )
    
    return engine.execute_test_scripts(test_scripts=test_scripts)