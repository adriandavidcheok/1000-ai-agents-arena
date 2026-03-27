import streamlit as st
import os
from openai import OpenAI
import concurrent.futures
import time
import random
from docx import Document
from io import BytesIO

st.set_page_config(page_title="1000 AI Agents Arena", layout="wide")

# ====================== SESSION STATE ======================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = None

# ====================== TOP HEADER ======================
st.title("🌀 1000 AI Agents Arena")
st.caption("Live in your browser • Shareable link • Code + LaTeX + Word • Ready for press release!")

if st.session_state.current_prompt:
    st.success(f"**Current Task:** {st.session_state.current_prompt}")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)
    num_agents = st.slider("Number of AI Agents", 100, 1000, 300, step=50)
    st.info(f"≈ {num_agents} agents running in parallel batches")

# ====================== PERSONAS ======================
PERSONAS = ["Python Coder", "LaTeX Architect", "Code Reviewer", "Document Engineer", "Algorithm Expert", "Math LaTeX Specialist", "Debugging Wizard", "Research Coder", "Full-Stack Developer", "Scientific Writer"] * 100

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

    with st.chat_message("assistant"):
        client = OpenAI()
        
        left_col, right_col = st.columns([2, 1])
        
        with left_col:
            st.subheader("🔥 Live Swarm — 1000 Agents Thinking")
            progress_bar = st.progress(0)
            status_text = st.empty()
            thoughts_container = st.expander("📢 What each agent is thinking (live)", expanded=True)
            thoughts_list = []

            all_contributions = []
            batch_size = 50
            max_workers = 40

            def get_agent_response(i):
                persona = random.choice(PERSONAS)
                agent_id = f"Agent #{i+1}"
                
                system_prompt = f"""
                You are {persona} in a swarm of {num_agents} AI agents.
                User request: {prompt}
                Previous contributions: {''.join(all_contributions[-3:]) if all_contributions else 'None yet'}
                
                Respond EXACTLY in this format:
                Thinking: [one short, clear sentence about what you are thinking/contributing right now]
                Contribution: [your full helpful response — include complete code or LaTeX snippets if needed]
                """
                try:
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "system", "content": system_prompt},
                                  {"role": "user", "content": "Contribute now!"}],
                        temperature=0.85,
                        max_tokens=400
                    )
                    reply = response.choices[0].message.content.strip()
                    if "Thinking:" in reply and "Contribution:" in reply:
                        thinking = reply.split("Thinking:")[1].split("Contribution:")[0].strip()
                        contribution = reply.split("Contribution:")[1].strip()
                    else:
                        thinking = reply[:120] + "..."
                        contribution = reply
                    return thinking, contribution, f"**{agent_id} — {persona}**"
                except Exception as e:
                    return f"Error: {str(e)[:80]}", "", f"**{agent_id}**"

            for batch_start in range(0, num_agents, batch_size):
                batch_end = min(batch_start + batch_size, num_agents)
                status_text.text(f"🚀 Launching batch {batch_start//batch_size + 1} of {num_agents} agents...")
                
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(get_agent_response, i) for i in range(batch_start, batch_end)]
                    for idx, future in enumerate(concurrent.futures.as_completed(futures)):
                        thinking, contribution, header = future.result()
                        all_contributions.append(contribution)
                        
                        thoughts_list.append(f"{header} thinks: {thinking}")
                        with thoughts_container:
                            st.markdown("• " + thoughts_list[-1])
                        
                        progress = (batch_start + idx + 1) / num_agents
                        progress_bar.progress(progress)
                        time.sleep(0.02)

            st.success(f"✅ All {num_agents} agents contributed!")

        # ====================== RIGHT COLUMN — LIVE PREVIEW ======================
        with right_col:
            st.subheader("📄 Live Preview")
            preview_placeholder = st.empty()

        # ====================== FINAL SYNTHESIS ======================
        synthesis_prompt = f"""
        You are the Master Synthesizer.
        Full swarm input: {''.join(all_contributions)}
        User request: {prompt}
        
        Produce:
        1. Brief summary
        2. Complete ready-to-run Python code (in ```python block)
        3. Full professional LaTeX document (complete \\documentclass{{article}} ... \\end{{document}})
        """
        
        final_response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.7,
            max_tokens=4000
        )
        final_text = final_response.choices[0].message.content

        # Fill the right column
        with preview_placeholder.container():
            st.markdown("**Final Output Ready**")
            
            # Python code
            if "```python" in final_text:
                code_start = final_text.find("```python") + 9
                code_end = final_text.find("```", code_start)
                python_code = final_text[code_start:code_end].strip()
                st.code(python_code, language="python")
                st.download_button("📥 Download Python (.py)", python_code, "agent_code.py", key="py_btn")

            # LaTeX
            if "\\documentclass" in final_text:
                latex_start = final_text.find("\\documentclass")
                latex_code = final_text[latex_start:].strip()
                st.code(latex_code[:1500] + "\n... (full document)", language="latex")
                st.download_button("📥 Download LaTeX (.tex)", latex_code, "agent_paper.tex", key="tex_btn")
                st.latex(latex_code[:800] + "\n..." if len(latex_code) > 800 else latex_code)

            # Word document
            doc = Document()
            doc.add_heading("1000 AI Agents Output", 0)
            doc.add_paragraph(final_text[:2000] + "\n\n(full document continues in the files above)")
            bio = BytesIO()
            doc.save(bio)
            st.download_button("📥 Download Word (.docx)", bio.getvalue(), "agent_document.docx", 
                              "application/vnd.openxmlformats-officedocument.wordprocessingml.document", key="docx_btn")

    # Save to history
    st.session_state.messages.append({"role": "assistant", "content": f"**{num_agents} AI Agents Swarm completed!**"})

st.caption("💡 Refresh the page if you want to clear everything. Your public link is ready for the press release!")
