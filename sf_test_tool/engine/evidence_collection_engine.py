"""
evidence_collection_engine.py — Evidence Collection Engine
Phase 1: Core Testing Infrastructure

FEATURES:
  • Screenshot capture (Playwright)
  • Video recording (browser sessions)
  • API request/response logging
  • Database state snapshots
  • File organization and storage
  • Optional enable/disable per test
"""

import os
import json
import base64
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path

# Optional imports - gracefully handle if not installed
try:
    from playwright.sync_api import sync_playwright, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

class EvidenceCollector:
    """
    Collects test evidence including screenshots, videos, and logs.
    """
    
    def __init__(
        self,
        evidence_dir: str = "./evidence",
        enable_screenshots: bool = True,
        enable_video: bool = False,
        enable_api_logs: bool = True
    ):
        """
        Initialize evidence collector.
        
        Args:
            evidence_dir: Directory to store evidence files
            enable_screenshots: Capture screenshots
            enable_video: Record video
            enable_api_logs: Log API requests/responses
        """
        self.evidence_dir = Path(evidence_dir)
        self.enable_screenshots = enable_screenshots and PLAYWRIGHT_AVAILABLE
        self.enable_video = enable_video and CV2_AVAILABLE
        self.enable_api_logs = enable_api_logs
        
        # Create directories
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.screenshots_dir = self.evidence_dir / "screenshots"
        self.videos_dir = self.evidence_dir / "videos"
        self.logs_dir = self.evidence_dir / "logs"
        
        if self.enable_screenshots:
            self.screenshots_dir.mkdir(exist_ok=True)
        if self.enable_video:
            self.videos_dir.mkdir(exist_ok=True)
        if self.enable_api_logs:
            self.logs_dir.mkdir(exist_ok=True)
        
        # Current test context
        self.current_test_id = None
        self.current_evidence = {}
        
        # API log buffer
        self.api_logs = []
    
    def start_test(self, test_id: str):
        """Start evidence collection for a test."""
        self.current_test_id = test_id
        self.current_evidence = {
            "test_id": test_id,
            "screenshots": [],
            "videos": [],
            "api_logs": [],
            "start_time": datetime.now().isoformat()
        }
        self.api_logs = []
    
    def end_test(self) -> Dict:
        """
        End evidence collection and return summary.
        
        Returns:
            Dict with paths to all collected evidence
        """
        if self.current_evidence:
            self.current_evidence["end_time"] = datetime.now().isoformat()
            self.current_evidence["api_logs"] = self.api_logs.copy()
        
        evidence = self.current_evidence
        self.current_evidence = {}
        self.api_logs = []
        self.current_test_id = None
        
        return evidence
    
    # ── SCREENSHOT CAPTURE ────────────────────────────────────
    
    def capture_screenshot(
        self,
        page: Optional[object] = None,
        url: Optional[str] = None,
        label: str = "screenshot"
    ) -> Optional[str]:
        """
        Capture screenshot of current page state.
        
        Args:
            page: Playwright page object (if available)
            url: URL to screenshot (if page not provided)
            label: Label for the screenshot
        
        Returns:
            Path to screenshot file
        """
        if not self.enable_screenshots:
            return None
        
        if not PLAYWRIGHT_AVAILABLE:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{self.current_test_id}_{label}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        
        try:
            if page:
                # Use provided page object
                page.screenshot(path=str(filepath), full_page=True)
            elif url:
                # Create new page for URL
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    new_page = browser.new_page()
                    new_page.goto(url, wait_until="networkidle")
                    new_page.screenshot(path=str(filepath), full_page=True)
                    browser.close()
            else:
                return None
            
            # Add to evidence
            if self.current_evidence:
                self.current_evidence["screenshots"].append({
                    "label": label,
                    "path": str(filepath),
                    "timestamp": datetime.now().isoformat()
                })
            
            return str(filepath)
        
        except Exception as e:
            print(f"Screenshot capture failed: {e}")
            return None
    
    def screenshot_element(
        self,
        page: object,
        selector: str,
        label: str = "element"
    ) -> Optional[str]:
        """
        Capture screenshot of specific element.
        
        Args:
            page: Playwright page object
            selector: CSS selector for element
            label: Label for screenshot
        
        Returns:
            Path to screenshot file
        """
        if not self.enable_screenshots or not PLAYWRIGHT_AVAILABLE:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{self.current_test_id}_{label}_{timestamp}.png"
        filepath = self.screenshots_dir / filename
        
        try:
            element = page.locator(selector)
            element.screenshot(path=str(filepath))
            
            if self.current_evidence:
                self.current_evidence["screenshots"].append({
                    "label": label,
                    "path": str(filepath),
                    "selector": selector,
                    "timestamp": datetime.now().isoformat()
                })
            
            return str(filepath)
        
        except Exception as e:
            print(f"Element screenshot failed: {e}")
            return None
    
    # ── VIDEO RECORDING ───────────────────────────────────────
    
    def start_video_recording(self, page: object) -> bool:
        """
        Start recording video of browser session.
        
        Args:
            page: Playwright page object
        
        Returns:
            True if recording started successfully
        """
        if not self.enable_video or not PLAYWRIGHT_AVAILABLE:
            return False
        
        try:
            # Playwright's built-in video recording
            # This needs to be enabled when creating the context
            return True
        except Exception as e:
            print(f"Video recording start failed: {e}")
            return False
    
    def stop_video_recording(self, page: object) -> Optional[str]:
        """
        Stop video recording and save file.
        
        Returns:
            Path to video file
        """
        if not self.enable_video:
            return None
        
        try:
            # Get video path from Playwright context
            video_path = page.video.path() if hasattr(page, 'video') else None
            
            if video_path and self.current_evidence:
                self.current_evidence["videos"].append({
                    "path": str(video_path),
                    "timestamp": datetime.now().isoformat()
                })
            
            return str(video_path) if video_path else None
        
        except Exception as e:
            print(f"Video recording stop failed: {e}")
            return None
    
    # ── API LOGGING ───────────────────────────────────────────
    
    def log_api_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict] = None,
        body: Optional[str] = None
    ):
        """Log an API request."""
        if not self.enable_api_logs:
            return
        
        log_entry = {
            "type": "request",
            "method": method,
            "url": url,
            "headers": headers or {},
            "body": body,
            "timestamp": datetime.now().isoformat()
        }
        
        self.api_logs.append(log_entry)
    
    def log_api_response(
        self,
        status_code: int,
        headers: Optional[Dict] = None,
        body: Optional[str] = None,
        duration_ms: Optional[float] = None
    ):
        """Log an API response."""
        if not self.enable_api_logs:
            return
        
        log_entry = {
            "type": "response",
            "status_code": status_code,
            "headers": headers or {},
            "body": body,
            "duration_ms": duration_ms,
            "timestamp": datetime.now().isoformat()
        }
        
        self.api_logs.append(log_entry)
    
    def save_api_logs(self) -> Optional[str]:
        """
        Save API logs to file.
        
        Returns:
            Path to log file
        """
        if not self.enable_api_logs or not self.api_logs:
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.current_test_id}_api_logs_{timestamp}.json"
        filepath = self.logs_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(self.api_logs, f, indent=2)
            
            return str(filepath)
        
        except Exception as e:
            print(f"API log save failed: {e}")
            return None
    
    # ── DATABASE STATE ────────────────────────────────────────
    
    def snapshot_database_state(
        self,
        query_results: Dict,
        label: str = "db_snapshot"
    ) -> Optional[str]:
        """
        Save database query results as evidence.
        
        Args:
            query_results: Dict of query results
            label: Label for snapshot
        
        Returns:
            Path to snapshot file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.current_test_id}_{label}_{timestamp}.json"
        filepath = self.logs_dir / filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(query_results, f, indent=2)
            
            return str(filepath)
        
        except Exception as e:
            print(f"Database snapshot failed: {e}")
            return None
    
    # ── EVIDENCE RETRIEVAL ────────────────────────────────────
    
    def get_evidence_summary(self, test_id: str) -> Dict:
        """
        Get summary of all evidence for a test.
        
        Returns:
            Dict with paths and metadata
        """
        summary = {
            "test_id": test_id,
            "screenshots": [],
            "videos": [],
            "logs": []
        }
        
        # Find all files for this test
        for screenshot in self.screenshots_dir.glob(f"{test_id}*.png"):
            summary["screenshots"].append(str(screenshot))
        
        for video in self.videos_dir.glob(f"{test_id}*.webm"):
            summary["videos"].append(str(video))
        
        for log in self.logs_dir.glob(f"{test_id}*.json"):
            summary["logs"].append(str(log))
        
        return summary
    
    def cleanup_old_evidence(self, days_old: int = 30):
        """
        Delete evidence files older than specified days.
        
        Args:
            days_old: Delete files older than this many days
        """
        import time
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        
        for directory in [self.screenshots_dir, self.videos_dir, self.logs_dir]:
            for file in directory.glob("*"):
                if file.stat().st_mtime < cutoff_time:
                    try:
                        file.unlink()
                    except Exception:
                        pass


# ══════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════

def create_evidence_collector(
    test_id: str,
    evidence_dir: str = "./evidence",
    screenshots: bool = True,
    video: bool = False,
    api_logs: bool = True
) -> EvidenceCollector:
    """
    Create and initialize an evidence collector for a test.
    
    Usage:
        collector = create_evidence_collector(
            test_id="TEST-001",
            screenshots=True,
            video=True
        )
        
        collector.start_test("TEST-001")
        collector.capture_screenshot(page=page, label="login_page")
        evidence = collector.end_test()
    """
    collector = EvidenceCollector(
        evidence_dir=evidence_dir,
        enable_screenshots=screenshots,
        enable_video=video,
        enable_api_logs=api_logs
    )
    
    collector.start_test(test_id)
    
    return collector