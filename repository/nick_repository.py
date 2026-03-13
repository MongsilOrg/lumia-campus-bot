from service.superbase import supabase

# 닉네임 변경 return new_nick : str
async def nick_change(user_id , new_nick):
    await supabase.rpc("nick_change", {"u_id": user_id, "new_nick": new_nick}).execute()
    return new_nick