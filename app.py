import os
import tempfile

import streamlit as st
from groq import Groq
from dotenv import load_dotenv

from rag import carregar_arquivos, buscar_contexto

# Carrega variáveis do .env
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("Erro: GROQ_API_KEY não encontrada no arquivo .env")

# Cliente Groq
client = Groq(api_key=api_key)

uploaded_files = st.file_uploader(
    "Envie seus arquivos (PDF, TXT, DOCX)",
    type=["pdf", "txt", "docx"],
    accept_multiple_files=True
)

if uploaded_files:
    caminhos = []
    for file in uploaded_files:
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, file.name)
        with open(temp_path, "wb") as f:
            f.write(file.getbuffer())
        caminhos.append(temp_path)

    carregar_arquivos(caminhos)
    st.success("Arquivos carregados e indexados com sucesso!")

def gerar_resposta(mensagem):
    # Recupera contexto
    contexto = buscar_contexto(mensagem, k=5)

    # Se nada relevante encontrado:
    if not contexto:
        return "Não há dados suficientes nos arquivos fornecidos para responder isso."

    # Se houver contexto suficiente:
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

        except Exception as e:
            print(f"Falha no modelo {modelo}: {e}")

    return "Erro: nenhum modelo conseguiu responder."

# ========= UI Streamlit ========= #

st.set_page_config(page_title="Chatbot Groq", page_icon="🤖")
st.title("🤖 Chatbot com Groq Cloud + Streamlit (.env)")

if "historico" not in st.session_state:
    st.session_state.historico = []

user_msg = st.chat_input("Digite sua mensagem...")

if user_msg:
    st.session_state.historico.append(("user", user_msg))
    resposta = gerar_resposta(user_msg)
    st.session_state.historico.append(("assistant", resposta))

for role, content in st.session_state.historico:
    with st.chat_message(role):
        st.write(content)
