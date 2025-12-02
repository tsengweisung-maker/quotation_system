import streamlit as st
import pandas as pd
import time
from modules import calculator, database, pdf_gen, ui_components

# 設定頁面
st.set_page_config(page_title="報價管理系統", layout="wide", page_icon="💼")

# --- 🔐 1. 門禁系統 ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    
    st.header("🔒 請登入系統")
    password = st.text_input("請輸入授權密碼", type="password")
    
    # 預設密碼 1234
    correct_password = st.secrets.get("APP_PASSWORD", "1234")
    
    if st.button("登入"):
        if password == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("密碼錯誤")
    return False

if not check_password():
    st.stop()

# ==========================================
# 主程式 (登入後)
# ==========================================

calculator.render_simple_calculator()

st.sidebar.title("功能選單")
page = st.sidebar.radio("Go to", ["🏠 首頁概覽", "📝 新增報價單", "📊 歷史定價比較", "🗃️ 資料庫管理"])

# --- 頁面 0: 首頁概覽 ---
if page == "🏠 首頁概覽":
    st.title("📊 營運儀表板")
    st.write("歡迎使用報價管理系統。")
    with st.spinner("更新數據中..."):
        q_count, total_amt = database.get_dashboard_stats()
    col1, col2 = st.columns(2)
    col1.metric("總報價單數", f"{q_count} 張")
    col2.metric("累積報價金額", f"${total_amt:,.0f}")

# --- 頁面 1: 新增報價單 ---
elif page == "📝 新增報價單":
    st.title("📝 新增報價單")
    
    clients_list = database.get_clients()
    raw_products = database.get_products()
    
    if raw_products:
        products_map = {item['name']: item['dealer_price'] for item in raw_products}
    else:
        products_map = {}

    if not products_map:
        st.warning("⚠️ 目前資料庫中沒有產品資料！請先前往左側「🗃️ 資料庫管理」新增產品。")
        products_map = {"(無產品)": 0}
    
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
                client_name = ""
        
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
            current_prod = row["product"]
            if current_prod not in products_map: current_prod = list(products_map.keys())[0]
            prod_name = st.selectbox(f"p_{i}", list(products_map.keys()), index=list(products_map.keys()).index(current_prod), key=f"p_{i}", label_visibility="collapsed")
            dealer_ref_price = products_map[prod_name]
            
        with c3:
            price = st.number_input(f"pr_{i}", value=float(row["price"]), key=f"price_input_{i}", label_visibility="collapsed")
        with c4:
            qty = st.number_input(f"qt_{i}", value=int(row["qty"]), key=f"qty_input_{i}", label_visibility="collapsed")

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

    if st.button("💾 儲存並生成 PDF", type="primary", use_container_width=True):
        if not client_name or "(無產品)" in [r['product'] for r in st.session_state.rows]:
            st.error("資料不完整，無法存檔")
            st.stop()

        with st.spinner("儲存中..."):
            success, result_msg = database.save_quotation(client_id, quote_date, st.session_state.rows, 0)
        
        if success:
            st.success(f"✅ 單號：{result_msg}")
            pdf_data = {"id": result_msg, "date": str(quote_date), "client_name": client_name, "items": [{"name": r["product"], "price": r["price"], "qty": r["qty"]} for r in st.session_state.rows]}
            pdf_file = pdf_gen.create_quotation_pdf(pdf_data, show_stamp=show_stamp)
            st.download_button(label="📥 下載 PDF", data=pdf_file, file_name=f"{result_msg}.pdf", mime="application/pdf")
        else:
            st.error(f"存檔失敗: {result_msg}")

# --- 頁面 2: 歷史定價 ---
elif page == "📊 歷史定價比較":
    ui_components.render_price_analysis_page()

# --- 頁面 3: 資料庫管理 ---
elif page == "🗃️ 資料庫管理":
    st.title("🗃️ 資料庫管理")
    tab1, tab2 = st.tabs(["📦 產品管理", "👥 客戶管理"])
    
    with tab1:
        st.subheader("批次匯入 (Excel)")
        st.info("支援欄位：NO, 型號, 牌價, 經銷價, 規格")
        uploaded_file = st.file_uploader("上傳 Excel", type=["xlsx", "csv"])
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'): 
                    df = pd.read_csv(uploaded_file)
                else: 
                    df = pd.read_excel(uploaded_file)
                
                st.write("預覽 (前5筆):")
                preview_df = df.head().copy()
                cols_hide = [c for c in preview_df.columns if "NO" in str(c).upper() or "訂購" in str(c)]
                st.dataframe(preview_df.drop(columns=cols_hide, errors='ignore'))
                
                if st.button("🚀 確認匯入"):
                    with st.spinner("寫入中..."):
                        success, msg = database.batch_import_products(df)
                        if success: 
                            st.success(msg)
                            time.sleep(2)
                            st.rerun()
                        else: 
                            st.error(msg)
            except Exception as e:
                st.error(f"讀取錯誤: {e}")

                st.subheader("手動新增")
        with st.form("add_prod"):
            c1, c2 = st.columns([3, 2])
            nm = c1.text_input("產品名稱")
            sp = c1.text_input("規格")
            pr = c2.number_input("價格", step=100)
            
            if st.form_submit_button("新增"):
                if nm: 
                    # 先檢查資料庫物件是否存在
                    if not database.supabase:
                        st.error("❌ 無法寫入：資料庫未連線。請嘗試重啟程式 (Kill Terminal) 以讀取 secrets.toml。")
                    elif database.add_product(nm, sp, pr):
                        st.success("✅ 已新增！")
                        time.sleep(1) 
                        st.rerun()
                    else:
                        st.error("新增失敗，請檢查上方錯誤訊息 (通常是 RLS 鎖定)")
                else:
                    st.warning("請輸入產品名稱")
        
        st.subheader("現有產品")
        st.dataframe(database.get_products(), use_container_width=True)

    with tab2:
        with st.form("add_cli"):
            nm = st.text_input("公司名稱")
            tax = st.text_input("統一編號")
            cont = st.text_input("聯絡人")
            if st.form_submit_button("新增"):
                if nm: database.add_client(nm, tax, cont, "", ""); st.success("已新增"); st.rerun()
        st.subheader("現有客戶")
        st.dataframe(database.get_clients(), use_container_width=True)