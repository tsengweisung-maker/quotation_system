import streamlit as st

def render_simple_calculator():
    # --- 1. 初始化 Session State ---
    if 'calc_current' not in st.session_state: st.session_state.calc_current = "0"  # 當前輸入 (大字)
    if 'calc_expression' not in st.session_state: st.session_state.calc_expression = "" # 運算過程 (小字)
    if 'calc_history' not in st.session_state: st.session_state.calc_history = []   # 歷史紀錄
    if 'new_entry' not in st.session_state: st.session_state.new_entry = True       # 是否準備輸入新數字

    # --- 2. 邏輯處理函數 ---
    def on_click(key):
        curr = st.session_state.calc_current
        
        # 數字鍵
        if key in "0123456789":
            if st.session_state.new_entry or curr == "0":
                st.session_state.calc_current = key
                st.session_state.new_entry = False
            else:
                st.session_state.calc_current += key
        
        # 小數點
        elif key == ".":
            if "." not in curr:
                st.session_state.calc_current += "."
                st.session_state.new_entry = False
        
        # 正負號切換 (+/-)
        elif key == "±":
            if curr != "0":
                if curr.startswith("-"):
                    st.session_state.calc_current = curr[1:]
                else:
                    st.session_state.calc_current = "-" + curr

        # 基礎運算 (+ - * /)
        elif key in ["+", "-", "×", "÷"]:
            st.session_state.calc_expression = f"{curr} {key}"
            st.session_state.new_entry = True
        
        # 百分比 (%)
        elif key == "%":
            try:
                val = float(curr)
                st.session_state.calc_current = f"{val / 100:g}"
            except: pass

        # 等於 (=) - 核心計算邏輯
        elif key == "=":
            if st.session_state.calc_expression:
                try:
                    # 將 × ÷ 換回 Python 的 * /
                    expr_str = st.session_state.calc_expression + " " + curr
                    eval_str = expr_str.replace("×", "*").replace("÷", "/")
                    
                    result = eval(eval_str)
                    
                    # 處理結果顯示
                    res_str = f"{result:g}" 
                    
                    # 寫入歷史紀錄
                    st.session_state.calc_history.insert(0, f"{expr_str} = {res_str}")
                    
                    # 更新顯示
                    st.session_state.calc_current = res_str
                    st.session_state.calc_expression = ""
                    st.session_state.new_entry = True
                except:
                    st.session_state.calc_current = "Error"
                    st.session_state.new_entry = True

        # --- 清除鍵 ---
        elif key == "C":
            st.session_state.calc_current = "0"
            st.session_state.calc_expression = ""
            st.session_state.new_entry = True
        
        elif key == "⌫": # Backspace
            if len(curr) > 1:
                st.session_state.calc_current = curr[:-1]
            else:
                st.session_state.calc_current = "0"
                st.session_state.new_entry = True

        # --- 歷史清除 ---
        elif key == "clear_history":
            st.session_state.calc_history = []

    # --- 3. UI 佈局 (簡化版 - 側邊欄專用) ---
    
    with st.sidebar:
        st.markdown("### 🧮 快速計算")

        # A. 鍵盤速算輸入
        kb_input = st.text_input("⌨️ 鍵盤輸入 (Enter)", key="kb_simple_input", placeholder="如: 500*0.8")
        if kb_input:
            try:
                allowed = set("0123456789.+-*/ ")
                if set(kb_input).issubset(allowed):
                    res = str(eval(kb_input))
                    st.success(f"= {res}")
                    st.session_state.calc_history.insert(0, f"{kb_input} = {res}")
                else:
                    st.error("格式錯誤")
            except: pass

        st.divider()
        
        # B. 顯示幕區
        st.markdown(f"<div style='text-align: right; color: gray; font-size: 12px; min-height: 20px;'>{st.session_state.calc_expression}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align: right; font-size: 24px; font-weight: bold; margin-bottom: 10px; background-color: #f0f2f6; padding: 5px; border-radius: 5px;'>{st.session_state.calc_current}</div>", unsafe_allow_html=True)

        # C. 按鈕矩陣
        buttons_grid = [
            ["C", "⌫", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "-"],
            ["1", "2", "3", "+"],
            ["±", "0", ".", "="]
        ]

        for row in buttons_grid:
            cols = st.columns(4)
            for i, btn_label in enumerate(row):
                btn_type = "primary" if btn_label in ["=", "+", "-", "×", "÷"] else "secondary"
                if cols[i].button(btn_label, key=f"s_btn_{btn_label}", type=btn_type, use_container_width=True):
                    on_click(btn_label)
                    st.rerun()

        # D. 歷史紀錄
        st.caption("📜 紀錄")
        if not st.session_state.calc_history:
            st.text("...")
        else:
            with st.container(height=150):
                for item in st.session_state.calc_history:
                    st.text(item)
            
            if st.button("清空紀錄", key="del_simple_hist", use_container_width=True):
                on_click("clear_history")
                st.rerun()