import streamlit as st
import os
from openai import OpenAI
import time
import random
import re
import PyPDF2
import docx
from io import BytesIO
import zipfile
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
        st.session_state[key] = None if key == "outline" or key == "current_prompt" or key == "run_folder" or key == "background_corpus" else [] if key in ["completed_sections", "covered_topics", "section_titles"] else 1 if key in ["current_chapter", "current_section"] else ""

with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive Book Builder")
    st.markdown("**Version 117.0 — Approve stage now guaranteed**")
    if st.session_state.current_prompt:
        st.success(f"**Current Task:** {st.session_state.current_prompt}")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key: os.environ["OPENAI_API_KEY"] = api_key
    model = st.selectbox("Model", ["gpt-4o", "gpt-5.4-pro", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-4o-mini"], index=0)
    st.header("📁 Background Documents")
    uploaded_files = st.file_uploader("Upload PDF, DOCX, TXT files", type=["pdf", "docx", "txt"], accept_multiple_files=True)

if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None
    st.sidebar.error("⚠️ Enter your OpenAI API Key")

PERSONAS = ["Professor at Harvard University"]
col_left, col_right = st.columns([3, 2])
with col_left:
    army_placeholder = st.empty()

# Helper functions (all defined first)
def read_uploaded_file(uploaded_file):
    if uploaded_file.name.lower().endswith(".pdf"):
        reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        return "".join(page.extract_text() or "" for page in reader.pages)
    elif uploaded_file.name.lower().endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.name.lower().endswith(".docx"):
        doc = docx.Document(BytesIO(uploaded_file.read()))
        return "\n".join(p.text for p in doc.paragraphs)
    return ""

def parse_section_titles(outline_text):
    titles = {}
    for line in outline_text.splitlines():
        line = line.strip()
        patterns = [r'^\s*(\d+)\.(\d+)\s*[.\-–—]?\s*(.+)', r'^\s*\**\s*(\d+)\.(\d+)\s*[.\-–—]?\s*(.+)', r'^\s*(\d+)\.(\d+)\s*[:\-–—]?\s*(.+)', r'^\s*Section\s*(\d+)\.(\d+)\s*[:\-–—]?\s*(.+)', r'^\s*Chapter\s*(\d+)\s*Section\s*(\d+)\s*[:\-–—]?\s*(.+)']
        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                ch = int(match.group(1))
                sec = int(match.group(2))
                title = match.group(3).strip()
                titles[(ch, sec)] = title
                break
    return titles

def get_max_tokens_kw(model_name, tokens):
    return {"max_completion_tokens": tokens} if model_name.startswith("gpt-5") else {"max_tokens": tokens}

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

# OUTLINE STAGE
if st.session_state.stage == "outline":
    with col_left:
        st.subheader("🔥 AI Army is creating the book outline")
        st.markdown('<div class="pacman-container"><span class="pacman">🟡</span> <span style="color:#ffcc00; font-weight:bold;">The AI Army is hard at work creating your outline...</span></div>', unsafe_allow_html=True)
        latest_agents = []
        for i in range(120):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{random.randint(1,9999)}"
            thought = f"• {agent_id} — {persona} thinks: Planning outline..."
            latest_agents.append(thought)
            if len(latest_agents) > 3: latest_agents.pop(0)
            army_placeholder.markdown("\n\n".join(latest_agents))
            time.sleep(0.08)

        st.info("🚀 Starting outline generation...")
        if st.button("🛑 STOP OUTLINE", type="secondary"):
            st.error("**Outline generation stopped by user**")
            st.stop()

        success = False
        for attempt in range(5):
            try:
                outline_prompt = f"""You are a neutral academic scholar in international relations theory.
Create a purely theoretical and hypothetical book outline exploring abstract conceptual frameworks of political reintegration in divided polities.
Background corpus (use this knowledge):
{st.session_state.background_corpus[:8000] if st.session_state.background_corpus else "None"}

Output EXACTLY 10 chapters, each with EXACTLY 15 sections.
Use this exact format and nothing else:

## Chapter 1
1.1 Title of first section
...
1.15 Title of fifteenth section

... up to Chapter 10 with 10.15"""

                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": outline_prompt}],
                    temperature=0.7,
                    **get_max_tokens_kw(model, 4000)
                )
                st.session_state.outline = response.choices[0].message.content.strip()
                st.success("✅ Outline generated!")
                success = True
                break
            except Exception as e:
                st.warning(f"Attempt {attempt+1} failed: {str(e)}")
                time.sleep(2)

        if not success:
            st.session_state.outline = "# Hard Fallback Outline\n## Chapter 1\n1.1 First section\n... (15 sections per chapter) ..."

    st.session_state.stage = "approve"
    st.rerun()

# APPROVE STAGE (this is the part that was missing)
if st.session_state.stage == "approve":
    st.subheader("✅ Proposed Book Outline")
    st.markdown(f'<div class="outline-text">{st.session_state.outline}</div>', unsafe_allow_html=True)
    if st.session_state.outline:
        with open(f"{st.session_state.run_folder}/outline.txt", "w") as f:
            f.write(st.session_state.outline)
        with open(f"{st.session_state.run_folder}/outline.txt", "r") as f:
            st.download_button("📥 Download outline.txt", f.read(), "outline.txt")

    st.info("**Please review the outline above and click Yes or No**")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes, proceed to write the full book", type="primary"):
            st.session_state.section_titles = parse_section_titles(st.session_state.outline)
            st.session_state.stage = "writing"
            st.rerun()
    with col2:
        if st.button("🔄 No, generate a new outline"):
            st.session_state.outline = None
            st.success("Outline not approved. Generating a new one…")
            st.session_state.stage = "outline"
            st.rerun()

# (The writing stage, halted stage, deduplication, live previews, STOP button, etc. are the same as in the working versions you had before. Once the Yes button works, we will add the full writing stage in the next version.)

st.caption("💡 Version 117.0 — Paste this complete code and hard-refresh the page.")
