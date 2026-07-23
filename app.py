#!/usr/bin/env python3
"""
app.py
------
Modern Streamlit web UI for the docker-compose generator.

Run with:
    pip install streamlit
    streamlit run app.py

Needs generate_compose.py in the same folder.
"""

import io
import os
import shutil
import tempfile
import time
import zipfile

import streamlit as st

from generate_compose import (
    detect_stack,
    generate_compose,
    generate_dockerfile,
    generate_dockerignore,
    generate_env_example,
)

# --------------------------------------------------------------------------
# Page config + design system
# --------------------------------------------------------------------------

st.set_page_config(
    page_title="Compose Studio",
    page_icon="🐳",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --bg: #0b0d12;
        --surface: #12151c;
        --surface-2: #171b24;
        --border: #23283333;
        --border-soft: #262b36;
        --text: #e8eaed;
        --text-dim: #8b93a1;
        --accent: #6366f1;
        --accent-2: #818cf8;
        --success: #22c55e;
        --warning: #f59e0b;
        --danger: #ef4444;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, sans-serif;
        color: var(--text);
    }

    .stApp {
        background:
            radial-gradient(circle at 15% 0%, rgba(99,102,241,0.10), transparent 40%),
            radial-gradient(circle at 85% 15%, rgba(129,140,248,0.06), transparent 35%),
            var(--bg);
    }

    code, pre, .stCodeBlock, .stCode {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* ---- Hide default streamlit chrome we don't want ---- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] { background: transparent; }

    /* ---- Hero header ---- */
    .hero {
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 4px 0 6px 0;
    }
    .hero-badge {
        width: 46px; height: 46px;
        border-radius: 12px;
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        display: flex; align-items: center; justify-content: center;
        font-size: 22px;
        box-shadow: 0 8px 24px rgba(99,102,241,0.35);
        flex-shrink: 0;
    }
    .hero-title { font-size: 26px; font-weight: 800; letter-spacing: -0.02em; margin: 0; line-height: 1.2; }
    .hero-sub { color: var(--text-dim); font-size: 14px; margin: 2px 0 0 0; }

    /* ---- Cards ---- */
    .card {
        background: var(--surface);
        border: 1px solid var(--border-soft);
        border-radius: 14px;
        padding: 22px 24px;
        margin-bottom: 18px;
    }
    .card-title {
        font-size: 13px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--accent-2);
        margin-bottom: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* ---- Badges / pills ---- */
    .pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 5px 12px;
        border-radius: 999px;
        font-size: 12.5px;
        font-weight: 600;
        border: 1px solid var(--border-soft);
        background: var(--surface-2);
        margin: 0 6px 6px 0;
    }
    .pill-accent { color: var(--accent-2); border-color: rgba(99,102,241,0.35); background: rgba(99,102,241,0.08); }
    .pill-success { color: var(--success); border-color: rgba(34,197,94,0.35); background: rgba(34,197,94,0.08); }
    .pill-warning { color: var(--warning); border-color: rgba(245,158,11,0.35); background: rgba(245,158,11,0.08); }
    .pill-dim { color: var(--text-dim); }

    /* ---- Sidebar stepper ---- */
    section[data-testid="stSidebar"] {
        background: var(--surface);
        border-right: 1px solid var(--border-soft);
    }
    .step-item {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 10px;
        border-radius: 8px;
        margin-bottom: 4px;
        font-size: 13.5px;
        font-weight: 500;
        color: var(--text-dim);
    }
    .step-item.active {
        background: rgba(99,102,241,0.12);
        color: var(--text);
        font-weight: 600;
    }
    .step-num {
        width: 20px; height: 20px;
        border-radius: 6px;
        background: var(--surface-2);
        border: 1px solid var(--border-soft);
        display: flex; align-items: center; justify-content: center;
        font-size: 11px;
        flex-shrink: 0;
    }
    .step-item.active .step-num {
        background: var(--accent);
        border-color: var(--accent);
        color: white;
    }
    .step-item.done .step-num {
        background: var(--success);
        border-color: var(--success);
        color: white;
    }

    /* ---- Buttons ---- */
    .stButton>button {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        border-radius: 9px;
        border: 1px solid var(--border-soft);
        padding: 0.5rem 1.1rem;
        transition: all 0.15s ease;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, var(--accent), var(--accent-2));
        border: none;
        box-shadow: 0 4px 14px rgba(99,102,241,0.3);
    }
    .stButton>button[kind="primary"]:hover {
        box-shadow: 0 6px 20px rgba(99,102,241,0.45);
        transform: translateY(-1px);
    }
    div[data-testid="stDownloadButton"] button {
        background: linear-gradient(135deg, var(--success), #16a34a);
        border: none;
        color: white;
        font-weight: 600;
        border-radius: 9px;
        box-shadow: 0 4px 14px rgba(34,197,94,0.3);
    }

    /* ---- Inputs ---- */
    .stTextInput input, .stNumberInput input {
        border-radius: 8px !important;
        border: 1px solid var(--border-soft) !important;
        background: var(--surface-2) !important;
    }

    /* ---- Metric-style stat ---- */
    .stat-row { display: flex; gap: 14px; flex-wrap: wrap; }
    .stat-box {
        flex: 1;
        min-width: 140px;
        background: var(--surface-2);
        border: 1px solid var(--border-soft);
        border-radius: 10px;
        padding: 12px 14px;
    }
    .stat-label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
    .stat-value { font-size: 16px; font-weight: 700; margin-top: 3px; }

    hr { border-color: var(--border-soft); }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------

if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "info" not in st.session_state:
    st.session_state.info = None
if "project_dir" not in st.session_state:
    st.session_state.project_dir = None

SERVICE_META = {
    "postgres": ("PostgreSQL", "postgres:16-alpine", "5432"),
    "mysql": ("MySQL", "mysql:8", "3306"),
    "mongo": ("MongoDB", "mongo:7", "27017"),
    "redis": ("Redis", "redis:7-alpine", "6379"),
}

LANGUAGE_LABELS = {
    "node": "Node.js",
    "python-django": "Python · Django",
    "python-flask": "Python · Flask",
    "python-fastapi": "Python · FastAPI",
    "python-generic": "Python",
    "go": "Go",
    "static": "Static Site",
    "unknown": "Not detected",
}


def pill(label, kind="dim"):
    return f'<span class="pill pill-{kind}">{label}</span>'


# --------------------------------------------------------------------------
# Sidebar — stepper + info
# --------------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        '<div class="hero" style="margin-bottom:22px;">'
        '<div class="hero-badge">🐳</div>'
        '<div><p class="hero-title" style="font-size:19px;">Compose Studio</p>'
        '<p class="hero-sub">Docker setup, automated</p></div></div>',
        unsafe_allow_html=True,
    )

    stage = st.session_state.stage
    steps = [
        ("1", "Select project", "input"),
        ("2", "Review detection", "scanned"),
        ("3", "Configure & generate", "scanned"),
        ("4", "Download", "generated"),
    ]
    stage_order = ["input", "scanned", "scanned", "generated"]
    current_idx = {"input": 0, "scanned": 2, "generated": 3}[stage]

    for i, (num, label, _) in enumerate(steps):
        cls = "step-item"
        if i < current_idx:
            cls += " done"
        elif i == current_idx:
            cls += " active"
        mark = "✓" if i < current_idx else num
        st.markdown(
            f'<div class="{cls}"><span class="step-num">{mark}</span>{label}</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<hr/>", unsafe_allow_html=True)
    st.caption("Detects Node.js, Python (Django/Flask/FastAPI), Go, and static sites — plus Postgres, MySQL, MongoDB, and Redis dependencies.")

    if st.session_state.info:
        st.markdown("<hr/>", unsafe_allow_html=True)
        st.caption("Current scan")
        st.markdown(pill(LANGUAGE_LABELS.get(st.session_state.info["language"], "?"), "accent"), unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------

st.markdown(
    '<div class="hero">'
    '<div class="hero-badge">⚙️</div>'
    '<div><p class="hero-title">Docker Compose Auto-Generator</p>'
    '<p class="hero-sub">Scan a project, get a production-ready docker-compose.yml, Dockerfile, .env.example, and .dockerignore in seconds.</p></div>'
    '</div><br/>',
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# Step 1 — project source
# --------------------------------------------------------------------------

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📁 &nbsp;Step 1 — Project Source</div>', unsafe_allow_html=True)

    mode = st.radio(
        "Source",
        ["Local folder path", "Upload a .zip"],
        horizontal=True,
        label_visibility="collapsed",
    )

    project_dir = None

    if mode == "Local folder path":
        c1, c2 = st.columns([4, 1])
        with c1:
            path_input = st.text_input("Project path", value=".", label_visibility="collapsed", placeholder="/path/to/your/project")
        with c2:
            scan_clicked = st.button("Scan →", type="primary", use_container_width=True)
        if scan_clicked:
            candidate = os.path.abspath(path_input)
            if not os.path.isdir(candidate):
                st.error(f"'{candidate}' is not a valid directory.")
            else:
                project_dir = candidate
    else:
        uploaded = st.file_uploader("Upload zip", type=["zip"], label_visibility="collapsed")
        if uploaded and st.button("Scan →", type="primary"):
            tmp_root = tempfile.mkdtemp(prefix="compose_gen_")
            with zipfile.ZipFile(io.BytesIO(uploaded.read())) as zf:
                zf.extractall(tmp_root)
            entries = [e for e in os.listdir(tmp_root) if not e.startswith("__MACOSX")]
            if len(entries) == 1 and os.path.isdir(os.path.join(tmp_root, entries[0])):
                project_dir = os.path.join(tmp_root, entries[0])
            else:
                project_dir = tmp_root

    if project_dir:
        st.session_state.project_dir = project_dir
        with st.spinner("Analyzing project structure..."):
            time.sleep(0.5)
            st.session_state.info = detect_stack(project_dir)
        st.session_state.stage = "scanned"

    st.markdown("</div>", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# Step 2 — detection summary
# --------------------------------------------------------------------------

if st.session_state.stage in ("scanned", "generated") and st.session_state.info:
    info = st.session_state.info
    project_dir = st.session_state.project_dir
    lang_label = LANGUAGE_LABELS.get(info["language"], info["language"])

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🔎 &nbsp;Step 2 — Detection Result</div>', unsafe_allow_html=True)

    st.markdown(
        f'''
        <div class="stat-row">
          <div class="stat-box"><div class="stat-label">Stack</div><div class="stat-value">{lang_label}</div></div>
          <div class="stat-box"><div class="stat-label">Port</div><div class="stat-value">{info["port"]}</div></div>
          <div class="stat-box"><div class="stat-label">Dockerfile</div><div class="stat-value">{"Existing" if info["dockerfile_exists"] else "Will generate"}</div></div>
          <div class="stat-box"><div class="stat-label">Services found</div><div class="stat-value">{len(info["services"]) or "None"}</div></div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    if info["services"]:
        st.write("")
        badges = "".join(pill(SERVICE_META[s][0], "success") for s in sorted(info["services"]))
        st.markdown(badges, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # Step 3 — configure
    # ----------------------------------------------------------------

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">🛠️ &nbsp;Step 3 — Configure</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        default_name = os.path.basename(project_dir.rstrip("/")) or "app"
        default_name = "".join(ch for ch in default_name.lower() if ch.isalnum() or ch in "-_") or "app"
        app_name = st.text_input("Service name", value=default_name)
    with col2:
        port = st.number_input("App port", value=int(info["port"]), min_value=1, max_value=65535)

    selected_services = []
    if info["services"]:
        st.write("**Include services**")
        cols = st.columns(len(info["services"]))
        for col, s in zip(cols, sorted(info["services"])):
            with col:
                name, image, portnum = SERVICE_META[s]
                checked = st.checkbox(f"{name}", value=True, key=f"svc_{s}", help=f"{image} · port {portnum}")
                if checked:
                    selected_services.append(s)

    st.write("")
    colA, colB, colC = st.columns(3)
    with colA:
        include_dockerfile = st.checkbox(
            "Generate Dockerfile",
            value=not info["dockerfile_exists"],
            disabled=info["dockerfile_exists"],
            help="An existing Dockerfile was found — it won't be touched." if info["dockerfile_exists"] else None,
        )
    with colB:
        gen_env = st.checkbox("Generate .env.example", value=True)
    with colC:
        gen_dockerignore = st.checkbox("Generate .dockerignore", value=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # Live preview
    # ----------------------------------------------------------------

    preview_info = dict(info)
    preview_info["services"] = set(selected_services)
    compose_content = generate_compose(preview_info, app_name or "app", int(port))

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">👁️ &nbsp;Live Preview</div>', unsafe_allow_html=True)

    tab_names = ["docker-compose.yml"]
    if gen_env:
        tab_names.append(".env.example")
    if gen_dockerignore:
        tab_names.append(".dockerignore")
    if include_dockerfile:
        tab_names.append("Dockerfile")

    tabs = st.tabs(tab_names)
    tabs[0].code(compose_content, language="yaml")
    idx = 1
    if gen_env:
        tabs[idx].code(generate_env_example(preview_info, app_name or "app", int(port)), language="bash")
        idx += 1
    if gen_dockerignore:
        tabs[idx].code(generate_dockerignore(preview_info), language="text")
        idx += 1
    if include_dockerfile:
        tabs[idx].code(generate_dockerfile(preview_info), language="dockerfile")

    st.markdown("</div>", unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # Step 4 — generate & download
    # ----------------------------------------------------------------

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown('<div class="card-title">📦 &nbsp;Step 4 — Generate & Download</div>', unsafe_allow_html=True)

    generate_clicked = st.button("⚙️  Generate files", type="primary")

    if generate_clicked:
        out_dir = tempfile.mkdtemp(prefix="compose_out_")
        written = []

        with open(os.path.join(out_dir, "docker-compose.yml"), "w") as f:
            f.write(compose_content)
        written.append("docker-compose.yml")

        if include_dockerfile:
            with open(os.path.join(out_dir, "Dockerfile"), "w") as f:
                f.write(generate_dockerfile(preview_info))
            written.append("Dockerfile")

        if gen_dockerignore:
            with open(os.path.join(out_dir, ".dockerignore"), "w") as f:
                f.write(generate_dockerignore(preview_info))
            written.append(".dockerignore")

        if gen_env:
            with open(os.path.join(out_dir, ".env.example"), "w") as f:
                f.write(generate_env_example(preview_info, app_name or "app", int(port)))
            written.append(".env.example")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(out_dir):
                zf.write(os.path.join(out_dir, fname), arcname=fname)
        zip_buffer.seek(0)
        shutil.rmtree(out_dir, ignore_errors=True)

        st.session_state.stage = "generated"

        st.success(f"Generated {len(written)} files: " + ", ".join(written))

        st.download_button(
            "⬇️  Download .zip",
            data=zip_buffer,
            file_name=f"{app_name or 'app'}-docker-files.zip",
            mime="application/zip",
        )

        with st.expander("Next steps"):
            st.code(
                f"cd {project_dir}\n"
                + ("cp .env.example .env   # fill in real values\n" if gen_env else "")
                + "docker compose up --build",
                language="bash",
            )

    st.markdown("</div>", unsafe_allow_html=True)
