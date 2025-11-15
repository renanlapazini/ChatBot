import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

# Carrega variáveis do .env
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("Erro: GROQ_API_KEY não encontrada no arquivo .env")

# Cliente Groq
client = Groq(api_key=api_key)


def gerar_resposta(mensagem):
    modelos = [
        "llama-3.1-8b-instant",
        "allam-2-7b"  # fallback
    ]

    for modelo in modelos:
        try:
            response = client.chat.completions.create(
                model=modelo,
                messages=[{"role": "user", "content": mensagem}],
                temperature=0.7,
                max_tokens=300
            )

            # ACESSO CORRETO!
            return response.choices[0].message.content

        except Exception as e:
            print(f"⚠️ Falha no modelo {modelo}: {e}")

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
