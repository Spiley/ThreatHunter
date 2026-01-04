import os
import fitz
import faiss
import torch
import gradio as gr
from llama_cpp import Llama
from huggingface_hub import hf_hub_download
from sentence_transformers import SentenceTransformer

# -----------------------------
# 1. Config & Model Download
# -----------------------------
# Llama-3.2-3B is perfect voor CPU. We gebruiken de 4-bit versie voor snelheid.
MODEL_REPO = "bartowski/Llama-3.2-3B-Instruct-GGUF"
MODEL_FILE = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHUNK_SIZE = 1000  # Grotere blokken zijn nu mogelijk!
TOP_K = 3

# Download het model naar een lokale map
print("Model controleren/downloaden...")
model_path = hf_hub_download(repo_id=MODEL_REPO, filename=MODEL_FILE)

# -----------------------------
# 2. PDF & Vector Logic
# -----------------------------
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text("text") + "\n"
    return text

def chunk_text(text, size=CHUNK_SIZE):
    # Splitsen op basis van tekens, maar probeer zinnen heel te houden
    sentences = text.split('. ')
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) < size:
            current += s + ". "
        else:
            chunks.append(current.strip())
            current = s + ". "
    if current: chunks.append(current.strip())
    return chunks

class VectorStore:
    def __init__(self, name):
        self.embedder = SentenceTransformer(name)
        self.index = None
        self.chunks = []

    def build(self, chunks):
        self.chunks = chunks
        embeddings = self.embedder.encode(chunks, convert_to_numpy=True)
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings.astype("float32"))

    def search(self, query):
        q_emb = self.embedder.encode([query], convert_to_numpy=True).astype("float32")
        faiss.normalize_L2(q_emb)
        _, ids = self.index.search(q_emb, TOP_K)
        return [self.chunks[i] for i in ids[0] if i != -1]

# -----------------------------
# 3. Llama.cpp Chat Logica
# -----------------------------
llm = None
vs = VectorStore(EMBED_MODEL)

def load_llama():
    global llm
    if llm is None:
        print("Llama model laden in geheugen...")
        llm = Llama(
            model_path=model_path,
            n_ctx=4096,      # Groot context window
            n_threads=8,     # Pas dit aan naar je aantal CPU cores
            verbose=False
        )

def generate_answer(message, history):
    global llm, vs
    if not vs.chunks: return "Upload eerst een PDF."
    
    # Zoek relevante tekst
    context_chunks = vs.search(message)
    context_text = "\n---\n".join(context_chunks)

    # Llama-3 instructie-template
    prompt = f"""<|start_header_id|>system<|end_header_id|>
Je bent een cybersecurity expert. Gebruik de onderstaande tekst uit een OpenVAS rapport om de vraag te beantwoorden. 
Antwoord kort, feitelijk en in het Nederlands. Als het niet in de tekst staat, zeg je dat je het niet weet.

Context:
{context_text}<|eot_id|><|start_header_id|>user<|end_header_id|>
{message}<|eot_id|><|start_header_id|>assistant<|end_header_id|>"""

    output = llm(prompt, max_tokens=512, stop=["<|eot_id|>"], echo=False)
    return output["choices"][0]["text"].strip()

# -----------------------------
# 4. Interface
# -----------------------------
def process_pdf(file):
    load_llama()
    text = extract_text_from_pdf(file.name)
    chunks = chunk_text(text)
    vs.build(chunks)
    return f"✅ Rapport verwerkt. {len(chunks)} fragmenten klaar voor analyse."

with gr.Blocks(theme=gr.themes.Soft()) as demo:
    gr.Markdown("OpenVAS PDF Chatbot")
    with gr.Row():
        pdf_file = gr.File(label="PDF Rapport")
        status = gr.Textbox(label="Status", interactive=False)
    
    upload_btn = gr.Button("Analyseer PDF", variant="primary")
    chatbot = gr.ChatInterface(fn=generate_answer)

    upload_btn.click(process_pdf, inputs=[pdf_file], outputs=[status])

if __name__ == "__main__":
    demo.launch()