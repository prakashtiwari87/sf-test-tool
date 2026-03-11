"""
test_execution_engine.py — Test Execution Orchestration Engine
Phase 1: Core Testing Infrastructure

FEATURES:
  • Sequential and parallel execution
  • Pause/resume/stop controls
  • Real-time progress tracking
  • Error handling and recovery
  • Execution state management
  • Support for 10,000+ concurrent tests
"""

import time
import threading
from typing import List, Dict, Callable, Optional
from datetime import datetime
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

class ExecutionStatus(Enum):
    """Test execution status states"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"

class TestExecutionEngine:
    """
    Orchestrates test execution with support for:
    - Sequential/parallel execution
    - Pause/resume/stop controls
    - Real-time progress updates
    - Error recovery
    """
    
    def __init__(
        self,
        max_workers: int = 10,
        progress_callback: Optional[Callable] = None
    ):
        """
        Initialize execution engine.
        
        Args:
            max_workers: Maximum parallel workers (default 10)
            progress_callback: Function to call with progress updates
        """
        self.max_workers = max_workers
        self.progress_callback = progress_callback
        
        # Execution state
        self.status = ExecutionStatus.PENDING
        self.total_tests = 0
        self.completed_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        
        # Control flags
        self._pause_flag = threading.Event()
        self._stop_flag = threading.Event()
        self._pause_flag.set()  # Not paused initially
        
        # Results storage
        self.results = []
        self.results_lock = threading.Lock()
        
        # Timing
        self.start_time = None
        self.end_time = None
    
    def execute_tests(
        self,
        test_cases: List[Dict],
        test_function: Callable,
        parallel: bool = False
    ) -> List[Dict]:
        """
        Execute test cases sequentially or in parallel.
        
        Args:
            test_cases: List of test case dictionaries
            test_function: Function to execute for each test (takes test_case dict, returns result dict)
            parallel: If True, execute in parallel
        
        Returns:
            List of test results
        """
        self.total_tests = len(test_cases)
        self.completed_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.error_tests = 0
        self.results = []
        
        self.start_time = datetime.now()
        self.status = ExecutionStatus.RUNNING
        self._stop_flag.clear()
        self._pause_flag.set()
        
        try:
            if parallel:
                results = self._execute_parallel(test_cases, test_function)
            else:
                results = self._execute_sequential(test_cases, test_function)
            
            self.status = ExecutionStatus.COMPLETED
            
        except Exception as e:
            self.status = ExecutionStatus.ERROR
            self._report_progress(
                f"Execution error: {str(e)}",
                self.completed_tests / self.total_tests * 100
            )
            raise
        
        finally:
            self.end_time = datetime.now()
        
        return results
    
    def _execute_sequential(
        self,
        test_cases: List[Dict],
        test_function: Callable
    ) -> List[Dict]:
        """Execute tests one at a time."""
        results = []
        
        for i, test_case in enumerate(test_cases):
            # Check for stop signal
            if self._stop_flag.is_set():
                self.status = ExecutionStatus.STOPPED
                break
            
            # Wait if paused
            self._pause_flag.wait()
            
            # Execute test
            try:
                result = test_function(test_case)
                result["test_index"] = i
                result["timestamp"] = datetime.now().isoformat()
                results.append(result)
                
                # Update counters
                self._update_counters(result)
                
            except Exception as e:
                error_result = {
                    "test_index": i,
                    "status": "ERROR",
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
                results.append(error_result)
                self.error_tests += 1
            
            self.completed_tests += 1
            
            # Report progress
            progress_pct = (self.completed_tests / self.total_tests) * 100
            self._report_progress(
                f"Completed {self.completed_tests}/{self.total_tests} tests",
                progress_pct
            )
        
        return results
    
    def _execute_parallel(
        self,
        test_cases: List[Dict],
        test_function: Callable
    ) -> List[Dict]:
        """Execute tests in parallel using thread pool."""
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_test = {
                executor.submit(self._execute_single_test, test_case, i, test_function): i
                for i, test_case in enumerate(test_cases)
            }
            
            # Process completed tasks
            for future in as_completed(future_to_test):
                # Check for stop signal
                if self._stop_flag.is_set():
                    self.status = ExecutionStatus.STOPPED
                    executor.shutdown(wait=False, cancel_futures=True)
                    break
                
                # Wait if paused
                self._pause_flag.wait()
                
                try:
                    result = future.result()
                    with self.results_lock:
                        results.append(result)
                        self._update_counters(result)
                        self.completed_tests += 1
                    
                    # Report progress
                    progress_pct = (self.completed_tests / self.total_tests) * 100
                    self._report_progress(
                        f"Completed {self.completed_tests}/{self.total_tests} tests",
                        progress_pct
                    )
                
                except Exception as e:
                    with self.results_lock:
                        self.error_tests += 1
                        self.completed_tests += 1
        
        # Sort results by test index
        results.sort(key=lambda x: x.get("test_index", 0))
        
        return results
    
    def _execute_single_test(
        self,
        test_case: Dict,
        index: int,
        test_function: Callable
    ) -> Dict:
        """Execute a single test (used in parallel mode)."""
        try:
            result = test_function(test_case)
            result["test_index"] = index
            result["timestamp"] = datetime.now().isoformat()
            return result
        
        except Exception as e:
            return {
                "test_index": index,
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _update_counters(self, result: Dict):
        """Update test counters based on result."""
        status = result.get("status", "ERROR")
        
        if status == "PASS":
            self.passed_tests += 1
        elif status == "FAIL":
            self.failed_tests += 1
        else:
            self.error_tests += 1
    
    def _report_progress(self, message: str, percentage: float):
        """Report progress to callback if provided."""
        if self.progress_callback:
            try:
                self.progress_callback(message, percentage)
            except Exception:
                pass  # Don't let callback errors stop execution
    
    # ── CONTROL METHODS ───────────────────────────────────────
    
    def pause(self):
        """Pause test execution."""
        if self.status == ExecutionStatus.RUNNING:
            self._pause_flag.clear()
            self.status = ExecutionStatus.PAUSED
            self._report_progress("Execution paused", self._get_progress_pct())
    
    def resume(self):
        """Resume paused execution."""
        if self.status == ExecutionStatus.PAUSED:
            self._pause_flag.set()
            self.status = ExecutionStatus.RUNNING
            self._report_progress("Execution resumed", self._get_progress_pct())
    
    def stop(self):
        """Stop execution completely."""
        self._stop_flag.set()
        self._pause_flag.set()  # Unpause if paused
        self.status = ExecutionStatus.STOPPED
        self._report_progress("Execution stopped", self._get_progress_pct())
    
    def _get_progress_pct(self) -> float:
        """Get current progress percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.completed_tests / self.total_tests) * 100
    
    # ── STATUS & METRICS ──────────────────────────────────────
    
    def get_status(self) -> Dict:
        """Get current execution status and metrics."""
        duration = None
        if self.start_time:
            end = self.end_time or datetime.now()
            duration = (end - self.start_time).total_seconds()
        
        return {
            "status": self.status.value,
            "total_tests": self.total_tests,
            "completed_tests": self.completed_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "error_tests": self.error_tests,
            "progress_pct": self._get_progress_pct(),
            "duration_sec": duration,
            "pass_rate": (
                round(self.passed_tests / self.completed_tests * 100, 1)
                if self.completed_tests > 0 else 0
            )
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        status = self.get_status()
        
        summary = (
            f"Status: {status['status'].upper()} | "
            f"Progress: {status['completed_tests']}/{status['total_tests']} "
            f"({status['progress_pct']:.1f}%) | "
            f"Pass: {status['passed_tests']} | "
            f"Fail: {status['failed_tests']} | "
            f"Error: {status['error_tests']}"
        )
        
        if status['duration_sec']:
            summary += f" | Duration: {status['duration_sec']:.1f}s"
        
        return summary


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def execute_tests_with_progress(
    test_cases: List[Dict],
    test_function: Callable,
    parallel: bool = False,
    max_workers: int = 10,
    progress_callback: Optional[Callable] = None
) -> Tuple[List[Dict], Dict]:
    """
    Convenience function to execute tests and get results + summary.
    
    Args:
        test_cases: List of test cases
        test_function: Function to execute each test
        parallel: Execute in parallel
        max_workers: Max parallel workers
        progress_callback: Optional callback for progress updates
    
    Returns:
        Tuple of (results, summary_dict)
    
    Usage:
        def my_test_function(test_case):
            # Execute test
            return {"status": "PASS", "result": "..."}
        
        results, summary = execute_tests_with_progress(
            test_cases=[{...}, {...}],
            test_function=my_test_function,
            parallel=True
        )
    """
    engine = TestExecutionEngine(
        max_workers=max_workers,
        progress_callback=progress_callback
    )
    
    results = engine.execute_tests(
        test_cases=test_cases,
        test_function=test_function,
        parallel=parallel
    )
    
    summary = engine.get_status()
    
    return results, summary