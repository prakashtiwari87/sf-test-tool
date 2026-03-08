"""
theme.py — AmplifyQA Global Design System
NeuraFlash - Part of Accenture  |  v5

CHANGES IN v5
  1.  Salesforce org connection pill REMOVED from navbar right-side.
      inject_css() still accepts org_name/sf_connected params (backward compat)
      but the pill is no longer rendered in the navbar HTML.
  2.  Logo container now uses full navbar height (72px) with object-fit:contain
      and object-position:left center — logo fills the full red-boxed area
      without any distortion of the original aspect ratio.
  3.  Home and Settings tabs: white-space:nowrap so they never truncate.
  4.  Flash-of-sidebar ELIMINATED via MutationObserver + staggered timers.
  5.  All other v4 design system rules preserved.
"""

import os
import base64

# ─────────────────────────────────────────────────────────────
# BRAND PALETTE
# ─────────────────────────────────────────────────────────────
NAVY     = "#1a2744"
TEAL     = "#2ec4b6"
LIGHT_BG = "#f5f8fb"


def _logo_base64() -> str:
    logo_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "assets", "logo.png"
    )
    try:
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


# ─────────────────────────────────────────────────────────────
# EARLY-INJECT CSS + MutationObserver (kills sidebar flash)
# ─────────────────────────────────────────────────────────────
_EARLY_CSS = """
<style id="aqa-early-hide">
[data-testid="stSidebarNav"],
[data-testid="stSidebar"],
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],
section[data-testid="stSidebar"],
div[data-testid="stSidebarUserContent"],
button[data-testid="stSidebarCollapseButton"],
.st-emotion-cache-1gv3r4d,
.st-emotion-cache-aw8t99,
.st-emotion-cache-16idsys,
.st-emotion-cache-1egp75f,
.css-1d391kg, .css-18e3th9,
nav[data-testid="stSidebarNav"] {
    display:none!important;visibility:hidden!important;
    width:0!important;min-width:0!important;max-width:0!important;
    overflow:hidden!important;opacity:0!important;pointer-events:none!important;
    position:fixed!important;left:-9999px!important;
}
#MainMenu,footer,header,.stDeployButton{display:none!important;visibility:hidden!important;}
.main,[data-testid="stAppViewContainer"]>.main{margin-left:0!important;padding-left:0!important;}
</style>
<script>
(function(){
  var css='[data-testid="stSidebar"],[data-testid="stSidebarNav"],'
    +'[data-testid="collapsedControl"],[data-testid="stSidebarCollapsedControl"],'
    +'[data-testid="stSidebarCollapseButton"],section[data-testid="stSidebar"],'
    +'button[data-testid="stSidebarCollapseButton"],'
    +'.css-1d391kg,.css-18e3th9,.st-emotion-cache-1gv3r4d,.st-emotion-cache-aw8t99'
    +'{display:none!important;visibility:hidden!important;width:0!important;'
    +'min-width:0!important;opacity:0!important;pointer-events:none!important;'
    +'position:fixed!important;left:-9999px!important;}';
  function inject(){var e=document.createElement('style');e.textContent=css;(document.head||document.documentElement).appendChild(e);}
  inject();
  document.addEventListener('DOMContentLoaded',inject);
  [50,150,400,900,1800].forEach(function(t){setTimeout(inject,t);});
  var K='display:none!important;visibility:hidden!important;width:0!important;min-width:0!important;opacity:0!important;pointer-events:none!important;position:fixed!important;left:-9999px!important;';
  function kill(n){if(!n||!n.getAttribute)return;var t=(n.getAttribute('data-testid')||'').toLowerCase();if(t.indexOf('sidebar')>=0||t==='collapsedcontrol')n.style.cssText=K;}
  var obs=new MutationObserver(function(ms){ms.forEach(function(m){m.addedNodes.forEach(function(n){kill(n);if(n.querySelectorAll)n.querySelectorAll('[data-testid*="sidebar"],[data-testid*="Sidebar"],[data-testid="collapsedControl"],[data-testid="stSidebarCollapseButton"]').forEach(kill);});});});
  function start(){obs.observe(document.documentElement,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
})();
</script>
"""


# ─────────────────────────────────────────────────────────────
# MAIN CSS — full NeuraFlash / Accenture design system
# ─────────────────────────────────────────────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ── SIDEBAR WIPE (belt+braces) ─────────────────────────────── */
[data-testid="stSidebarNav"],[data-testid="stSidebar"],
[data-testid="collapsedControl"],[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapseButton"],section[data-testid="stSidebar"],
div[data-testid="stSidebarUserContent"],button[data-testid="stSidebarCollapseButton"],
.css-1d391kg,.css-18e3th9,.st-emotion-cache-1gv3r4d,.st-emotion-cache-aw8t99{
    display:none!important;visibility:hidden!important;
    width:0!important;min-width:0!important;max-width:0!important;
    opacity:0!important;position:fixed!important;left:-9999px!important;
}
#MainMenu,footer,header,.stDeployButton{display:none!important;visibility:hidden!important;}

/* ── CONTENT OFFSET below 72px navbar ───────────────────────── */
.main .block-container,[data-testid="stMainBlockContainer"],.block-container{
    padding-top:88px!important;padding-left:36px!important;
    padding-right:36px!important;max-width:1440px!important;margin:0 auto!important;
}
.main,[data-testid="stAppViewContainer"]>.main{margin-left:0!important;}

/* ── BASE ────────────────────────────────────────────────────── */
html,body,[class*="css"],.stApp{
    font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif!important;
    -webkit-font-smoothing:antialiased!important;
}
.stApp{background:#f5f8fb!important;}

/* ════════════════════════════════════════════════════════════
   FIXED TOP NAVBAR  (72px tall)
════════════════════════════════════════════════════════════ */
#aqanav{
    position:fixed;top:0;left:0;right:0;z-index:999999;
    height:72px;
    background:linear-gradient(135deg,#0d1628 0%,#1a2744 55%,#1e3040 100%);
    display:flex;align-items:center;padding:0 28px;
    box-shadow:0 3px 28px rgba(0,0,0,0.5);
    border-bottom:1px solid rgba(46,196,182,0.2);
    box-sizing:border-box;gap:0;
}

/* ── Logo — fills full navbar height, no distortion ─────────── */
#aqanav .anav-logo{
    display:flex;align-items:center;
    width:240px;          /* wide enough for the logo image */
    min-width:200px;
    max-width:260px;
    height:72px;          /* full navbar height */
    flex-shrink:0;
    text-decoration:none!important;cursor:pointer;
    overflow:hidden;
    padding:5px 0;        /* tiny vertical breathing room */
    box-sizing:border-box;
}
#aqanav .anav-logo img{
    height:100%;          /* fill container height */
    width:100%;
    object-fit:contain;   /* keep original aspect ratio */
    object-position:left center;
    display:block;
    filter:drop-shadow(0 2px 8px rgba(0,0,0,0.35));
}
#aqanav .anav-logo-fallback{display:flex;flex-direction:column;gap:2px;}
#aqanav .anav-logo-name{font-size:20px;font-weight:900;color:white!important;letter-spacing:-0.6px;line-height:1.15;white-space:nowrap;}
#aqanav .anav-logo-tag{font-size:9.5px;color:#2ec4b6!important;text-transform:uppercase;letter-spacing:1.4px;font-weight:600;white-space:nowrap;}

/* ── Divider ─────────────────────────────────────────────────── */
#aqanav .anav-divider{width:1px;height:38px;background:rgba(255,255,255,0.1);margin:0 20px;flex-shrink:0;}

/* ── Nav links ────────────────────────────────────────────────── */
#aqanav .anav-links{flex:1;display:flex;align-items:center;justify-content:center;gap:2px;overflow:hidden;}
#aqanav .anav-links a{
    color:rgba(255,255,255,0.78)!important;text-decoration:none!important;
    font-size:15px!important;font-weight:500!important;
    padding:10px 17px!important;border-radius:9px!important;
    transition:all 0.18s ease!important;
    white-space:nowrap!important;       /* ← prevents truncation */
    display:inline-flex!important;align-items:center!important;
    gap:6px!important;border:1px solid transparent!important;line-height:1!important;
}
#aqanav .anav-links a:hover{background:rgba(46,196,182,0.14)!important;color:white!important;border-color:rgba(46,196,182,0.34)!important;}
#aqanav .anav-links a.anav-active{background:rgba(46,196,182,0.22)!important;color:#2ec4b6!important;font-weight:700!important;border-color:rgba(46,196,182,0.48)!important;}

/* ── Separators ──────────────────────────────────────────────── */
#aqanav .anav-sep{width:1px;height:26px;background:rgba(255,255,255,0.1);margin:0 4px;flex-shrink:0;}

/* ════════════════════════════════════════════════════════════
   PAGE SUB-HEADER
════════════════════════════════════════════════════════════ */
.amplify-header{
    background:linear-gradient(135deg,#1a2744 0%,#1e4060 60%,#2ec4b6 100%);
    padding:18px 28px;border-radius:16px;margin-bottom:24px;
    display:flex;align-items:center;justify-content:space-between;
    box-shadow:0 4px 24px rgba(26,39,68,0.28);border:1px solid rgba(46,196,182,0.22);
}
.amplify-header,.amplify-header *{color:#ffffff!important;}
.amplify-header .brand-title{font-size:21px!important;font-weight:900!important;letter-spacing:-0.5px;margin:0;color:#ffffff!important;}
.amplify-header .brand-sub{font-size:12.5px!important;color:rgba(255,255,255,0.82)!important;margin:3px 0 0;font-weight:400;}
.amplify-header .header-right{display:flex;align-items:center;gap:12px;}

/* ════════════════════════════════════════════════════════════
   HERO BANNER
════════════════════════════════════════════════════════════ */
.hero-wrap{
    background:linear-gradient(135deg,#0d1628 0%,#1a2744 40%,#1e4060 70%,#2ec4b6 100%);
    padding:60px 52px;border-radius:22px;margin-bottom:32px;
    position:relative;overflow:hidden;
}
.hero-wrap,.hero-wrap p,.hero-wrap h1,.hero-wrap h2,.hero-wrap h3,
.hero-wrap span,.hero-wrap strong,.hero-wrap div,.hero-wrap li,.hero-wrap em{color:#ffffff!important;}
.hero-wrap::before{content:'';position:absolute;top:-100px;right:-80px;width:400px;height:400px;background:rgba(46,196,182,0.06);border-radius:50%;pointer-events:none;}
.hero-wrap::after{content:'';position:absolute;bottom:-120px;left:20%;width:520px;height:520px;background:rgba(255,255,255,0.025);border-radius:50%;pointer-events:none;}
.hero-wrap h1{font-size:48px!important;font-weight:900!important;line-height:1.1!important;margin:0 0 18px!important;letter-spacing:-2px!important;color:#ffffff!important;}
.hero-badge{display:inline-flex;align-items:center;gap:7px;background:rgba(46,196,182,0.22);border:1px solid rgba(46,196,182,0.45);color:#2ec4b6!important;padding:7px 18px;border-radius:20px;font-size:13px;font-weight:700;margin-bottom:20px;}
.hero-sub{font-size:16px!important;line-height:1.8!important;color:rgba(255,255,255,0.92)!important;max-width:720px;}
.hero-stat{text-align:center;padding:24px 16px;background:rgba(255,255,255,0.1);border-radius:16px;border:1px solid rgba(255,255,255,0.18);backdrop-filter:blur(8px);transition:all 0.22s;}
.hero-stat:hover{background:rgba(46,196,182,0.18);border-color:rgba(46,196,182,0.42);transform:translateY(-3px);}
.hero-stat .snum{font-size:38px!important;font-weight:900!important;color:#ffffff!important;display:block;letter-spacing:-1.5px;}
.hero-stat .slbl{font-size:12px!important;color:rgba(255,255,255,0.78)!important;text-transform:uppercase;letter-spacing:0.7px;margin-top:5px;display:block;}

/* ── CARDS ───────────────────────────────────────────────────── */
.aqa-card{background:white;border-radius:16px;padding:22px;box-shadow:0 2px 16px rgba(0,0,0,0.06);border:1px solid rgba(26,39,68,0.08);transition:all 0.2s ease;height:100%;}
.aqa-card:hover{box-shadow:0 8px 32px rgba(26,39,68,0.14);transform:translateY(-2px);border-color:rgba(46,196,182,0.24);}
.aqa-card h3{font-size:15px;font-weight:700;color:#1a2744!important;margin:10px 0 7px;}
.aqa-card p{font-size:13px;color:#6b7280!important;line-height:1.65;margin:0;}

/* ── WIZARD ──────────────────────────────────────────────────── */
.wizard-box{background:white;border-radius:18px;padding:32px;box-shadow:0 4px 28px rgba(0,0,0,0.08);border:1px solid rgba(46,196,182,0.14);margin-bottom:22px;}
.wizard-step-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:#2ec4b6;margin-bottom:6px;}
.wizard-title{font-size:21px;font-weight:800;color:#1a2744;margin:0 0 5px;letter-spacing:-0.5px;}
.wizard-sub{font-size:14px;color:#6b7280;margin:0;}

/* ── OPTION CARDS ────────────────────────────────────────────── */
.option-card{background:white;border:2px solid #e5e7eb;border-radius:16px;padding:26px 18px;text-align:center;transition:all 0.2s;cursor:pointer;margin-bottom:8px;}
.option-card:hover{border-color:#2ec4b6;box-shadow:0 4px 20px rgba(46,196,182,0.18);transform:translateY(-2px);}
.option-card .icon{font-size:40px;margin-bottom:12px;}
.option-card h4{font-size:14px;font-weight:700;color:#1a2744;margin:0 0 5px;}
.option-card p{font-size:12px;color:#6b7280;margin:0;line-height:1.5;}

/* ── PILLS ───────────────────────────────────────────────────── */
.pill{display:inline-flex;align-items:center;gap:4px;padding:3px 12px;border-radius:20px;font-size:12px;font-weight:600;}
.pill-green{background:#d1fae5;color:#065f46!important;}
.pill-red{background:#fee2e2;color:#991b1b!important;}
.pill-amber{background:#fef3c7;color:#92400e!important;}
.pill-blue{background:#dbeafe;color:#1e40af!important;}
.pill-purple{background:#ede9fe;color:#5b21b6!important;}
.pill-teal{background:#ccfbf1;color:#065f46!important;}

/* ── KPI TILES ───────────────────────────────────────────────── */
.kpi-tile{background:white;border-radius:14px;padding:18px 22px;text-align:center;box-shadow:0 2px 12px rgba(0,0,0,0.06);border-top:4px solid #2ec4b6;}
.kpi-tile.green{border-color:#10b981;}.kpi-tile.red{border-color:#ef4444;}
.kpi-tile.amber{border-color:#f59e0b;}.kpi-tile.navy{border-color:#1a2744;}
.kpi-num{font-size:36px;font-weight:900;color:#1a2744;line-height:1;letter-spacing:-1px;}
.kpi-lbl{font-size:11px;color:#6b7280;text-transform:uppercase;letter-spacing:0.6px;margin-top:5px;}

/* ── BUTTONS ─────────────────────────────────────────────────── */
.stButton>button{border-radius:10px!important;font-weight:600!important;font-family:'Inter',sans-serif!important;transition:all 0.2s ease!important;}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#1a2744,#2ec4b6)!important;border:none!important;color:white!important;box-shadow:0 2px 12px rgba(46,196,182,0.32)!important;}
.stButton>button[kind="primary"]:hover{box-shadow:0 4px 20px rgba(46,196,182,0.48)!important;transform:translateY(-1px)!important;}

/* ── INPUTS ──────────────────────────────────────────────────── */
.stTextInput>div>div>input,.stTextArea>div>div>textarea{border-radius:10px!important;border-color:#e5e7eb!important;font-family:'Inter',sans-serif!important;font-size:14px!important;}
.stTextInput>div>div>input:focus,.stTextArea>div>div>textarea:focus{border-color:#2ec4b6!important;box-shadow:0 0 0 3px rgba(46,196,182,0.14)!important;}

/* ── TABS ────────────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"]{gap:4px;background:#eef2f8;padding:5px;border-radius:12px;}
.stTabs [data-baseweb="tab"]{border-radius:9px!important;font-weight:600!important;font-size:14px!important;color:#6b7280!important;padding:9px 18px!important;}
.stTabs [aria-selected="true"]{background:white!important;color:#1a2744!important;box-shadow:0 1px 6px rgba(0,0,0,0.1)!important;}

/* ── EXPANDERS ───────────────────────────────────────────────── */
.streamlit-expanderHeader{background:#f5f8fb!important;border-radius:10px!important;font-weight:600!important;font-family:'Inter',sans-serif!important;color:#1a2744!important;}

/* ── METRICS ─────────────────────────────────────────────────── */
[data-testid="stMetric"]{background:white;border-radius:12px;padding:14px 18px;box-shadow:0 1px 8px rgba(0,0,0,0.05);border:1px solid #f3f4f6;}
[data-testid="stMetricValue"]{font-family:'Inter',sans-serif!important;font-weight:800!important;color:#1a2744!important;}

/* ── SCROLLBAR ───────────────────────────────────────────────── */
::-webkit-scrollbar{width:5px;height:5px;}
::-webkit-scrollbar-track{background:#f1f5f9;}
::-webkit-scrollbar-thumb{background:linear-gradient(#1a2744,#2ec4b6);border-radius:3px;}

/* ── SECTION DIVIDER ─────────────────────────────────────────── */
.sec-head{display:flex;align-items:center;gap:10px;margin:26px 0 14px;}
.sec-head span{font-size:16px;font-weight:700;color:#1a2744;white-space:nowrap;}
.sec-head hr{flex:1;border:none;border-top:1px solid #e5e7eb;margin:0;}

/* ── FADE IN ─────────────────────────────────────────────────── */
@keyframes fadeUp{from{opacity:0;transform:translateY(16px);}to{opacity:1;transform:translateY(0);}}
.fade-in{animation:fadeUp 0.38s ease forwards;}

/* ── BRAND FOOTER ────────────────────────────────────────────── */
.brand-footer{margin-top:40px;padding:18px 28px;background:linear-gradient(135deg,#0d1628,#1a2744);border-radius:14px;display:flex;align-items:center;justify-content:space-between;font-size:12px;}
.brand-footer,.brand-footer *{color:rgba(255,255,255,0.82)!important;}
.brand-footer strong{color:#2ec4b6!important;}
.brand-footer-right{font-size:11px;opacity:0.7;}

/* ── PLATFORM HEADERS ────────────────────────────────────────── */
.sf-hero{background:linear-gradient(135deg,#003366 0%,#0070d2 100%);border-radius:16px;padding:28px;border:1px solid rgba(0,161,224,0.3);}
.sf-hero,.sf-hero *{color:#ffffff!important;}
.bedrock-hero{background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);border-radius:16px;padding:26px;border:1px solid rgba(251,191,36,0.18);box-shadow:0 4px 24px rgba(0,0,0,0.2);}
.bedrock-hero,.bedrock-hero *{color:#ffffff!important;}
.bedrock-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(251,191,36,0.12);border:1px solid rgba(251,191,36,0.28);color:#fbbf24!important;padding:4px 14px;border-radius:20px;font-size:11px;font-weight:700;letter-spacing:0.5px;margin-bottom:12px;}
.agentforce-hero{background:linear-gradient(135deg,#0c1445 0%,#1a237e 100%);border-radius:16px;padding:26px;border:1px solid rgba(99,102,241,0.3);}
.agentforce-hero,.agentforce-hero *{color:#ffffff!important;}

/* ── RUNNER BADGES ───────────────────────────────────────────── */
.badge-pass{background:#d1fae5;color:#065f46!important;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;}
.badge-fail{background:#fee2e2;color:#9b1c1c!important;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;}
.badge-error{background:#fef3c7;color:#92400e!important;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:700;}
.scenario-pass{border-left:4px solid #059669!important;}
.scenario-fail{border-left:4px solid #dc2626!important;}
.scenario-error{border-left:4px solid #d97706!important;}
</style>
"""


# ─────────────────────────────────────────────────────────────
# NAVBAR BUILDER
# ─────────────────────────────────────────────────────────────

_SF_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 44'%3E"
    "%3Cpath fill='%2300a1e0' d='M26.1 4.3C28.7 1.6 32.4 0 36.4 0c6.1 0 11.4 3.4 "
    "14.2 8.5 1.1-.5 2.4-.8 3.7-.8 5.2 0 9.5 4.2 9.5 9.4s-4.3 9.4-9.5 9.4H16c-6.6 "
    "0-12-5.4-12-12.1C4 8.7 8 4.1 13.3 3.7c3.1.1 5.9 1.3 7.9 3.2L26.1 4.3z'/%3E%3C/svg%3E"
)
_AF_SVG = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E"
    "%3Ccircle cx='12' cy='8' r='4' fill='%23a78bfa'/%3E"
    "%3Crect x='4' y='14' width='16' height='8' rx='4' fill='%23a78bfa'/%3E%3C/svg%3E"
)


def _build_navbar_html(logo_b64: str, org_name: str = "",
                       sf_connected: bool = False) -> str:
    """
    Builds fixed top navbar HTML.
    Connection pill intentionally omitted (v5 — Issue 1 fix).
    org_name / sf_connected params retained for backward compat only.
    """
    if logo_b64:
        logo_inner = (
            '<img src="data:image/png;base64,' + logo_b64 + '"'
            ' alt="AmplifyQA"/>'
        )
    else:
        logo_inner = (
            '<div class="anav-logo-fallback">'
            '<span class="anav-logo-name">⚡ AmplifyQA</span>'
            '<span class="anav-logo-tag">NeuraFlash - Part of Accenture</span>'
            '</div>'
        )

    nav = [
        ("/",
         '<span style="font-size:16px;">🏠</span>',
         "Home"),
        ("/Salesforce_Testing",
         '<img src="' + _SF_SVG + '" style="height:14px;width:auto;vertical-align:middle;"/>',
         "Salesforce"),
        ("/Agentforce_Testing",
         '<img src="' + _AF_SVG + '" style="height:14px;width:auto;vertical-align:middle;"/>',
         "Agentforce"),
        ("/Bedrock_AgentCore_Testing",
         '<span style="color:#FF9900;font-size:13px;font-weight:800;">AWS</span>',
         "Bedrock"),
        None,
        ("/Reports",
         '<span style="color:#34d399;font-size:14px;">▲</span>',
         "Reports"),
        ("/Test_History",
         '<span style="color:#60a5fa;font-size:14px;">◷</span>',
         "History"),
        ("/Metadata_Explorer",
         '<span style="color:#f9a8d4;font-size:14px;">◎</span>',
         "Metadata"),
        None,
        ("/Settings",
         '<span style="color:#cbd5e0;font-size:14px;">⚙</span>',
         "Settings"),
    ]

    sep   = '<div class="anav-sep"></div>'
    links = ""
    for item in nav:
        if item is None:
            links += sep
            continue
        url, icon, label = item
        links += (
            '<a href="' + url + '"'
            ' class="anav-link" data-navpath="' + url + '"'
            ' target="_top">'
            + icon + '&nbsp;' + label +
            '</a>'
        )

    js = (
        '<script>'
        '(function(){'
        'var run=function(){'
        'try{'
        'var p=(window.top||window).location.pathname;'
        'document.querySelectorAll(".anav-link").forEach(function(a){'
        'var h=a.getAttribute("data-navpath");'
        'var m=(h==="/"&&(p==="/"||p===""||/\\/(app)?$/.test(p)))'
        '||(h!=="/"&&p.toLowerCase().indexOf(h.replace(/\\//,"").toLowerCase())>=0);'
        'if(m)a.classList.add("anav-active");'
        'else a.classList.remove("anav-active");'
        '});'
        '}catch(e){}'
        '};'
        'run();'
        'document.addEventListener("DOMContentLoaded",run);'
        'setTimeout(run,200);setTimeout(run,600);'
        '})();'
        '</script>'
    )

    # anav-right / connection pill deliberately removed (v5)
    return (
        '<div id="aqanav">'
        '<a href="/" class="anav-logo" target="_top">' + logo_inner + '</a>'
        '<div class="anav-divider"></div>'
        '<div class="anav-links">' + links + '</div>'
        '</div>'
        + js
    )


# ─────────────────────────────────────────────────────────────
# PUBLIC API
# ─────────────────────────────────────────────────────────────

def inject_css(org_name: str = "", sf_connected: bool = False):
    """
    Call as the VERY FIRST st.* call after st.set_page_config().
    Injects sidebar-kill, design-system CSS, and fixed top navbar.
    Connection pill removed in v5 — params kept for backward compat.
    """
    import streamlit as st
    logo_b64 = _logo_base64()
    st.markdown(_EARLY_CSS, unsafe_allow_html=True)
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
    st.markdown(
        _build_navbar_html(logo_b64, org_name, sf_connected),
        unsafe_allow_html=True
    )


def render_header(page_title: str, page_icon: str,
                  org_name: str = "", environment: str = ""):
    """Per-page gradient sub-header. All text is white."""
    import streamlit as st

    env_html = ""
    if environment and str(environment).strip():
        e       = str(environment).strip()
        is_prod = "prod" in e.lower()
        bg      = "rgba(220,38,38,0.2)"  if is_prod else "rgba(46,196,182,0.2)"
        fg      = "#ff6b6b"              if is_prod else "#2ec4b6"
        bdr     = "rgba(220,38,38,0.4)" if is_prod else "rgba(46,196,182,0.4)"
        env_html = (
            '<span style="background:' + bg + ';color:' + fg + ' !important;'
            'padding:5px 14px;border-radius:20px;font-size:11px;'
            'font-weight:700;border:1px solid ' + bdr + ';letter-spacing:0.3px;">'
            + e + '</span>'
        )

    org_html = ""
    if org_name and str(org_name).strip():
        org_html = (
            '<span style="color:rgba(255,255,255,0.9) !important;'
            'font-size:13px;font-weight:600;">'
            '🏢 ' + str(org_name).strip() + '</span>'
        )

    st.markdown(
        '<div class="amplify-header fade-in">'
        '<div>'
        '<p class="brand-title">' + page_icon + '&nbsp;' + page_title + '</p>'
        '<p class="brand-sub">AmplifyQA &nbsp;·&nbsp; AI-Augmented Testing Platform'
        '&nbsp;·&nbsp; NeuraFlash - Part of Accenture</p>'
        '</div>'
        '<div class="header-right">'
        + org_html
        + ('&nbsp;&nbsp;' if org_html and env_html else '')
        + env_html
        + '</div></div>',
        unsafe_allow_html=True
    )


def render_brand_footer():
    """NeuraFlash brand strip — optionally call at bottom of any page."""
    import streamlit as st
    st.markdown(
        '<div class="brand-footer">'
        '<div>⚡ <strong>AmplifyQA</strong>&nbsp;—&nbsp;AI-Augmented Testing Platform</div>'
        '<div class="brand-footer-right">Powered by <strong>NeuraFlash</strong>'
        ' — Part of <strong>Accenture</strong></div>'
        '</div>',
        unsafe_allow_html=True
    )


def render_sidebar_logo():
    """No-op — kept for backward compatibility."""
    pass