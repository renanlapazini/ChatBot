import datetime
import os
import tempfile

import streamlit as st
from groq import Groq
from dotenv import load_dotenv

from rag import carregar_arquivos, buscar_contexto
from database import (
    criar_chat,
    salvar_mensagem,
    buscar_historico,
    listar_chats,
    salvar_arquivo,
    atualizar_titulo_chat,
)
from filename_utils import sanitize_filename, sanitize_storage_path
from chat_titles import generate_chat_title

# Carrega variáveis do .env
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("Erro: GROQ_API_KEY não encontrada no arquivo .env")

# Cliente Groq
client = Groq(api_key=api_key)


def gerar_resposta(mensagem: str) -> str:
    """Gera resposta usando o contexto recuperado via RAG."""
    contexto = buscar_contexto(mensagem, k=5)

    if not contexto:
        return "Não há dados suficientes nos arquivos fornecidos para responder isso."

    prompt = (
        "Responda SOMENTE com base nos trechos abaixo. "
        "Se a resposta não estiver nos trechos, diga que não há dados suficientes.\n\n"
        "Trechos relevantes:\n"
        + "\n---\n".join(contexto)
        + "\n\nPergunta do usuário:\n"
        + mensagem
    )

    modelos = [
        "llama-3.1-8b-instant",
        "allam-2-7b"
    ]

    for modelo in modelos:
        try:
            response = client.chat.completions.create(
                model=modelo,
                messages=[
                    {"role": "system", "content": "Responda estritamente usando apenas as informações dos documentos."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            return response.choices[0].message.content
        except Exception as exc:
            st.write(f"Falha no modelo {modelo}: {exc}")

    return "Erro: nenhum modelo conseguiu responder."

st.set_page_config(page_title="Chatbot", page_icon="🤖")
st.title("🤖 Chatbot com múltiplos chats")

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

# Sidebar de seleção e criação de chats
with st.sidebar:
    st.header("💬 Chats")

    try:
        chats = listar_chats()
    except Exception as exc:
        st.error(f"Não foi possível listar os chats: {exc}")
        chats = []

    for chat in chats:
        chat_id = chat.get("id")
        label = chat.get("title") or f"Chat {chat_id}"
        if st.button(label, key=f"chat-{chat_id}"):
            st.session_state.chat_id = chat_id
            st.rerun()

    if st.button("➕ Novo chat"):
        titulo = "Novo chat"
        try:
            novo_chat_id = criar_chat(titulo)
        except Exception as exc:
            st.error(f"Não foi possível criar o chat: {exc}")
            novo_chat_id = None

        if novo_chat_id is not None:
            st.session_state.chat_id = novo_chat_id
            st.rerun()

# Garante que um chat foi escolhido
if not st.session_state.chat_id:
    st.info("Selecione ou crie um novo chat para começar.")
    st.stop()

chat_id = st.session_state.chat_id

st.subheader("Arquivos do chat")
uploaded_files = st.file_uploader(
    "Envie seus arquivos (PDF, TXT, DOCX)",
    type=["pdf", "txt", "docx"],
    accept_multiple_files=True,
    key=f"uploader-{chat_id}"
)

if uploaded_files:
    caminhos = []
    for file in uploaded_files:
        safe_name = sanitize_filename(file.name)
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, safe_name)
        file_bytes = file.getvalue()
        with open(temp_path, "wb") as f:
            f.write(file_bytes)

        armazenamento_path = sanitize_storage_path(f"{chat_id}/{safe_name}")
        try:
            salvar_arquivo(safe_name, armazenamento_path, file_bytes)
        except Exception as exc:
            st.warning(f"Não foi possível salvar {safe_name} no Supabase: {exc}")

        caminhos.append(temp_path)

    carregar_arquivos(caminhos)
    st.success("Arquivos carregados e indexados com sucesso!")

st.divider()

# Histórico do chat atual
try:
    historico = buscar_historico(chat_id)
except Exception as exc:
    st.error(f"Não foi possível buscar o histórico: {exc}")
    historico = []

if not historico:
    st.caption("Nenhuma mensagem ainda. Envie algo para começar!")

for msg in historico:
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    with st.chat_message(role):
        st.write(content)

user_msg = st.chat_input("Digite sua mensagem...")

if user_msg:
    primeira_mensagem = not historico
    try:
        salvar_mensagem(chat_id, "user", user_msg)
    except Exception as exc:
        st.warning(f"Não foi possível salvar a mensagem do usuário: {exc}")

    if primeira_mensagem:
        novo_titulo = generate_chat_title(user_msg)
        try:
            atualizar_titulo_chat(chat_id, novo_titulo)
        except Exception as exc:
            st.warning(f"Não foi possível atualizar o título do chat: {exc}")

    try:
        resposta = gerar_resposta(user_msg)
    except Exception as exc:
        st.error(f"Erro ao gerar resposta: {exc}")
        resposta = "Não foi possível gerar uma resposta no momento."

    try:
        salvar_mensagem(chat_id, "assistant", resposta)
    except Exception as exc:
        st.warning(f"Não foi possível salvar a resposta do bot: {exc}")

    st.rerun()
