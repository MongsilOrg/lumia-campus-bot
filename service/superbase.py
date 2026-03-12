import os
from supabase import acreate_client, AsyncClient

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase: AsyncClient | None = None

async def init_supabase():
    global supabase
    if supabase is None:
        supabase = await acreate_client(url, key)
    return supabase