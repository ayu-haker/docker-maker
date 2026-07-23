#!/usr/bin/env python3
"""
app.py
------
Streamlit web UI (styled like a terminal) for the docker-compose generator.

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
# Page + terminal-style CSS
# --------------------------------------------------------------------------

st.set_page_config(page_title="Docker Compose Auto-Generator", page_icon="🐳", layout="wide")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"]  {
        font-family: 'JetBrains Mono', 'Courier New', monospace;
    }

    .terminal {
        background-color: #0d1117;
        color: #39ff14;
        padding: 18px 20px;
        border-radius: 10px;
        border: 1px solid #30363d;
        font-family: 'JetBrains Mono', 'Courier New', monospace;
        font-size: 14px;
        line-height: 1.55;
        white-space: pre-wrap;
        overflow-x: auto;
        box-shadow: 0 0 18px rgba(57,255,20,0.08);
    }
    .terminal .dim { color: #6e7681; }
    .terminal .cyan { color: #39c5cf; }
    .terminal .yellow { color: #e3b341; }
    .terminal .red { color: #ff7b72; }
    .terminal .white { color: #e6edf3; }

    .term-header {
        background: #161b22;
        border: 1px solid #30363d;
        border-bottom: none;
        border-radius: 10px 10px 0 0;
        padding: 8px 14px;
        display: flex;
        gap: 6px;
    }
    .dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }
    .dot-red { background: #ff5f56; }
    .dot-yellow { background: #ffbd2e; }
    .dot-green { background: #27c93f; }

    .stButton>button {
        font-family: 'JetBrains Mono', monospace;
        background-color: #238636;
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton>button:hover {
        background-color: #2ea043;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def term_dots():
    st.markdown(
        '<div class="term-header"><span class="dot dot-red"></span>'
        '<span class="dot dot-yellow"></span><span class="dot dot-green"></span></div>',
        unsafe_allow_html=True,
    )


def term_print(html_lines):
    """Render a block of lines inside the fake terminal styling."""
    term_dots()
    content = "\n".join(html_lines)
    st.markdown(f'<div class="terminal">{content}</div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Session state
# --------------------------------------------------------------------------

if "stage" not in st.session_state:
    st.session_state.stage = "input"
if "info" not in st.session_state:
    st.session_state.info = None
if "project_dir" not in st.session_state:
    st.session_state.project_dir = None
if "tmp_root" not in st.session_state:
    st.session_state.tmp_root = None

SERVICE_LABELS = {
    "postgres": "PostgreSQL — image: postgres:16-alpine, port 5432",
    "mysql": "MySQL — image: mysql:8, port 3306",
    "mongo": "MongoDB — image: mongo:7, port 27017",
    "redis": "Redis — image: redis:7-alpine, port 6379",
}

LANGUAGE_LABELS = {
    "node": "Node.js",
    "python-django": "Python (Django)",
    "python-flask": "Python (Flask)",
    "python-fastapi": "Python (FastAPI)",
    "python-generic": "Python (generic)",
    "go": "Go",
    "static": "Static site (HTML/CSS/JS)",
    "unknown": "Could not detect confidently",
}

# --------------------------------------------------------------------------
# Header
# --------------------------------------------------------------------------

st.markdown("## 🐳 Docker Compose Auto-Generator")
st.caption("Terminal-styled Streamlit UI — scans your project and writes docker-compose.yml, Dockerfile, .env.example, and .dockerignore")

# --------------------------------------------------------------------------
# Step 1 — get the project onto disk (local path or zip upload)
# --------------------------------------------------------------------------

with st.container(border=True):
    st.markdown("#### Step 1 — Project select karo")
    mode = st.radio(
        "Project kaise doge?",
        ["Local folder path (Streamlit isi machine pe chal raha ho)", "Zip file upload karo"],
        horizontal=False,
    )

    project_dir = None

    if mode.startswith("Local"):
        path_input = st.text_input("Project folder ka absolute path", value=".")
        if st.button("🔍 Scan Project", type="primary"):
            candidate = os.path.abspath(path_input)
            if not os.path.isdir(candidate):
                st.error(f"'{candidate}' ek valid directory nahi hai.")
            else:
                project_dir = candidate
    else:
        uploaded = st.file_uploader("Project ka .zip upload karo", type=["zip"])
        if uploaded and st.button("🔍 Scan Project", type="primary"):
            tmp_root = tempfile.mkdtemp(prefix="compose_gen_")
            with zipfile.ZipFile(io.BytesIO(uploaded.read())) as zf:
                zf.extractall(tmp_root)
            # If the zip contains a single top-level folder, descend into it
            entries = [e for e in os.listdir(tmp_root) if not e.startswith("__MACOSX")]
            if len(entries) == 1 and os.path.isdir(os.path.join(tmp_root, entries[0])):
                project_dir = os.path.join(tmp_root, entries[0])
            else:
                project_dir = tmp_root
            st.session_state.tmp_root = tmp_root

    if project_dir:
        st.session_state.project_dir = project_dir
        with st.spinner("Scanning project..."):
            time.sleep(0.6)
            st.session_state.info = detect_stack(project_dir)
        st.session_state.stage = "scanned"

# --------------------------------------------------------------------------
# Step 2 — show detection + let user tweak
# --------------------------------------------------------------------------

if st.session_state.stage in ("scanned", "generated") and st.session_state.info:
    info = st.session_state.info
    project_dir = st.session_state.project_dir

    with st.container(border=True):
        st.markdown("#### Step 2 — Detection Result")
        lang_label = LANGUAGE_LABELS.get(info["language"], info["language"])
        lines = [
            f'<span class="dim">$</span> <span class="cyan">scan</span> {project_dir}',
            "",
            f'<span class="white">Stack       :</span> <span class="cyan">{lang_label}</span>',
            f'<span class="white">Port        :</span> {info["port"]}',
            f'<span class="white">Dockerfile  :</span> '
            + ("<span class=\"yellow\">already exists — will be reused</span>" if info["dockerfile_exists"]
               else "<span class=\"dim\">not found — one will be generated</span>"),
            f'<span class="white">Services    :</span> '
            + (", ".join(sorted(info["services"])) if info["services"] else "<span class=\"dim\">none detected</span>"),
        ]
        term_print(lines)

    with st.container(border=True):
        st.markdown("#### Step 3 — Configure")
        col1, col2 = st.columns(2)
        with col1:
            default_name = os.path.basename(project_dir.rstrip("/")) or "app"
            default_name = "".join(ch for ch in default_name.lower() if ch.isalnum() or ch in "-_") or "app"
            app_name = st.text_input("App/service ka naam", value=default_name)
        with col2:
            port = st.number_input("App port", value=int(info["port"]), min_value=1, max_value=65535)

        selected_services = []
        if info["services"]:
            st.markdown("**Detected services — konse include karne hain?**")
            for s in sorted(info["services"]):
                checked = st.checkbox(SERVICE_LABELS.get(s, s), value=True, key=f"svc_{s}")
                if checked:
                    selected_services.append(s)

        colA, colB, colC = st.columns(3)
        with colA:
            include_dockerfile = st.checkbox(
                "Dockerfile generate karo",
                value=not info["dockerfile_exists"],
                disabled=info["dockerfile_exists"],
                help="Existing Dockerfile hai to isse touch nahi kiya jaata" if info["dockerfile_exists"] else None,
            )
        with colB:
            gen_env = st.checkbox("Generate .env.example", value=True)
        with colC:
            gen_dockerignore = st.checkbox("Generate .dockerignore", value=True)

    # --- Build compose preview live ---
    preview_info = dict(info)
    preview_info["services"] = set(selected_services)
    compose_content = generate_compose(preview_info, app_name or "app", int(port))

    with st.container(border=True):
        st.markdown("#### Preview — docker-compose.yml")
        term_dots()
        st.code(compose_content, language="yaml")

        if gen_env:
            with st.expander("Preview — .env.example"):
                st.code(generate_env_example(preview_info, app_name or "app", int(port)), language="bash")
        if gen_dockerignore:
            with st.expander("Preview — .dockerignore"):
                st.code(generate_dockerignore(preview_info), language="text")
        if include_dockerfile:
            with st.expander("Preview — Dockerfile"):
                st.code(generate_dockerfile(preview_info), language="dockerfile")

    if st.button("⚙️ Generate files & download zip", type="primary"):
        out_dir = tempfile.mkdtemp(prefix="compose_out_")
        log_lines = []

        with open(os.path.join(out_dir, "docker-compose.yml"), "w") as f:
            f.write(compose_content)
        log_lines.append('<span class="dim">✔</span> docker-compose.yml')

        if include_dockerfile:
            with open(os.path.join(out_dir, "Dockerfile"), "w") as f:
                f.write(generate_dockerfile(preview_info))
            log_lines.append('<span class="dim">✔</span> Dockerfile  <span class="yellow">(CMD line check kar lena)</span>')

        if gen_dockerignore:
            with open(os.path.join(out_dir, ".dockerignore"), "w") as f:
                f.write(generate_dockerignore(preview_info))
            log_lines.append('<span class="dim">✔</span> .dockerignore')

        if gen_env:
            with open(os.path.join(out_dir, ".env.example"), "w") as f:
                f.write(generate_env_example(preview_info, app_name or "app", int(port)))
            log_lines.append('<span class="dim">✔</span> .env.example')

        # zip it up
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(out_dir):
                zf.write(os.path.join(out_dir, fname), arcname=fname)
        zip_buffer.seek(0)

        with st.container(border=True):
            st.markdown("#### Done")
            term_print(log_lines)

        st.download_button(
            "⬇️ Download generated files (.zip)",
            data=zip_buffer,
            file_name=f"{app_name or 'app'}-docker-files.zip",
            mime="application/zip",
        )
        st.info(
            "Zip extract karke apne project folder me daal do, phir:\n\n"
            "```\ncp .env.example .env   # values fill karo\ndocker compose up --build\n```"
        )

        shutil.rmtree(out_dir, ignore_errors=True)
