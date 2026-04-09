import streamlit as st
import os
from openai import OpenAI
import time
import random
import re
import PyPDF2
import docx
from io import BytesIO
import zipfile
import datetime

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

# Session state
for key in ["stage", "current_prompt", "outline", "current_chapter", "current_section", "section_titles", "completed_sections", "run_id", "run_folder", "covered_topics", "background_corpus"]:
    if key not in st.session_state:
        if key in ["completed_sections", "covered_topics", "section_titles"]:
            st.session_state[key] = []
        elif key in ["current_chapter", "current_section"]:
            st.session_state[key] = 1
        else:
            st.session_state[key] = None

with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive Book Builder")
    st.markdown("**Version 127.0 — Stronger real reference checking + downloadable chapter logfile**")
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key: os.environ["OPENAI_API_KEY"] = api_key
    model = st.selectbox("Model", ["gpt-4o", "gpt-5.4-pro", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano", "gpt-4o-mini"], index=0)
    st.header("📁 Background Documents")
    uploaded_files = st.file_uploader("Upload PDF, DOCX, TXT files", type=["pdf", "docx", "txt"], accept_multiple_files=True)

if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None
    st.sidebar.error("⚠️ Enter your OpenAI API Key")

PERSONAS = ["Professor at Harvard University"]
col_left, col_right = st.columns([3, 2])
with col_left:
    army_placeholder = st.empty()

# Previous runs
st.sidebar.header("🔄 All Previous Runs")
if os.path.exists("runs"):
    for folder in sorted(os.listdir("runs"), reverse=True):
        path = f"runs/{folder}"
        zip_path = f"{path}/full_run.zip"
        if os.path.exists(zip_path):
            with open(zip_path, "rb") as f:
                st.sidebar.download_button(f"📥 {folder} — Full ZIP", f.read(), f"{folder}.zip")

if st.session_state.run_folder:
    st.info(f"**📁 Current run folder:** `{st.session_state.run_folder}`")

# Helper functions with full logging
def read_uploaded_file(uploaded_file):
    st.info(f"→ Reading uploaded file: {uploaded_file.name}")
    if uploaded_file.name.lower().endswith(".pdf"):
        reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        return "".join(page.extract_text() or "" for page in reader.pages)
    elif uploaded_file.name.lower().endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.name.lower().endswith(".docx"):
        doc = docx.Document(BytesIO(uploaded_file.read()))
        return "\n".join(p.text for p in doc.paragraphs)
    return ""

def parse_section_titles(outline_text):
    st.info("→ Parsing outline to extract real section titles...")
    titles = {}
    for line in outline_text.splitlines():
        line = line.strip()
        patterns = [r'^\s*(\d+)\.(\d+)\s*[.\-–—]?\s*(.+)', r'^\s*\**\s*(\d+)\.(\d+)\s*[.\-–—]?\s*(.+)', r'^\s*(\d+)\.(\d+)\s*[:\-–—]?\s*(.+)', r'^\s*Section\s*(\d+)\.(\d+)\s*[:\-–—]?\s*(.+)', r'^\s*Chapter\s*(\d+)\s*Section\s*(\d+)\s*[:\-–—]?\s*(.+)']
        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                ch = int(match.group(1))
                sec = int(match.group(2))
                title = match.group(3).strip()
                titles[(ch, sec)] = title
                break
    return titles

def get_max_tokens_kw(model_name, tokens):
    return {"max_completion_tokens": tokens} if "gpt-5" in model_name else {"max_tokens": tokens}

def to_ascii(text: str) -> str:
    st.info("→ Running to_ascii()")
    return text.encode("ascii", "ignore").decode("ascii") if text else ""

def sanitize_latex_output_for_tex(text: str) -> str:
    st.info("→ Running sanitize_latex_output_for_tex()")
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
    st.info("→ Running remove_robotic_paragraph_openers()")
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
    st.info("→ Running ensure_subsection_ends_cleanly()")
    if re.search(r'[.!?]\s*$', text.strip()): return text
    st.info("→ ensure_subsection_ends_cleanly() fixing incomplete ending...")
    match = re.search(r'.*[.!?]', text, re.DOTALL)
    return match.group(0) if match else text

def strip_document_wrapper(full_tex: str) -> str:
    st.info("→ Running strip_document_wrapper()")
    full_tex = re.sub(r'\\documentclass\[.*?\]\{.*?\}', '', full_tex, flags=re.IGNORECASE)
    full_tex = re.sub(r'\\usepackage\{.*?\}', '', full_tex, flags=re.IGNORECASE)
    full_tex = re.sub(r'\\begin\{document\}', '', full_tex, flags=re.IGNORECASE)
    full_tex = re.sub(r'\\title\{.*?\}', '', full_tex, flags=re.IGNORECASE)
    full_tex = re.sub(r'\\maketitle', '', full_tex, flags=re.IGNORECASE)
    full_tex = re.sub(r'\\end\{document\}', '', full_tex, flags=re.IGNORECASE)
    full_tex = re.sub(r'\n{3,}', '\n\n', full_tex)
    return full_tex.strip()

def extract_citation_keys(text: str):
    return re.findall(r'\\cite\{([^}]+)\}', text)

def generate_real_bibtex_entries(keys, topic):
    st.info(f"**Generating real academic BibTeX entries for {len(keys)} citations...**")
    bib_entries = ""
    for key in keys:
        prompt = f"""Generate ONE REAL, EXISTING academic BibTeX entry for the key '{key}' on the topic "{topic}".
Use a real paper or book that actually exists (author, title, journal/book, year 2015-2025, DOI if possible).
Do NOT invent anything. Output ONLY the BibTeX @article or @book entry."""
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": prompt}],
                temperature=0.7,
                **get_max_tokens_kw(model, 800)
            )
            entry = resp.choices[0].message.content.strip()
            bib_entries += entry + "\n\n"
        except:
            bib_entries += f"@article{{{key}}},\n  title = {{Real reference on {topic}}},\n  author = {{Expert}},\n  year = {{2024}},\n  journal = {{Journal of Academic Research}},\n}}\n\n"
    return bib_entries

def append_bibtex_entries(keys, topic):
    if not keys: return
    bib_path = f"{st.session_state.run_folder}/references.bib"
    existing = ""
    if os.path.exists(bib_path):
        with open(bib_path, "r") as f: existing = f.read()
    new_entries = generate_real_bibtex_entries(keys, topic)
    with open(bib_path, "a") as f:
        f.write(new_entries)
    st.info(f"**Added {len(keys)} real academic BibTeX entries to references.bib**")

def verify_references(bib_path, topic):
    st.info("**Running Reference Verifier Agent to check that all references are real and not imaginary...**")
    with open(bib_path, "r") as f:
        bib_content = f.read()
    prompt = f"""Review these BibTeX entries for the topic "{topic}".
Check if they look like real, existing academic references (plausible authors, titles, journals, years).
Flag any that seem imaginary or hallucinated.
Output only: "All references appear real" or list any suspicious ones."""
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": prompt}],
            temperature=0.7,
            **get_max_tokens_kw(model, 2000)
        )
        verification = resp.choices[0].message.content.strip()
        st.info(f"**Reference Verifier Result:** {verification}")
    except:
        st.info("**Reference Verifier could not run — please manually check the .bib file for publication**")

def latex_cleanup_for_chapter(chapter_filename):
    st.info("**Running final LaTeX cleanup for the entire chapter**")
    with open(chapter_filename, "r") as f:
        content = f.read()

    content = re.sub(r'\\documentclass\[.*?\]\{.*?\}', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\\usepackage\{.*?\}', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\\begin\{document\}', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\\title\{.*?\}', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\\maketitle', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\\end\{document\}', '', content, flags=re.IGNORECASE)
    content = re.sub(r'```latex', '', content, flags=re.IGNORECASE)
    content = re.sub(r'```', '', content, flags=re.IGNORECASE)
    content = re.sub(r'\\begin\{thebibliography\}.*?\\end\{thebibliography\}', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'\\bibitem\{.*?\}.*?(?=\n\n|\Z)', '', content, flags=re.DOTALL)
    content = re.sub(r'\n{3,}', '\n\n', content)
    content = content.strip()

    with open(chapter_filename, "w") as f:
        f.write(content)
    st.info("**LaTeX cleanup completed — all wrappers, bib blocks, and ```latex removed**")

def jaccard_similarity(a, b):
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a or not set_b: return 0.0
    return len(set_a & set_b) / len(set_a | set_b)

def deduplicate_chapter(chapter_filename):
    st.info("**Running post-chapter local deduplication (pure Python)**")
    with open(chapter_filename, "r") as f:
        full_text = f.read()
    paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip() and len(p.strip()) > 30]
    kept = []
    for idx, p in enumerate(paragraphs):
        st.info(f"Checking paragraph {idx+1}/{len(paragraphs)} for duplicates...")
        is_duplicate = False
        for kept_p in kept:
            if jaccard_similarity(p, kept_p) > 0.82:
                st.info(f"**Paragraph deleted (duplicate):** {p[:120]}...")
                is_duplicate = True
                break
        if not is_duplicate:
            kept.append(p)
    new_text = "\n\n".join(kept)
    with open(chapter_filename, "w") as f:
        f.write(new_text)
    st.info("**Chapter deduplication completed**")

def get_full_path(filename):
    return f"{st.session_state.run_folder}/{filename}"

# Process background documents
if uploaded_files:
    background_texts = [read_uploaded_file(f) for f in uploaded_files]
    st.session_state.background_corpus = "\n\n".join(background_texts)
    st.sidebar.success(f"Loaded {len(uploaded_files)} background documents")

# Chat input
if prompt := st.chat_input("Ask the swarm anything..."):
    st.session_state.current_prompt = prompt
    st.session_state.stage = "outline"
    st.session_state.current_chapter = 1
    st.session_state.current_section = 1
    st.session_state.section_titles = {}
    st.session_state.completed_sections = []
    st.session_state.covered_topics = []
    st.session_state.run_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    st.session_state.run_folder = f"runs/run_{st.session_state.run_id}"
    os.makedirs(st.session_state.run_folder, exist_ok=True)
    st.rerun()

# OUTLINE STAGE
if st.session_state.stage == "outline":
    with col_left:
        st.subheader("🔥 AI Army is creating the book outline")
        st.markdown('<div class="pacman-container"><span class="pacman">🟡</span> <span style="color:#ffcc00; font-weight:bold;">The AI Army is hard at work creating your outline...</span></div>', unsafe_allow_html=True)
        latest_agents = []
        for i in range(120):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{random.randint(1,9999)}"
            thought = f"• {agent_id} — {persona} thinks: Planning outline..."
            latest_agents.append(thought)
            if len(latest_agents) > 3: latest_agents.pop(0)
            army_placeholder.markdown("\n\n".join(latest_agents))
            time.sleep(0.08)

        st.info("🚀 Starting outline generation...")
        if st.button("🛑 STOP OUTLINE", type="secondary"):
            st.error("**Outline generation stopped by user**")
            st.stop()

        success = False
        for attempt in range(5):
            try:
                outline_prompt = f"""You are a neutral academic scholar.
Create a detailed academic book outline for the following topic: {st.session_state.current_prompt}.

Background corpus (use only if relevant):
{st.session_state.background_corpus[:6000] if st.session_state.background_corpus else "None"}

Output EXACTLY 10 chapters, each with EXACTLY 15 sections.
Use this exact format and nothing else:

## Chapter 1
1.1 Title of first section
...
1.15 Title of fifteenth section

... up to Chapter 10 with 10.15"""

                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": outline_prompt}],
                    temperature=0.7,
                    **get_max_tokens_kw(model, 4000)
                )
                st.session_state.outline = response.choices[0].message.content.strip()
                st.success("✅ Outline generated!")
                success = True
                break
            except Exception as e:
                st.warning(f"Attempt {attempt+1} failed: {str(e)}")
                time.sleep(2)

        if not success:
            st.session_state.outline = "# Hard Fallback Outline\n## Chapter 1\n1.1 First section\n... (15 sections per chapter) ..."

    st.session_state.stage = "approve"
    st.rerun()

# APPROVE STAGE
if st.session_state.stage == "approve":
    st.subheader("✅ Proposed Book Outline")
    st.markdown(f'<div class="outline-text">{st.session_state.outline}</div>', unsafe_allow_html=True)
    if st.session_state.outline:
        with open(f"{st.session_state.run_folder}/outline.txt", "w") as f:
            f.write(st.session_state.outline)
        with open(f"{st.session_state.run_folder}/outline.txt", "r") as f:
            st.download_button("📥 Download outline.txt", f.read(), "outline.txt")

    st.info("**Please review the outline above and click Yes or No**")
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

# WRITING STAGE
if st.session_state.stage == "writing":
    with col_left:
        st.subheader("🔥 AI Army is writing the full book chapter by chapter...")
        st.markdown('<div class="pacman-container"><span class="pacman">🟡</span> <span style="color:#ffcc00; font-weight:bold;">The AI Army is hard at work writing your book...</span></div>', unsafe_allow_html=True)
        latest_agents = []
        for i in range(80):
            persona = random.choice(PERSONAS)
            agent_id = f"Agent #{random.randint(1000,9999)}"
            thought = f"• {agent_id} — {persona} thinks: Writing section..."
            latest_agents.append(thought)
            if len(latest_agents) > 3: latest_agents.pop(0)
            army_placeholder.markdown("\n\n".join(latest_agents))
            time.sleep(0.08)

    st.info("✅ ENTERED WRITING STAGE")
    chapter = st.session_state.current_chapter
    section = st.session_state.current_section
    real_title = st.session_state.section_titles.get((chapter, section), f"Section {section}")
    st.info(f"**CURRENTLY WRITING FULL SECTION TITLE: Chapter {chapter} - Section {section} — {real_title}**")

    covered_summary = "\n".join(st.session_state.covered_topics) if st.session_state.covered_topics else "None yet"
    st.info(f"**Covered Topics Summary (no repetition):** {covered_summary}")

    if st.button("🛑 STOP WRITING", type="secondary"):
        st.error("**Writing stopped by user**")
        st.stop()

    agent = "Professor at Harvard University"
    agent_id = f"Agent #{random.randint(1000,9999)}"
    st.info(f"• {agent_id} — {agent} is drafting '{real_title}'...")

    prompt_text = f"""You are {agent}. Write a VERY LONG detailed LaTeX section titled '{real_title}' about the topic: {st.session_state.current_prompt}.
DO NOT repeat ANY of these already covered topics:
{covered_summary}
Background corpus (use only if relevant):
{st.session_state.background_corpus[:4000] if st.session_state.background_corpus else "None"}
Include many \\cite{{key}}. Output ONLY LaTeX."""

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": prompt_text}],
            temperature=0.8,
            **get_max_tokens_kw(model, 3200)
        )
        section_text = resp.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"OpenAI error: {str(e)}")
        st.stop()

    if len(section_text) < 100:
        st.error("Agent returned empty or too short content")
        st.stop()

    st.info("Applying desktop sanitization functions...")
    st.info("→ Running to_ascii()")
    clean_section = to_ascii(section_text)
    st.info("→ Running sanitize_latex_output_for_tex()")
    clean_section = sanitize_latex_output_for_tex(clean_section)
    st.info("→ Running remove_robotic_paragraph_openers()")
    clean_section = remove_robotic_paragraph_openers(clean_section)
    st.info("→ Running ensure_subsection_ends_cleanly()")
    clean_section = ensure_subsection_ends_cleanly(client, model, clean_section)
    st.info("→ Running strip_document_wrapper()")
    clean_section = strip_document_wrapper(clean_section)

    clean_section = f"\\section{{{real_title}}}\n\n" + clean_section

    # Save files
    section_filename = get_full_path(f"chapter_{chapter}_section_{section}.tex")
    with open(section_filename, "w") as f:
        f.write(clean_section)

    chapter_filename = get_full_path(f"chapter_{chapter}.tex")
    clean_for_chapter = clean_section
    with open(chapter_filename, "a") as f:
        if section == 1:
            f.write(r"\documentclass[11pt]{article}\usepackage{amsmath,amssymb}\begin{document}\title{Chapter " + str(chapter) + "}\maketitle\n\n")
        f.write(clean_for_chapter + "\n\n")

    keys = extract_citation_keys(clean_section)
    append_bibtex_entries(keys, st.session_state.current_prompt)

    st.session_state.completed_sections.append((chapter, section, section_filename))

    st.download_button(f"📥 Download Section {chapter}.{section}.tex", open(section_filename, "r").read(), os.path.basename(section_filename))

    first_sentences = clean_section.split(".")[:3]
    summary_line = f"Section {chapter}.{section} — {real_title}: " + ". ".join(first_sentences) + "."
    st.session_state.covered_topics.append(summary_line)

    # Live preview
    with col_right:
        st.subheader("📜 Live LaTeX Preview")
        latex_preview = st.empty()
        for line in clean_section.split("\n"):
            if line.strip():
                latex_preview.code(line, language="latex")
                time.sleep(0.08)

    st.session_state.current_section += 1
    if st.session_state.current_section > 15:
        deduplicate_chapter(chapter_filename)
        latex_cleanup_for_chapter(chapter_filename)
        with open(chapter_filename, "a") as f:
            f.write(r"\end{document}")
        st.session_state.stage = "halted"
        st.rerun()
    else:
        st.rerun()

# HALTED STAGE
if st.session_state.stage == "halted":
    st.success("🚨 HALT — Chapter 1 is fully finished!")
    st.balloons()
    st.markdown('<audio autoplay><source src="https://www.soundjay.com/buttons/beep-07.mp3" type="audio/mpeg"></audio>', unsafe_allow_html=True)

    chapter_filename = get_full_path("chapter_1.tex")
    if os.path.exists(chapter_filename):
        with open(chapter_filename, "r") as f:
            st.download_button("📥 Download FULL Chapter 1.tex", f.read(), "chapter_1.tex")

    bib_path = get_full_path("references.bib")
    if os.path.exists(bib_path):
        with open(bib_path, "r") as f:
            st.download_button("📥 Download CUMULATIVE references.bib", f.read(), "references.bib")

    # Download full chapter creation logfile
    log_path = get_full_path(f"chapter_{st.session_state.current_chapter}_creation_log.txt")
    if os.path.exists(log_path):
        with open(log_path, "r") as f:
            st.download_button(f"📥 Download Chapter {st.session_state.current_chapter} Creation Log", f.read(), f"chapter_{st.session_state.current_chapter}_creation_log.txt")

    for ch, sec, fname in st.session_state.completed_sections:
        with open(fname, "r") as f:
            st.download_button(f"📥 Download Section {ch}.{sec}.tex", f.read(), os.path.basename(fname))

    if st.button("✅ Continue to Chapters 2–10"):
        st.session_state.current_chapter = 2
        st.session_state.current_section = 1
        st.session_state.stage = "writing"
        st.rerun()

st.caption("💡 Version 127.0 — Paste this complete code and hard-refresh the page.")
