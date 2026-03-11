from service.superbase import supabase

# 자신의 구매 내역 조회
# 반환 형식 {'store_name': '루미아 캠퍼스 아이콘', 'store_product': 'jadas82211'}
def get_log(user_id):
    response = (
        supabase.table("store")
        .select("store_name , store_product")
        .eq("user_id", user_id)
        .execute()
    )
    res = response.data
    return res[0] if res else None