import os

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = "https://zevhkcbbqtonjdxztylr.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_KEY:
    raise ValueError("Erro: SUPABASE_KEY não encontrada no arquivo .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

