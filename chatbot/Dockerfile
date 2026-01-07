# 1. Basis image (licht, stabiel)
FROM python:3.14-slim

# 2. System dependencies (nodig voor PyMuPDF, FAISS, llama.cpp)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 3. Werkdirectory in container
WORKDIR /app

# 4. Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Projectbestanden kopiëren
COPY chatbot-local.py .

# 6. Gradio gebruikt poort 7860
EXPOSE 7860

# 7. Start de app
CMD ["python", "chatbot-local.py"]