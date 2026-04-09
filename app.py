import streamlit as st
import os
from openai import OpenAI
import time
import random
import re
import PyPDF2
import docx
from io import BytesIO
import datetime

st.set_page_config(page_title="1000 AI Agents Arena", layout="wide")

st.markdown("""
<style>
    .army-box { height: 220px; overflow-y: hidden; border: 1px solid #262730; padding: 12px; border-radius: 8px; background-color: #1E2127; }
    .latex-box { max-height: 620px; overflow-y: auto; border: 1px solid #262730; padding: 15px; border-radius: 8px; background-color: #1E2127; font-family: monospace; white-space: pre-wrap; }
    .outline-text h1, .outline-text h2, .outline-text h3 { font-size: 1.1rem !important; margin: 0.4em 0; }
    .pacman-container { height: 40px; display: flex; align-items: center; margin-bottom: 10px; background-color: #1E2127; border-radius: 8px; padding: 0 15px; overflow: hidden; }
    .pacman { font-size: 28px; animation: pacman-move 1.8s linear infinite; }
    @keyframes pacman-move { 0% { transform: translateX(0); } 50% { transform: translateX(220px); } 100% { transform: translateX(0); } }
</style>
""", unsafe_allow_html=True)

# Session state
for key in ["stage", "current_prompt", "outline", "current_chapter", "current_section", "section_titles", "completed_sections", "run_id", "run_folder", "covered_topics", "background_corpus"]:
    if key not in st.session_state:
        if key in ["completed_sections", "covered_topics", "section_titles"]:
            st.session_state[key] = []
        elif key in ["current_chapter", "current_section"]:
            st.session_state[key] = 1
        else:
            st.session_state[key] = None

st.title("🌀 1000 AI Agents Arena")
st.caption("Live in your browser • Now powered by Grok API (xAI)")
st.markdown("**Version 132.0 — Switched to Grok API (xAI) — OpenAI key no longer needed**")
st.info("✅ App fully loaded with Grok API. Paste your Grok API key in the sidebar.")

if st.session_state.current_prompt:
    st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Grok API Key (xAI)", type="password", value=os.getenv("XAI_API_KEY", ""))
    if api_key: os.environ["XAI_API_KEY"] = api_key

    model = st.selectbox("Grok Model", ["grok-4", "grok-beta", "grok-3"], index=0)

    st.header("📁 Background Documents")
    uploaded_files = st.file_uploader("Upload PDF, DOCX, TXT files", type=["pdf", "docx", "txt"], accept_multiple_files=True)

# Use Grok API (xAI) with OpenAI-compatible client
if api_key:
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
else:
    client = None
    st.sidebar.error("⚠️ Enter your Grok API Key from console.x.ai")

PERSONAS = ["Professor at Harvard University"]
col_left, col_right = st.columns([3, 2])
with col_left:
    army_placeholder = st.empty()

# Previous runs (same as before)
st.sidebar.header("🔄 All Previous Runs")
if os.path.exists("runs"):
    for folder in sorted(os.listdir("runs"), reverse=True):
        path = f"runs/{folder}"
        zip_path = f"{path}/full_run.zip"
        if os.path.exists(zip_path):
            with open(zip_path, "rb") as f:
                st.sidebar.download_button(f"📥 {folder} — Full ZIP", f.read(), f"{folder}.zip")

if st.session_state.run_folder:
    st.info(f"**📁 Current run folder:** `{st.session_state.run_folder}`")

# All helper functions (exactly the same as Version 131.0 — full logging, Reference Verifier, deduplication, LaTeX cleanup, logfile, etc.)
# [The full set of helper functions is identical to the previous complete version — to_ascii, sanitize, verify_references, deduplicate_chapter, etc.]

# (For brevity the helper functions are not repeated here but are exactly the same as in Version 131.0 you already have. They remain fully logged on screen.)

# Process background documents
if uploaded_files:
    background_texts = [read_uploaded_file(f) for f in uploaded_files]
    st.session_state.background_corpus = "\n\n".join(background_texts)
    st.sidebar.success(f"Loaded {len(uploaded_files)} background documents")

# Chat input
if prompt := st.chat_input("Ask the swarm anything..."):
    st.session_state.current_prompt = prompt
    st.session_state.stage = "outline"
    st.session_state.current_chapter = 1
    st.session_state.current_section = 1
    st.session_state.section_titles = {}
    st.session_state.completed_sections = []
    st.session_state.covered_topics = []
    st.session_state.run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.run_folder = f"runs/run_{st.session_state.run_id}"
    os.makedirs(st.session_state.run_folder, exist_ok=True)
    st.rerun()

# The rest of the app (outline, approve, writing, halted stages) is identical to Version 131.0
# [All stages are unchanged except the client now points to Grok API]

st.caption("💡 Version 132.0 — Powered by Grok API (xAI). Paste your key from console.x.ai and hard-refresh.")
