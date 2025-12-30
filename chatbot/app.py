import os
import re
import fitz  # PyMuPDF
import faiss
import torch
import gradio as gr
import numpy as np

from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline


# -----------------------------
# Config
# -----------------------------
# Klein en CPU-vriendelijk. Wil je een ander model? Verander deze string.
HF_LLM_MODEL = os.getenv("HF_LLM_MODEL", "google/flan-t5-base")

# Embeddings model (goed en compact)
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

CHUNK_SIZE = 400   # tekens per chunk (simpel)
CHUNK_OVERLAP = 150
TOP_K = 3          # hoeveel chunks we meegeven aan LLM


# -----------------------------
# PDF -> tekst
# -----------------------------
def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    parts = []
    for i, page in enumerate(doc):
        text = page.get_text("text") or ""
        text = re.sub(r"\s+\n", "\n", text)
        parts.append(f"\n\n--- Page {i+1} ---\n{text}")
    return "\n".join(parts).strip()


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap
        if start < 0:
            start = 0
        if end == len(text):
            break
    return chunks


# -----------------------------
# Vector store (FAISS)
# -----------------------------
class VectorStore:
    def __init__(self, embedder_name: str):
        self.embedder = SentenceTransformer(embedder_name, device="cuda" if torch.cuda.is_available() else "cpu")
        self.index = None
        self.chunks = []
        self.dim = None

    def build(self, chunks):
        self.chunks = chunks
        emb = self.embedder.encode(chunks, convert_to_numpy=True, show_progress_bar=True)
        emb = emb.astype("float32")
        self.dim = emb.shape[1]

        # Cosine similarity via normalized vectors + inner product
        faiss.normalize_L2(emb)
        self.index = faiss.IndexFlatIP(self.dim)
        self.index.add(emb)

    def search(self, query: str, top_k: int = TOP_K):
        q = self.embedder.encode([query], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(q)
        scores, ids = self.index.search(q, top_k)
        results = []
        for score, idx in zip(scores[0], ids[0]):
            if idx == -1:
                continue
            results.append((float(score), self.chunks[idx]))
        return results


# -----------------------------
# LLM (Hugging Face)
# -----------------------------
def load_llm(model_name: str):
    tokenizer = AutoTokenizer.from_pretrained(model_name)

    # Zet model op GPU als beschikbaar
    if torch.cuda.is_available():
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name, torch_dtype=torch.float16).to("cuda")
        device = 0
    else:
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        device = -1

    gen = pipeline(
        "text2text-generation",
        model=model,
        tokenizer=tokenizer,
        max_new_tokens=256,
        do_sample=False,
        device=device,
    )
    return gen


def make_prompt(question: str, contexts: list[str]) -> str:
    context_block = "\n\n".join(contexts)

    return (
        "You are a cybersecurity assistant analysing a Greenbone/OpenVAS report.\n"
        "Answer ONLY using the information in the report below.\n"
        "If the answer is not present, say: "
        "'Deze informatie staat niet in het OpenVAS-rapport.'\n\n"
        "OpenVAS Report Data:\n"
        f"{context_block}\n\n"
        f"Question: {question}\n"
        "Answer (short and factual):"
    )


# -----------------------------
# App state
# -----------------------------
vs = None
llm = None
loaded_pdf_name = None


def ingest_pdf(file_obj):
    global vs, llm, loaded_pdf_name

    if file_obj is None:
        return "Upload eerst een PDF."

    pdf_path = file_obj.name
    loaded_pdf_name = os.path.basename(pdf_path)

    text = extract_text_from_pdf(pdf_path)
    if not text:
        return "Kon geen tekst uit de PDF halen (is het een gescande PDF zonder tekstlaag?)."

    chunks = chunk_text(text)
    vs = VectorStore(EMBED_MODEL)
    vs.build(chunks)

    if llm is None:
        llm = load_llm(HF_LLM_MODEL)

    return f"✅ PDF ingeladen: {loaded_pdf_name}\nChunks: {len(chunks)}\nLLM: {HF_LLM_MODEL}\nEmbeddings: {EMBED_MODEL}"


def answer(message, history):
    global vs, llm, loaded_pdf_name

    if vs is None or llm is None:
        return "Upload eerst een PDF en klik op 'Inladen'."

    hits = vs.search(message, TOP_K)
    contexts = [c for _, c in hits]

    prompt = make_prompt(message, contexts)
    out = llm(prompt)[0]["generated_text"]

    # Voeg (optioneel) korte bronhint toe (wel netjes, niet te lang)
    return out.strip()


with gr.Blocks(title="Chat met PDF") as demo:
    gr.Markdown("# 📄💬 Chat met je PDF (simpel)")
    with gr.Row():
        pdf = gr.File(label="Upload PDF", file_types=[".pdf"])
        status = gr.Textbox(label="Status", lines=6)

    load_btn = gr.Button("Inladen")
    load_btn.click(fn=ingest_pdf, inputs=[pdf], outputs=[status])

    chatbot = gr.ChatInterface(fn=answer)

if __name__ == "__main__":
    demo.launch()
