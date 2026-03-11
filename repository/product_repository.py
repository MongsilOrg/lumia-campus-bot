from service.superbase import supabase

# 상품추가
# return [id : int , name : str]
def add_product(name , cost , con , image_url = None):
    data = {
        "product_name" : name,
        "product_cost" : cost,
        "product_image" : image_url,
        "constructor" : con,
    }

    res = supabase.table("products").insert(data).execute()
    return [res.data[0]['id'],res.data[0]['product_name']] if res else None

# 사용자 삭제
# return name : int
def delete_user(user_id):
    res = supabase.table("users").delete().eq("user_id", user_id).execute()
    return res.data[0]['id'] if res else None
