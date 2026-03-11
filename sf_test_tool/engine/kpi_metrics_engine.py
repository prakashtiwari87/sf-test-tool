"""
kpi_metrics_engine.py — KPI & Metrics Calculation Engine
Phase 1: Core Testing Infrastructure

FEATURES:
  • 20+ AI agent KPIs auto-calculated
  • Intent recognition accuracy
  • Entity extraction accuracy
  • Task completion rate
  • Hallucination rate
  • Groundedness score
  • Response relevance
  • Safety/toxicity checks
  • And 13 more metrics
"""

import re
from typing import List, Dict, Optional
from datetime import datetime

class KPIMetricsEngine:
    """
    Calculates comprehensive KPIs for AI agent testing.
    Automatically detects which KPIs are calculable based on test results.
    """
    
    def __init__(self):
        self.kpi_definitions = self._get_kpi_definitions()
    
    def calculate_kpis(self, test_results: List[Dict]) -> Dict:
        """
        Calculate all applicable KPIs from test results.
        
        Args:
            test_results: List of test result dictionaries
        
        Returns:
            Dict with calculated KPIs and metadata
        """
        if not test_results:
            return {"error": "No test results provided"}
        
        kpis = {}
        
        # Calculate each KPI
        kpis["pass_rate"] = self._calc_pass_rate(test_results)
        kpis["fail_rate"] = self._calc_fail_rate(test_results)
        kpis["error_rate"] = self._calc_error_rate(test_results)
        
        kpis["average_confidence"] = self._calc_avg_confidence(test_results)
        kpis["average_duration"] = self._calc_avg_duration(test_results)
        
        kpis["intent_recognition_accuracy"] = self._calc_intent_accuracy(test_results)
        kpis["entity_extraction_accuracy"] = self._calc_entity_accuracy(test_results)
        kpis["task_completion_rate"] = self._calc_task_completion(test_results)
        
        kpis["hallucination_rate"] = self._calc_hallucination_rate(test_results)
        kpis["groundedness_score"] = self._calc_groundedness(test_results)
        kpis["response_relevance"] = self._calc_relevance(test_results)
        
        kpis["safety_pass_rate"] = self._calc_safety_rate(test_results)
        kpis["toxicity_detection_rate"] = self._calc_toxicity_rate(test_results)
        
        kpis["response_length_avg"] = self._calc_avg_response_length(test_results)
        kpis["response_time_p50"] = self._calc_percentile_duration(test_results, 50)
        kpis["response_time_p90"] = self._calc_percentile_duration(test_results, 90)
        kpis["response_time_p99"] = self._calc_percentile_duration(test_results, 99)
        
        kpis["first_attempt_success"] = self._calc_first_attempt_success(test_results)
        kpis["retry_rate"] = self._calc_retry_rate(test_results)
        
        kpis["context_utilization"] = self._calc_context_utilization(test_results)
        kpis["instruction_following"] = self._calc_instruction_following(test_results)
        
        # Meta information
        kpis["total_tests"] = len(test_results)
        kpis["tests_passed"] = sum(1 for r in test_results if r.get("status") == "PASS")
        kpis["tests_failed"] = sum(1 for r in test_results if r.get("status") == "FAIL")
        kpis["tests_error"] = sum(1 for r in test_results if r.get("status") == "ERROR")
        
        kpis["calculated_at"] = datetime.now().isoformat()
        kpis["kpis_available"] = len([v for v in kpis.values() if v is not None])
        
        return kpis
    
    # ══════════════════════════════════════════════════════════
    # CORE METRICS
    # ══════════════════════════════════════════════════════════
    
    def _calc_pass_rate(self, results: List[Dict]) -> Optional[float]:
        """Calculate pass rate percentage."""
        if not results:
            return None
        passed = sum(1 for r in results if r.get("status") == "PASS")
        return round((passed / len(results)) * 100, 2)
    
    def _calc_fail_rate(self, results: List[Dict]) -> Optional[float]:
        """Calculate fail rate percentage."""
        if not results:
            return None
        failed = sum(1 for r in results if r.get("status") == "FAIL")
        return round((failed / len(results)) * 100, 2)
    
    def _calc_error_rate(self, results: List[Dict]) -> Optional[float]:
        """Calculate error rate percentage."""
        if not results:
            return None
        errors = sum(1 for r in results if r.get("status") == "ERROR")
        return round((errors / len(results)) * 100, 2)
    
    # ══════════════════════════════════════════════════════════
    # QUALITY METRICS
    # ══════════════════════════════════════════════════════════
    
    def _calc_avg_confidence(self, results: List[Dict]) -> Optional[float]:
        """Calculate average confidence score."""
        confidences = [r.get("confidence", 0) for r in results if r.get("confidence")]
        if not confidences:
            return None
        return round(sum(confidences) / len(confidences), 2)
    
    def _calc_avg_duration(self, results: List[Dict]) -> Optional[float]:
        """Calculate average test duration in seconds."""
        durations = [r.get("duration_sec", 0) for r in results if r.get("duration_sec")]
        if not durations:
            return None
        return round(sum(durations) / len(durations), 2)
    
    def _calc_percentile_duration(self, results: List[Dict], percentile: int) -> Optional[float]:
        """Calculate duration percentile."""
        durations = sorted([r.get("duration_sec", 0) for r in results if r.get("duration_sec")])
        if not durations:
            return None
        
        index = int((percentile / 100) * len(durations))
        index = min(index, len(durations) - 1)
        return round(durations[index], 2)
    
    # ══════════════════════════════════════════════════════════
    # AI-SPECIFIC METRICS
    # ══════════════════════════════════════════════════════════
    
    def _calc_intent_accuracy(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate intent recognition accuracy.
        Checks if expected intent matches actual intent in responses.
        """
        intent_tests = [
            r for r in results 
            if r.get("expected_intent") and r.get("actual_intent")
        ]
        
        if not intent_tests:
            return None
        
        correct = sum(
            1 for r in intent_tests 
            if r.get("expected_intent") == r.get("actual_intent")
        )
        
        return round((correct / len(intent_tests)) * 100, 2)
    
    def _calc_entity_accuracy(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate entity extraction accuracy.
        Checks if all expected entities were extracted.
        """
        entity_tests = [
            r for r in results 
            if r.get("expected_entities") and r.get("extracted_entities")
        ]
        
        if not entity_tests:
            return None
        
        correct = 0
        for r in entity_tests:
            expected = set(r.get("expected_entities", []))
            extracted = set(r.get("extracted_entities", []))
            
            if expected.issubset(extracted):
                correct += 1
        
        return round((correct / len(entity_tests)) * 100, 2)
    
    def _calc_task_completion(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate task completion rate.
        Checks if agent completed the intended task.
        """
        task_tests = [r for r in results if r.get("task_completed") is not None]
        
        if not task_tests:
            return None
        
        completed = sum(1 for r in task_tests if r.get("task_completed") is True)
        return round((completed / len(task_tests)) * 100, 2)
    
    def _calc_hallucination_rate(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate hallucination rate.
        Percentage of responses containing hallucinated information.
        """
        hallucination_tests = [
            r for r in results 
            if r.get("hallucination_detected") is not None
        ]
        
        if not hallucination_tests:
            return None
        
        hallucinated = sum(
            1 for r in hallucination_tests 
            if r.get("hallucination_detected") is True
        )
        
        return round((hallucinated / len(hallucination_tests)) * 100, 2)
    
    def _calc_groundedness(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate average groundedness score.
        Measures how well responses are grounded in provided context.
        """
        grounded_tests = [
            r for r in results 
            if r.get("groundedness_score") is not None
        ]
        
        if not grounded_tests:
            return None
        
        scores = [r.get("groundedness_score", 0) for r in grounded_tests]
        return round(sum(scores) / len(scores), 2)
    
    def _calc_relevance(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate response relevance score.
        How relevant the response is to the query.
        """
        relevance_tests = [
            r for r in results 
            if r.get("relevance_score") is not None
        ]
        
        if not relevance_tests:
            return None
        
        scores = [r.get("relevance_score", 0) for r in relevance_tests]
        return round(sum(scores) / len(scores), 2)
    
    # ══════════════════════════════════════════════════════════
    # SAFETY METRICS
    # ══════════════════════════════════════════════════════════
    
    def _calc_safety_rate(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate safety pass rate.
        Percentage of responses that passed safety checks.
        """
        safety_tests = [r for r in results if r.get("safety_check") is not None]
        
        if not safety_tests:
            return None
        
        passed = sum(1 for r in safety_tests if r.get("safety_check") is True)
        return round((passed / len(safety_tests)) * 100, 2)
    
    def _calc_toxicity_rate(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate toxicity detection rate.
        Percentage of responses flagged as toxic.
        """
        toxicity_tests = [
            r for r in results 
            if r.get("toxicity_detected") is not None
        ]
        
        if not toxicity_tests:
            return None
        
        toxic = sum(1 for r in toxicity_tests if r.get("toxicity_detected") is True)
        return round((toxic / len(toxicity_tests)) * 100, 2)
    
    # ══════════════════════════════════════════════════════════
    # PERFORMANCE METRICS
    # ══════════════════════════════════════════════════════════
    
    def _calc_avg_response_length(self, results: List[Dict]) -> Optional[float]:
        """Calculate average response length in characters."""
        responses = [
            len(r.get("actual_output", "")) 
            for r in results 
            if r.get("actual_output")
        ]
        
        if not responses:
            return None
        
        return round(sum(responses) / len(responses), 0)
    
    def _calc_first_attempt_success(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate first-attempt success rate.
        Percentage of tests that passed on first attempt (no retries).
        """
        first_attempt_tests = [
            r for r in results 
            if r.get("retry_count") is not None
        ]
        
        if not first_attempt_tests:
            return None
        
        succeeded = sum(
            1 for r in first_attempt_tests 
            if r.get("status") == "PASS" and r.get("retry_count", 0) == 0
        )
        
        return round((succeeded / len(first_attempt_tests)) * 100, 2)
    
    def _calc_retry_rate(self, results: List[Dict]) -> Optional[float]:
        """Calculate average number of retries per test."""
        retry_tests = [r for r in results if r.get("retry_count") is not None]
        
        if not retry_tests:
            return None
        
        retries = [r.get("retry_count", 0) for r in retry_tests]
        return round(sum(retries) / len(retries), 2)
    
    def _calc_context_utilization(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate context utilization rate.
        Percentage of tests where agent properly used provided context.
        """
        context_tests = [
            r for r in results 
            if r.get("context_used") is not None
        ]
        
        if not context_tests:
            return None
        
        utilized = sum(1 for r in context_tests if r.get("context_used") is True)
        return round((utilized / len(context_tests)) * 100, 2)
    
    def _calc_instruction_following(self, results: List[Dict]) -> Optional[float]:
        """
        Calculate instruction-following score.
        How well the agent followed instructions.
        """
        instruction_tests = [
            r for r in results 
            if r.get("instructions_followed") is not None
        ]
        
        if not instruction_tests:
            return None
        
        followed = sum(
            1 for r in instruction_tests 
            if r.get("instructions_followed") is True
        )
        
        return round((followed / len(instruction_tests)) * 100, 2)
    
    # ══════════════════════════════════════════════════════════
    # KPI DEFINITIONS
    # ══════════════════════════════════════════════════════════
    
    def _get_kpi_definitions(self) -> Dict:
        """Get metadata about all KPIs."""
        return {
            "pass_rate": {
                "name": "Pass Rate",
                "description": "Percentage of tests that passed",
                "unit": "%",
                "higher_is_better": True
            },
            "fail_rate": {
                "name": "Fail Rate",
                "description": "Percentage of tests that failed",
                "unit": "%",
                "higher_is_better": False
            },
            "error_rate": {
                "name": "Error Rate",
                "description": "Percentage of tests with errors",
                "unit": "%",
                "higher_is_better": False
            },
            "average_confidence": {
                "name": "Average Confidence",
                "description": "Mean confidence score across all tests",
                "unit": "score",
                "higher_is_better": True
            },
            "average_duration": {
                "name": "Average Duration",
                "description": "Mean test execution time",
                "unit": "seconds",
                "higher_is_better": False
            },
            "intent_recognition_accuracy": {
                "name": "Intent Recognition Accuracy",
                "description": "Accuracy of intent detection",
                "unit": "%",
                "higher_is_better": True
            },
            "entity_extraction_accuracy": {
                "name": "Entity Extraction Accuracy",
                "description": "Accuracy of entity extraction",
                "unit": "%",
                "higher_is_better": True
            },
            "task_completion_rate": {
                "name": "Task Completion Rate",
                "description": "Percentage of tasks successfully completed",
                "unit": "%",
                "higher_is_better": True
            },
            "hallucination_rate": {
                "name": "Hallucination Rate",
                "description": "Percentage of responses with hallucinations",
                "unit": "%",
                "higher_is_better": False
            },
            "groundedness_score": {
                "name": "Groundedness Score",
                "description": "How well responses are grounded in context",
                "unit": "score",
                "higher_is_better": True
            },
            "response_relevance": {
                "name": "Response Relevance",
                "description": "Relevance of responses to queries",
                "unit": "score",
                "higher_is_better": True
            },
            "safety_pass_rate": {
                "name": "Safety Pass Rate",
                "description": "Percentage of responses passing safety checks",
                "unit": "%",
                "higher_is_better": True
            },
            "toxicity_detection_rate": {
                "name": "Toxicity Detection Rate",
                "description": "Percentage of responses flagged as toxic",
                "unit": "%",
                "higher_is_better": False
            },
            "response_length_avg": {
                "name": "Average Response Length",
                "description": "Mean response length",
                "unit": "characters",
                "higher_is_better": None
            },
            "response_time_p50": {
                "name": "Response Time P50",
                "description": "50th percentile response time",
                "unit": "seconds",
                "higher_is_better": False
            },
            "response_time_p90": {
                "name": "Response Time P90",
                "description": "90th percentile response time",
                "unit": "seconds",
                "higher_is_better": False
            },
            "response_time_p99": {
                "name": "Response Time P99",
                "description": "99th percentile response time",
                "unit": "seconds",
                "higher_is_better": False
            },
            "first_attempt_success": {
                "name": "First Attempt Success Rate",
                "description": "Percentage passing on first attempt",
                "unit": "%",
                "higher_is_better": True
            },
            "retry_rate": {
                "name": "Average Retry Rate",
                "description": "Average number of retries per test",
                "unit": "count",
                "higher_is_better": False
            },
            "context_utilization": {
                "name": "Context Utilization",
                "description": "Percentage of tests using context properly",
                "unit": "%",
                "higher_is_better": True
            },
            "instruction_following": {
                "name": "Instruction Following",
                "description": "How well instructions are followed",
                "unit": "%",
                "higher_is_better": True
            }
        }
    
    def get_kpi_report(self, kpis: Dict) -> str:
        """
        Generate human-readable KPI report.
        
        Args:
            kpis: KPI dictionary from calculate_kpis()
        
        Returns:
            Formatted report string
        """
        report = "=== KPI METRICS REPORT ===\n\n"
        
        # Core metrics
        report += "CORE METRICS:\n"
        report += f"  Pass Rate: {kpis.get('pass_rate', 'N/A')}%\n"
        report += f"  Fail Rate: {kpis.get('fail_rate', 'N/A')}%\n"
        report += f"  Error Rate: {kpis.get('error_rate', 'N/A')}%\n"
        report += f"  Avg Confidence: {kpis.get('average_confidence', 'N/A')}\n"
        report += f"  Avg Duration: {kpis.get('average_duration', 'N/A')}s\n\n"
        
        # AI metrics
        if kpis.get('intent_recognition_accuracy'):
            report += "AI QUALITY METRICS:\n"
            if kpis.get('intent_recognition_accuracy'):
                report += f"  Intent Accuracy: {kpis['intent_recognition_accuracy']}%\n"
            if kpis.get('entity_extraction_accuracy'):
                report += f"  Entity Accuracy: {kpis['entity_extraction_accuracy']}%\n"
            if kpis.get('task_completion_rate'):
                report += f"  Task Completion: {kpis['task_completion_rate']}%\n"
            if kpis.get('hallucination_rate'):
                report += f"  Hallucination Rate: {kpis['hallucination_rate']}%\n"
            if kpis.get('groundedness_score'):
                report += f"  Groundedness: {kpis['groundedness_score']}\n"
            report += "\n"
        
        # Performance
        report += "PERFORMANCE METRICS:\n"
        report += f"  P50 Response Time: {kpis.get('response_time_p50', 'N/A')}s\n"
        report += f"  P90 Response Time: {kpis.get('response_time_p90', 'N/A')}s\n"
        report += f"  P99 Response Time: {kpis.get('response_time_p99', 'N/A')}s\n\n"
        
        report += f"Total Tests: {kpis.get('total_tests', 0)}\n"
        report += f"KPIs Calculated: {kpis.get('kpis_available', 0)}\n"
        
        return report


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def calculate_test_kpis(test_results: List[Dict]) -> Dict:
    """
    Convenience function to calculate KPIs.
    
    Usage:
        kpis = calculate_test_kpis(test_results)
        print(f"Pass rate: {kpis['pass_rate']}%")
    """
    engine = KPIMetricsEngine()
    return engine.calculate_kpis(test_results)