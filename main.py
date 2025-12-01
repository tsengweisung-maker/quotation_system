import streamlit as st
import pandas as pd
from modules import calculator, database, pdf_gen, ui_components

# 設定頁面
st.set_page_config(page_title="報價管理系統", layout="wide")

# 1. 載入側邊欄計算機
calculator.render_simple_calculator()

# 2. 側邊欄選單
page = st.sidebar.radio("功能", ["📝 新增報價單", "📊 歷史定價比較", "🗃️ 資料庫管理"])

# --- 頁面 1: 新增報價單 ---
if page == "📝 新增報價單":
    st.title("📝 新增報價單")
    
    # 讀取資料庫
    clients_list = database.get_clients() # 取得客戶清單
    products_map = database.get_products() # 取得產品與價格表
    
    # 上半部：客戶選擇與設定
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            # 建立選單：格式為 "ID: 公司名稱"
            client_options = [f"{c['id']}: {c['name']}" for c in clients_list]
            selected_client_str = st.selectbox("選擇客戶", client_options)
            # 解析出 client_id
            if selected_client_str:
                client_id = int(selected_client_str.split(":")[0])
                client_name = selected_client_str.split(":")[1].strip()
        
        with col2:
            quote_date = st.date_input("報價日期")
            
        with col3:
            show_stamp = st.checkbox("顯示公司大小章", value=True)
            st.caption("正式報價單請勾選")

    st.divider()

    # 中間：報價明細 (Grid Layout)
    if "rows" not in st.session_state:
        st.session_state.rows = [{"product": list(products_map.keys())[0], "price": 0, "qty": 1}]

    # 顯示表頭
    h1, h2, h3, h4, h5, h6 = st.columns([0.5, 3, 2, 2, 1.5, 1])
    h2.text("產品名稱")
    h3.text("單價")
    h4.text("數量")

    # 動態產生每一行
    for i, row in enumerate(st.session_state.rows):
        c1, c2, c3, c4, c5, c6 = st.columns([0.5, 3, 2, 2, 1.5, 1])
        
        with c2:
            # 產品選單
            prod_name = st.selectbox(f"產品 {i+1}", list(products_map.keys()), key=f"p_{i}", label_visibility="collapsed")
            # 取得該產品的建議售價 (Dealer Price)
            dealer_ref_price = products_map[prod_name]
            
        with c3:
            # 單價輸入
            price = st.number_input(f"price_{i}", value=row["price"], key=f"price_input_{i}", label_visibility="collapsed")
            
        with c4:
            # 數量輸入
            qty = st.number_input(f"qty_{i}", value=row["qty"], key=f"qty_input_{i}", label_visibility="collapsed")

        # 功能: 警示邏輯 (價差 > 40%)
        if dealer_ref_price > 0 and price > 0:
            ratio = price / dealer_ref_price
            if ratio < 0.6:
                c1.markdown("### ⚠️")
                c1.caption(f"{ratio:.0%}")

        # 功能: 查歷史按鈕
        with c5:
            if st.button("📜 歷史", key=f"hist_{i}"):
                ui_components.show_history_modal(client_name, prod_name)

        # 功能: 刪除按鈕
        with c6:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.rows.pop(i)
                st.rerun()
        
        # 更新 Session State
        st.session_state.rows[i] = {"product": prod_name, "price": price, "qty": qty}

    if st.button("➕ 新增品項"):
        st.session_state.rows.append({"product": list(products_map.keys())[0], "price": 0, "qty": 1})
        st.rerun()

    st.divider()

    # 底部：生成 PDF
    if st.button("🖨️ 生成 PDF 報價單", type="primary", use_container_width=True):
        # 準備要傳給 PDF 引擎的資料
        pdf_data = {
            "id": "2024-TEST-001", # 這裡之後可以寫自動編號邏輯
            "date": str(quote_date),
            "client_name": client_name,
            "items": [
                {"name": r["product"], "price": r["price"], "qty": r["qty"]} 
                for r in st.session_state.rows
            ]
        }
        
        # 呼叫 PDF 模組
        pdf_file = pdf_gen.create_quotation_pdf(pdf_data, show_stamp=show_stamp)
        
        st.download_button(
            label="📥 下載 PDF 檔案",
            data=pdf_file,
            file_name=f"Quotation_{client_name}.pdf",
            mime="application/pdf"
        )

# --- 頁面 2 & 3 (暫時留空，先跑通主流程) ---
elif page == "📊 歷史定價比較":
    ui_components.render_price_analysis_page()

elif page == "🗃️ 資料庫管理":
    st.info("資料庫管理功能開發中...")