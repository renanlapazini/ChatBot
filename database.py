import datetime
from supabase_client import supabase

# SALVAR MENSAGEM
def salvar_mensagem(role, content, user_id=None):
    data = {
        "role": role,
        "content": content,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }

    if user_id is not None:
        data["user_id"] = user_id

    return supabase.table("messages").insert(data).execute()

# BUSCAR HISTÓRICO
def buscar_historico(user_id=None):
    query = supabase.table("messages").select("*")

    if user_id is not None:
        query = query.eq("user_id", user_id)

    response = query.order("timestamp", desc=False).execute()
    return response.data

# SALVAR ARQUIVO
def salvar_arquivo(nome, caminho, dados_bytes):
    result = supabase.storage.from_("uploads").upload(
        caminho,
        dados_bytes,
        {"content-type": "application/octet-stream"}
    )

    if "error" in result:
        raise RuntimeError(f"Erro ao enviar arquivo: {result['error']}")

    data = {
        "file_name": nome,
        "path": caminho,
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
    }

    return supabase.table("files").insert(data).execute()

# LISTAR ARQUIVOS
def listar_arquivos():
    return supabase.storage.from_("uploads").list()
