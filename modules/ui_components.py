import streamlit as st
import pandas as pd
import time
from modules import database

# --- 1. 彈出視窗 (Modal) ---
@st.dialog("歷史報價查詢")
def show_history_modal(client_name, product_name):
    st.subheader(f"客戶：{client_name}")
    st.text(f"產品：{product_name}")
    
    # 初始化 Session State (用於分頁)
    if "hist_data" not in st.session_state:
        st.session_state.hist_data = []
    if "hist_offset" not in st.session_state:
        st.session_state.hist_offset = 0
    if "hist_has_more" not in st.session_state:
        st.session_state.hist_has_more = True

    # 顯示進度條
    progress_bar = st.progress(0)
    
    # 載入資料邏輯
    def load_more_data():
        progress_bar.progress(30)
        
        # 呼叫資料庫 (每次抓5筆)
        new_data, has_more = database.fetch_history_items(
            client_name, 
            product_name, 
            offset=st.session_state.hist_offset, 
            limit=5
        )
        
        # 為了演示，如果資料庫沒資料，我們產生一些假資料讓您看效果
        # (正式上線後請刪除這段假資料邏輯)
        if not new_data and st.session_state.hist_offset == 0:
            new_data = [
                {"quote_date": "2023-12-01", "unit_price": 5000, "dealer_price_snapshot": 10000},
                {"quote_date": "2023-11-15", "unit_price": 5200, "dealer_price_snapshot": 10000},
                {"quote_date": "2023-10-20", "unit_price": 5500, "dealer_price_snapshot": 10000},
            ]
            has_more = False

        st.session_state.hist_data.extend(new_data)
        st.session_state.hist_offset += 5
        st.session_state.hist_has_more = has_more
        
        progress_bar.progress(100)
        time.sleep(0.2)
        progress_bar.empty()

    # 第一次打開自動載入
    if len(st.session_state.hist_data) == 0:
        load_more_data()

    # 顯示表格
    if st.session_state.hist_data:
        df = pd.DataFrame(st.session_state.hist_data)
        
        # 確保有這些欄位 (防止資料庫回傳缺漏)
        if 'dealer_price_snapshot' not in df.columns: df['dealer_price_snapshot'] = 1
        if 'unit_price' not in df.columns: df['unit_price'] = 0
        if 'quote_date' not in df.columns: df['quote_date'] = 'N/A'

        # 計算折數
        df['折數'] = df.apply(lambda x: f"{x['unit_price']/(x['dealer_price_snapshot'] if x['dealer_price_snapshot'] else 1):.2%}", axis=1)
        
        # 整理顯示欄位
        display_df = df[['quote_date', 'unit_price', '折數']].rename(
            columns={'quote_date': '日期', 'unit_price': '金額'}
        )
        st.table(display_df)
    else:
        st.info("查無歷史資料")

    # 載入更多按鈕
    if st.session_state.hist_has_more:
        if st.button("📥 載入更多 (下5筆)"):
            load_more_data()
            st.rerun()
    elif st.session_state.hist_data:
        st.caption("✅ 已達最後一筆")

# --- 2. 歷史定價比較頁面 (獨立頁面) ---
def render_price_analysis_page():
    st.title("📊 歷史定價比較")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        search_term = st.text_input("輸入產品名稱搜尋", placeholder="例如: FX3U")
    with col2:
        st.write("") # 排版
        st.write("")
        do_search = st.button("🔍 搜尋", use_container_width=True)
    
    # 這裡可以實作跟上方類似的分頁邏輯
    # 為了簡化，目前先顯示靜態訊息，等到資料庫有資料後再串接
    if do_search or search_term:
        st.info(f"正在搜尋：{search_term} ... (資料庫串接中)")
        # 未來在這裡呼叫 database.fetch_history_items 並顯示大表格