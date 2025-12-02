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

# --- 讀取功能 (Read) ---

def get_clients():
    if not supabase: return []
    # 依 ID 排序，最新的在下面
    response = supabase.table("clients").select("*").order("id").execute()
    return response.data

def get_products():
    if not supabase: return {}
    response = supabase.table("products").select("*").order("id").execute()
    # 回傳完整資料以便管理頁面使用，但也保留字典格式給報價頁面用
    return response.data

# --- 寫入功能 (Create/Update) ---

def add_client(name, tax_id, contact, phone, address):
    if not supabase: return False
    try:
        data = {
            "name": name,
            "tax_id": tax_id,
            "contact_person": contact,
            "phone": phone,
            "address": address
        }
        supabase.table("clients").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"新增失敗: {e}")
        return False

def add_product(name, spec, price):
    if not supabase: return False
    try:
        data = {
            "name": name,
            "spec": spec,
            "dealer_price": price
        }
        supabase.table("products").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"新增失敗: {e}")
        return False

# 取得歷史紀錄 (給彈出視窗用)
def fetch_history_items(client_name, product_name, offset=0, limit=5):
    if not supabase: return [], False
    try:
        # 這裡需對應您 Supabase 實際的資料表結構
        # 先簡單實作：搜尋報價明細
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