"""
llm_judge_engine.py — LLM-as-Judge Evaluation Engine
Phase 1: Core Testing Infrastructure

FEATURES:
  • Multi-model voting system (2-10 judges)
  • Individual verdicts with reasoning
  • Consensus scoring with confidence levels
  • Support for all LLM providers
  • Automatic pass/fail determination
  • Detailed judgment records
"""

import os
import json
from typing import List, Dict, Tuple, Optional
from datetime import datetime
from connectors.llm_connector import get_llm_response
from config.settings_manager import get_selected_judge_models

class LLMJudgeEngine:
    """
    Multi-model LLM-as-Judge evaluation engine.
    Uses consensus voting from multiple LLM judges to determine test pass/fail.
    """
    
    def __init__(self, judge_models: Optional[List[str]] = None):
        """
        Initialize judge engine with specified models or use saved selection.
        
        Args:
            judge_models: List of model IDs to use as judges
        """
        if judge_models:
            self.judge_models = judge_models
        else:
            # Load from database
            saved_models = get_selected_judge_models()
            self.judge_models = [
                m.get("model_id") for m in saved_models 
                if m.get("model_id")
            ]
        
        if not self.judge_models:
            raise ValueError(
                "No judge models configured. Go to Settings → Judge Models "
                "to select at least one model."
            )
    
    def evaluate_response(
        self,
        test_input: str,
        expected_output: str,
        actual_output: str,
        context: Optional[str] = None
    ) -> Dict:
        """
        Evaluate a test response using multiple LLM judges.
        
        Args:
            test_input: The test input/prompt
            expected_output: Expected response
            actual_output: Actual AI agent response
            context: Optional context or additional info
        
        Returns:
            Dict with verdict, confidence, individual results, and reasoning
        """
        individual_results = []
        
        # Get judgment from each judge model
        for model_id in self.judge_models:
            try:
                verdict = self._get_single_judgment(
                    model_id=model_id,
                    test_input=test_input,
                    expected_output=expected_output,
                    actual_output=actual_output,
                    context=context
                )
                individual_results.append(verdict)
            except Exception as e:
                # Log error but continue with other judges
                individual_results.append({
                    "judge_model": model_id,
                    "verdict": "ERROR",
                    "reasoning": f"Judge error: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                })
        
        # Calculate consensus
        consensus = self._calculate_consensus(individual_results)
        
        return {
            "status": consensus["final_verdict"],
            "confidence": consensus["confidence"],
            "consensus": consensus["verdict_summary"],
            "judge_summary": consensus["summary_text"],
            "individual_results": individual_results,
            "models_used": len(individual_results),
            "pass_count": consensus["pass_count"],
            "fail_count": consensus["fail_count"],
            "error_count": consensus["error_count"],
            "timestamp": datetime.now().isoformat()
        }
    
    def _get_single_judgment(
        self,
        model_id: str,
        test_input: str,
        expected_output: str,
        actual_output: str,
        context: Optional[str] = None
    ) -> Dict:
        """
        Get judgment from a single LLM judge.
        
        Returns:
            Dict with verdict (PASS/FAIL), confidence score, and reasoning
        """
        # Build evaluation prompt
        eval_prompt = self._build_evaluation_prompt(
            test_input=test_input,
            expected_output=expected_output,
            actual_output=actual_output,
            context=context
        )
        
        # Get LLM response
        response, error = get_llm_response(
            prompt=eval_prompt,
            model=model_id,
            max_tokens=500,
            temperature=0.1  # Low temperature for consistency
        )
        
        if error or not response:
            raise Exception(f"LLM call failed: {error}")
        
        # Parse judgment
        judgment = self._parse_judgment(response, model_id)
        
        return judgment
    
    def _build_evaluation_prompt(
        self,
        test_input: str,
        expected_output: str,
        actual_output: str,
        context: Optional[str] = None
    ) -> str:
        """
        Build the evaluation prompt for the judge.
        """
        prompt = f"""You are an expert AI testing judge. Evaluate whether the AI agent's response correctly matches the expected outcome.

TEST INPUT:
{test_input}

EXPECTED OUTPUT:
{expected_output}

ACTUAL OUTPUT:
{actual_output}
"""
        
        if context:
            prompt += f"""
ADDITIONAL CONTEXT:
{context}
"""
        
        prompt += """
EVALUATION CRITERIA:
1. Does the actual output semantically match the expected output?
2. Are all key requirements from the expected output present?
3. Is the response accurate and appropriate?
4. Are there any critical errors or omissions?

RESPONSE FORMAT:
Provide your evaluation in this exact format:

VERDICT: [PASS or FAIL]
CONFIDENCE: [number from 0-100]
REASONING: [2-3 sentences explaining your decision]

Be strict but fair. Minor wording differences are acceptable if the meaning is correct.
"""
        
        return prompt
    
    def _parse_judgment(self, response: str, model_id: str) -> Dict:
        """
        Parse the judge's response into structured format.
        """
        try:
            # Extract verdict
            verdict = "FAIL"  # Default to fail
            if "VERDICT: PASS" in response or "VERDICT:PASS" in response:
                verdict = "PASS"
            elif "VERDICT: FAIL" in response or "VERDICT:FAIL" in response:
                verdict = "FAIL"
            
            # Extract confidence
            confidence = 50  # Default
            for line in response.split('\n'):
                if 'CONFIDENCE:' in line:
                    try:
                        conf_str = line.split('CONFIDENCE:')[1].strip()
                        # Extract first number found
                        import re
                        numbers = re.findall(r'\d+', conf_str)
                        if numbers:
                            confidence = min(100, max(0, int(numbers[0])))
                    except:
                        pass
            
            # Extract reasoning
            reasoning = ""
            if 'REASONING:' in response:
                reasoning = response.split('REASONING:')[1].strip()
            else:
                # Use full response if no structured format
                reasoning = response.strip()
            
            return {
                "judge_model": model_id,
                "verdict": verdict,
                "confidence": confidence,
                "reasoning": reasoning[:500],  # Limit length
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            # Fallback parsing
            return {
                "judge_model": model_id,
                "verdict": "FAIL",
                "confidence": 0,
                "reasoning": f"Parse error: {str(e)}. Raw: {response[:200]}",
                "timestamp": datetime.now().isoformat()
            }
    
    def _calculate_consensus(self, individual_results: List[Dict]) -> Dict:
        """
        Calculate consensus from individual judge verdicts.
        
        Uses weighted voting based on confidence scores.
        """
        pass_count = 0
        fail_count = 0
        error_count = 0
        
        pass_confidence_sum = 0
        fail_confidence_sum = 0
        
        for result in individual_results:
            verdict = result.get("verdict", "ERROR")
            confidence = result.get("confidence", 0)
            
            if verdict == "PASS":
                pass_count += 1
                pass_confidence_sum += confidence
            elif verdict == "FAIL":
                fail_count += 1
                fail_confidence_sum += confidence
            else:
                error_count += 1
        
        # Determine final verdict
        if pass_count > fail_count:
            final_verdict = "PASS"
            confidence = (pass_confidence_sum / pass_count) if pass_count > 0 else 0
        elif fail_count > pass_count:
            final_verdict = "FAIL"
            confidence = (fail_confidence_sum / fail_count) if fail_count > 0 else 0
        else:
            # Tie - use average confidence to decide
            avg_pass = (pass_confidence_sum / pass_count) if pass_count > 0 else 0
            avg_fail = (fail_confidence_sum / fail_count) if fail_count > 0 else 0
            
            if avg_pass > avg_fail:
                final_verdict = "PASS"
                confidence = avg_pass
            else:
                final_verdict = "FAIL"
                confidence = avg_fail
        
        # Build summary
        total_judges = len(individual_results)
        verdict_summary = f"{pass_count}/{total_judges} judges voted PASS"
        
        summary_text = (
            f"Consensus: {final_verdict} with {confidence:.0f}% confidence. "
            f"{pass_count} PASS, {fail_count} FAIL"
        )
        
        if error_count > 0:
            summary_text += f", {error_count} errors"
        
        return {
            "final_verdict": final_verdict,
            "confidence": round(confidence, 1),
            "verdict_summary": verdict_summary,
            "summary_text": summary_text,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "error_count": error_count,
            "total_judges": total_judges
        }
    
    def batch_evaluate(
        self,
        test_cases: List[Dict]
    ) -> List[Dict]:
        """
        Evaluate multiple test cases in batch.
        
        Args:
            test_cases: List of dicts with keys: test_input, expected_output, actual_output
        
        Returns:
            List of evaluation results
        """
        results = []
        
        for i, test_case in enumerate(test_cases):
            try:
                result = self.evaluate_response(
                    test_input=test_case.get("test_input", ""),
                    expected_output=test_case.get("expected_output", ""),
                    actual_output=test_case.get("actual_output", ""),
                    context=test_case.get("context")
                )
                result["test_case_index"] = i
                results.append(result)
            except Exception as e:
                results.append({
                    "test_case_index": i,
                    "status": "ERROR",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                })
        
        return results


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def evaluate_single_test(
    test_input: str,
    expected_output: str,
    actual_output: str,
    context: Optional[str] = None,
    judge_models: Optional[List[str]] = None
) -> Dict:
    """
    Convenience function to evaluate a single test.
    
    Usage:
        result = evaluate_single_test(
            test_input="What is 2+2?",
            expected_output="4",
            actual_output="The answer is 4"
        )
        print(result["status"])  # PASS or FAIL
        print(result["confidence"])  # 0-100
    """
    engine = LLMJudgeEngine(judge_models=judge_models)
    return engine.evaluate_response(
        test_input=test_input,
        expected_output=expected_output,
        actual_output=actual_output,
        context=context
    )


def get_available_judges() -> List[str]:
    """
    Get list of configured judge models.
    
    Returns:
        List of model IDs
    """
    saved_models = get_selected_judge_models()
    return [m.get("model_id") for m in saved_models if m.get("model_id")]