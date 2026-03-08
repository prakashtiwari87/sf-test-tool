import re
import json
from playwright.sync_api import sync_playwright

def run_ui_test(salesforce_instance_url, test_case, input_data, sf):
    """
    Run a UI-based test using Playwright browser automation.
    Navigates Salesforce pages, fills forms, clicks buttons, and captures results.
    """
    action = test_case.get("action", "").upper()
    page_path = test_case.get("ui_page_path", "")
    
    results_log = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # ── Authenticate via session token ──
            page.goto(salesforce_instance_url)
            page.evaluate(f"""
                document.cookie = 'sid={sf.session_id}; domain=.salesforce.com; path=/';
            """)

            target_url = f"{salesforce_instance_url}{page_path}" if page_path else salesforce_instance_url
            page.goto(target_url, wait_until="networkidle", timeout=30000)
            results_log.append(f"Navigated to: {target_url}")

            # ── Fill Form Fields ──
            if isinstance(input_data, dict) and action in ["CREATE", "EDIT", "POST"]:
                for field_name, field_value in input_data.items():
                    try:
                        # Try multiple selector strategies for Salesforce Lightning
                        selectors = [
                            f"input[placeholder*='{field_name}']",
                            f"[data-field='{field_name}'] input",
                            f"lightning-input[label*='{field_name}'] input",
                            f"[title='{field_name}']",
                            f"input[name='{field_name}']"
                        ]

                        filled = False
                        for selector in selectors:
                            elements = page.query_selector_all(selector)
                            if elements:
                                elements[0].fill(str(field_value))
                                results_log.append(f"✅ Filled '{field_name}' with '{field_value}'")
                                filled = True
                                break

                        if not filled:
                            results_log.append(f"⚠️ Could not find field '{field_name}' on page")

                    except Exception as e:
                        results_log.append(f"❌ Error filling '{field_name}': {str(e)}")

                # Click Save
                try:
                    page.click("button:has-text('Save')", timeout=5000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                    results_log.append("✅ Clicked Save button")
                except Exception:
                    results_log.append("⚠️ Could not click Save — button may have different label")

            # ── Verify / Read content ──
            elif action in ["VERIFY", "READ", "GET"]:
                content = page.inner_text("body")
                results_log.append(f"Page content captured ({len(content)} chars)")
                results_log.append(content[:1000])

            # ── Click specific element ──
            elif action == "CLICK":
                target = str(input_data)
                try:
                    page.click(f"button:has-text('{target}')", timeout=5000)
                    results_log.append(f"✅ Clicked: {target}")
                except Exception:
                    try:
                        page.click(f"a:has-text('{target}')", timeout=5000)
                        results_log.append(f"✅ Clicked link: {target}")
                    except Exception as e:
                        results_log.append(f"❌ Could not click '{target}': {str(e)}")

            # Capture final page state
            final_content = page.inner_text("body")
            results_log.append(f"Final page state: {final_content[:500]}")

            # Check for error toasts
            error_indicators = page.query_selector_all(".forceInlineMessage.error, .slds-theme--error")
            if error_indicators:
                results_log.append("⚠️ Error indicator found on page")

            browser.close()

        return "\n".join(results_log), None

    except Exception as e:
        return "\n".join(results_log), f"UI Test Error: {str(e)}"