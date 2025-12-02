import streamlit as st
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
import pandas as pd
from datetime import datetime

# --- 初始化連線 ---
@st.cache_resource
def init_connection():
    try:
        # 1. 檢查 secrets 是否存在
        if "SUPABASE_URL" not in st.secrets:
            st.error("❌ 系統讀取不到 SUPABASE_URL！請確認 secrets.toml 設定正確。")
            return None
            
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        
        # 2. 設定連線逾時 (60秒)，解決免費版休眠問題
        options = ClientOptions(postgrest_client_timeout=60)
        
        return create_client(url, key, options=options)
    except Exception as e:
        st.error(f"🔥 資料庫連線初始化失敗: {str(e)}")
        return None

supabase: Client = init_connection()

# --- 讀取功能 (Read) ---

def get_clients():
    if not supabase: return []
    try:
        response = supabase.table("clients").select("*").order("id").execute()
        return response.data
    except Exception as e:
        print(f"讀取客戶失敗: {e}")
        return []

def get_products():
    if not supabase: return []
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
        return False

# --- 批次匯入功能 (Excel) ---
def batch_import_products(df):
    """
    將 Pandas DataFrame 批次寫入 products 表
    支援格式: [NO., 型號, 牌價, 經銷價, 規格, 訂購品(V)]
    """
    if not supabase: return False, "資料庫未連線"
    
    try:
        # 0. 清理欄位名稱
        df.columns = [str(c).strip() for c in df.columns]

        # 1. 智慧欄位對照
        if '型號' in df.columns: df = df.rename(columns={'型號': 'name'})
        elif '品名' in df.columns: df = df.rename(columns={'品名': 'name'})
        
        if '規格' in df.columns: df = df.rename(columns={'規格': 'spec'})
        
        if '牌價' in df.columns: df = df.rename(columns={'牌價': 'dealer_price'})
        elif '經銷價' in df.columns: df = df.rename(columns={'經銷價': 'dealer_price'})
        elif '單價' in df.columns: df = df.rename(columns={'單價': 'dealer_price'})

        # 2. 檢查必要欄位
        required_cols = ["name", "dealer_price"]
        if not all(col in df.columns for col in required_cols):
            return False, "Excel 缺少必要欄位 (需包含: 型號/品名, 牌價/經銷價)"
            
        # 3. 補上選填欄位
        if "spec" not in df.columns: df["spec"] = ""
            
        # 4. 資料清理 (處理 NaN 空值)
        df['name'] = df['name'].astype(str)
        df['spec'] = df['spec'].fillna("").astype(str)
        df['dealer_price'] = pd.to_numeric(df['dealer_price'], errors='coerce').fillna(0)

        # 5. 轉換並寫入
        records = df[["name", "spec", "dealer_price"]].to_dict(orient="records")
        supabase.table("products").insert(records).execute()
        
        return True, f"成功匯入 {len(records)} 筆產品！"
        
    except Exception as e:
        return False, f"匯入錯誤: {str(e)}"

# --- 報價單存檔與編號 ---
def generate_quote_no():
    if not supabase: return "OFFLINE-001"
    current_ym = datetime.now().strftime("%Y%m")
    prefix = f"QUO-{current_ym}-"
    try:
        response = supabase.table("quotations").select("quote_no").ilike("quote_no", f"{prefix}%").order("quote_no", desc=True).limit(1).execute()
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
        # 1. 寫入主表
        main_data = {"quote_no": new_quote_no, "client_id": client_id, "quote_date": str(date)}
        res_main = supabase.table("quotations").insert(main_data).execute()
        if not res_main.data: return False, "主表寫入失敗"
        
        quotation_id = res_main.data[0]['id']
        
        # 2. 寫入明細表
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

# --- 歷史查詢 ---
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
        # st.error(f"查詢錯誤: {e}")
        return [], False

def fetch_history_items(client_name, product_name, offset=0, limit=5):
    # 簡易版歷史查詢 (給 Modal 用)
    return search_product_history(product_name, offset, limit)

# --- 儀表板統計 ---
def get_dashboard_stats():
    if not supabase: return 0, 0
    try:
        res_count = supabase.table("quotations").select("id", count="exact").execute()
        total_quotes = res_count.count
        
        # 簡易計算總金額 (僅供 MVP 使用)
        res_items = supabase.table("quotation_items").select("unit_price, quantity").execute()
        total_amount = sum([item['unit_price'] * item['quantity'] for item in res_items.data])
        
        return total_quotes, total_amount
    except:
        return 0, 0