from service.superbase import supabase

# 자신의 포인트 조회 return point : int
async def fetch_point(user_id):
    response = await supabase.table("users").select("user_point").eq("user_id", user_id).execute()
    data = response.data
    return data[0]["user_point"] if data else None

# 포인트 증가
# return point : int
async def plus_point(user_id, value):
    point = await supabase.rpc("plus_point", {"u_id": user_id, "amount": value}).execute()
    return point.data

# 포인트 감소
# return point : int
async def minus_point(user_id , value):
    point = await supabase.rpc("minus_point", {"u_id": user_id, "amount": value}).execute()
    return point.data

# 포인트 업데이트
# return point : int
async def update_point(user_id, value):
    point = await supabase.rpc("update_point", {"u_id": user_id, "new_value": value}).execute()
    return point.data


if __name__ == "__main__":
    test_user_id = 123123  # 확인할 사용자 ID
    print("current point:", fetch_point(test_user_id))
