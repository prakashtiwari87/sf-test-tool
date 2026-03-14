"""
agent_discovery_engine.py — Agent Discovery Engine
Phase 3 Enterprise: Full Implementation

FEATURES:
  • Auto-discover agents from Salesforce
  • Fetch agent metadata
  • Identify channel support
  • Store agents in database
  • Update agent status
"""

import json
from typing import List, Dict, Optional
from datetime import datetime
from engine.agentforce_db_manager import save_agent

class AgentDiscoveryEngine:
    """
    Discovers and registers Agentforce agents from Salesforce.
    """
    
    def __init__(self, sf_connection: object, org_domain: str):
        """
        Initialize agent discovery engine.
        
        Args:
            sf_connection: Salesforce connection object
            org_domain: Salesforce org domain
        """
        self.sf = sf_connection
        self.org_domain = org_domain
    
    def discover_all_agents(self) -> List[Dict]:
        """
        Discover all Agentforce agents in the org.
        
        Returns:
            List of discovered agent dictionaries
        """
        agents = []
        
        # Method 1: Query BotDefinition
        bot_agents = self._discover_from_bot_definition()
        agents.extend(bot_agents)
        
        # Method 2: Query AgentWork (if available)
        # This is for newer Agentforce agents
        agentforce_agents = self._discover_from_agentforce()
        agents.extend(agentforce_agents)
        
        # Method 3: Einstein Bots
        einstein_bots = self._discover_einstein_bots()
        agents.extend(einstein_bots)
        
        # Deduplicate by agent_id
        unique_agents = {agent['agent_id']: agent for agent in agents}
        
        return list(unique_agents.values())
    
    def _discover_from_bot_definition(self) -> List[Dict]:
        """Discover agents from BotDefinition object."""
        try:
            query = """
                SELECT Id, DeveloperName, MasterLabel, Description, Type
                FROM BotDefinition
                WHERE IsActive = true
            """
            
            result = self.sf.query(query)
            records = result.get('records', [])
            
            agents = []
            for record in records:
                agent = {
                    'agent_id': record.get('Id'),
                    'agent_name': record.get('MasterLabel') or record.get('DeveloperName'),
                    'agent_description': record.get('Description'),
                    'org_domain': self.org_domain,
                    'supports_chat': 1,
                    'supports_email': 0,
                    'supports_sms': 0,
                    'supports_voice': 0,
                    'supports_slack': 0,
                    'api_endpoint': f"/services/data/v60.0/einstein/bots/{record.get('Id')}",
                    'status': 'active',
                    'source': 'BotDefinition'
                }
                agents.append(agent)
            
            return agents
        
        except Exception as e:
            print(f"Error discovering from BotDefinition: {e}")
            return []
    
    def _discover_from_agentforce(self) -> List[Dict]:
        """Discover agents from Agentforce-specific objects."""
        try:
            # Try to query Agent metadata
            # This is for newer Agentforce agents
            query = """
                SELECT Id, Name, Description
                FROM Agent
                WHERE IsActive = true
            """
            
            result = self.sf.query(query)
            records = result.get('records', [])
            
            agents = []
            for record in records:
                agent = {
                    'agent_id': record.get('Id'),
                    'agent_name': record.get('Name'),
                    'agent_description': record.get('Description'),
                    'org_domain': self.org_domain,
                    'supports_chat': 1,
                    'supports_email': 1,
                    'supports_sms': 1,
                    'supports_voice': 1,
                    'supports_slack': 1,
                    'api_endpoint': f"/services/data/v60.0/agent/{record.get('Id')}",
                    'status': 'active',
                    'source': 'Agent'
                }
                agents.append(agent)
            
            return agents
        
        except Exception as e:
            # Agent object may not exist in all orgs
            print(f"Agentforce objects not available: {e}")
            return []
    
    def _discover_einstein_bots(self) -> List[Dict]:
        """Discover Einstein Bots."""
        try:
            query = """
                SELECT Id, DeveloperName, MasterLabel
                FROM BotVersion
                WHERE IsActive = true
            """
            
            result = self.sf.query(query)
            records = result.get('records', [])
            
            agents = []
            for record in records:
                agent = {
                    'agent_id': record.get('Id'),
                    'agent_name': record.get('MasterLabel') or record.get('DeveloperName'),
                    'agent_description': 'Einstein Bot',
                    'org_domain': self.org_domain,
                    'supports_chat': 1,
                    'supports_email': 0,
                    'supports_sms': 0,
                    'supports_voice': 0,
                    'supports_slack': 0,
                    'api_endpoint': f"/services/data/v60.0/einstein/bots/versions/{record.get('Id')}",
                    'status': 'active',
                    'source': 'BotVersion'
                }
                agents.append(agent)
            
            return agents
        
        except Exception as e:
            print(f"Error discovering Einstein Bots: {e}")
            return []
    
    def discover_and_save_agents(self) -> Dict:
        """
        Discover agents and save them to database.
        
        Returns:
            Summary of discovery results
        """
        # Discover agents
        discovered_agents = self.discover_all_agents()
        
        # Save to database
        saved_count = 0
        failed_count = 0
        
        for agent in discovered_agents:
            try:
                success = save_agent(
                    agent_id=agent['agent_id'],
                    agent_name=agent['agent_name'],
                    org_domain=agent['org_domain'],
                    agent_description=agent.get('agent_description'),
                    supports_chat=agent.get('supports_chat', 1),
                    supports_email=agent.get('supports_email', 0),
                    supports_sms=agent.get('supports_sms', 0),
                    supports_voice=agent.get('supports_voice', 0),
                    supports_slack=agent.get('supports_slack', 0),
                    api_endpoint=agent.get('api_endpoint')
                )
                
                if success:
                    saved_count += 1
                else:
                    failed_count += 1
            
            except Exception as e:
                print(f"Error saving agent {agent['agent_name']}: {e}")
                failed_count += 1
        
        return {
            'discovered': len(discovered_agents),
            'saved': saved_count,
            'failed': failed_count,
            'agents': discovered_agents
        }
    
    def get_agent_details(self, agent_id: str) -> Optional[Dict]:
        """
        Get detailed information about a specific agent.
        
        Args:
            agent_id: Agent ID
        
        Returns:
            Agent details dictionary
        """
        try:
            # Try to get from BotDefinition first
            bot = self.sf.BotDefinition.get(agent_id)
            
            if bot:
                return {
                    'agent_id': bot.get('Id'),
                    'agent_name': bot.get('MasterLabel'),
                    'description': bot.get('Description'),
                    'type': bot.get('Type'),
                    'is_active': bot.get('IsActive'),
                    'created_date': bot.get('CreatedDate'),
                    'last_modified_date': bot.get('LastModifiedDate')
                }
        
        except Exception as e:
            print(f"Error fetching agent details: {e}")
        
        return None
    
    def test_agent_connectivity(self, agent_id: str) -> Dict:
        """
        Test if agent is accessible via API.
        
        Args:
            agent_id: Agent ID to test
        
        Returns:
            Connectivity test results
        """
        try:
            # Try to fetch agent metadata
            agent_details = self.get_agent_details(agent_id)
            
            if agent_details:
                return {
                    'accessible': True,
                    'agent_id': agent_id,
                    'agent_name': agent_details.get('agent_name'),
                    'is_active': agent_details.get('is_active'),
                    'message': 'Agent is accessible'
                }
            else:
                return {
                    'accessible': False,
                    'agent_id': agent_id,
                    'message': 'Agent not found or not accessible'
                }
        
        except Exception as e:
            return {
                'accessible': False,
                'agent_id': agent_id,
                'error': str(e),
                'message': 'Error accessing agent'
            }


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def discover_agents_from_org(
    sf_connection: object,
    org_domain: str,
    save_to_db: bool = True
) -> Dict:
    """
    Quick function to discover agents from Salesforce org.
    
    Usage:
        from connectors.salesforce_connector import connect_with_oauth
        sf, _ = connect_with_oauth(...)
        
        result = discover_agents_from_org(
            sf_connection=sf,
            org_domain="yourorg.my.salesforce.com",
            save_to_db=True
        )
        
        print(f"Found {result['discovered']} agents")
    """
    engine = AgentDiscoveryEngine(sf_connection, org_domain)
    
    if save_to_db:
        return engine.discover_and_save_agents()
    else:
        agents = engine.discover_all_agents()
        return {
            'discovered': len(agents),
            'agents': agents
        }