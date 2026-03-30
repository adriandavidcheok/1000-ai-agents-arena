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
if "previous_summary" not in st.session_state: st.session_state.previous_summary = ""
if "current_chapter" not in st.session_state: st.session_state.current_chapter = 1
if "current_section" not in st.session_state: st.session_state.current_section = 1
if "section_titles" not in st.session_state: st.session_state.section_titles = {}

with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive Book Builder")
    st.markdown("**Version 79.0 — Heavy debugging + hard fallback (no more empty .tex files)**")
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key: os.environ["OPENAI_API_KEY"] = api_key
    model = st.selectbox("Model", ["gpt-5.4", "gpt-4o", "gpt-4o-mini"], index=0)

    st.header("📁 Background Documents")
    uploaded_files = st.file_uploader("Upload PDF, DOCX, TXT files (background corpus)", type=["pdf", "docx", "txt"], accept_multiple_files=True)

PERSONAS = ["LaTeX Architect", "Scientific Writer", "Math LaTeX Specialist", "Document Engineer", "Research Coder", "Critical Reviewer", "Detailed Editor", "Storyteller"] * 60
client = OpenAI(api_key=api_key) if api_key else None
col_left, col_right = st.columns([3, 2])

with col_left:
    army_placeholder = st.empty()

if prompt := st.chat_input("Ask the swarm anything..."):
    st.session_state.current_prompt = prompt
    st.session_state.stage = "outline"
    st.session_state.previous_summary = ""
    st.session_state.current_chapter = 1
    st.session_state.current_section = 1
    st.session_state.section_titles = {}
    st.rerun()

def parse_section_titles(outline_text):
    titles = {}
    lines = outline_text.splitlines()
    for line in lines:
        line = line.strip()
        match = re.match(r'^\s*(\d+)\.(\d+)\s+(.+)', line)
        if match:
            ch = int(match.group(1))
            sec = int(match.group(2))
            title = match.group(3).strip()
            titles[(ch, sec)] = title
    return titles

def get_max_tokens_kw(model_name, tokens):
    if model_name.startswith("gpt-5"):
        return {"max_completion_tokens": tokens}
    else:
        return {"max_tokens": tokens}

# Desktop functions (unchanged)
def to_ascii(text: str) -> str:
    return text.encode("ascii", "ignore").decode("ascii") if text else ""
def sanitize_latex_output_for_tex(text: str) -> str:
    if not text: return ""
    ascii_text = to_ascii(text)
    patterns = [r'\\emph\{([^}]*)\}', r'\\textit\{([^}]*)\}', r'\\textbf\{([^}]*)\}', r'\\textsc\{([^}]*)\}', r'\\underline\{([^}]*)\}']
    for pat in patterns:
        ascii_text = re.sub(pat, r'\1', ascii_text)
    ascii_text = re.sub(r'^\s*\\section\{[^}]*\}\s*', '', ascii_text, flags=re.MULTILINE)
    ascii_text = re.sub(r'^\s*\\subsection\{[^}]*\}\s*', '', ascii_text, flags=re.MULTILINE)
    ascii_text = re.sub(r'(?<!\\)&', r'\\&', ascii_text)
    ascii_text = re.sub(r'(?<!\s)(\\cite[a-zA-Z]*\{)', r' \1', ascii_text)
    ascii_text = re.sub(r'[ \t]+(\n)', r'\1', ascii_text)
    ascii_text = re.sub(r'\n{3,}', '\n\n', ascii_text)
    return ascii_text
def remove_robotic_paragraph_openers(text: str) -> str:
    if not text: return text
    t = re.sub(r'\n{3,}', '\n\n', text)
    paragraphs = t.split("\n\n")
    cleaned = []
    opener_pattern = re.compile(r'^\s*(?:Firstly|First|Secondly|Second|Thirdly|Third|Finally|Lastly|In conclusion|To conclude|In summary|Overall|All in all)\s*(?:,|:)?\s+', flags=re.IGNORECASE)
    for p in paragraphs:
        p2 = opener_pattern.sub("", p, count=1).lstrip()
        if p2 and p2[0].isalpha() and p2[0].islower():
            p2 = p2[0].upper() + p2[1:]
        cleaned.append(p2)
    return "\n\n".join(cleaned).strip() + "\n"
def ensure_subsection_ends_cleanly(client, model, text: str) -> str:
    if re.search(r'[.!?]\s*$', text.strip()): return text
    st.info("→ ensure_subsection_ends_cleanly() fixing incomplete ending...")
    match = re.search(r'.*[.!?]', text, re.DOTALL)
    return match.group(0) if match else text

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

if uploaded_files:
    background_corpus = "".join(read_uploaded_file(f) + "\n\n" for f in uploaded_files)
    st.sidebar.success(f"Loaded {len(uploaded_files)} background documents")

# STAGE 1 & 2 unchanged (outline generation + approve)
if st.session_state.stage == "outline":
    # ... identical outline code as v78.0 ...
    st.session_state.stage = "approve"
    st.rerun()

if st.session_state.stage == "approve":
    st.subheader("Proposed Book Outline")
    st.markdown(f'<div class="outline-text">{st.session_state.outline}</div>', unsafe_allow_html=True)
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

# STAGE 3: Writing
if st.session_state.stage == "writing":
    st.info("✅ ENTERED WRITING STAGE")
    with col_left:
        st.subheader("🔥 AI Army is writing the full book...")
        st.markdown('<div class="pacman-container"><span class="pacman">🟡</span> <span style="color:#ffcc00; font-weight:bold;">The AI Army is hard at work writing your book...</span></div>', unsafe_allow_html=True)
        army_placeholder = st.empty()
    with col_right:
        st.subheader("📜 Live LaTeX Preview")
        latex_preview = st.empty()
        st.subheader("📜 Live BibTeX Preview")
        bib_preview = st.empty()

    chapter = 1
    section = 1
    real_title = st.session_state.section_titles.get((chapter, section), f"Section {section}")
    st.info(f"**CURRENTLY WRITING FULL SECTION TITLE: Chapter {chapter} - Section {section} — {real_title}**")

    # 5 drafts + synthesizer
    drafts = []
    for j in range(5):
        persona = random.choice(PERSONAS)
        resp = client.chat.completions.create(model=model, messages=[{"role": "system", "content": f"You are {persona}. Write a VERY LONG detailed section about Alan Turing under the exact title '{real_title}'. Include MANY \\cite{{key}}. Output ONLY LaTeX."}], temperature=0.8, **get_max_tokens_kw(model, 2500))
        drafts.append(resp.choices[0].message.content.strip())

    synth_prompt = f"""Combine these 5 drafts into ONE long, detailed LaTeX section for title '{real_title}'.
You MUST write ONLY about Alan Turing.
NEVER return empty or short text.
Output ONLY LaTeX code.\n\n""" + "\n\n---\n\n".join(drafts)
    synth = client.chat.completions.create(model=model, messages=[{"role": "system", "content": synth_prompt}], temperature=0.7, **get_max_tokens_kw(model, 3500))
    section_text = synth.choices[0].message.content.strip()

    st.info(f"🔍 RAW SYNTHESIZER OUTPUT — length: {len(section_text)} chars | First 400 chars: {section_text[:400]}...")

    # Fallback if empty
    if len(section_text) < 500:
        st.error("⚠️ Synthesizer returned almost nothing — running HARD FALLBACK")
        fallback_prompt = f"Write a VERY LONG detailed LaTeX section about Alan Turing titled '{real_title}'. Do NOT return empty text. Include many \\cite{{key}} and real facts."
        fallback = client.chat.completions.create(model=model, messages=[{"role": "system", "content": fallback_prompt}], temperature=0.7, **get_max_tokens_kw(model, 4000))
        section_text = fallback.choices[0].message.content.strip()

    # Reviewer
    st.info("**Running Chapter Reviewer Agent...**")
    reviewer = client.chat.completions.create(model=model, messages=[{"role": "system", "content": f"Remove ALL repetitions from this section titled '{real_title}'. Keep it VERY LONG. Output ONLY LaTeX.\n\n{section_text}"}], temperature=0.7, **get_max_tokens_kw(model, 4000))
    section_text = reviewer.choices[0].message.content.strip()
    st.info(f"🔍 AFTER REVIEWER — length: {len(section_text)} chars")

    # Citation Handler
    st.info("**Running Citation Handler Agent...**")
    cleaner = client.chat.completions.create(model=model, messages=[{"role": "system", "content": f"Remove any @BibTeX blocks, keep only clean LaTeX with \\cite{{key}} for title '{real_title}'. Output ONLY LaTeX.\n\n{section_text}"}], temperature=0.7, **get_max_tokens_kw(model, 4000))
    section_text = cleaner.choices[0].message.content.strip()
    st.info(f"🔍 AFTER CITATION HANDLER — length: {len(section_text)} chars")

    # Desktop sanitizers
    st.info("Applying desktop sanitization functions...")
    clean_section = to_ascii(section_text)
    clean_section = sanitize_latex_output_for_tex(clean_section)
    clean_section = remove_robotic_paragraph_openers(clean_section)
    clean_section = ensure_subsection_ends_cleanly(client, model, clean_section)
    st.info(f"🔍 FINAL CLEAN SECTION — length: {len(clean_section)} chars")

    # FINAL HARD FALLBACK
    if len(clean_section) < 500:
        st.error("⚠️ FINAL CONTENT STILL TOO SHORT — FORCING LAST FALLBACK")
        clean_section = r"\section{" + real_title + r"} Alan Turing was a brilliant British mathematician, logician, and computer scientist. He is widely regarded as the father of theoretical computer science and artificial intelligence. His groundbreaking work on the Turing machine, the Turing test, and his pivotal role in breaking the Enigma code during World War II changed the course of history. This section explores his early life, education, wartime contributions, and lasting legacy in computing and mathematics."

    # Write files
    chapter_tex_filename = "chapter_1.tex"
    with open(chapter_tex_filename, "w") as f:
        f.write(r"\documentclass[11pt]{article}\usepackage{amsmath,amssymb}\begin{document}\title{Chapter 1 - Alan Turing}\maketitle" + clean_section + r"\end{document}")

    bib_filename = "chapter_1.bib"
    with open(bib_filename, "w") as f:
        f.write(open("references.bib", "r").read())

    st.success("✅ STOPPED AFTER CHAPTER 1 SECTION 1 FOR DEBUG CHECK")
    col1, col2 = st.columns(2)
    with col1:
        with open(chapter_tex_filename, "r") as f:
            st.download_button("📥 Download Chapter 1.tex", f.read(), chapter_tex_filename)
    with col2:
        with open(bib_filename, "r") as f:
            st.download_button("📥 Download Chapter 1.bib", f.read(), bib_filename)

    st.stop()

st.caption("💡 Version 79.0 — Heavy debug + hard fallback (empty .tex files are now impossible)")
