from service.superbase import supabase

# 자신의 포인트 조회 return point : int
def fetch_point(user_id):
    response = (
        supabase.table("users")
        .select("user_point")
        .eq("user_id", user_id)
        .execute()
    )
    res = response.data
    return res[0]['user_point'] if res else None

# 포인트 증가
# return point : int
def plus_point(user_id , value):
    supabase.rpc("plus_point", {"u_id": user_id, "amount": value}).execute()
    return fetch_point(user_id)

# 포인트 감소
# return point : int
def minus_point(user_id , value):
    supabase.rpc("minus_point", {"u_id": user_id, "amount": value}).execute()
    return fetch_point(user_id)

# 포인트 업데이트
# return point : int
def update_point(user_id, value):
    supabase.rpc("update_point", {"u_id": user_id, "new_value": value}).execute()
    return fetch_point(user_id)


if __name__ == "__main__":
    test_user_id = 123123  # 확인할 사용자 ID
    print("current point:", fetch_point(test_user_id))
