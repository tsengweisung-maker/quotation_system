import streamlit as st
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions # 新增這行

# 初始化連線
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        
        # 【關鍵修正】設定更長的等待時間 (預設通常只有 5-10秒)
        # 我們把它設為 60 秒，給免費版資料庫足夠的時間「起床」
        options = ClientOptions(postgrest_client_timeout=60)
        
        return create_client(url, key, options=options)
    except Exception as e:
        print(f"連線初始化失敗: {e}")
        return None

supabase: Client = init_connection()

# --- 讀取功能 (Read) ---

def get_clients():
    if not supabase: return []
    try:
        response = supabase.table("clients").select("*").order("id").execute()
        return response.data
    except Exception as e:
        # 如果讀取失敗，回傳空陣列避免當機，並印出錯誤
        print(f"讀取客戶失敗: {e}")
        return []

def get_products():
    if not supabase: return {}
    try:
        response = supabase.table("products").select("*").order("id").execute()
        return response.data
    except Exception as e:
        print(f"讀取產品失敗: {e}")
        return []

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

# --- 新增功能：報價單存檔與編號 ---
from datetime import datetime

def generate_quote_no():
    if not supabase: return "OFFLINE-001"
    current_ym = datetime.now().strftime("%Y%m")
    prefix = f"QUO-{current_ym}-"
    try:
        response = supabase.table("quotations")\
            .select("quote_no")\
            .ilike("quote_no", f"{prefix}%")\
            .order("quote_no", desc=True)\
            .limit(1)\
            .execute()
        if response.data:
            last_no = response.data[0]['quote_no']
            seq = int(last_no.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}{seq:03d}"
    except:
        return f"{prefix}000"

def save_quotation(client_id, date, items, total_amount):
    if not supabase: return False, "資料庫未連線"
    new_quote_no = generate_quote_no()
    try:
        main_data = {
            "quote_no": new_quote_no,
            "client_id": client_id,
            "quote_date": str(date)
        }
        res_main = supabase.table("quotations").insert(main_data).execute()
        if not res_main.data: return False, "主表寫入失敗"
        
        quotation_id = res_main.data[0]['id']
        items_data = []
        for item in items:
            items_data.append({
                "quotation_id": quotation_id,
                "product_name": item['product'],
                "quantity": item['qty'],
                "unit_price": item['price'],
                "dealer_price_snapshot": 0 
            })
        supabase.table("quotation_items").insert(items_data).execute()
        return True, new_quote_no
    except Exception as e:
        return False, str(e)

# --- 歷史資料查詢 (進階版) ---
def search_product_history(product_keyword, offset=0, limit=10):
    if not supabase: return [], False
    try:
        response = supabase.table("quotation_items")\
            .select("*, quotations(quote_date, quote_no, clients(name))")\
            .ilike("product_name", f"%{product_keyword}%")\
            .order("id", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        data = response.data
        formatted_data = []
        for item in data:
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
        has_more = len(data) == limit
        return formatted_data, has_more
    except Exception as e:
        return [], False

# 取得歷史紀錄 (給彈出視窗用 - 簡易版兼容)
def fetch_history_items(client_name, product_name, offset=0, limit=5):
    # 這裡我們直接複用上面的搜尋邏輯，但參數稍微不同，為了保持相容性
    # 實際上您可以在 ui_components 改呼叫 search_product_history
    # 這裡保留舊函式介面以防報錯
    return search_product_history(product_name, offset, limit)

# --- 儀表板統計功能 ---
def get_dashboard_stats():
    if not supabase: return 0, 0
    try:
        res_count = supabase.table("quotations").select("id", count="exact").execute()
        total_quotes = res_count.count
        res_items = supabase.table("quotation_items").select("unit_price, quantity").execute()
        total_amount = sum([item['unit_price'] * item['quantity'] for item in res_items.data])
        return total_quotes, total_amount
    except:
        return 0, 0

# --- 批次匯入功能 ---

def batch_import_products(df):
    """
    將 Pandas DataFrame 批次寫入 products 表
    預期 Excel 欄位: ['品名', '規格', '價格']
    """
    if not supabase: return False, "資料庫未連線"
    
    try:
        # 1. 欄位對照 (Excel中文 -> 資料庫英文)
        # 為了容錯，我們允許使用者欄位名稱有一點點誤差
        rename_map = {
            "品名": "name", "產品名稱": "name", "產品": "name",
            "規格": "spec", "規格說明": "spec",
            "價格": "dealer_price", "單價": "dealer_price", "成本": "dealer_price", "經銷價": "dealer_price"
        }
        
        # 重新命名欄位
        df = df.rename(columns=rename_map)
        
        # 2. 檢查必要欄位是否存在
        required_cols = ["name", "dealer_price"]
        if not all(col in df.columns for col in required_cols):
            return False, f"Excel 缺少必要欄位，請確保有包含：{required_cols} (或對應的中文)"
            
        # 3. 補上選填欄位 (如果沒填規格，就補空字串)
        if "spec" not in df.columns:
            df["spec"] = ""
            
        # 4. 轉換資料格式 (Pandas 轉 List of Dicts)
        # 只取我們需要的欄位，避免寫入錯誤
        records = df[["name", "spec", "dealer_price"]].to_dict(orient="records")
        
        # 5. 寫入 Supabase
        supabase.table("products").insert(records).execute()
        
        return True, f"成功匯入 {len(records)} 筆產品！"
        
    except Exception as e:
        return False, str(e)