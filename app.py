import datetime
import os
import tempfile
import uuid

import streamlit as st
from groq import Groq
from dotenv import load_dotenv

from rag import carregar_arquivos, buscar_contexto, limpar_chat_contexto
from database import (
    criar_chat,
    salvar_mensagem,
    buscar_historico,
    listar_chats,
    salvar_arquivo,
    atualizar_titulo_chat,
    deletar_chat,
)
from filename_utils import sanitize_filename, sanitize_storage_path
from chat_titles import generate_chat_title
from auth import sign_up, sign_in, sign_out, get_current_user, set_session

# Carrega variáveis do .env
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("Erro: GROQ_API_KEY não encontrada no arquivo .env")

# Cliente Groq
client = Groq(api_key=api_key)


def gerar_resposta(chat_id: int, mensagem: str) -> str:
    """Gera resposta usando o contexto recuperado via RAG."""
    contexto = buscar_contexto(mensagem, chat_id, k=5)

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


def process_pending_uploads(chat_id: int, user_id: str) -> list[str]:
    """Envia arquivos pendentes ao Supabase e retorna caminhos temporários."""
    ensure_supabase_session()
    pending_map = st.session_state.pending_uploads.get(chat_id)
    if not pending_map:
        return []

    processed_paths: list[str] = []
    for file_id, metadata in list(pending_map.items()):
        original_name = metadata["original_name"]
        temp_path = metadata["temp_path"]
        safe_name = sanitize_filename(original_name)
        armazenamento_path = sanitize_storage_path(f"{chat_id}/{safe_name}")

        try:
            with open(temp_path, "rb") as temp_file:
                file_bytes = temp_file.read()
            salvar_arquivo(chat_id, safe_name, armazenamento_path, file_bytes)
        except Exception as exc:
            st.warning(f"Não foi possível enviar {original_name}: {exc}")
            continue

        processed_paths.append(temp_path)
        del pending_map[file_id]

    if pending_map:
        st.session_state.pending_uploads[chat_id] = pending_map
    else:
        st.session_state.pending_uploads.pop(chat_id, None)

    return processed_paths

def clear_auth_state():
    st.session_state.auth_user = None
    st.session_state.auth_token = None
    st.session_state.auth_refresh_token = None
    st.session_state.chat_id = None
    st.session_state.pending_delete_chat_id = None
    st.session_state.pending_delete_chat_title = ""
    st.session_state.pending_uploads = {}
    st.session_state.upload_tokens = {}


def bootstrap_user_session():
    token = st.session_state.auth_token
    refresh = st.session_state.auth_refresh_token
    if token and refresh:
        try:
            set_session(token, refresh)
        except Exception:
            clear_auth_state()
            return
    if not token or st.session_state.auth_user is not None:
        return
    try:
        user = get_current_user(token)
    except Exception:
        clear_auth_state()
        return
    if user:
        st.session_state.auth_user = user
    else:
        clear_auth_state()


def ensure_supabase_session() -> bool:
    """Força o cliente Supabase a usar os tokens do usuário logado."""
    token = st.session_state.get("auth_token")
    refresh = st.session_state.get("auth_refresh_token")
    if not token or not refresh:
        st.warning("Sessão expirada. Faça login novamente.")
        clear_auth_state()
        st.stop()
    try:
        set_session(token, refresh)
    except Exception as exc:
        st.warning(f"Não foi possível renovar a sessão: {exc}")
        clear_auth_state()
        st.stop()
    return True


st.set_page_config(page_title="Chatbot", page_icon="🤖")
st.title("🤖 Chatbot com múltiplos chats")

if "chat_id" not in st.session_state:
    st.session_state.chat_id = None

if "pending_delete_chat_id" not in st.session_state:
    st.session_state.pending_delete_chat_id = None
    st.session_state.pending_delete_chat_title = ""

if "pending_uploads" not in st.session_state:
    st.session_state.pending_uploads = {}

if "upload_tokens" not in st.session_state:
    st.session_state.upload_tokens = {}

if "auth_user" not in st.session_state:
    st.session_state.auth_user = None

if "auth_token" not in st.session_state:
    st.session_state.auth_token = None

if "auth_refresh_token" not in st.session_state:
    st.session_state.auth_refresh_token = None

bootstrap_user_session()

# Sidebar de autenticação e chats
with st.sidebar:
    st.header("Conta")
    current_user = st.session_state.auth_user

    if current_user:
        st.success(f"Logado como {current_user.get('email', 'usuário')}" )
        if st.button("Sair"):
            try:
                sign_out()
            except Exception as exc:
                st.warning(f"Erro ao sair: {exc}")
            clear_auth_state()
            st.rerun()
    else:
        login_tab, signup_tab = st.tabs(["Entrar", "Cadastrar"])
        with login_tab:
            with st.form("login-form"):
                login_email = st.text_input("Email", key="login-email")
                login_password = st.text_input("Senha", type="password", key="login-password")
                login_submit = st.form_submit_button("Entrar")
                if login_submit:
                    if not login_email or not login_password:
                        st.warning("Informe email e senha.")
                    else:
                        try:
                            auth_result = sign_in(login_email, login_password)
                        except Exception as exc:
                            st.error(f"Erro ao entrar: {exc}")
                        else:
                            user = auth_result.get("user")
                            token = auth_result.get("access_token")
                            if not user or not token:
                                st.error("Falha ao recuperar sessão do usuário.")
                            else:
                                st.session_state.auth_user = user
                                st.session_state.auth_token = token
                                st.session_state.auth_refresh_token = auth_result.get("refresh_token")
                                try:
                                    set_session(token, st.session_state.auth_refresh_token)
                                except Exception as exc:
                                    st.error(f"Não foi possível estabelecer sessão: {exc}")
                                    clear_auth_state()
                                    st.stop()
                                st.session_state.chat_id = None
                                st.session_state.pending_delete_chat_id = None
                                st.session_state.pending_delete_chat_title = ""
                                st.session_state.pending_uploads = {}
                                st.session_state.upload_tokens = {}
                                st.success("Login realizado!")
                                st.rerun()
        with signup_tab:
            with st.form("signup-form"):
                signup_email = st.text_input("Email", key="signup-email")
                signup_password = st.text_input("Senha", type="password", key="signup-password")
                signup_submit = st.form_submit_button("Cadastrar")
                if signup_submit:
                    if not signup_email or not signup_password:
                        st.warning("Informe email e senha para cadastro.")
                    else:
                        try:
                            user = sign_up(signup_email, signup_password)
                        except Exception as exc:
                            st.error(f"Erro ao cadastrar: {exc}")
                        else:
                            if user:
                                st.success("Cadastro realizado! Verifique seu email para confirmar a conta.")
                            else:
                                st.info("Cadastro enviado. Verifique seu email para confirmar.")

    if current_user:
        st.divider()
        st.header("💬 Chats")

        user_id = current_user.get("id")
        ensure_supabase_session()
        try:
            chats = listar_chats(user_id)
        except Exception as exc:
            st.error(f"Não foi possível listar os chats: {exc}")
            chats = []

        chat_ids = {chat.get("id") for chat in chats if chat.get("id") is not None}
        if st.session_state.chat_id and st.session_state.chat_id not in chat_ids:
            st.session_state.chat_id = None

        for chat in chats:
            chat_id = chat.get("id")
            label = chat.get("title") or f"Chat {chat_id}"
            select_col, delete_col = st.columns([0.7, 0.3], gap="small")
            with select_col:
                if st.button(label, key=f"chat-{chat_id}", use_container_width=True):
                    st.session_state.chat_id = chat_id
                    st.rerun()
            with delete_col:
                if st.button(
                    "🗑️",
                    key=f"delete-{chat_id}",
                    help="Excluir chat",
                    type="secondary",
                    use_container_width=True,
                ):
                    st.session_state.pending_delete_chat_id = chat_id
                    st.session_state.pending_delete_chat_title = label
                    st.rerun()

        if st.button("➕ Novo chat"):
            titulo = "Novo chat"
            ensure_supabase_session()
            try:
                novo_chat_id = criar_chat(titulo, user_id)
            except Exception as exc:
                st.error(f"Não foi possível criar o chat: {exc}")
                novo_chat_id = None

            if novo_chat_id is not None:
                st.session_state.chat_id = novo_chat_id
                st.rerun()

        pending_delete = st.session_state.pending_delete_chat_id
        if pending_delete:
            st.warning(f"Deseja apagar '{st.session_state.pending_delete_chat_title}'? Esta ação é permanente.")
            confirm_col, cancel_col = st.columns(2)
            with confirm_col:
                if st.button("Confirmar exclusão", key="confirm-delete"):
                    ensure_supabase_session()
                    try:
                        deletar_chat(pending_delete)
                    except Exception as exc:
                        st.error(f"Não foi possível remover o chat: {exc}")
                    else:
                        if st.session_state.chat_id == pending_delete:
                            st.session_state.chat_id = None
                        st.session_state.pending_uploads.pop(pending_delete, None)
                        st.session_state.upload_tokens.pop(pending_delete, None)
                        limpar_chat_contexto(pending_delete)
                        st.session_state.pending_delete_chat_id = None
                        st.session_state.pending_delete_chat_title = ""
                        st.rerun()
            with cancel_col:
                if st.button("Cancelar", key="cancel-delete"):
                    st.session_state.pending_delete_chat_id = None
                    st.session_state.pending_delete_chat_title = ""
                    st.rerun()

    current_user = st.session_state.auth_user
    if not current_user:
        st.stop()

    user_id = current_user.get("id")

# Garante que um chat foi escolhido
if not st.session_state.chat_id:
    st.info("Selecione ou crie um novo chat para começar.")
    st.stop()

chat_id = st.session_state.chat_id

st.subheader("Arquivos do chat")
upload_token = st.session_state.upload_tokens.get(chat_id, 0)
uploaded_files = st.file_uploader(
    "Envie seus arquivos (PDF, TXT, DOCX)",
    type=["pdf", "txt", "docx"],
    accept_multiple_files=True,
    key=f"uploader-{chat_id}-{upload_token}"
)

pending_map = st.session_state.pending_uploads.setdefault(chat_id, {})

if uploaded_files:
    novos_arquivos = 0
    for file in uploaded_files:
        file_bytes = file.getvalue()
        file_id = f"{file.name}-{len(file_bytes)}"
        if file_id in pending_map:
            continue

        temp_dir = tempfile.gettempdir()
        safe_name = sanitize_filename(file.name)
        unique_name = f"chatbot_{chat_id}_{uuid.uuid4().hex}_{safe_name}"
        temp_path = os.path.join(temp_dir, unique_name)
        with open(temp_path, "wb") as temp_file:
            temp_file.write(file_bytes)

        pending_map[file_id] = {
            "original_name": file.name,
            "temp_path": temp_path,
        }
        novos_arquivos += 1

    if novos_arquivos:
        st.info("Arquivos prontos. Eles serão enviados e indexados junto com sua próxima mensagem.")

if pending_map:
    fila = ", ".join(metadata["original_name"] for metadata in pending_map.values())
    st.caption(f"Na fila: {fila}")

st.divider()

# Histórico do chat atual
ensure_supabase_session()
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
    staged_paths = process_pending_uploads(chat_id, user_id)
    if staged_paths:
        try:
            carregar_arquivos(staged_paths, chat_id)
        except Exception as exc:
            st.error(f"Não foi possível indexar os arquivos: {exc}")
        else:
            st.success("Arquivos enviados e indexados junto com sua mensagem.")
            st.session_state.upload_tokens[chat_id] = st.session_state.upload_tokens.get(chat_id, 0) + 1
        finally:
            for path in staged_paths:
                try:
                    os.remove(path)
                except OSError:
                    pass

    primeira_mensagem = not historico
    try:
        ensure_supabase_session()
        salvar_mensagem(chat_id, "user", user_msg)
    except Exception as exc:
        st.warning(f"Não foi possível salvar a mensagem do usuário: {exc}")

    if primeira_mensagem:
        novo_titulo = generate_chat_title(user_msg)
        try:
            ensure_supabase_session()
            atualizar_titulo_chat(chat_id, novo_titulo)
        except Exception as exc:
            st.warning(f"Não foi possível atualizar o título do chat: {exc}")

    try:
        resposta = gerar_resposta(chat_id, user_msg)
    except Exception as exc:
        st.error(f"Erro ao gerar resposta: {exc}")
        resposta = "Não foi possível gerar uma resposta no momento."

    try:
        ensure_supabase_session()
        salvar_mensagem(chat_id, "assistant", resposta)
    except Exception as exc:
        st.warning(f"Não foi possível salvar a resposta do bot: {exc}")

    st.rerun()
