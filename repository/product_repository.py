from service.superbase import supabase

def fetch_products():
    response = (
        supabase.table("users")
        .select("*")
        .execute()
    )

    print(response.data)
    print(response)


if __name__ == "__main__":
    fetch_products()