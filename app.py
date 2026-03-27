import streamlit as st
import os
from openai import OpenAI
import concurrent.futures
import time
import random
from docx import Document
from io import BytesIO

st.set_page_config(page_title="1000 AI Agents Arena", layout="wide")

# Custom CSS - makes the Current Task banner STICKY at the very top
st.markdown("""
<style>
    .sticky-header {
        position: sticky;
        top: 0;
        z-index: 1000;
        background-color: #0E1117;
        padding: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = None

# ====================== STICKY TOP BANNER ======================
with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Code + LaTeX + Word")
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always visible at top):** {st.session_state.current_prompt}")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key
    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)
    num_agents = st.slider("Number of AI Agents", 100, 1000, 300, step=50)

# ====================== PERSONAS ======================
PERSONAS = ["Python Coder", "LaTeX Architect", "Code Reviewer", "Document Engineer", "Algorithm Expert", "Math LaTeX Specialist", "Debugging Wizard", "Research Coder", "Full-Stack Developer", "Scientific Writer"] * 50

# ====================== CHAT HISTORY ======================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ====================== USER INPUT ======================
if prompt := st.chat_input("Ask the swarm anything (e.g. 'Create a quantum simulator in Python and write the full LaTeX paper + Word version')"):
    st.session_state.current_prompt = prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ====================== TWO-COLUMN LAYOUT ======================
    left_col, right_col = st.columns([2, 1])

    # LEFT COLUMN - Live Swarm
    with left_col:
        st.subheader("🔥 Live Swarm — Agents Thinking")
        progress_bar = st.progress(0)
        status_text = st.empty()
        thoughts_container = st.expander("📢 What each agent is thinking (live)", expanded=True)

        client = OpenAI()
        all_contributions = []

        def get_agent_response(i):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{i+1}"
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": f"You are {persona} in a swarm of {num_agents} agents. User request: {prompt}. Respond EXACTLY in this format:\nThinking: [one short sentence]\nContribution: [your full response]"}],
                    temperature=0.85,
                    max_tokens=400
                )
                reply = response.choices[0].message.content.strip()
                thinking = reply.split("Contribution:")[0].replace("Thinking:", "").strip() if "Contribution:" in reply else reply[:100]
                contribution = reply.split("Contribution:")[1].strip() if "Contribution:" in reply else reply
                return thinking, contribution, f"**{agent_id} — {persona}**"
            except Exception:
                return "Error", "", f"**{agent_id}**"

        batch_size = 50
        for batch_start in range(0, num_agents, batch_size):
            batch_end = min(batch_start + batch_size, num_agents)
            status_text.text(f"🚀 Launching batch {batch_start//batch_size + 1}...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
                futures = [executor.submit(get_agent_response, i) for i in range(batch_start, batch_end)]
                for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                    thinking, contribution, header = future.result()
                    all_contributions.append(contribution)
                    with thoughts_container:
                        st.markdown(f"• {header} thinks: {thinking}")
                    progress_bar.progress((batch_start + idx + 1) / num_agents)
                    time.sleep(0.02)

        st.success(f"✅ All {num_agents} agents contributed!")

    # RIGHT COLUMN - Three Preview Windows
    with right_col:
        st.subheader("📄 Final Preview & Downloads")
        client = OpenAI()

        synthesis_prompt = f"""
        You are the Master Synthesizer. Full swarm input: {''.join(all_contributions[:50])}
        User request: {prompt}
        Produce:
        1. Brief summary
        2. Complete ready-to-run Python code in ```python block
        3. Full professional LaTeX document starting with \\documentclass
        """
        final_response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        final_text = final_response.choices[0].message.content

        # Python Preview
        st.markdown("**🐍 Python Code**")
        if "```python" in final_text:
            code_start = final_text.find("```python") + 9
            code_end = final_text.find("```", code_start)
            python_code = final_text[code_start:code_end].strip()
            st.code(python_code, language="python")
            st.download_button("📥 Download Python (.py)", python_code, "agent_code.py")
        else:
            st.info("No Python code generated this time.")

        # LaTeX Preview
        st.markdown("**📜 LaTeX Document**")
        if "\\documentclass" in final_text:
            latex_start = final_text.find("\\documentclass")
            latex_code = final_text[latex_start:].strip()
            st.code(latex_code[:1500] + "\n... (full document)", language="latex")
            st.download_button("📥 Download LaTeX (.tex)", latex_code, "agent_paper.tex")
            st.latex(latex_code[:800] + "\n..." if len(latex_code) > 800 else latex_code)
        else:
            st.info("No LaTeX document generated this time.")

        # Word Preview
        st.markdown("**📝 Word Document**")
        doc = Document()
        doc.add_heading("1000 AI Agents Output", 0)
        doc.add_paragraph(final_text[:2500])
        bio = BytesIO()
        doc.save(bio)
        st.download_button("📥 Download Word (.docx)", bio.getvalue(), "agent_document.docx",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    # Save to history
    st.session_state.messages.append({"role": "assistant", "content": f"**{num_agents} AI Agents Swarm completed** — see right column"})

st.caption("💡 Refresh the page to start a new task. Your public link is ready for the press release!")
