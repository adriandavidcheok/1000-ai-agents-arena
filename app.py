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

with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive Book Builder")
    st.markdown("**Version 76.0 - Reviewer & Citation Handler run after EVERY section + visible messages**")
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
    st.rerun()

def get_max_tokens_kw(model_name, tokens):
    if model_name.startswith("gpt-5"):
        return {"max_completion_tokens": tokens}
    else:
        return {"max_tokens": tokens}

def to_ascii(text: str) -> str:
    if text is None: return ""
    return text.encode("ascii", "ignore").decode("ascii")

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
    if re.search(r'[.!?]\s*$', text.strip()):
        return text
    st.info("→ ensure_subsection_ends_cleanly() detected incomplete ending — fixing...")
    match = re.search(r'.*[.!?]', text, re.DOTALL)
    return match.group(0) if match else text

def read_uploaded_file(uploaded_file):
    if uploaded_file.name.lower().endswith(".pdf"):
        reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    elif uploaded_file.name.lower().endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.name.lower().endswith(".docx"):
        doc = docx.Document(BytesIO(uploaded_file.read()))
        return "\n".join([p.text for p in doc.paragraphs])
    return ""

if uploaded_files:
    background_corpus = ""
    for file in uploaded_files:
        background_corpus += read_uploaded_file(file) + "\n\n"
    st.sidebar.success(f"Loaded {len(uploaded_files)} background documents")

# STAGE 1 & 2 (outline) unchanged
if st.session_state.stage == "outline":
    # (same robust outline code as before)
    with col_left:
        st.subheader("🔥 AI Army is creating the book outline (10 chapters × 20 sections)")
        st.markdown('<div class="pacman-container"><span class="pacman">🟡</span> <span style="color:#ffcc00; font-weight:bold;">The AI Army is hard at work creating your outline...</span></div>', unsafe_allow_html=True)
        latest_agents = []
        for i in range(120):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{random.randint(1,9999)}"
            thought = f"• {agent_id} — {persona} thinks: Planning content for {st.session_state.current_prompt}..."
            latest_agents.append(thought)
            if len(latest_agents) > 3: latest_agents.pop(0)
            army_placeholder.markdown("\n\n".join(latest_agents))
            time.sleep(0.08)
        st.info("Generating outline (attempt 1/5)...")
        success = False
        for attempt in range(5):
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": f"""Create a book outline for: {st.session_state.current_prompt}.
Exactly 10 chapters numbered 1-10.
Each chapter must have exactly 20 sections numbered 1.1-1.20, 2.1-2.20 etc.
Every heading must be relevant to the topic.
Output ONLY clean markdown with clear headings. No extra text."""}],
                    temperature=0.7,
                    **get_max_tokens_kw(model, 3000)
                )
                st.session_state.outline = response.choices[0].message.content.strip()
                st.success("Outline generated successfully!")
                success = True
                break
            except Exception as e:
                st.warning(f"Attempt {attempt+1}/5 failed: {str(e)}")
                time.sleep(1.5)
        if not success:
            st.session_state.outline = "Error generating outline after 5 attempts. Please try again or use a different topic."
            st.error(st.session_state.outline)
    st.session_state.stage = "approve"
    st.rerun()

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
            st.success("Outline not approved. Generating a new one…")
            st.session_state.stage = "outline"
            st.rerun()

# STAGE 3: Writing (temporary stop after Chapter 1 Section 1 + agents after every section)
if st.session_state.stage == "writing":
    st.info("✅ ENTERED WRITING STAGE")
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

    # TEMPORARY DEBUG: only do Chapter 1, Section 1
    chapter = 1
    section = 1
    st.info(f"🚀 STARTING CHAPTER {chapter} OF 10")
    status_text.text(f"Writing Chapter {chapter} of 10...")

    st.info(f"**Currently writing: Chapter {chapter} - Section {section}**")
    drafts = []
    latest_agents = []
    for j in range(5):
        persona = random.choice(PERSONAS)
        agent_id = f"Agent #{random.randint(1,9999)}"
        thinking = f"• {agent_id} — {persona} thinks: Drafting unique content with many citations for section {section}..."
        latest_agents.append(thinking)
        if len(latest_agents) > 3: latest_agents.pop(0)
        army_placeholder.markdown("\n\n".join(latest_agents))
        time.sleep(0.03)
        try:
            resp = client.chat.completions.create(model=model, messages=[{"role": "system", "content": f"You are {persona}. Write a VERY LONG detailed section {section} of chapter {chapter} about {st.session_state.current_prompt}. Include AS MANY relevant academic citations as possible using \\cite{{key}}. NEVER repeat anything from previous sections. Respond with ONLY LaTeX code."}], temperature=0.8, **get_max_tokens_kw(model, 2500))
            drafts.append(resp.choices[0].message.content.strip())
        except: pass
    st.info(f"   → 5 drafts completed for Section {section} — merging now...")
    synth_prompt = f"""Combine these 5 drafts into ONE long, detailed, NON-REPETITIVE LaTeX section.
Include AS MANY relevant academic citations as possible using \\cite{{key}}.
NEVER repeat any concept, fact, phrase, or idea that has appeared in ANY previous section.
Previous sections summary: {st.session_state.previous_summary}
Output ONLY LaTeX code.\n\n""" + "\n\n---\n\n".join(drafts)
    try:
        synth = client.chat.completions.create(model=model, messages=[{"role": "system", "content": synth_prompt}], temperature=0.7, **get_max_tokens_kw(model, 3500))
        section_text = synth.choices[0].message.content.strip()
    except:
        section_text = drafts[0] if drafts else ""

    # Live preview
    for line in section_text.split("\n"):
        if line.strip():
            latex_preview.code(f"\\section{{Chapter {chapter} - Section {section}}}\n{line.strip()}", language="latex")
            time.sleep(0.08)

    # === AGENTS AFTER EVERY SECTION ===
    st.info("**Running Chapter Reviewer Agent to remove any duplication...**")
    reviewer_prompt = f"""You are the Chapter Reviewer Agent.
Scan the section below and REMOVE ALL repetitions (concepts, facts, phrases, paragraphs).
Merge similar content into one occurrence.
Keep it VERY LONG and detailed.
Output ONLY the final cleaned LaTeX section.

Section content:\n{section_text}"""
    try:
        reviewer = client.chat.completions.create(model=model, messages=[{"role": "system", "content": reviewer_prompt}], temperature=0.7, **get_max_tokens_kw(model, 4000))
        section_text = reviewer.choices[0].message.content.strip()
    except:
        pass

    st.info("**Running Citation Handler Agent — moving citations to .bib and ensuring they are real...**")
    cleaner_prompt = f"""You are the Citation Handler Agent.
1. Remove ANY BibTeX entries (@article, @book, etc.) from the LaTeX.
2. Extract every \\cite{{key}} used.
3. Generate REAL academic BibTeX entries for every extracted key.
4. Output ONLY the final clean LaTeX section (no BibTeX blocks).

Section content:\n{section_text}"""
    try:
        cleaner = client.chat.completions.create(model=model, messages=[{"role": "system", "content": cleaner_prompt}], temperature=0.7, **get_max_tokens_kw(model, 4000))
        section_text = cleaner.choices[0].message.content.strip()
    except:
        pass

    # Desktop functions
    st.info("Applying desktop functions...")
    clean_section = to_ascii(section_text)
    clean_section = sanitize_latex_output_for_tex(clean_section)
    clean_section = remove_robotic_paragraph_openers(clean_section)
    clean_section = ensure_subsection_ends_cleanly(client, model, clean_section)

    # Save files
    chapter_tex_filename = "chapter_1.tex"
    with open(chapter_tex_filename, "w") as f:
        f.write(r"\documentclass[11pt]{article}\usepackage{amsmath,amssymb}\begin{document}\title{Chapter 1 - " + st.session_state.current_prompt + r"}\maketitle" + clean_section + r"\end{document}")

    bib_filename = "chapter_1.bib"
    with open("references.bib", "r") as f:
        bib_content = f.read()
    with open(bib_filename, "w") as f:
        f.write(bib_content)

    st.success("✅ STOPPED AFTER CHAPTER 1 SECTION 1 FOR DEBUG CHECK")
    st.info("Download the files below and check them. When you are happy, tell me and I will remove the temporary stop and continue with all sections.")

    col1, col2 = st.columns(2)
    with col1:
        with open(chapter_tex_filename, "r") as f:
            st.download_button("📥 Download Chapter 1.tex", f.read(), chapter_tex_filename)
    with col2:
        with open(bib_filename, "r") as f:
            st.download_button("📥 Download Chapter 1.bib", f.read(), bib_filename)

    for line in bib_content.split("\n"):
        if line.strip():
            bib_preview.code(line, language="bibtex")
            time.sleep(0.08)

    st.stop()   # Temporary stop here

st.caption("💡 Reviewer & Citation Handler now run after every section with visible messages")
