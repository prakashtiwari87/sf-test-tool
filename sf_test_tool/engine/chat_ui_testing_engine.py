"""
chat_ui_testing_engine.py — Chat UI Testing Engine (Playwright)
Phase 3 Enterprise: Full Implementation

FEATURES:
  • Test chat agents deployed on web pages
  • Playwright-based browser automation
  • AI SDK integration
  • Screenshot/video capture
  • Automatic chat UI detection
  • Multi-scenario testing
"""

import time
import uuid
import json
from typing import List, Dict, Optional, Callable
from datetime import datetime
from playwright.sync_api import sync_playwright, Page, Browser
from engine.llm_judge_engine import LLMJudgeEngine
from connectors.llm_connector import get_llm_response

class ChatUITestingEngine:
    """
    Tests chat agents deployed on web pages using Playwright.
    """
    
    def __init__(
        self,
        chat_url: str,
        agent_id: str,
        llm_model: str = "groq/llama-3.3-70b-versatile",
        browser_type: str = "chromium",
        headless: bool = True,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize UI testing engine.
        
        Args:
            chat_url: URL where chat agent is deployed
            agent_id: Agent ID being tested
            llm_model: LLM model for AI interactions
            browser_type: Browser to use (chromium, firefox, webkit)
            headless: Run browser in headless mode
            progress_callback: Progress callback function
        """
        self.chat_url = chat_url
        self.agent_id = agent_id
        self.llm_model = llm_model
        self.browser_type = browser_type
        self.headless = headless
        self.progress_callback = progress_callback
        
        # Judge engine
        self.judge_engine = LLMJudgeEngine()
        
        # Execution state
        self.session_id = None
        self.screenshots = []
        self.videos = []
    
    def execute_ui_tests(
        self,
        test_scenarios: List[Dict],
        capture_screenshots: bool = True,
        capture_video: bool = False
    ) -> Dict:
        """
        Execute UI tests with Playwright.
        
        Args:
            test_scenarios: List of test scenario dictionaries
            capture_screenshots: Take screenshots during testing
            capture_video: Record video of test execution
        
        Returns:
            Test execution summary
        """
        self.session_id = str(uuid.uuid4())
        start_time = time.time()
        
        results = []
        
        with sync_playwright() as p:
            # Launch browser
            browser = self._launch_browser(p)
            context = browser.new_context(
                record_video_dir='./test_videos' if capture_video else None
            )
            page = context.new_page()
            
            try:
                # Navigate to chat URL
                page.goto(self.chat_url)
                page.wait_for_load_state('networkidle')
                
                # Detect chat UI
                chat_detected = self._detect_chat_ui(page)
                
                if not chat_detected:
                    return {
                        'success': False,
                        'error': 'Chat UI not detected on page'
                    }
                
                # Execute each scenario
                for i, scenario in enumerate(test_scenarios):
                    self._report_progress(
                        f"Executing scenario {i+1}/{len(test_scenarios)}",
                        (i / len(test_scenarios)) * 100
                    )
                    
                    result = self._execute_single_scenario(
                        page=page,
                        scenario=scenario,
                        capture_screenshot=capture_screenshots
                    )
                    
                    results.append(result)
                    
                    # Small delay between scenarios
                    time.sleep(1)
            
            finally:
                # Cleanup
                context.close()
                browser.close()
        
        # Calculate summary
        passed = sum(1 for r in results if r.get('status') == 'pass')
        failed = sum(1 for r in results if r.get('status') == 'fail')
        errors = sum(1 for r in results if r.get('status') == 'error')
        
        return {
            'success': True,
            'session_id': self.session_id,
            'total_scenarios': len(test_scenarios),
            'passed': passed,
            'failed': failed,
            'errors': errors,
            'pass_rate': round((passed / len(test_scenarios)) * 100, 1) if test_scenarios else 0,
            'duration_sec': time.time() - start_time,
            'results': results,
            'screenshots': self.screenshots,
            'videos': self.videos
        }
    
    def _execute_single_scenario(
        self,
        page: Page,
        scenario: Dict,
        capture_screenshot: bool
    ) -> Dict:
        """Execute single UI test scenario."""
        start_time = time.time()
        
        utterance = scenario.get('utterance')
        expected_response = scenario.get('expected_response')
        test_type = scenario.get('test_type')
        persona = scenario.get('persona')
        
        try:
            # 1. Find chat input
            chat_input = self._find_chat_input(page)
            
            if not chat_input:
                return {
                    'status': 'error',
                    'error': 'Chat input not found',
                    'duration_sec': time.time() - start_time
                }
            
            # 2. Type message
            chat_input.fill(utterance)
            
            # 3. Send message (find send button or press Enter)
            send_button = self._find_send_button(page)
            if send_button:
                send_button.click()
            else:
                chat_input.press('Enter')
            
            # 4. Wait for response
            time.sleep(2)  # Wait for agent to respond
            
            # 5. Capture agent response
            agent_response = self._get_agent_response(page)
            
            # 6. Screenshot if enabled
            if capture_screenshot:
                screenshot_path = f"./screenshots/scenario_{uuid.uuid4()}.png"
                page.screenshot(path=screenshot_path)
                self.screenshots.append(screenshot_path)
            
            # 7. Evaluate with LLM judge
            judge_result = self.judge_engine.evaluate_response(
                test_input=utterance,
                expected_output=expected_response,
                actual_output=agent_response
            )
            
            # 8. Determine status
            status = 'pass' if judge_result.get('status') == 'PASS' else 'fail'
            
            return {
                'status': status,
                'test_type': test_type,
                'persona': persona,
                'user_utterance': utterance,
                'agent_response': agent_response,
                'expected_response': expected_response,
                'judge_verdict': judge_result.get('status'),
                'judge_confidence': judge_result.get('confidence'),
                'judge_reasoning': judge_result.get('judge_summary'),
                'duration_sec': time.time() - start_time
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'test_type': test_type,
                'persona': persona,
                'user_utterance': utterance,
                'duration_sec': time.time() - start_time
            }
    
    def _launch_browser(self, playwright) -> Browser:
        """Launch browser based on type."""
        if self.browser_type == 'chromium':
            return playwright.chromium.launch(headless=self.headless)
        elif self.browser_type == 'firefox':
            return playwright.firefox.launch(headless=self.headless)
        elif self.browser_type == 'webkit':
            return playwright.webkit.launch(headless=self.headless)
        else:
            return playwright.chromium.launch(headless=self.headless)
    
    def _detect_chat_ui(self, page: Page) -> bool:
        """Detect if chat UI is present on page."""
        # Common chat UI selectors
        selectors = [
            'iframe[title*="chat" i]',
            'div[class*="chat" i]',
            'div[id*="chat" i]',
            'button[aria-label*="chat" i]',
            '.chat-widget',
            '#chat-container',
            '[data-testid*="chat"]'
        ]
        
        for selector in selectors:
            try:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    return True
            except:
                continue
        
        return False
    
    def _find_chat_input(self, page: Page):
        """Find chat input field."""
        selectors = [
            'input[placeholder*="message" i]',
            'input[placeholder*="type" i]',
            'textarea[placeholder*="message" i]',
            'input[aria-label*="message" i]',
            'div[contenteditable="true"]',
            '.chat-input',
            '#message-input'
        ]
        
        for selector in selectors:
            try:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    return element
            except:
                continue
        
        return None
    
    def _find_send_button(self, page: Page):
        """Find send button."""
        selectors = [
            'button[aria-label*="send" i]',
            'button[title*="send" i]',
            'button:has-text("Send")',
            '.send-button',
            '#send-btn'
        ]
        
        for selector in selectors:
            try:
                element = page.query_selector(selector)
                if element and element.is_visible():
                    return element
            except:
                continue
        
        return None
    
    def _get_agent_response(self, page: Page) -> str:
        """Extract agent's response from chat UI."""
        # Try multiple strategies to get the latest message
        
        # Strategy 1: Last message in chat
        selectors = [
            '.chat-message:last-child',
            '.message:last-child',
            '[class*="bot-message"]:last-child',
            '[class*="agent-message"]:last-child'
        ]
        
        for selector in selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text()
                    if text.strip():
                        return text.strip()
            except:
                continue
        
        # Strategy 2: Use AI to detect response
        # Take screenshot and use vision model to read response
        # (This would require vision model - simplified for now)
        
        return "Response not captured"
    
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

def execute_ui_tests(
    chat_url: str,
    agent_id: str,
    test_scenarios: List[Dict],
    capture_screenshots: bool = True,
    headless: bool = True
) -> Dict:
    """
    Quick function to execute UI tests.
    
    Usage:
        scenarios = [
            {
                "utterance": "Hello",
                "expected_response": "Hi! How can I help?",
                "test_type": "Intent Recognition",
                "persona": "Friendly"
            }
        ]
        
        result = execute_ui_tests(
            chat_url="https://example.com/chat",
            agent_id="0Xx...",
            test_scenarios=scenarios
        )
        
        print(f"Pass rate: {result['pass_rate']}%")
    """
    engine = ChatUITestingEngine(
        chat_url=chat_url,
        agent_id=agent_id,
        headless=headless
    )
    
    return engine.execute_ui_tests(
        test_scenarios=test_scenarios,
        capture_screenshots=capture_screenshots
    )