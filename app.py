import streamlit as st
import os
from openai import OpenAI
import concurrent.futures
import time
import random
from io import BytesIO

st.set_page_config(page_title="1000 AI Agents Arena", layout="wide")

# CSS for sticky top and fixed scrollable LaTeX box
st.markdown("""
<style>
    .sticky { position: sticky; top: 0; z-index: 1000; background-color: #0E1117; padding: 10px 0; border-bottom: 1px solid #262730; }
    .latex-box {
        max-height: 620px;
        overflow-y: auto;
        border: 1px solid #262730;
        padding: 15px;
        border-radius: 8px;
        background-color: #1E2127;
        font-family: monospace;
    }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = None

# ====================== STICKY TOP BANNER ======================
with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive LaTeX Builder")
    st.markdown("**Version 18.0 - Massive LaTeX Builder**")
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    model = st.selectbox("Latest Model", ["gpt-4o", "gpt-4o-mini", "o1-preview"], index=0)
    num_agents = st.slider("Number of AI Agents", 100, 1000, 300, step=50)
    num_rounds = st.slider("Collaboration Rounds", 2, 6, 4)

PERSONAS = ["Python Coder", "LaTeX Architect", "Code Reviewer", "Document Engineer", "Algorithm Expert", "Math LaTeX Specialist", "Debugging Wizard", "Research Coder", "Full-Stack Developer", "Scientific Writer"] * 50

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask the swarm anything (e.g. 'Write a 50-page LaTeX paper on quantum computing')"):
    st.session_state.current_prompt = prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    col_left, col_right = st.columns([2, 1])

    # LEFT COLUMN - Single agent live overwrite
    with col_left:
        st.subheader("🔥 Live Swarm — Agents Thinking (one at a time)")
        progress_bar = st.progress(0)
        status_text = st.empty()
        client = OpenAI()
        all_contributions = []

        def get_agent_response(i, round_num, current_latex=""):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{i+1} (Round {round_num})"
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": f"You are {persona} in a collaborative swarm building a massive LaTeX document. Current LaTeX so far: {current_latex[-2000:]}. Previous contributions: {''.join(all_contributions[-5:])}. User request: {prompt}. Respond EXACTLY in this format:\nThinking: [one short sentence]\nContribution: [your detailed LaTeX content or outline section]"}],
                    temperature=0.85,
                    max_tokens=600
                )
                reply = response.choices[0].message.content.strip()
                thinking = reply.split("Contribution:")[0].replace("Thinking:", "").strip() if "Contribution:" in reply else reply[:120]
                contribution = reply.split("Contribution:")[1].strip() if "Contribution:" in reply else reply
                return thinking, contribution, f"**{agent_id} — {persona}**"
            except Exception:
                return "Error", "", f"**{agent_id}**"

        current_latex = ""
        for round_num in range(1, num_rounds + 1):
            st.write(f"**Round {round_num} of {num_rounds}**")
            batch_size = 50
            for batch_start in range(0, num_agents, batch_size):
                batch_end = min(batch_start + batch_size, num_agents)
                status_text.text(f"🚀 Round {round_num} — Launching batch {batch_start//batch_size + 1}...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
                    futures = [executor.submit(get_agent_response, i, round_num, current_latex) for i in range(batch_start, batch_end)]
                    for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                        thinking, contribution, header = future.result()
                        all_contributions.append(contribution)
                        if "\\documentclass" in contribution or "\\section" in contribution:
                            current_latex += "\n" + contribution
                        status_text.text(f"🧠 {header} thinks: {thinking}")
                        progress_bar.progress(((round_num-1)*num_agents + batch_start + idx + 1) / (num_rounds * num_agents))
                        time.sleep(0.08)

        st.success(f"✅ All {num_agents} agents × {num_rounds} rounds completed!")

    # RIGHT COLUMN - ONLY LaTeX with fixed scrollable box
    with col_right:
        st.subheader("📜 Massive LaTeX Document (scrollable)")

        client = OpenAI()
        final_prompt = f"""
        You are the Master LaTeX Architect. You have seen {num_agents * num_rounds} agent contributions and a growing LaTeX document.
        User request: {prompt}
        Assemble EVERYTHING into one complete, extremely long, detailed professional LaTeX document.
        Make it as long and comprehensive as possible — expand every section with explanations, equations, examples, and content.
        Start with \\documentclass{{article}} and include many sections/subsections.
        Output the FULL LaTeX code only.
        """

        final_response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": final_prompt}],
            temperature=0.7,
            max_tokens=16000
        )
        final_latex = final_response.choices[0].message.content

        # Fixed-height scrollable LaTeX box
        st.markdown('<div class="latex-box">' + st.code(final_latex, language="latex") + '</div>', unsafe_allow_html=True)
        st.download_button("📥 Download Full LaTeX (.tex)", final_latex, "massive_paper.tex")

    st.session_state.messages.append({"role": "assistant", "content": f"**Massive LaTeX document generated** — scroll the right panel"})

st.caption("💡 Agents now create outline first, then write detailed sections. Right LaTeX box is fixed size with vertical scroll bar.")
