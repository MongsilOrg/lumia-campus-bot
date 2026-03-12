from service.superbase import supabase

# 상품 전체 조회
# return [product_name : str]
def fetch_product():
    response = (
        supabase.table("products")
        .select("*")
        .execute()
    )
    res = response.data
    return [data['product_name'] for data in res] if res else []

# 상품추가
# return [id : int , name : str]
def add_product(product_name , price , con , image_url = None):
    data = {
        "product_name" : product_name,
        "product_cost" : price,
        "product_image" : image_url,
        "constructor" : con,
    }
    res = supabase.table("products").insert(data).execute()
    return [res.data[0]['id'],res.data[0]['product_name']] if res else None

# 상품 삭제
# return product_name : str
def delete_product(product_name):
    res = supabase.table("products").delete().eq("product_name", product_name).execute()
    if res.data and len(res.data) > 0:
        return res.data[0]['product_name']
    else:
        return None
    
# 상품 구매
# return 
# 상품이 없을 경우 = '주문하신 상품은 존재하지 않습니다 관리자에게 문의 주세요'
# 포인트가 부족할 경우 = '포인트가 부족합니다.'
# 재고가 없을 경우 = '재고가 없습니다 관리자에게 문의 주세요'
# return = [coupon code : str , point : int]
def buy_product(user_id , product_name):
    from repository.point_repository import fetch_point
    res = supabase.rpc("buy_product", {'u_id': user_id, 'p_name': product_name}).execute()
    point = fetch_point(user_id)
    data = res.data
    return [data,point] if res else None

# 쿠폰 코드 추출
# 관리자들이 쿠폰 코드를 추출 할 때 사용 혹은 무료 코드도 사용 가능함.
# return
# 재고가 없는 경우 = '재고가 없습니다'
# return = coupon code : str
def extract_coupon_code(user_id , product_name):
    res = supabase.rpc("extract_code", {'u_id': user_id, 'p_name': product_name}).execute()
    data = res.data
    return data if res else None