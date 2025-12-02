import streamlit as st
import pandas as pd
import time
from modules import calculator, database, pdf_gen, ui_components

# 設定頁面
st.set_page_config(page_title="贊翔實業 - 報價管理系統", layout="wide", page_icon="💼")

# --- 🔐 1. 門禁系統 (登入檢查) ---
def check_password():
    """Returns `True` if the user had the correct password."""
    
    # 如果已經登入成功，直接回傳 True
    if st.session_state.get("password_correct", False):
        return True

    # 顯示登入框
    st.header("🔒 請登入系統")
    password = st.text_input("請輸入授權密碼", type="password")
    
    if st.button("登入"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("密碼錯誤")
    return False

if not check_password():
    st.stop() # 如果沒登入，程式停在這裡，不顯示後面內容

# ==========================================
# 登入成功後，才會執行以下內容
# ==========================================

# 2. 載入側邊欄計算機
calculator.render_simple_calculator()

# 3. 側邊欄選單
st.sidebar.title("功能選單")
page = st.sidebar.radio("Go to", ["🏠 首頁概覽", "📝 新增報價單", "📊 歷史定價比較", "🗃️ 資料庫管理"])

# --- 頁面 0: 首頁概覽 (Dashboard) ---
if page == "🏠 首頁概覽":
    st.title("📊 營運儀表板")
    st.write("歡迎回到報價管理系統。")
    
    # 讀取統計數據
    with st.spinner("更新數據中..."):
        q_count, total_amt = database.get_dashboard_stats()
    
    # 顯示 3 個大指標
    col1, col2, col3 = st.columns(3)
    col1.metric("總報價單數", f"{q_count} 張", "+1")
    col2.metric("累積報價金額", f"${total_amt:,.0f}", delta_color="normal")
    col3.metric("系統狀態", "🟢 連線正常")
    
    st.divider()
    st.subheader("快速操作")
    c1, c2 = st.columns(2)
    if c1.button("📝 立即新增報價單", use_container_width=True):
        # 這裡單純提示，實際操作需點側邊欄 (Streamlit 限制)
        st.info("請點擊左側選單「新增報價單」")
        
    st.caption("系統版本 v1.0 | 開發者: AI 架構師")

# --- 頁面 1: 新增報價單 ---
elif page == "📝 新增報價單":
    st.title("📝 新增報價單")
    
    # 讀取資料庫
    clients_list = database.get_clients()
    raw_products = database.get_products()
    
    if raw_products:
        products_map = {item['name']: item['dealer_price'] for item in raw_products}
    else:
        products_map = {}

    if not products_map:
        st.warning("⚠️ 無產品資料，請先至「資料庫管理」新增。")
        st.stop()

    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
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

    st.divider()

    if "rows" not in st.session_state:
        st.session_state.rows = [{"product": list(products_map.keys())[0], "price": 0, "qty": 1}]

    h1, h2, h3, h4, h5, h6 = st.columns([0.5, 3, 2, 2, 1.5, 1])
    h2.text("產品名稱")
    h3.text("單價")
    h4.text("數量")

    for i, row in enumerate(st.session_state.rows):
        c1, c2, c3, c4, c5, c6 = st.columns([0.5, 3, 2, 2, 1.5, 1])
        
        with c2:
            # 產品選單防呆
            current_prod = row["product"]
            if current_prod not in products_map: current_prod = list(products_map.keys())[0]
            
            prod_name = st.selectbox(f"p_{i}", list(products_map.keys()), index=list(products_map.keys()).index(current_prod), key=f"p_{i}", label_visibility="collapsed")
            dealer_ref_price = products_map[prod_name]
            
        with c3:
            price = st.number_input(f"pr_{i}", value=float(row["price"]), key=f"price_input_{i}", label_visibility="collapsed")
            
        with c4:
            qty = st.number_input(f"qt_{i}", value=int(row["qty"]), key=f"qty_input_{i}", label_visibility="collapsed")

        # 警示邏輯
        if dealer_ref_price > 0 and price > 0:
            ratio = price / dealer_ref_price
            if ratio < 0.6:
                c1.markdown("### ⚠️")
                c1.caption(f"{ratio:.0%}")

        with c5:
            if st.button("📜 歷史", key=f"hist_{i}"):
                ui_components.show_history_modal(client_name, prod_name)

        with c6:
            if st.button("🗑️", key=f"del_{i}"):
                st.session_state.rows.pop(i)
                st.rerun()
        
        st.session_state.rows[i] = {"product": prod_name, "price": price, "qty": qty}

    if st.button("➕ 新增品項"):
        st.session_state.rows.append({"product": list(products_map.keys())[0], "price": 0, "qty": 1})
        st.rerun()

    st.divider()

    col_submit, col_status = st.columns([1, 4])
    with col_submit:
        submit_btn = st.button("💾 儲存並生成 PDF", type="primary", use_container_width=True)
    
    if submit_btn:
        if not client_name or len(st.session_state.rows) == 0:
            st.error("請檢查資料完整性")
            st.stop()

        with st.spinner("正在儲存..."):
            success, result_msg = database.save_quotation(
                client_id=client_id,
                date=quote_date,
                items=st.session_state.rows,
                total_amount=0 
            )
        
        if success:
            quote_no = result_msg
            st.success(f"✅ 成功！單號：{quote_no}")
            
            pdf_data = {
                "id": quote_no, 
                "date": str(quote_date),
                "client_name": client_name,
                "items": [
                    {"name": r["product"], "price": r["price"], "qty": r["qty"]} 
                    for r in st.session_state.rows
                ]
            }
            
            pdf_file = pdf_gen.create_quotation_pdf(pdf_data, show_stamp=show_stamp)
            
            st.download_button(
                label=f"📥 下載 PDF",
                data=pdf_file,
                file_name=f"{quote_no}_{client_name}.pdf",
                mime="application/pdf"
            )
        else:
            st.error(f"失敗: {result_msg}")

# --- 頁面 2: 歷史定價比較 ---
elif page == "📊 歷史定價比較":
    ui_components.render_price_analysis_page()

# --- 頁面 3: 資料庫管理 ---
elif page == "🗃️ 資料庫管理":
    st.title("🗃️ 資料庫管理")
    
    tab1, tab2 = st.tabs(["📦 產品管理", "👥 客戶管理"])
    
    with tab1:
        with st.form("add_product_form", clear_on_submit=True):
            col1, col2 = st.columns([3, 2])
            new_p_name = col1.text_input("產品型號/名稱")
            new_p_spec = col1.text_input("規格說明")
            new_p_price = col2.number_input("經銷牌價 (成本)", min_value=0, step=100)
            
            if st.form_submit_button("新增產品"):
                if new_p_name:
                    database.add_product(new_p_name, new_p_spec, new_p_price)
                    st.success("已新增")
                    st.rerun()
        
        st.dataframe(database.get_products(), use_container_width=True)

    with tab2:
        with st.form("add_client_form", clear_on_submit=True):
            c_name = st.text_input("公司名稱")
            c_tax = st.text_input("統一編號")
            c_contact = st.text_input("聯絡人")
            
            if st.form_submit_button("新增客戶"):
                if c_name:
                    database.add_client(c_name, c_tax, c_contact, "", "")
                    st.success("已新增")
                    st.rerun()
                    
        st.dataframe(database.get_clients(), use_container_width=True)