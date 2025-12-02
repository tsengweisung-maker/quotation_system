import streamlit as st
import pandas as pd
import time
from modules import database

# --- 共用工具：顯示資料表格 ---
def display_history_table(data_list):
    if not data_list:
        st.info("查無資料")
        return

    df = pd.DataFrame(data_list)
    
    # 計算折數 (單價 / 經銷價)
    # 防呆：避免除以 0
    def calc_ratio(row):
        cost = row.get('經銷價', 0)
        price = row.get('單價', 0)
        if cost and cost > 0:
            return f"{price / cost:.2%}"
        return "N/A"

    df['折數'] = df.apply(calc_ratio, axis=1)
    
    # 調整欄位順序
    cols = ['日期', '客戶', '產品', '數量', '單價', '折數', '單號']
    # 只顯示存在的欄位
    display_cols = [c for c in cols if c in df.columns]
    
    st.dataframe(
        df[display_cols], 
        use_container_width=True,
        hide_index=True,
        column_config={
            "單價": st.column_config.NumberColumn(format="$%d"),
            "日期": st.column_config.DateColumn(format="YYYY-MM-DD"),
        }
    )

# --- 功能 1: 彈出視窗 (給報價單頁面用) ---
@st.dialog("📜 歷史報價查詢")
def show_history_modal(client_name, product_name):
    st.subheader(f"產品：{product_name}")
    st.caption(f"查詢客戶：{client_name}")
    
    # 初始化 Session (只存在於這個視窗開啟期間)
    if "modal_data" not in st.session_state:
        st.session_state.modal_data = []
        st.session_state.modal_offset = 0
        st.session_state.modal_has_more = True
        st.session_state.modal_first_load = True

    # 載入資料邏輯
    def load_data():
        bar = st.progress(0, text="正在連線資料庫...")
        time.sleep(0.1) # 讓使用者有感
        
        # 呼叫資料庫 (我們用搜尋功能，但關鍵字鎖定產品名)
        # 這裡為了簡單，我們搜尋所有客戶買過這個產品的紀錄，讓您參考價格
        new_data, has_more = database.search_product_history(
            product_name, 
            offset=st.session_state.modal_offset, 
            limit=5 # 彈出視窗一次載入 5 筆
        )
        
        bar.progress(80, text="整理數據中...")
        st.session_state.modal_data.extend(new_data)
        st.session_state.modal_offset += 5
        st.session_state.modal_has_more = has_more
        
        bar.progress(100, text="完成！")
        time.sleep(0.2)
        bar.empty()
        st.session_state.modal_first_load = False

    # 自動觸發第一次載入
    if st.session_state.modal_first_load:
        load_data()
        st.rerun()

    # 顯示內容
    display_history_table(st.session_state.modal_data)

    # 載入更多按鈕
    if st.session_state.modal_has_more:
        if st.button("🔽 載入更多 (5筆)", key="btn_modal_more", use_container_width=True):
            load_data()
            st.rerun()
    elif st.session_state.modal_data:
        st.caption("✅ 已顯示所有資料")

# --- 功能 2: 歷史定價比較 (獨立頁面用) ---
def render_price_analysis_page():
    st.title("📊 歷史定價分析")
    
    # 搜尋區
    col1, col2 = st.columns([4, 1])
    with col1:
        keyword = st.text_input("輸入產品名稱關鍵字", placeholder="例如: FX3U", key="search_kw")
    with col2:
        st.write("")
        st.write("")
        do_search = st.button("🔍 搜尋", type="primary", use_container_width=True)

    st.divider()

    # 初始化 Session State (用於分頁記憶)
    if "analysis_data" not in st.session_state:
        st.session_state.analysis_data = []
        st.session_state.analysis_offset = 0
        st.session_state.analysis_has_more = False
        st.session_state.last_keyword = ""

    # 觸發搜尋 (重置狀態)
    if do_search:
        st.session_state.analysis_data = []
        st.session_state.analysis_offset = 0
        st.session_state.analysis_has_more = True
        st.session_state.last_keyword = keyword
        
        # 執行第一次載入
        with st.spinner("🔍 搜尋中..."):
            new_data, has_more = database.search_product_history(keyword, offset=0, limit=10)
            st.session_state.analysis_data = new_data
            st.session_state.analysis_offset = 10
            st.session_state.analysis_has_more = has_more

    # 顯示結果
    if st.session_state.analysis_data:
        st.subheader(f"🔎 '{st.session_state.last_keyword}' 的報價紀錄")
        display_history_table(st.session_state.analysis_data)
        
        # 載入更多按鈕
        if st.session_state.analysis_has_more:
            if st.button("🔽 載入更多 (10筆)", key="btn_page_more", use_container_width=True):
                # 顯示進度條效果
                bar = st.progress(0, text="載入更多資料...")
                time.sleep(0.2)
                
                new_data, has_more = database.search_product_history(
                    st.session_state.last_keyword, 
                    offset=st.session_state.analysis_offset, 
                    limit=10
                )
                
                bar.progress(100)
                st.session_state.analysis_data.extend(new_data)
                st.session_state.analysis_offset += 10
                st.session_state.analysis_has_more = has_more
                bar.empty()
                st.rerun()
        else:
            st.caption("✅ 已達最後一筆")
    
    elif do_search: # 有按搜尋但沒資料
        st.warning("查無相關資料")