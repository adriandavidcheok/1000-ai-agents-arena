import streamlit as st
import os
from openai import OpenAI
import time
import random
from io import BytesIO

st.set_page_config(page_title="1000 AI Agents Arena", layout="wide")

st.markdown("""
<style>
    .army-box { max-height: 580px; overflow-y: auto; border: 1px solid #262730; padding: 12px; border-radius: 8px; background-color: #1E2127; }
    .latex-box { max-height: 620px; overflow-y: auto; border: 1px solid #262730; padding: 15px; border-radius: 8px; background-color: #1E2127; font-family: monospace; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = None

with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive LaTeX Builder")
    st.markdown("**Version 25.0 - Faster AI Army (120 agents)**")
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    model = st.selectbox("Latest Model", ["gpt-4o-mini", "gpt-4o", "o1-preview"], index=0)
    num_agents = st.slider("Number of AI Agents", 50, 1000, 120, step=50)
    num_rounds = st.slider("Conversation Rounds", 3, 10, 5)

PERSONAS = ["LaTeX Architect", "Scientific Writer", "Math LaTeX Specialist", "Document Engineer", "Research Coder", "Critic", "Optimist", "Devil's Advocate"] * 60

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
        f.write(r"\documentclass[11pt]{article}\usepackage{amsmath,amssymb}\begin{document}\title{" + prompt + r"}\maketitle\begin{abstract}This massive document is being built live by the AI Army.\end{abstract}")

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("🔥 AI Army Conversation (agents talking to each other)")
        army_container = st.container(height=580)
        client = OpenAI()
        conversation_history = []

        def get_agent_response(i, round_num):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{i+1}"
            last_messages = "\n".join(conversation_history[-10:]) if conversation_history else "No previous messages."
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": f"You are {persona} in a live AI Army discussion. Previous messages: {last_messages}. User request: {prompt}. Respond EXACTLY in this format:\nThinking: [one short sentence]\nContribution: [your reply or new LaTeX section]"}],
                    temperature=0.9,
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
            for i in range(num_agents):
                thinking, contribution, header = get_agent_response(i, round_num)
                conversation_history.append(f"{header}: {contribution}")
                if len(conversation_history) > 15:
                    conversation_history.pop(0)
                with army_container:
                    st.markdown(f"• {header} thinks: {thinking}")
                with open(tex_filename, "a") as f:
                    f.write("\n\n" + contribution)
                time.sleep(0.03)   # very fast now

        st.success(f"✅ AI Army conversation finished!")

    with col_right:
        st.subheader("📜 Massive LaTeX Document (fixed scrollable)")
        with open(tex_filename, "r") as f:
            final_latex = f.read()
        st.markdown('<div class="latex-box">' + st.code(final_latex, language="latex") + '</div>', unsafe_allow_html=True)
        st.download_button("📥 Download Full LaTeX (.tex)", final_latex, "massive_paper.tex")

    st.session_state.messages.append({"role": "assistant", "content": f"**AI Army conversation completed**"})

st.caption("💡 Faster version. Left conversation auto-scrolls and shows latest agents. Right LaTeX box is fixed with its own scroll bar.")
