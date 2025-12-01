import streamlit as st
from supabase import create_client, Client

# 初始化連線
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except:
        return None

supabase: Client = init_connection()

# 取得客戶清單
def get_clients():
    if not supabase: return [{"id": 0, "name": "連線失敗"}]
    response = supabase.table("clients").select("id, name").execute()
    return response.data

# 取得產品與價格
def get_products():
    if not supabase: return {"範例產品": 1000}
    response = supabase.table("products").select("name, dealer_price").execute()
    # 轉成字典格式: {"產品名": 價格}
    return {item['name']: item['dealer_price'] for item in response.data}

# 取得歷史紀錄 (給彈出視窗用)
def fetch_history_items(client_name, product_name, offset=0, limit=5):
    if not supabase: return [], False
    
    # 這裡做一個 Join 查詢 (簡化版，先查 items)
    # 實際運作需確保 quotation_items 有資料
    try:
        response = supabase.table("quotation_items")\
            .select("*")\
            .eq("product_name", product_name)\
            .range(offset, offset + limit)\
            .execute()
        
        data = response.data
        has_more = len(data) == limit
        return data, has_more
    except:
        return [], False