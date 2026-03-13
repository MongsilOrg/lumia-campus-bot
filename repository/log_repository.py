from service.superbase import supabase

# 구매 내역 조회
# 반환 형식 [name : str , product : str]
async def get_log(user_id, page=1, page_size=20):
    start = (page - 1) * page_size
    end = start + page_size - 1
    response = (
        await supabase.table("store")
        .select("store_name, store_product", count='exact')
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .range(start, end)
        .execute()
    )
    data = [[item['store_name'], item['store_product']] for item in response.data]
    return data, response.count

# 상품별 구매 내역 조회
# 반환 형식 [name : str]
async def get_product_log(product_name, page=1, page_size=20):
    start = (page - 1) * page_size
    end = start + page_size - 1
    response = (
        await supabase.table("store")
        .select("user_id, users(user_name)", count='exact')
        .eq("store_name", product_name)
        .not_.is_("user_id", "null")
        .order("created_at", desc=True)
        .range(start, end)
        .execute()
    )
    data = [[item['users']['user_name']] for item in response.data]
    return data, response.count