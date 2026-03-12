import os

from dotenv import load_dotenv
from supabase import acreate_client, AsyncClient

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase: AsyncClient | None = None

async def init_supabase():
    global supabase
    if supabase is None:
        supabase = await acreate_client(url, key)
    return supabase