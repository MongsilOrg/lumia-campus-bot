from collections import Counter

from service.superbase import supabase


# 상품별 재고(미할당 쿠폰 수) 조회
# return {"상품명": 재고수, ...}
async def fetch_product_stock():
    response = (
        await supabase.table("store")
        .select("store_name")
        .is_("user_id", "null")
        .execute()
    )
    return dict(Counter(row["store_name"] for row in response.data))

# 상품 전체 조회
# return [product_name : str]
async def fetch_product():
    response = (
        await supabase.table("products")
        .select("*")
        .execute()
    )
    return [[data['product_name'], data['product_cost'], data.get('product_image')] for data in response.data]

# 상품추가
# return [id : int , name : str]
async def add_product(product_name , price , con , image_url = None):
    data = {
        "product_name" : product_name,
        "product_cost" : price,
        "product_image" : image_url,
        "constructor" : con,
    }
    res = await supabase.table("products").insert(data).execute()
    return [res.data[0]['id'],res.data[0]['product_name']] if res else None

# 상품 삭제
# return product_name : str
async def delete_product(product_name):
    res = await supabase.table("products").delete().eq("product_name", product_name).execute()
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
async def buy_product(user_id , product_name):
    from repository.point_repository import fetch_point
    res = await supabase.rpc("buy_product", {'u_id': user_id, 'p_name': product_name}).execute()
    point = await fetch_point(user_id)
    data = res.data
    return [data,point] if res else None

# 쿠폰 코드 추출
# 관리자들이 쿠폰 코드를 추출 할 때 사용 혹은 무료 코드도 사용 가능함.
# return
# 재고가 없는 경우 = '재고가 없습니다'
# return = coupon code : str
async def extract_coupon_code(user_id , product_name):
    res = await supabase.rpc("extract_code", {'u_id': user_id, 'p_name': product_name}).execute()
    data = res.data
    return data if res else None

async def add_coupon_code(product_name , coupon_code):
    data = {
        "store_name" : product_name,
        "store_product" : coupon_code,

    }
    res = await supabase.table("store").insert(data).execute()
    return res.data if res else None