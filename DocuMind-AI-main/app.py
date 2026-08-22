import os
import streamlit as st

from utils.pdf_loader import extract_text_from_pdf
from utils.ocr import extract_text_from_image
from utils.cleaner import clean_text
from utils.summarizer import generate_summary, ask_document
from utils.rag import store_document, search_document, remove_document, clear_all_documents
from utils.extractor import extract_information

# --------------------------------------------------
# Streamlit Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="DocuMind AI",
    page_icon="📄",
    layout="wide"
)

# --------------------------------------------------
# Sidebar
# --------------------------------------------------
with st.sidebar:
    st.title("📄 DocuMind AI")

    st.markdown("---")

    st.subheader("Supported Files")

    st.write("✅ PDF")
    st.write("✅ JPG")
    st.write("✅ JPEG")
    st.write("✅ PNG")

    st.markdown("---")

    st.info("Upload one or more documents to begin.")

    st.markdown("---")

    st.subheader("About")

    st.write("""
    AI-powered Document Intelligence System

    • OCR

    • AI Summary

    • Multi-Document Chat (RAG)

    • Information Extraction
    """)

# --------------------------------------------------
# Directories
# --------------------------------------------------
UPLOAD_DIR = "data/uploads"
EXTRACT_DIR = "data/extracted"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(EXTRACT_DIR, exist_ok=True)

# --------------------------------------------------
# Session State
# --------------------------------------------------
if "summaries" not in st.session_state:
    st.session_state.summaries = {}          # {filename: summary_text}

if "extracted_texts" not in st.session_state:
    st.session_state.extracted_texts = {}    # {filename: extracted_text}

if "indexed_files" not in st.session_state:
    st.session_state.indexed_files = set()   # filenames already stored in ChromaDB

if "messages" not in st.session_state:
    st.session_state.messages = []

# --------------------------------------------------
# Main Page
# --------------------------------------------------
st.title("📄 DocuMind AI")
st.subheader("Intelligent Document Assistant")

st.write(
    "Upload one or more PDFs or images to extract text, summarize, "
    "and chat across all of your documents at once."
)

st.divider()

# --------------------------------------------------
# File Upload (multiple files)
# --------------------------------------------------
uploaded_files = st.file_uploader(
    "Upload PDF or Image files",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True
)

col_a, col_b = st.columns([1, 5])
with col_a:
    if st.button("🗑️ Clear all documents"):
        clear_all_documents()
        st.session_state.summaries = {}
        st.session_state.extracted_texts = {}
        st.session_state.indexed_files = set()
        st.session_state.messages = []
        st.rerun()

# --------------------------------------------------
# Process Documents
# --------------------------------------------------
if uploaded_files:

    progress = st.progress(0)
    total = len(uploaded_files)

    for idx, uploaded_file in enumerate(uploaded_files):

        # Save File
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)

        if not os.path.exists(file_path):
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

        # Only extract + index a file once
        if uploaded_file.name not in st.session_state.indexed_files:

            extension = uploaded_file.name.split(".")[-1].lower()

            if extension == "pdf":
                extracted_text = extract_text_from_pdf(file_path)
            else:
                extracted_text = extract_text_from_image(file_path)

            extracted_text = clean_text(extracted_text)

            st.session_state.extracted_texts[uploaded_file.name] = extracted_text

            with st.spinner(f"Indexing {uploaded_file.name}..."):
                store_document(extracted_text, source=uploaded_file.name)

            st.session_state.indexed_files.add(uploaded_file.name)

            # Save extracted text to disk
            text_path = os.path.join(EXTRACT_DIR, uploaded_file.name + ".txt")
            with open(text_path, "w", encoding="utf-8") as f:
                f.write(extracted_text)

        progress.progress(int(((idx + 1) / total) * 100))

    st.success(f"✅ {total} file(s) uploaded and indexed successfully!")

    all_filenames = list(st.session_state.extracted_texts.keys())

    # --------------------------------------------------
    # Tabs
    # --------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "📄 Extracted Text",
        "📝 AI Summary",
        "💬 Chat",
        "📌 Information"
    ])

    # ==================================================
    # TAB 1 - Extracted Text (per document)
    # ==================================================
    with tab1:

        selected_doc = st.selectbox(
            "Select a document",
            all_filenames,
            key="extract_select"
        )

        doc_text = st.session_state.extracted_texts[selected_doc]

        st.text_area(
            "Extracted Text",
            doc_text,
            height=450
        )

        st.download_button(
            "⬇ Download Extracted Text",
            doc_text,
            file_name=f"{selected_doc}.txt",
            mime="text/plain"
        )

    # ==================================================
    # TAB 2 - AI Summary (per document)
    # ==================================================
    with tab2:

        summary_doc = st.selectbox(
            "Select a document",
            all_filenames,
            key="summary_select"
        )

        if st.button("📝 Generate AI Summary"):

            with st.spinner("Generating Summary..."):
                st.session_state.summaries[summary_doc] = generate_summary(
                    st.session_state.extracted_texts[summary_doc]
                )

        if st.session_state.summaries.get(summary_doc):

            st.markdown(st.session_state.summaries[summary_doc])

            st.download_button(
                "⬇ Download Summary",
                st.session_state.summaries[summary_doc],
                file_name=f"{summary_doc}_summary.txt",
                mime="text/plain"
            )

    # ==================================================
    # TAB 3 - Multi-Document Chat
    # ==================================================
    with tab3:

        search_scope = st.multiselect(
            "Search within (leave empty to search all documents)",
            all_filenames,
            default=[]
        )

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        question = st.text_input(
            "Ask anything about your document(s)",
            key="question_input"
        )

        if st.button("Ask", key="ask_button") and question:

            with st.spinner("Searching..."):

                results = search_document(
                    question,
                    sources=search_scope if search_scope else None
                )

                context = "\n\n".join(
                    f"[Source: {r['source']}]\n{r['text']}" for r in results
                )

                answer = ask_document(context, question)

                sources_used = sorted({r["source"] for r in results})

            st.session_state.messages.append(
                {"role": "user", "content": question}
            )

            answer_with_sources = answer
            if sources_used:
                answer_with_sources += (
                    "\n\n*Sources: " + ", ".join(sources_used) + "*"
                )

            st.session_state.messages.append(
                {"role": "assistant", "content": answer_with_sources}
            )

            st.rerun()

    # ==================================================
    # TAB 4 - Information Extraction (per document)
    # ==================================================
    with tab4:

        info_doc = st.selectbox(
            "Select a document",
            all_filenames,
            key="info_select"
        )

        info = extract_information(st.session_state.extracted_texts[info_doc])

        st.json(info)

    # --------------------------------------------------
    # Statistics (combined across all documents)
    # --------------------------------------------------
    st.divider()

    st.subheader("📊 Document Statistics")

    combined_text = "\n".join(st.session_state.extracted_texts.values())

    s1, s2, s3 = st.columns(3)

    s1.metric("Documents", len(all_filenames))
    s2.metric("Total Words", len(combined_text.split()))
    s3.metric("Total Characters", len(combined_text))

# --------------------------------------------------
# Footer
# --------------------------------------------------
st.markdown("---")

st.caption(
    "🚀 DocuMind AI | Built with Streamlit • EasyOCR • OpenCV • Gemini • ChromaDB"
)