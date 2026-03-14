"""
agentforce_api_connector.py — Agentforce API Connector
Phase 3 Enterprise: Full Implementation

FEATURES:
  • Call Agentforce Agent API
  • Support for Agentforce DX
  • Testing API integration
  • Session management
  • Multi-turn conversations
"""

import requests
import json
from typing import Dict, Optional, List
from datetime import datetime
import time

class AgentforceAPIConnector:
    """
    Connector for Salesforce Agentforce API endpoints.
    Supports Agent API, Agentforce DX, and Testing API.
    """
    
    def __init__(
        self,
        instance_url: str,
        access_token: str,
        api_version: str = "v60.0"
    ):
        """
        Initialize Agentforce API connector.
        
        Args:
            instance_url: Salesforce instance URL
            access_token: OAuth access token
            api_version: Salesforce API version
        """
        self.instance_url = instance_url.rstrip('/')
        self.access_token = access_token
        self.api_version = api_version
        self.base_url = f"{self.instance_url}/services/data/{api_version}"
        
        # Session tracking
        self.sessions = {}
    
    # ══════════════════════════════════════════════════════════
    # AGENT API
    # ══════════════════════════════════════════════════════════
    
    def send_message_to_agent(
        self,
        agent_id: str,
        message: str,
        session_id: Optional[str] = None,
        context: Optional[Dict] = None
    ) -> Dict:
        """
        Send message to Agentforce agent via Agent API.
        
        Args:
            agent_id: Agent ID
            message: User message
            session_id: Optional session ID for conversation continuity
            context: Optional context data
        
        Returns:
            Agent response dictionary
        """
        start_time = time.time()
        
        # Generate session ID if not provided
        if not session_id:
            session_id = self._generate_session_id()
        
        # Build request payload
        payload = {
            "message": message,
            "sessionId": session_id
        }
        
        if context:
            payload["context"] = context
        
        # API endpoint
        endpoint = f"{self.base_url}/einstein/bots/{agent_id}/chat"
        
        try:
            # Make API call
            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            response_data = response.json()
            
            # Store session
            self.sessions[session_id] = {
                'agent_id': agent_id,
                'last_message': message,
                'last_response': response_data,
                'updated_at': datetime.now().isoformat()
            }
            
            # Parse response
            return {
                'success': True,
                'session_id': session_id,
                'response': response_data.get('message', ''),
                'intent': response_data.get('intent'),
                'entities': response_data.get('entities', []),
                'confidence': response_data.get('confidence'),
                'actions': response_data.get('actions', []),
                'duration_sec': time.time() - start_time,
                'raw_response': response_data
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e),
                'duration_sec': time.time() - start_time
            }
    
    def send_conversation(
        self,
        agent_id: str,
        messages: List[str],
        session_id: Optional[str] = None
    ) -> Dict:
        """
        Send multi-turn conversation to agent.
        
        Args:
            agent_id: Agent ID
            messages: List of messages in order
            session_id: Optional session ID
        
        Returns:
            Conversation results
        """
        if not session_id:
            session_id = self._generate_session_id()
        
        conversation_results = []
        
        for i, message in enumerate(messages):
            result = self.send_message_to_agent(
                agent_id=agent_id,
                message=message,
                session_id=session_id
            )
            
            result['turn_number'] = i + 1
            conversation_results.append(result)
            
            # Small delay between messages
            if i < len(messages) - 1:
                time.sleep(0.5)
        
        return {
            'session_id': session_id,
            'total_turns': len(messages),
            'results': conversation_results,
            'success': all(r.get('success') for r in conversation_results)
        }
    
    # ══════════════════════════════════════════════════════════
    # AGENTFORCE DX API
    # ══════════════════════════════════════════════════════════
    
    def call_dx_test(
        self,
        agent_id: str,
        test_payload: Dict
    ) -> Dict:
        """
        Call Agentforce DX testing endpoint.
        
        Args:
            agent_id: Agent ID
            test_payload: DX test payload
        
        Returns:
            Test results
        """
        endpoint = f"{self.base_url}/agentforce/dx/test/{agent_id}"
        
        try:
            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                json=test_payload,
                timeout=60
            )
            
            response.raise_for_status()
            return {
                'success': True,
                'results': response.json()
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # ══════════════════════════════════════════════════════════
    # TESTING API
    # ══════════════════════════════════════════════════════════
    
    def run_testing_api(
        self,
        agent_id: str,
        test_cases: List[Dict]
    ) -> Dict:
        """
        Run tests using Salesforce Testing API.
        
        Args:
            agent_id: Agent ID
            test_cases: List of test case dictionaries
        
        Returns:
            Testing API results
        """
        endpoint = f"{self.base_url}/agentforce/testing/{agent_id}/run"
        
        payload = {
            "testCases": test_cases
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                json=payload,
                timeout=120
            )
            
            response.raise_for_status()
            return {
                'success': True,
                'results': response.json()
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # ══════════════════════════════════════════════════════════
    # METADATA & INFO
    # ══════════════════════════════════════════════════════════
    
    def get_agent_metadata(self, agent_id: str) -> Dict:
        """
        Get agent metadata.
        
        Args:
            agent_id: Agent ID
        
        Returns:
            Agent metadata
        """
        endpoint = f"{self.base_url}/einstein/bots/{agent_id}"
        
        try:
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                timeout=30
            )
            
            response.raise_for_status()
            return {
                'success': True,
                'metadata': response.json()
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_agent_capabilities(self, agent_id: str) -> Dict:
        """
        Get agent capabilities (intents, entities, actions).
        
        Args:
            agent_id: Agent ID
        
        Returns:
            Agent capabilities
        """
        endpoint = f"{self.base_url}/einstein/bots/{agent_id}/capabilities"
        
        try:
            response = requests.get(
                endpoint,
                headers=self._get_headers(),
                timeout=30
            )
            
            response.raise_for_status()
            return {
                'success': True,
                'capabilities': response.json()
            }
        
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    # ══════════════════════════════════════════════════════════
    # SESSION MANAGEMENT
    # ══════════════════════════════════════════════════════════
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        return self.sessions.get(session_id)
    
    def clear_session(self, session_id: str):
        """Clear session data."""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def clear_all_sessions(self):
        """Clear all sessions."""
        self.sessions = {}
    
    # ══════════════════════════════════════════════════════════
    # HELPER METHODS
    # ══════════════════════════════════════════════════════════
    
    def _get_headers(self) -> Dict:
        """Get request headers."""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        import uuid
        return str(uuid.uuid4())


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def create_agentforce_connector(
    sf_connection: object
) -> AgentforceAPIConnector:
    """
    Create Agentforce API connector from Salesforce connection.
    
    Usage:
        from connectors.salesforce_connector import connect_with_oauth
        sf, _ = connect_with_oauth(...)
        
        connector = create_agentforce_connector(sf)
        
        result = connector.send_message_to_agent(
            agent_id="0Xx...",
            message="Hello"
        )
    """
    return AgentforceAPIConnector(
        instance_url=sf_connection.sf_instance,
        access_token=sf_connection.session_id
    )


def quick_agent_test(
    sf_connection: object,
    agent_id: str,
    test_message: str
) -> Dict:
    """
    Quick test of agent connectivity.
    
    Usage:
        result = quick_agent_test(
            sf_connection=sf,
            agent_id="0Xx...",
            test_message="Hello, can you help me?"
        )
        
        print(f"Response: {result['response']}")
    """
    connector = create_agentforce_connector(sf_connection)
    return connector.send_message_to_agent(agent_id, test_message)