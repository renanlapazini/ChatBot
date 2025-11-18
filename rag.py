from typing import Dict, List

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader
from docx import Document

# Modelo de embedding
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Índices e chunks por chat
_indices_por_chat: Dict[int, faiss.IndexFlatL2] = {}
_chunks_por_chat: Dict[int, List[str]] = {}
_THRESHOLD = 1.2


def carregar_arquivos(caminhos, chat_id: int) -> int:
    """Carrega arquivos do chat informado e atualiza o índice correspondente."""
    if not caminhos:
        return 0

    novos_chunks = _extrair_chunks(caminhos)
    if not novos_chunks:
        return 0

    chunk_list = _chunks_por_chat.setdefault(chat_id, [])
    chunk_list.extend(novos_chunks)

    emb = embed_model.encode(novos_chunks)
    emb = np.array(emb, dtype="float32")

    index = _indices_por_chat.get(chat_id)
    if index is None:
        index = faiss.IndexFlatL2(emb.shape[1])
        _indices_por_chat[chat_id] = index

    index.add(emb)
    return len(novos_chunks)


def buscar_contexto(pergunta, chat_id: int, k=5) -> List[str]:
    index = _indices_por_chat.get(chat_id)
    chunk_list = _chunks_por_chat.get(chat_id)
    if index is None or not chunk_list:
        return []

    emb = embed_model.encode([pergunta]).astype("float32")
    distancias, indices = index.search(emb, k)

    resultados = []
    for dist, i in zip(distancias[0], indices[0]):
        if dist < _THRESHOLD and 0 <= i < len(chunk_list):
            resultados.append(chunk_list[i])

    return resultados


def limpar_chat_contexto(chat_id: int):
    """Remove índice e chunks associados a um chat (ex.: após exclusão)."""
    _indices_por_chat.pop(chat_id, None)
    _chunks_por_chat.pop(chat_id, None)


def _extrair_chunks(caminhos) -> List[str]:
    textos: List[str] = []

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

    chunks: List[str] = []
    for texto in textos:
        partes = [p.strip() for p in texto.split(". ") if p.strip()]
        chunks.extend(partes)

    return chunks
