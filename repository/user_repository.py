from service.superbase import supabase

# 사용자 추가
# return id : int
async def add_user(discord_id, name , email = None, point = 0):
    data = {
        "user_name" : name,
        "user_id" : discord_id,
        "user_point" : point,
    }
    if email is not None:
        data["user_email"] = email
    res = await supabase.table("users").insert(data).execute()
    return res.data[0]['id'] if res.data else None

# 사용자 삭제
# return user_name : str
async def delete_user(user_id):
    res = await supabase.table("users").delete().eq("user_id", user_id).execute()
    return res.data[0]['user_name'] if res.data else None
