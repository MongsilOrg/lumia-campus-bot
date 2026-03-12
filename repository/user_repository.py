from service.superbase import supabase

# 임시 사용자 추가(이메일이 필수)
# return id : int
def add_user(discord_id, name , email , point = 0):
    data = {
        "user_name" : name,
        "user_id" : discord_id,
        "user_point" : point,
        "user_email" : email,
    }
    res = supabase.table("users").insert(data).execute()
    return res.data[0]['id'] if res else None

# 사용자 삭제
# return user_name : str
def delete_user(user_id):
    res = supabase.table("users").delete().eq("user_id", user_id).execute()
    return res.data[0]['user_name'] if res else None
