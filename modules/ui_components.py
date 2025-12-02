import streamlit as st
import pandas as pd
import time
from modules import database

def display_history_table(data_list):
    if not data_list:
        st.info("查無資料")
        return

    df = pd.DataFrame(data_list)
    
    # 計算折數
    def calc_ratio(row):
        cost = row.get('經銷價', 0)
        price = row.get('單價', 0)
        if cost and cost > 0:
            return f"{price / cost:.2%}"
        return "N/A"

    df['折數'] = df.apply(calc_ratio, axis=1)
    
    cols = ['日期', '客戶', '產品', '數量', '單價', '折數', '單號']
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

# --- 彈出視窗 (Modal) ---
@st.dialog("📜 歷史報價查詢")
def show_history_modal(client_name, product_name):
    st.subheader(f"產品：{product_name}")
    st.caption(f"查詢客戶：{client_name}")
    
    if "modal_data" not in st.session_state:
        st.session_state.modal_data = []
        st.session_state.modal_offset = 0
        st.session_state.modal_has_more = True
        st.session_state.modal_first_load = True

    def load_data():
        bar = st.progress(0, text="正在連線資料庫...")
        time.sleep(0.1) 
        
        new_data, has_more = database.search_product_history(
            product_name, 
            offset=st.session_state.modal_offset, 
            limit=5 
        )
        
        bar.progress(80, text="整理數據中...")
        st.session_state.modal_data.extend(new_data)
        st.session_state.modal_offset += 5
        st.session_state.modal_has_more = has_more
        
        bar.progress(100, text="完成！")
        time.sleep(0.2)
        bar.empty()
        st.session_state.modal_first_load = False

    if st.session_state.modal_first_load:
        load_data()
        st.rerun()

    display_history_table(st.session_state.modal_data)

    if st.session_state.modal_has_more:
        if st.button("🔽 載入更多 (5筆)", key="btn_modal_more", use_container_width=True):
            load_data()
            st.rerun()
    elif st.session_state.modal_data:
        st.caption("✅ 已顯示所有資料")

# --- 歷史定價比較 (獨立頁面) ---
def render_price_analysis_page():
    st.title("📊 歷史定價分析")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        keyword = st.text_input("輸入產品名稱關鍵字", placeholder="例如: FX3U", key="search_kw")
    with col2:
        st.write("")
        st.write("")
        do_search = st.button("🔍 搜尋", type="primary", use_container_width=True)

    st.divider()

    if "analysis_data" not in st.session_state:
        st.session_state.analysis_data = []
        st.session_state.analysis_offset = 0
        st.session_state.analysis_has_more = False
        st.session_state.last_keyword = ""

    if do_search:
        st.session_state.analysis_data = []
        st.session_state.analysis_offset = 0
        st.session_state.analysis_has_more = True
        st.session_state.last_keyword = keyword
        
        with st.spinner("🔍 搜尋中..."):
            new_data, has_more = database.search_product_history(keyword, offset=0, limit=10)
            st.session_state.analysis_data = new_data
            st.session_state.analysis_offset = 10
            st.session_state.analysis_has_more = has_more

    if st.session_state.analysis_data:
        st.subheader(f"🔎 '{st.session_state.last_keyword}' 的報價紀錄")
        display_history_table(st.session_state.analysis_data)
        
        if st.session_state.analysis_has_more:
            if st.button("🔽 載入更多 (10筆)", key="btn_page_more", use_container_width=True):
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
    
    elif do_search: 
        st.warning("查無相關資料")