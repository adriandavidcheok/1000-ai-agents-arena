import streamlit as st
import os
from io import BytesIO

st.set_page_config(page_title="1000 AI Agents Arena", layout="wide")

# Sticky header CSS
st.markdown("""
<style>
    .sticky-header { position: sticky; top: 0; z-index: 1000; background-color: #0E1117; padding: 10px 0; border-bottom: 1px solid #262730; }
</style>
""", unsafe_allow_html=True)

# Session state
if "current_prompt" not in st.session_state:
    st.session_state.current_prompt = None

# ====================== STICKY TOP BANNER ======================
with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Code + LaTeX + Word")
    st.markdown("**Version 7.0 - Clean Restart Test**")   # ← YOU SHOULD SEE THIS
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

# ====================== SIDEBAR ======================
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

# ====================== CHAT HISTORY (simple) ======================
if "messages" not in st.session_state:
    st.session_state.messages = []
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ====================== USER INPUT ======================
if prompt := st.chat_input("Ask the swarm anything..."):
    st.session_state.current_prompt = prompt
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

# ====================== TWO-COLUMN LAYOUT (MAIN PAGE) ======================
if st.session_state.current_prompt:
    col_left, col_right = st.columns([2, 1])

    # LEFT COLUMN - Live Swarm Area
    with col_left:
        st.subheader("🔥 Live Swarm — Agents Thinking")
        st.info("This is where the 1000 agents will appear in the full version.")

    # RIGHT COLUMN - Three Preview Windows
    with col_right:
        st.subheader("📄 Final Preview & Downloads")

        st.markdown("**🐍 Python Code**")
        st.code("# Example Python code from the 1000 AI swarm", language="python")
        st.download_button("📥 Download Python (.py)", "# Example Python code", "agent_code.py")

        st.markdown("**📜 LaTeX Document**")
        st.code(r"\documentclass{article}\begin{document}Example LaTeX from swarm\end{document}", language="latex")
        st.download_button("📥 Download LaTeX (.tex)", r"\documentclass{article}\begin{document}Example LaTeX from swarm\end{document}", "agent_paper.tex")

        st.markdown("**📝 Word Document**")
        st.download_button("📥 Download Word (.docx)", b"Example Word document from the 1000 AI swarm", "agent_document.docx",
                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    st.session_state.messages.append({"role": "assistant", "content": "Swarm completed — see right column"})

st.caption("💡 If you see the right column with three download buttons, the layout works! Reply with a screenshot.")
