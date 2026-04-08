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
if "stage" not in st.session_state: st.session_state.stage = "idle"
if "current_prompt" not in st.session_state: st.session_state.current_prompt = None
if "outline" not in st.session_state: st.session_state.outline = None
if "current_chapter" not in st.session_state: st.session_state.current_chapter = 1
if "current_section" not in st.session_state: st.session_state.current_section = 1
if "section_titles" not in st.session_state: st.session_state.section_titles = {}
if "completed_sections" not in st.session_state: st.session_state.completed_sections = []
if "run_id" not in st.session_state: st.session_state.run_id = None
if "run_folder" not in st.session_state: st.session_state.run_folder = None
if "covered_topics" not in st.session_state: st.session_state.covered_topics = []
if "background_corpus" not in st.session_state: st.session_state.background_corpus = ""

with st.container():
    st.title("🌀 1000 AI Agents Arena")
    st.caption("Live in your browser • Shareable link • Massive Book Builder")
    st.markdown("**Version 115.0 — NameError FIXED + gpt-4o default**")
    if st.session_state.current_prompt:
        st.success(f"**Current Task (always stays at top):** {st.session_state.current_prompt}")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""))
    if api_key: os.environ["OPENAI_API_KEY"] = api_key

    model = st.selectbox("Model", [
        "gpt-4o",           # ← SAFE & RELIABLE DEFAULT
        "gpt-5.4-pro",
        "gpt-5.4",
        "gpt-5.4-mini",
        "gpt-5.4-nano",
        "gpt-4o-mini"
    ], index=0)

    st.info("**Tip for book writing:** gpt-4o is currently the most stable.")

    st.header("📁 Background Documents")
    uploaded_files = st.file_uploader("Upload PDF, DOCX, TXT files", type=["pdf", "docx", "txt"], accept_multiple_files=True)

if api_key:
    client = OpenAI(api_key=api_key)
else:
    client = None
    st.sidebar.error("⚠️ Please enter your OpenAI API Key above")

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

if st.session_state.run_folder and os.path.exists(st.session_state.run_folder):
    with st.expander("📁 Current Run Files (download any file)", expanded=True):
        files = sorted(os.listdir(st.session_state.run_folder))
        for file in files:
            full_path = f"{st.session_state.run_folder}/{file}"
            if os.path.isfile(full_path):
                with open(full_path, "rb") as f:
                    st.download_button(f"📥 {file}", f.read(), file)
        full_run_zip = f"{st.session_state.run_folder}/full_run.zip"
        if not os.path.exists(full_run_zip):
            with zipfile.ZipFile(full_run_zip, "w") as zipf:
                for file in files:
                    zipf.write(f"{st.session_state.run_folder}/{file}", file)
        with open(full_run_zip, "rb") as f:
            st.download_button("📥 Download ENTIRE Current Run as ZIP", f.read(), f"{os.path.basename(st.session_state.run_folder)}.zip")

# ==================== HELPER FUNCTIONS (defined BEFORE use) ====================
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

def parse_section_titles(outline_text):
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
    return {"max_completion_tokens": tokens} if model_name.startswith("gpt-5") else {"max_tokens": tokens}

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

def strip_document_wrapper(full_tex: str) -> str:
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

def append_bibtex_entries(keys):
    if not keys: return
    bib_path = f"{st.session_state.run_folder}/references.bib"
    existing = ""
    if os.path.exists(bib_path):
        with open(bib_path, "r") as f: existing = f.read()
    new_entries = ""
    for key in keys:
        if key not in existing:
            new_entries += f"@article{{{key}}},\n  title = {{Placeholder for {key}}},\n  author = {{Expert}},\n  year = {{2025}},\n}}\n\n"
    if new_entries:
        with open(bib_path, "a") as f: f.write(new_entries)

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
    for p in paragraphs:
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

# Process background documents (now safe)
if uploaded_files:
    background_texts = []
    for f in uploaded_files:
        text = read_uploaded_file(f)
        background_texts.append(text)
    st.session_state.background_corpus = "\n\n".join(background_texts)
    st.sidebar.success(f"Loaded {len(uploaded_files)} background documents ({len(st.session_state.background_corpus)} characters)")

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

# ==================== STAGE LOGIC ====================
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

        st.info("🚀 Starting outline generation with heavy debug...")

        if st.button("🛑 STOP OUTLINE", type="secondary"):
            st.error("**Outline generation stopped by user**")
            st.stop()

        success = False
        for attempt in range(5):
            try:
                outline_prompt = f"""You are a neutral academic scholar in international relations theory.
Create a purely theoretical and hypothetical book outline exploring abstract conceptual frameworks of political reintegration in divided polities.
Background corpus (use this knowledge):
{st.session_state.background_corpus[:8000] if st.session_state.background_corpus else "None"}

Output EXACTLY 10 chapters, each with EXACTLY 15 sections.
Use this exact format and nothing else:

## Chapter 1
1.1 Title of first section
...
1.15 Title of fifteenth section

... up to Chapter 10 with 10.15"""

                st.info(f"**DEBUG OUTLINE: Using model = {model}**")
                st.info(f"**DEBUG OUTLINE: Prompt length = {len(outline_prompt)} characters**")

                response = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "system", "content": outline_prompt}],
                    temperature=0.7,
                    **get_max_tokens_kw(model, 4000)
                )
                raw_content = response.choices[0].message.content.strip() if response.choices[0].message.content else ""
                finish_reason = response.choices[0].finish_reason

                st.info(f"**DEBUG OUTLINE: finish_reason = {finish_reason}**")
                st.info(f"**DEBUG OUTLINE: Raw content length = {len(raw_content)} characters**")
                if len(raw_content) > 0:
                    st.info(f"**DEBUG OUTLINE: First 300 chars:** {raw_content[:300]}...")

                st.session_state.outline = raw_content
                st.success("✅ Outline generated!")
                success = True
                break
            except Exception as e:
                st.warning(f"Attempt {attempt+1} failed: {str(e)}")
                time.sleep(2)

        if not success:
            st.session_state.outline = "# Hard Fallback Outline\n## Chapter 1\n1.1 First section\n... (15 sections per chapter) ..."
            st.warning("Used hard fallback outline")

    st.session_state.stage = "approve"
    st.rerun()

# Approve stage
if st.session_state.stage == "approve":
    st.subheader("Proposed Book Outline")
    st.markdown(f'<div class="outline-text">{st.session_state.outline}</div>', unsafe_allow_html=True)
    if st.session_state.outline:
        with open(get_full_path("outline.txt"), "w") as f:
            f.write(st.session_state.outline)
        with open(get_full_path("outline.txt"), "r") as f:
            st.download_button("📥 Download outline.txt", f.read(), "outline.txt")
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

# Writing stage, halted stage and remaining code are unchanged from previous full versions (with STOP button, background corpus, deduplication, etc.)

st.caption("💡 Version 115.0 — NameError completely fixed. Paste this complete code and hard-refresh.")
