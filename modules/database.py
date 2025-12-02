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

# --- 歷史資料查詢 (進階版) ---

def search_product_history(product_keyword, offset=0, limit=10):
    """
    搜尋產品歷史報價 (關聯查詢：明細 -> 主表 -> 客戶)
    """
    if not supabase: return [], False
    
    try:
        # 這是 Supabase 的強大之處：可以直接透過關聯抓取 nested data
        # 我們要抓：明細(*), 對應的主表(日期, 單號), 以及主表對應的客戶(名稱)
        response = supabase.table("quotation_items")\
            .select("*, quotations(quote_date, quote_no, clients(name))")\
            .ilike("product_name", f"%{product_keyword}%")\
            .order("id", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
            
        data = response.data
        
        # 整理資料格式 (扁平化)
        formatted_data = []
        for item in data:
            # 防呆：確保關聯資料存在
            q_data = item.get('quotations') or {}
            c_data = q_data.get('clients') or {}
            
            formatted_data.append({
                "日期": q_data.get('quote_date', 'N/A'),
                "單號": q_data.get('quote_no', 'N/A'),
                "客戶": c_data.get('name', '未知客戶'),
                "產品": item['product_name'],
                "數量": item['quantity'],
                "單價": item['unit_price'],
                "經銷價": item.get('dealer_price_snapshot', 0)
            })
            
        # 判斷是否還有更多資料 (如果回傳筆數 < limit，代表沒了)
        has_more = len(data) == limit
        
        return formatted_data, has_more
        
    except Exception as e:
        st.error(f"查詢錯誤: {e}")
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

# --- 儀表板統計功能 ---
def get_dashboard_stats():
    if not supabase: return 0, 0
    try:
        # 1. 取得報價單總數
        res_count = supabase.table("quotations").select("id", count="exact").execute()
        total_quotes = res_count.count
        
        # 2. 取得所有明細總金額 (簡易計算)
        # 注意：資料量大時建議改用 SQL View 或 RPC 處理，這裡先用 Python 算
        res_items = supabase.table("quotation_items").select("unit_price, quantity").execute()
        total_amount = sum([item['unit_price'] * item['quantity'] for item in res_items.data])
        
        return total_quotes, total_amount
    except:
        return 0, 0