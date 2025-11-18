"""Funções utilitárias para trabalhar com Supabase (chats, mensagens e arquivos)."""

import datetime
from typing import Any, Dict, List, Optional

from supabase_client import supabase
from filename_utils import sanitize_filename, sanitize_storage_path


def listar_chats() -> List[Dict[str, Any]]:
    """Retorna todos os chats ordenados do mais recente para o mais antigo."""
    response = (
        supabase
        .table("chats")
        .select("id,title,created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return response.data or []


def criar_chat(title: str) -> Optional[int]:
    """Cria um chat e retorna o ID criado."""
    payload = {
        "title": title,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }
    response = supabase.table("chats").insert(payload).execute()
    data = response.data or []
    if data:
        return data[0].get("id")
    return None


def salvar_mensagem(chat_id: int, role: str, content: str):
    """Salva mensagem vinculando o chat ao campo chat_id."""
    payload = {
        "chat_id": chat_id,
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    return supabase.table("messages").insert(payload).execute()


def buscar_historico(chat_id: int) -> List[Dict[str, Any]]:
    """Busca histórico filtrando por chat_id."""
    response = (
        supabase
        .table("messages")
        .select("*")
        .eq("chat_id", chat_id)
        .order("timestamp", desc=False)
        .execute()
    )
    return response.data or []


def salvar_arquivo(chat_id: int, nome: str, caminho: str, dados_bytes: bytes):
    """Faz upload para o Storage e armazena metadados na tabela files."""
    safe_name = sanitize_filename(nome)
    safe_path = sanitize_storage_path(caminho or safe_name)

    result = supabase.storage.from_("uploads").upload(
        safe_path,
        dados_bytes,
        {"content-type": "application/octet-stream"}
    )

    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(f"Erro ao enviar arquivo: {result['error']}")

    payload = {
        "chat_id": chat_id,
        "file_name": safe_name,
        "path": safe_path,
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
    }
    return supabase.table("files").insert(payload).execute()


def listar_arquivos(chat_id: int) -> List[Dict[str, Any]]:
    """Retorna metadados de arquivos associados a um chat específico."""
    response = (
        supabase
        .table("files")
        .select("id,file_name,path,uploaded_at")
        .eq("chat_id", chat_id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return response.data or []


def deletar_chat(chat_id: int):
    """Remove chat, mensagens e arquivos associados no Supabase."""
    if not chat_id:
        return

    files_response = (
        supabase
        .table("files")
        .select("id,path")
        .eq("chat_id", chat_id)
        .execute()
    )

    files_data = files_response.data or []
    file_ids = [item.get("id") for item in files_data if item.get("id")]
    file_paths = [item.get("path") for item in files_data if item.get("path")]

    if file_paths:
        supabase.storage.from_("uploads").remove(file_paths)

    if file_ids:
        supabase.table("files").delete().in_("id", file_ids).execute()

    supabase.table("messages").delete().eq("chat_id", chat_id).execute()
    supabase.table("chats").delete().eq("id", chat_id).execute()


def atualizar_titulo_chat(chat_id: int, novo_titulo: str):
    """Atualiza o título de um chat específico."""
    if not novo_titulo:
        return
    supabase.table("chats").update({"title": novo_titulo}).eq("id", chat_id).execute()


__all__ = [
    "listar_chats",
    "criar_chat",
    "salvar_mensagem",
    "buscar_historico",
    "salvar_arquivo",
    "listar_arquivos",
    "deletar_chat",
    "atualizar_titulo_chat",
]
