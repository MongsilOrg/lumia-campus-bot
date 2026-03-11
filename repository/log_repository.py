from service.superbase import supabase

# 자신의 구매 내역 조회
# 반환 형식 [name : str , product : str]
def get_log(user_id):
    response = (
        supabase.table("store")
        .select("store_name , store_product")
        .eq("user_id", user_id)
        .execute()
    )
    res = response.data
    return [res[0]['store_name'],res[0]['store_product']] if res else None