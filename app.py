import streamlit as st
import os
from openai import OpenAI
import time
import random
import re
import PyPDF2
import docx
from io import BytesIO

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

if "stage" not in st.session_state: st.session_state.stage = "idle"
if "current_prompt" not in st.session_state: st.session_state.current_prompt = None
if "outline" not in st.session_state: st.session_state.outline = None
if "chapter_files" not in st.session_state: st.session_state.chapter_files = {}  # chapter -> {"tex": path, "bib": path}

with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive Book Builder")
    st.markdown("**Version 58.0 - Full 10 Chapters + Per-Chapter Downloads**")
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key: os.environ["OPENAI_API_KEY"] = api_key
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)

PERSONAS = ["LaTeX Architect", "Scientific Writer", "Math LaTeX Specialist", "Document Engineer", "Research Coder", "Critical Reviewer", "Detailed Editor", "Storyteller"] * 60
client = OpenAI(api_key=api_key) if api_key else None
col_left, col_right = st.columns([3, 2])

with col_left:
    army_placeholder = st.empty()

if prompt := st.chat_input("Ask the swarm anything..."):
    st.session_state.current_prompt = prompt
    st.session_state.stage = "outline"
    st.rerun()

# STAGE 1: Outline (strict Alan Turing + 10×20)
if st.session_state.stage == "outline":
    with col_left:
        st.subheader("🔥 AI Army is creating the book outline (10 chapters × 20 sections)")
        st.markdown('<div class="pacman-container"><span class="pacman">🟡</span> <span style="color:#ffcc00; font-weight:bold;">The AI Army is hard at work creating your outline...</span></div>', unsafe_allow_html=True)
        latest_agents = []
        for i in range(120):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{random.randint(1,9999)}"
            thought = f"• {agent_id} — {persona} thinks: Planning Alan Turing-specific content..."
            latest_agents.append(thought)
            if len(latest_agents) > 3: latest_agents.pop(0)
            army_placeholder.markdown("\n\n".join(latest_agents))
            time.sleep(0.08)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": f"""You MUST create a book outline EXACTLY for this topic: {st.session_state.current_prompt}.
Output EXACTLY 10 chapters numbered 1 to 10. Each chapter MUST have EXACTLY 20 sections numbered 1.1 to 1.20 etc.
Every heading must be highly relevant to Alan Turing. Output ONLY clean markdown."""}],
                temperature=0.7, max_tokens=4000
            )
            st.session_state.outline = response.choices[0].message.content.strip()
        except Exception:
            st.session_state.outline = "Error generating outline."
    st.session_state.stage = "approve"
    st.rerun()

# STAGE 2: Approve
if st.session_state.stage == "approve":
    st.subheader("Proposed Book Outline (10 chapters × 20 sections)")
    st.markdown(f'<div class="outline-text">{st.session_state.outline}</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes, proceed to write the full book", type="primary"):
            st.session_state.stage = "writing"
            st.rerun()
    with col2:
        if st.button("🔄 No, generate a new outline"):
            st.session_state.outline = None
            st.session_state.stage = "outline"
            st.rerun()

# STAGE 3: Writing (FULL chapter-by-chapter loop + per-chapter downloads)
if st.session_state.stage == "writing":
    with col_left:
        st.subheader("🔥 AI Army is writing the full book chapter by chapter...")
        st.markdown('<div class="pacman-container"><span class="pacman">🟡</span> <span style="color:#ffcc00; font-weight:bold;">The AI Army is hard at work writing your book...</span></div>', unsafe_allow_html=True)
        army_placeholder = st.empty()
    with col_right:
        st.subheader("📜 Live LaTeX Preview (one line at a time)")
        latex_preview = st.empty()
        st.subheader("📜 Live BibTeX Preview (one line at a time)")
        bib_preview = st.empty()

    progress_bar = st.progress(0)
    status_text = st.empty()

    for chapter in range(1, 11):
        status_text.text(f"Writing Chapter {chapter} of 10...")
        chapter_tex = ""
        for section in range(1, 21):
            # 5 agents draft + synthesize
            drafts = []
            latest_agents = []
            for j in range(5):
                persona = random.choice(PERSONAS)
                agent_id = f"Agent #{random.randint(1,9999)}"
                thinking = f"• {agent_id} — {persona} thinks: Drafting detailed Alan Turing section {section}..."
                latest_agents.append(thinking)
                if len(latest_agents) > 3: latest_agents.pop(0)
                army_placeholder.markdown("\n\n".join(latest_agents))
                time.sleep(0.03)
                try:
                    resp = client.chat.completions.create(model=model, messages=[{"role": "system", "content": f"You are {persona}. Write a VERY LONG detailed section {section} of chapter {chapter} about Alan Turing. Include history, math, formulas, analysis. Use \\cite{{key}} for citations. Respond with ONLY LaTeX code."}], temperature=0.8, max_tokens=2500)
                    drafts.append(resp.choices[0].message.content.strip())
                except: pass
            # Synthesize
            try:
                synth = client.chat.completions.create(model=model, messages=[{"role": "system", "content": f"Combine these 5 drafts into ONE long, detailed, non-repetitive LaTeX section about Alan Turing. Make it even longer. Output ONLY LaTeX code.\n\n" + "\n\n---\n\n".join(drafts)}], temperature=0.7, max_tokens=3500)
                section_text = synth.choices[0].message.content.strip()
            except:
                section_text = drafts[0] if drafts else ""
            # Add to chapter
            chapter_tex += f"\n\n\\section{{Chapter {chapter} - Section {section}}}\n{section_text}"
            # Live one-line preview
            for line in section_text.split("\n"):
                if line.strip():
                    latex_preview.code(f"\\section{{Chapter {chapter} - Section {section}}}\n{line.strip()}", language="latex")
                    time.sleep(0.08)
            progress_bar.progress(min(1.0, (chapter-1)*20 + section / (10*20)))
        # After chapter finishes → save per-chapter files
        chapter_tex_filename = f"chapter_{chapter}.tex"
        with open(chapter_tex_filename, "w") as f:
            f.write(r"\documentclass[11pt]{article}\usepackage{amsmath,amssymb}\begin{document}\title{Chapter " + str(chapter) + " - Alan Turing}\maketitle" + chapter_tex + r"\end{document}")
        # BibTeX (same full list for every chapter)
        bib_filename = f"chapter_{chapter}.bib"
        with open("references.bib", "r") as f:
            bib_content = f.read()
        with open(bib_filename, "w") as f:
            f.write(bib_content)
        # Show download buttons immediately
        st.success(f"✅ Chapter {chapter} finished!")
        col1, col2 = st.columns(2)
        with col1:
            with open(chapter_tex_filename, "r") as f:
                st.download_button(f"📥 Download Chapter {chapter}.tex", f.read(), chapter_tex_filename)
        with col2:
            with open(bib_filename, "r") as f:
                st.download_button(f"📥 Download Chapter {chapter}.bib", f.read(), bib_filename)
        # One-line BibTeX preview (once per chapter)
        for line in bib_content.split("\n"):
            if line.strip():
                bib_preview.code(line, language="bibtex")
                time.sleep(0.08)

    st.success("✅ Full book has been written!")
    st.session_state.stage = "done"
    st.rerun()

# STAGE 4: Done (all downloads)
if st.session_state.stage == "done":
    st.subheader("🎉 Book is complete! All 10 chapters ready")
    # Full book + full bib
    with open("book.tex", "r") as f: full_tex = f.read()
    with open("references.bib", "r") as f: full_bib = f.read()
    col1, col2 = st.columns(2)
    with col1: st.download_button("📥 Full book.tex", full_tex, "book.tex")
    with col2: st.download_button("📥 Full references.bib", full_bib, "references.bib")
    # All per-chapter downloads
    st.subheader("Individual Chapter Downloads")
    for ch in range(1, 11):
        tex_file = f"chapter_{ch}.tex"
        bib_file = f"chapter_{ch}.bib"
        col1, col2 = st.columns(2)
        with col1:
            if os.path.exists(tex_file):
                with open(tex_file, "r") as f: st.download_button(f"Chapter {ch}.tex", f.read(), tex_file)
        with col2:
            if os.path.exists(bib_file):
                with open(bib_file, "r") as f: st.download_button(f"Chapter {ch}.bib", f.read(), bib_file)

st.caption("💡 Left: 3-line lively conversation + constant moving Pacman • Right: Live LaTeX + Live BibTeX (one line at a time) • Per-chapter downloads appear instantly")
