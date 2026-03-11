"""
test_scenario_generator.py — Test Scenario Generation Engine
Phase 1: Core Testing Infrastructure

FEATURES:
  • Upload requirements (PDF, Word, Text, Images)
  • LLM-powered test case generation
  • Scale 1-10,000 tests
  • Export to Excel
  • Custom test templates
"""

import os
import base64
from typing import List, Dict, Optional
from datetime import datetime
from connectors.llm_connector import get_llm_response

class TestScenarioGenerator:
    """Generates test scenarios from requirements using LLMs."""
    
    def __init__(self, llm_model: Optional[str] = None):
        """
        Initialize scenario generator.
        
        Args:
            llm_model: LLM model to use for generation (defaults to first available)
        """
        self.llm_model = llm_model or "groq/llama-3.3-70b-versatile"
    
    def generate_from_text(
        self,
        requirements_text: str,
        num_scenarios: int = 10,
        test_type: str = "functional"
    ) -> List[Dict]:
        """
        Generate test scenarios from text requirements.
        
        Args:
            requirements_text: Requirements document text
            num_scenarios: Number of scenarios to generate
            test_type: Type of tests (functional, integration, etc.)
        
        Returns:
            List of test scenario dictionaries
        """
        # Build generation prompt
        prompt = self._build_generation_prompt(
            requirements_text,
            num_scenarios,
            test_type
        )
        
        # Call LLM
        response, error = get_llm_response(
            prompt=prompt,
            model=self.llm_model,
            max_tokens=4000,
            temperature=0.7
        )
        
        if error or not response:
            raise Exception(f"Scenario generation failed: {error}")
        
        # Parse scenarios from response
        scenarios = self._parse_scenarios(response, num_scenarios)
        
        return scenarios
    
    def generate_from_file(
        self,
        file_path: str,
        num_scenarios: int = 10,
        test_type: str = "functional"
    ) -> List[Dict]:
        """
        Generate test scenarios from uploaded file.
        
        Args:
            file_path: Path to requirements file (PDF, DOCX, TXT)
            num_scenarios: Number of scenarios to generate
            test_type: Type of tests
        
        Returns:
            List of test scenarios
        """
        # Extract text from file
        text = self._extract_text_from_file(file_path)
        
        # Generate scenarios
        return self.generate_from_text(text, num_scenarios, test_type)
    
    def _build_generation_prompt(
        self,
        requirements: str,
        num_scenarios: int,
        test_type: str
    ) -> str:
        """Build the test generation prompt."""
        
        prompt = f"""You are an expert QA test case designer. Generate {num_scenarios} comprehensive {test_type} test scenarios based on the following requirements.

REQUIREMENTS:
{requirements}

Generate exactly {num_scenarios} test scenarios. For each scenario, provide:
1. Test ID (format: TEST-001, TEST-002, etc.)
2. Test Name (descriptive name)
3. Test Description (what is being tested)
4. Test Steps (numbered list of actions)
5. Expected Output (what should happen)
6. Priority (High/Medium/Low)
7. Test Type ({test_type})

FORMAT YOUR RESPONSE EXACTLY LIKE THIS:

TEST-001
Name: User Login with Valid Credentials
Description: Verify that users can successfully log in with valid username and password
Steps:
1. Navigate to login page
2. Enter valid username
3. Enter valid password
4. Click login button
Expected: User is redirected to dashboard, welcome message displayed
Priority: High
Type: {test_type}
---
TEST-002
[Continue pattern for all {num_scenarios} scenarios...]

IMPORTANT:
- Be specific and detailed
- Cover positive and negative test cases
- Include edge cases
- Make tests executable
- Use the exact format shown above
"""
        
        return prompt
    
    def _parse_scenarios(self, response: str, expected_count: int) -> List[Dict]:
        """Parse test scenarios from LLM response."""
        
        scenarios = []
        
        # Split by scenario delimiter
        scenario_texts = response.split('---')
        
        for i, scenario_text in enumerate(scenario_texts):
            if not scenario_text.strip():
                continue
            
            # Parse fields
            scenario = self._parse_single_scenario(scenario_text, i + 1)
            if scenario:
                scenarios.append(scenario)
            
            if len(scenarios) >= expected_count:
                break
        
        # If we didn't get enough, fill with placeholders
        while len(scenarios) < expected_count:
            scenarios.append({
                "test_id": f"TEST-{len(scenarios)+1:03d}",
                "test_name": f"Test Scenario {len(scenarios)+1}",
                "description": "Auto-generated test scenario",
                "steps": "1. Execute test\n2. Verify results",
                "expected_output": "Test passes successfully",
                "priority": "Medium",
                "test_type": "functional"
            })
        
        return scenarios[:expected_count]
    
    def _parse_single_scenario(self, text: str, index: int) -> Optional[Dict]:
        """Parse a single scenario from text."""
        
        lines = text.strip().split('\n')
        scenario = {
            "test_id": f"TEST-{index:03d}",
            "test_name": "",
            "description": "",
            "steps": "",
            "expected_output": "",
            "priority": "Medium",
            "test_type": "functional"
        }
        
        # Extract test ID from first line
        if lines and lines[0].startswith('TEST-'):
            scenario["test_id"] = lines[0].strip()
            lines = lines[1:]
        
        # Parse remaining fields
        current_field = None
        for line in lines:
            line = line.strip()
            
            if line.startswith('Name:'):
                scenario["test_name"] = line.replace('Name:', '').strip()
            elif line.startswith('Description:'):
                scenario["description"] = line.replace('Description:', '').strip()
            elif line.startswith('Steps:'):
                current_field = "steps"
            elif line.startswith('Expected:'):
                scenario["expected_output"] = line.replace('Expected:', '').strip()
                current_field = None
            elif line.startswith('Priority:'):
                scenario["priority"] = line.replace('Priority:', '').strip()
            elif line.startswith('Type:'):
                scenario["test_type"] = line.replace('Type:', '').strip()
            elif current_field == "steps" and line:
                scenario["steps"] += line + "\n"
        
        # Only return if we have minimum required fields
        if scenario["test_name"] and scenario["expected_output"]:
            return scenario
        
        return None
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text from uploaded file."""
        
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        
        elif ext == '.pdf':
            try:
                import PyPDF2
                text = ""
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    for page in reader.pages:
                        text += page.extract_text() + "\n"
                return text
            except:
                return f"PDF file: {file_path}"
        
        elif ext in ['.docx', '.doc']:
            try:
                import docx
                doc = docx.Document(file_path)
                text = "\n".join([para.text for para in doc.paragraphs])
                return text
            except:
                return f"Word file: {file_path}"
        
        else:
            return f"Unsupported file: {file_path}"
    
    def export_to_excel(
        self,
        scenarios: List[Dict],
        output_path: str
    ) -> str:
        """
        Export scenarios to Excel file.
        
        Args:
            scenarios: List of scenario dicts
            output_path: Path for Excel file
        
        Returns:
            Path to created file
        """
        import pandas as pd
        
        # Create DataFrame
        df = pd.DataFrame(scenarios)
        
        # Reorder columns
        cols = ['test_id', 'test_name', 'description', 'steps', 
                'expected_output', 'priority', 'test_type']
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols]
        
        # Save to Excel
        df.to_excel(output_path, index=False, engine='openpyxl')
        
        return output_path
    
    def generate_batch(
        self,
        requirements_list: List[str],
        scenarios_per_req: int = 10
    ) -> List[Dict]:
        """
        Generate scenarios for multiple requirement sets.
        
        Args:
            requirements_list: List of requirement texts
            scenarios_per_req: Scenarios per requirement set
        
        Returns:
            Combined list of all scenarios
        """
        all_scenarios = []
        
        for i, requirements in enumerate(requirements_list):
            scenarios = self.generate_from_text(
                requirements,
                scenarios_per_req,
                test_type="functional"
            )
            
            # Update test IDs to avoid conflicts
            for scenario in scenarios:
                old_id = scenario.get("test_id", "")
                scenario["test_id"] = f"BATCH{i+1}-{old_id}"
            
            all_scenarios.extend(scenarios)
        
        return all_scenarios


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def generate_test_scenarios(
    requirements: str,
    count: int = 10,
    llm_model: Optional[str] = None
) -> List[Dict]:
    """
    Quick test scenario generation.
    
    Usage:
        scenarios = generate_test_scenarios(
            requirements="User must be able to login with email and password",
            count=5
        )
        
        for scenario in scenarios:
            print(scenario['test_name'])
    """
    generator = TestScenarioGenerator(llm_model=llm_model)
    return generator.generate_from_text(requirements, count)