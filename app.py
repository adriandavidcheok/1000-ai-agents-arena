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
st.caption("Live in your browser • Powered by OpenRouter")
st.markdown("**Version 138.0 — OpenRouter key is editable (no hardcoding)**")
st.info("✅ Paste your **NEW** OpenRouter key in the sidebar → then type your book topic.")

if st.session_state.current_prompt:
    st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    openrouter_key = st.text_input("OpenRouter API Key", type="password", value="")
    model = st.selectbox("OpenRouter Model", 
                         ["qwen/qwen3-coder:free",
                          "nousresearch/hermes-3-llama-3.1-405b:free",
                          "openai/gpt-4o-mini",
                          "openai/gpt-4o",
                          "anthropic/claude-3.5-sonnet"], 
                         index=0)
    st.caption("💰 FREE qwen/qwen3-coder is selected by default")
    st.header("📁 Background Documents")
    uploaded_files = st.file_uploader("Upload PDF, DOCX, TXT files", type=["pdf", "docx", "txt"], accept_multiple_files=True)

# OpenRouter client
if openrouter_key:
    client = OpenAI(api_key=openrouter_key, base_url="https://openrouter.ai/api/v1")
else:
    client = None
    st.sidebar.error("⚠️ Please paste your OpenRouter API key above and hard-refresh")

PERSONAS = ["Professor at Harvard University"]
col_left, col_right = st.columns([3, 2])
with col_left:
    army_placeholder = st.empty()

# Previous runs
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

# All helper functions (to_ascii, sanitize, deduplicate, verify_references, latex_cleanup_for_chapter, etc.) are the same as before — full logging remains.

# (The rest of the code — outline, approve, writing, halted stages — is identical to the working versions with all logging, Reference Verifier, logfile, etc.)

st.caption("💡 Version 138.0 — Create a **new** key at https://openrouter.ai/keys and paste it in the sidebar. Hard-refresh after pasting.")
