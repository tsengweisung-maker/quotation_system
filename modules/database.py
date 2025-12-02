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


# --- 新增功能：報價單存檔與編號 ---

from datetime import datetime

def generate_quote_no():
    """產生報價單號: YYYYMM-001 (自動遞增)"""
    if not supabase: return "OFFLINE-001"
    
    # 取得當前年月
    current_ym = datetime.now().strftime("%Y%m")
    prefix = f"QUO-{current_ym}-"
    
    # 查詢資料庫中，這個月最新的單號
    try:
        # 搜尋符合 QUO-202512-% 的單號，依單號倒序排列，取第1筆
        response = supabase.table("quotations")\
            .select("quote_no")\
            .ilike("quote_no", f"{prefix}%")\
            .order("quote_no", desc=True)\
            .limit(1)\
            .execute()
            
        if response.data:
            # 如果有單，取出最後三碼 + 1
            last_no = response.data[0]['quote_no']
            seq = int(last_no.split("-")[-1]) + 1
        else:
            # 如果這個月沒單，從 001 開始
            seq = 1
            
        return f"{prefix}{seq:03d}"
        
    except Exception as e:
        print(f"編號生成錯誤: {e}")
        return f"{prefix}000"

def save_quotation(client_id, date, items, total_amount):
    """將報價單存入資料庫"""
    if not supabase: return False, "資料庫未連線"
    
    # 1. 產生新單號
    new_quote_no = generate_quote_no()
    
    try:
        # 2. 寫入主表 (quotations)
        main_data = {
            "quote_no": new_quote_no,
            "client_id": client_id,
            "quote_date": str(date),
            # 您可以在這裡加入 'memo' 或 'sales_rep' 等欄位
        }
        # 插入並回傳資料 (為了拿到自動產生的 id)
        res_main = supabase.table("quotations").insert(main_data).execute()
        
        if not res_main.data:
            return False, "主表寫入失敗"
            
        quotation_id = res_main.data[0]['id']
        
        # 3. 寫入明細表 (quotation_items)
        items_data = []
        for item in items:
            items_data.append({
                "quotation_id": quotation_id,
                "product_name": item['product'],
                "quantity": item['qty'],
                "unit_price": item['price'],
                # 這裡建議同時記錄當時的 dealer_price (需從前端傳入或這裡重查)，先暫時存 0 或傳入值
                "dealer_price_snapshot": 0 
            })
            
        supabase.table("quotation_items").insert(items_data).execute()
        
        return True, new_quote_no
        
    except Exception as e:
        return False, str(e)