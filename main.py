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
    raw_products = database.get_products() # 取得產品原始資料 (List)
    
    # 【關鍵修正】將原始資料轉換為報價單需要的字典格式 {產品名: 價格}
    if raw_products:
        products_map = {item['name']: item['dealer_price'] for item in raw_products}
    else:
        products_map = {}

    # 【防呆機制】如果資料庫完全沒產品，顯示提示並停止執行，避免當機
    if not products_map:
        st.warning("⚠️ 目前資料庫中沒有產品資料！請先前往左側「🗃️ 資料庫管理」新增產品。")
        st.stop() # 停止往下執行

    # 上半部：客戶選擇與設定
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            # 建立選單：格式為 "ID: 公司名稱"
            if clients_list:
                client_options = [f"{c['id']}: {c['name']}" for c in clients_list]
                selected_client_str = st.selectbox("選擇客戶", client_options)
                if selected_client_str:
                    client_id = int(selected_client_str.split(":")[0])
                    client_name = selected_client_str.split(":")[1].strip()
            else:
                st.warning("請先新增客戶資料")
                st.stop()
        
        with col2:
            quote_date = st.date_input("報價日期")
            
        with col3:
            show_stamp = st.checkbox("顯示公司大小章", value=True)
            st.caption("正式報價單請勾選")

    st.divider()

    # 中間：報價明細 (Grid Layout)
    if "rows" not in st.session_state:
        # 這裡現在安全了，因為前面有檢查 products_map 是否為空
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
            # 產品選單 (確保預設值存在於清單中)
            current_prod = row["product"]
            if current_prod not in products_map:
                current_prod = list(products_map.keys())[0]
                
            prod_name = st.selectbox(f"產品 {i+1}", list(products_map.keys()), index=list(products_map.keys()).index(current_prod), key=f"p_{i}", label_visibility="collapsed")
            # 取得該產品的建議售價
            dealer_ref_price = products_map[prod_name]
            
        with c3:
            price = st.number_input(f"price_{i}", value=float(row["price"]), key=f"price_input_{i}", label_visibility="collapsed")
            
        with c4:
            qty = st.number_input(f"qty_{i}", value=int(row["qty"]), key=f"qty_input_{i}", label_visibility="collapsed")

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
        pdf_data = {
            "id": "2024-TEST-001", 
            "date": str(quote_date),
            "client_name": client_name,
            "items": [
                {"name": r["product"], "price": r["price"], "qty": r["qty"]} 
                for r in st.session_state.rows
            ]
        }
        
        pdf_file = pdf_gen.create_quotation_pdf(pdf_data, show_stamp=show_stamp)
        
        st.download_button(
            label="📥 下載 PDF 檔案",
            data=pdf_file,
            file_name=f"Quotation_{client_name}.pdf",
            mime="application/pdf"
        )

# --- 頁面 2 & 3 ---
elif page == "📊 歷史定價比較":
    ui_components.render_price_analysis_page()

elif page == "🗃️ 資料庫管理":
    st.title("🗃️ 資料庫管理")
    
    tab1, tab2 = st.tabs(["📦 產品管理", "👥 客戶管理"])
    
    # --- 產品管理頁籤 ---
    with tab1:
        st.subheader("新增產品")
        with st.form("add_product_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 2])
            new_p_name = col1.text_input("產品型號/名稱")
            new_p_spec = col1.text_input("規格說明")
            new_p_price = col2.number_input("經銷牌價 (成本)", min_value=0, step=100)
            
            if st.form_submit_button("新增產品"):
                if new_p_name and new_p_price >= 0:
                    if database.add_product(new_p_name, new_p_spec, new_p_price):
                        st.success(f"產品 {new_p_name} 已新增！")
                        st.rerun()
                    else:
                        st.error("新增失敗，請檢查網路")
                else:
                    st.warning("請輸入產品名稱")
        
        st.divider()
        st.subheader("現有產品列表")
        current_products = database.get_products()
        if current_products:
            st.dataframe(current_products, use_container_width=True)

    # --- 客戶管理頁籤 ---
    with tab2:
        st.subheader("新增客戶")
        with st.form("add_client_form", clear_on_submit=True):
            c_name = st.text_input("公司名稱 (必填)")
            col1, col2 = st.columns(2)
            c_tax = col1.text_input("統一編號")
            c_contact = col2.text_input("聯絡人")
            c_phone = col1.text_input("電話")
            c_addr = st.text_input("地址")
            
            if st.form_submit_button("新增客戶"):
                if c_name:
                    if database.add_client(c_name, c_tax, c_contact, c_phone, c_addr):
                        st.success(f"客戶 {c_name} 已新增！")
                        st.rerun()
                else:
                    st.warning("請輸入公司名稱")
                    
        st.divider()
        st.subheader("現有客戶列表")
        current_clients = database.get_clients()
        if current_clients:
            st.dataframe(current_clients, use_container_width=True)