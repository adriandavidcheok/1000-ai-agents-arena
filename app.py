import streamlit as st
import os
from openai import OpenAI
import concurrent.futures
import time
import random
from docx import Document
from io import BytesIO

st.set_page_config(page_title="1000 AI Agents Arena", layout="wide")

# CSS for sticky top + fixed-height scrollable previews
st.markdown("""
<style>
    .sticky { position: sticky; top: 0; z-index: 1000; background-color: #0E1117; padding: 10px 0; border-bottom: 1px solid #262730; }
    .preview-box {
        max-height: 520px;
        overflow-y: auto;
        border: 1px solid #262730;
        padding: 12px;
        border-radius: 8px;
        background-color: #1E2127;
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
    st.caption("Live in your browser • Shareable link • Code + LaTeX + Word")
    st.markdown("**Version 17.0 - Fixed-Size Scrollable Previews**")
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
    num_rounds = st.slider("Collaboration Rounds", 1, 5, 3)

PERSONAS = ["Python Coder", "LaTeX Architect", "Code Reviewer", "Document Engineer", "Algorithm Expert", "Math LaTeX Specialist", "Debugging Wizard", "Research Coder", "Full-Stack Developer", "Scientific Writer"] * 50

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask the swarm anything..."):
    st.session_state.current_prompt = prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    col_left, col_right = st.columns([2, 1])

    # LEFT COLUMN - Single agent overwrite
    with col_left:
        st.subheader("🔥 Live Swarm — Agents Thinking (one at a time)")
        progress_bar = st.progress(0)
        status_text = st.empty()
        client = OpenAI()
        all_contributions = []

        def get_agent_response(i, round_num):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{i+1} (Round {round_num})"
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": f"You are {persona} in a collaborative swarm. Previous work: {''.join(all_contributions[-5:])}. User request: {prompt}. Respond EXACTLY in this format:\nThinking: [one short sentence]\nContribution: [your full response]"}],
                    temperature=0.85,
                    max_tokens=400
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
                batch_end = min(batch_start + batch_size, num_agents)
                status_text.text(f"🚀 Round {round_num} — Launching batch {batch_start//batch_size + 1}...")
                with concurrent.futures.ThreadPoolExecutor(max_workers=40) as executor:
                    futures = [executor.submit(get_agent_response, i, round_num) for i in range(batch_start, batch_end)]
                    for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                        thinking, contribution, header = future.result()
                        all_contributions.append(contribution)
                        status_text.text(f"🧠 {header} thinks: {thinking}")
                        progress_bar.progress(((round_num-1)*num_agents + batch_start + idx + 1) / (num_rounds * num_agents))
                        time.sleep(0.08)

        st.success(f"✅ All {num_agents} agents × {num_rounds} rounds completed!")

    # RIGHT COLUMN - Fixed height + vertical scroll bars
    with col_right:
        st.subheader("📄 Final Preview & Downloads")

        client = OpenAI()
        synthesis_prompt = f"""
        You are the Master Synthesizer. The user asked for a very long, detailed document.
        Full swarm input: {''.join(all_contributions[:40])}
        User request: {prompt}

        Produce a PROFESSIONAL, VERY LONG and DETAILED output (aim for thousands of words / many pages when asked for a long paper):
        1. Brief executive summary
        2. Complete ready-to-run Python code in ```python block (if relevant)
        3. FULL professional LaTeX document starting with \\documentclass{{article}} and containing many detailed sections, explanations, equations, and content.
        Make the LaTeX as long and complete as possible — expand every section with real content.
        """

        final_response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.7,
            max_tokens=16000
        )
        final_text = final_response.choices[0].message.content

        # Python - fixed scrollable box
        st.markdown("**🐍 Python Code**")
        if "```python" in final_text:
            code_start = final_text.find("```python") + 9
            code_end = final_text.find("```", code_start)
            python_code = final_text[code_start:code_end].strip()
            st.markdown(f'<div class="preview-box">{st.code(python_code, language="python")}</div>', unsafe_allow_html=True)
            st.download_button("📥 Download Python (.py)", python_code, "agent_code.py")
        else:
            st.info("No Python code generated.")

        # LaTeX - fixed scrollable box
        st.markdown("**📜 LaTeX Document**")
        if "\\documentclass" in final_text:
            latex_start = final_text.find("\\documentclass")
            latex_code = final_text[latex_start:].strip()
            st.markdown(f'<div class="preview-box">{st.code(latex_code[:5000] + "\\n... (scroll for full document)", language="latex")}</div>', unsafe_allow_html=True)
            st.download_button("📥 Download LaTeX (.tex)", latex_code, "agent_paper.tex")
            st.latex(latex_code[:800] + "\n..." if len(latex_code) > 800 else latex_code)
        else:
            st.info("No LaTeX document generated.")

        # Word - fixed scrollable box
        st.markdown("**📝 Word Document**")
        doc = Document()
        doc.add_heading("1000 AI Agents Output", 0)
        doc.add_paragraph(final_text[:6000])
        bio = BytesIO()
        doc.save(bio)
        st.markdown(f'<div class="preview-box">Word preview generated ({len(final_text)} characters). Use the download button.</div>', unsafe_allow_html=True)
        st.download_button("📥 Download Word (.docx)", bio.getvalue(), "agent_document.docx",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    st.session_state.messages.append({"role": "assistant", "content": f"**{num_agents} AI Agents × {num_rounds} rounds completed** — see right column"})

st.caption("💡 Right panels are now fixed size with vertical scroll bars. Try asking for a 50-page paper again.")
