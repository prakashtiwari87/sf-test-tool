"""
page_init.py — Drop-in page initialiser for every AmplifyQA inner page.

Usage (top of EVERY page after st.set_page_config):
    from config.page_init import page_init
    sf, org = page_init()

What it does:
  1. Injects early sidebar-kill CSS + MutationObserver (eliminates flash).
  2. Injects full design system CSS + fixed top navbar.
  3. Auto-connects Salesforce from saved credentials (if not already connected).
  4. Returns (sf_connection, org_info_dict) so each page can use them.

IMPORTANT: Each inner page's st.set_page_config() MUST include:
    initial_sidebar_state="collapsed"
This ensures Streamlit never attempts to render the sidebar at all.
"""

import streamlit as st

from config.settings_manager import (
    init_database,
    load_all_keys_to_env,
    get_active_salesforce_connection,
)
from config.theme import inject_css


def page_init(page_title: str = "AmplifyQA",
              org_name_override: str = "") -> tuple:
    """
    Call immediately after st.set_page_config().
    Returns (sf_connection | None, org_info_dict).
    """
    # ── DB + env keys ────────────────────────────────────────────
    init_database()
    load_all_keys_to_env()

    # ── Salesforce auto-connect ──────────────────────────────────
    sf  = st.session_state.get("sf_connection")
    org = st.session_state.get("sf_org_info", {})

    if not sf:
        active = get_active_salesforce_connection()
        if active and active.get("client_id"):
            try:
                from connectors.salesforce_connector import (
                    connect_with_oauth, get_org_info
                )
                sf_try, _ = connect_with_oauth(
                    client_id=active["client_id"],
                    client_secret=active["client_secret"],
                    domain=active["domain"],
                )
                if sf_try:
                    oi = get_org_info(sf_try)
                    st.session_state.sf_connection = sf_try
                    st.session_state.sf_org_info   = oi
                    sf  = sf_try
                    org = oi
            except Exception:
                pass  # Silently skip — page will show "not connected"

    # ── Inject CSS + navbar ──────────────────────────────────────
    display_name = org_name_override or org.get("org_name", "")
    inject_css(org_name=display_name, sf_connected=bool(sf))

    return sf, org