import streamlit as st
import os
from openai import OpenAI
import concurrent.futures
import time
import random
from io import BytesIO

st.set_page_config(page_title="1000 AI Agents Arena", layout="wide")

# CSS for fixed scrollable LaTeX box
st.markdown("""
<style>
    .latex-box {
        max-height: 620px;
        overflow-y: auto;
        border: 1px solid #262730;
        padding: 15px;
        border-radius: 8px;
        background-color: #1E2127;
        font-family: monospace;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = None

with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive LaTeX Builder")
    st.markdown("**Version 21.0 - Fixed Scrollable LaTeX + Anti-Repetition**")
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    model = st.selectbox("Latest Model", ["gpt-4o", "gpt-4o-mini", "o1-preview"], index=0)
    num_agents = st.slider("Number of AI Agents", 100, 1000, 400, step=50)
    num_rounds = st.slider("Collaboration Rounds", 3, 8, 5)

PERSONAS = ["LaTeX Architect", "Scientific Writer", "Math LaTeX Specialist", "Document Engineer", "Research Coder"] * 80

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask the swarm anything..."):
    st.session_state.current_prompt = prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    tex_filename = "massive_paper.tex"
    with open(tex_filename, "w") as f:
        f.write(r"\documentclass[11pt]{article}\usepackage{amsmath,amssymb}\begin{document}\title{" + prompt + r"}\maketitle\begin{abstract}This document is being built incrementally by the AI Army.\end{abstract}")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🔥 AI Army Conversation (many agents talking)")
        army_container = st.container(height=650)
        client = OpenAI()
        all_contributions = []

        def get_agent_response(i, round_num):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{i+1} (Round {round_num})"
            with open(tex_filename, "r") as f:
                current_latex = f.read()[-4000:]
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": f"You are {persona} in the AI Army. NEVER repeat any concept, section, or idea that has already been written. Current LaTeX: {current_latex}. Previous contributions: {''.join(all_contributions[-6:])}. User request: {prompt}. Respond EXACTLY in this format:\nThinking: [one short sentence]\nContribution: [new, unique LaTeX code for the next section/paragraph ONLY]"}],
                    temperature=0.85,
                    max_tokens=700
                )
                reply = response.choices[0].message.content.strip()
                thinking = reply.split("Contribution:")[0].replace("Thinking:", "").strip() if "Contribution:" in reply else reply[:120]
                contribution = reply.split("Contribution:")[1].strip() if "Contribution:" in reply else reply
                return thinking, contribution, f"**{agent_id} — {persona}**"
            except Exception:
                return "Error", "", f"**{agent_id}**"

        for round_num in range(1, num_rounds + 1):
            st.write(f"**Round {round_num} of {num_rounds}**")
            batch_size = 50
            for batch_start in range(0, num_agents, batch_size):
                with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
                    futures = [executor.submit(get_agent_response, i, round_num) for i in range(batch_start, batch_start + 50)]
                    for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                        thinking, contribution, header = future.result()
                        all_contributions.append(contribution)
                        with open(tex_filename, "a") as f:
                            f.write("\n\n" + contribution)
                        with army_container:
                            st.markdown(f"• {header} thinks: {thinking}")
                        time.sleep(0.06)

        st.success(f"✅ AI Army of {num_agents} agents × {num_rounds} rounds completed!")

    with col_right:
        st.subheader("📜 Massive LaTeX Document (fixed scrollable box)")

        with open(tex_filename, "r") as f:
            final_latex = f.read()

        st.markdown('<div class="latex-box">' + st.code(final_latex, language="latex") + '</div>', unsafe_allow_html=True)
        st.download_button("📥 Download Full LaTeX (.tex)", final_latex, "massive_paper.tex")

    st.session_state.messages.append({"role": "assistant", "content": f"**AI Army completed — massive LaTeX built on disk**"})

st.caption("💡 Right LaTeX box is fixed height with its own vertical scroll bar. Download button is always visible.")
