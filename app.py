import streamlit as st
import os
from openai import OpenAI
import time
import random

st.set_page_config(page_title="1000 AI Agents Arena", layout="wide")

st.markdown("""
<style>
    .army-box { height: 220px; overflow-y: hidden; border: 1px solid #262730; padding: 12px; border-radius: 8px; background-color: #1E2127; }
    .latex-box { max-height: 620px; overflow-y: auto; border: 1px solid #262730; padding: 15px; border-radius: 8px; background-color: #1E2127; font-family: monospace; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

if "stage" not in st.session_state:
    st.session_state.stage = "idle"
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = None
if "outline" not in st.session_state:
    st.session_state.outline = None
if "tex_content" not in st.session_state:
    st.session_state.tex_content = ""

with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive Book Builder")
    st.markdown("**Version 41.0 - Live LaTeX Preview + Constant Activity**")
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)
    num_agents = st.slider("Number of AI Agents", 50, 1000, 120, step=50)
    num_rounds = st.slider("Conversation Rounds", 3, 10, 5)

PERSONAS = ["LaTeX Architect", "Scientific Writer", "Math LaTeX Specialist", "Document Engineer", "Research Coder", "Critical Reviewer", "Detailed Editor", "Storyteller"] * 60

client = OpenAI()

col_left, col_right = st.columns([3, 2])

with col_left:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    army_placeholder = st.empty()

if prompt := st.chat_input("Ask the swarm anything..."):
    st.session_state.current_prompt = prompt
    st.session_state.messages = [{"role": "user", "content": prompt}]
    st.session_state.stage = "outline"
    st.rerun()

# STAGE 1: Outline
if st.session_state.stage == "outline":
    with col_left:
        st.subheader("🔥 AI Army is creating the book outline...")
        latest_agents = []
        def get_thought():
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{random.randint(1,9999)}"
            ideas = ["Planning chapter structure...", "Adding historical context...", "Thinking about technical depth...", "Ensuring unique content...", "Reviewing flow..."]
            return f"• {agent_id} — {persona} thinks: {random.choice(ideas)}"
        for i in range(100):
            thought = get_thought()
            latest_agents.append(thought)
            if len(latest_agents) > 3:
                latest_agents.pop(0)
            army_placeholder.markdown("\n\n".join(latest_agents))
            time.sleep(0.12)
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": f"Create a detailed book outline for: {st.session_state.current_prompt}. Exactly 10 chapters, each with exactly 20 sections. Output clean markdown with clear headings."}],
                temperature=0.8,
                max_tokens=1600
            )
            st.session_state.outline = response.choices[0].message.content.strip()
        except Exception:
            st.session_state.outline = "Error generating outline."
    st.session_state.stage = "approve"
    st.rerun()

# STAGE 2: Approve
if st.session_state.stage == "approve":
    st.subheader("Proposed Book Outline")
    st.markdown(st.session_state.outline)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Yes, proceed to write the full book", type="primary"):
            st.session_state.stage = "writing"
            st.rerun()
    with col2:
        if st.button("🔄 No, generate a new outline"):
            st.session_state.stage = "outline"
            st.rerun()

# STAGE 3: Writing with live preview
if st.session_state.stage == "writing":
    with col_left:
        st.subheader("🔥 AI Army is writing the full book...")
    with col_right:
        st.subheader("📜 Live LaTeX Preview (updating in real time)")
        latex_preview = st.empty()

    tex_filename = "book.tex"
    with open(tex_filename, "w") as f:
        f.write(r"\documentclass[11pt]{article}\usepackage{amsmath,amssymb}\begin{document}\title{" + st.session_state.current_prompt + r"}\maketitle\begin{abstract}This book was written collaboratively by the AI Army.\end{abstract}")

    st.session_state.tex_content = ""

    progress_bar = st.progress(0)
    status_text = st.empty()

    for chapter in range(1, 11):
        status_text.text(f"Writing Chapter {chapter} of 10...")
        for section in range(1, 21):
            drafts = []
            for j in range(5):
                persona = random.choice(PERSONAS)
                agent_id = f"Agent #{random.randint(1,9999)}"
                thinking = f"• {agent_id} — {persona} thinks: Drafting detailed content for section {section} of chapter {chapter} with historical context, technical depth, and LaTeX formulas..."
                latest_agents.append(thinking)
                if len(latest_agents) > 3:
                    latest_agents.pop(0)
                army_placeholder.markdown("\n\n".join(latest_agents))
                time.sleep(0.03)

                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": f"You are {persona}. Write a VERY LONG, detailed section {section} of chapter {chapter} for the book on {st.session_state.current_prompt}. Include historical context, technical explanations, mathematical formulas, and analysis. Make this section at least 800 words long. Respond with only the LaTeX code."}],
                        temperature=0.8,
                        max_tokens=2500
                    )
                    drafts.append(response.choices[0].message.content.strip())
                except Exception:
                    pass

            # Synthesizer
            if drafts:
                try:
                    synth = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": f"Combine these 5 drafts into ONE long, detailed, non-repetitive section. Make it even longer and better. Output only LaTeX code.\n\n" + "\n\n---\n\n".join(drafts)}],
                        temperature=0.7,
                        max_tokens=3500
                    )
                    section_text = synth.choices[0].message.content.strip()
                except Exception:
                    section_text = drafts[0] if drafts else ""
            else:
                section_text = ""

            with open(tex_filename, "a") as f:
                f.write(f"\n\n\\section{{Chapter {chapter} - Section {section}}}\n{section_text}")

            st.session_state.tex_content += f"\n\n\\section{{Chapter {chapter} - Section {section}}}\n{section_text}"
            latex_preview.code(st.session_state.tex_content, language="latex")

            progress_bar.progress(min(1.0, (chapter-1)*20 + section / (10*20)))

    st.success("✅ Full book has been written!")
    st.session_state.stage = "done"
    st.rerun()

# STAGE 4: Done
if st.session_state.stage == "done":
    st.subheader("🎉 Book is complete!")
    with open("book.tex", "r") as f:
        final_tex = f.read()
    with open("references.bib", "r") as f:
        final_bib = f.read()

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 Download book.tex", final_tex, "book.tex")
    with col2:
        st.download_button("📥 Download references.bib", final_bib, "references.bib")

st.caption("💡 Left: 3-line lively conversation • Right: Live LaTeX preview (updates in real time)")
