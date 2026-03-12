from service.superbase import supabase

# 자신의 구매 내역 조회
# 반환 형식 [name : str , product : str]
def get_log(user_id, page=1, page_size=20):
    start = (page - 1) * page_size
    end = start + page_size - 1
    response = (
        supabase.table("store")
        .select("store_name, store_product", count='exact')
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(start, end)
        .execute()
    )
    data = [[item['store_name'], item['store_product']] for item in response.data]
    return data, response.count