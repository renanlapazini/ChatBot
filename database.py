"""Funções utilitárias para trabalhar com Supabase (chats, mensagens e arquivos)."""

import datetime
from typing import Any, Dict, List, Optional

from supabase_client import supabase


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


def salvar_arquivo(nome: str, caminho: str, dados_bytes: bytes):
    """Faz upload para o Storage e armazena metadados na tabela files."""
    result = supabase.storage.from_("uploads").upload(
        caminho,
        dados_bytes,
        {"content-type": "application/octet-stream"}
    )

    if isinstance(result, dict) and result.get("error"):
        raise RuntimeError(f"Erro ao enviar arquivo: {result['error']}")

    payload = {
        "file_name": nome,
        "path": caminho,
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
    }
    return supabase.table("files").insert(payload).execute()


def listar_arquivos():
    """Lista os arquivos do bucket uploads."""
    return supabase.storage.from_("uploads").list()


__all__ = [
    "listar_chats",
    "criar_chat",
    "salvar_mensagem",
    "buscar_historico",
    "salvar_arquivo",
    "listar_arquivos",
]
