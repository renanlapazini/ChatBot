import os
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from docx import Document

# Modelo de embedding
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Vetores + textos originais
index = None
chunks = []


def carregar_arquivos(caminhos):
    """Carrega e indexa arquivos suportados para o mecanismo RAG."""

    global index, chunks

    textos = []

    for caminho in caminhos:
        if caminho.endswith(".pdf"):
            reader = PdfReader(caminho)
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            textos.append(text)

        elif caminho.endswith(".txt"):
            with open(caminho, "r", encoding="utf-8") as f:
                textos.append(f.read())

        elif caminho.endswith(".docx"):
            doc = Document(caminho)
            textos.append("\n".join(p.text for p in doc.paragraphs))

    novos_chunks = []
    for texto in textos:
        partes = [p.strip() for p in texto.split(". ") if p.strip()]
        novos_chunks.extend(partes)

    if not novos_chunks:
        index = None
        chunks = []
        return

    chunks = novos_chunks

    emb = embed_model.encode(chunks)
    emb = np.array(emb, dtype="float32")

    index = faiss.IndexFlatL2(emb.shape[1])
    index.add(emb)


def buscar_contexto(pergunta, k=5):
    if index is None:
        return []

    emb = embed_model.encode([pergunta]).astype("float32")
    distancias, indices = index.search(emb, k)

    resultados = []
    for dist, i in zip(distancias[0], indices[0]):
        if dist < 1.2:  # limiar para relevância
            resultados.append(chunks[i])

    return resultados
