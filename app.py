import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="窗簾店雲端專業版", layout="wide")

# 管理密碼
ADMIN_PASSWORD = "8888" 

# 建立雲端連線 (會自動抓取 Secrets 裡的 Service Account 資訊)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 讀取 Google Sheets 最新資料
    df = conn.read(ttl="0s")
    if df.empty:
        return pd.DataFrame(columns=["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工日期", "施工師傅", "狀態"])
    return df

df = load_data()

# 確保資料格式正確
df['總金額'] = pd.to_numeric(df['總金額'], errors='coerce').fillna(0)
df['已收金額'] = pd.to_numeric(df['已收金額'], errors='coerce').fillna(0)
df['師傅工資'] = pd.to_numeric(df['師傅工資'], errors='coerce').fillna(0)

# --- 側邊欄選單 ---
st.sidebar.title("功能選單")
menu = ["➕ 新增訂單", "🏗️ 施工進度管理", "🛠️ 修改/刪除訂單", "💰 財務報表與尾款追蹤"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能實作 (以新增訂單為例) ---
if choice == "➕ 新增訂單":
    st.header("📝 雲端新增訂單")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            c_id = st.text_input("訂單編號", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
            c_date = st.date_input("訂單日期", datetime.now())
            c_name = st.text_input("客戶姓名")
        with col2:
            c_total = st.number_input("總金額", min_value=0)
            c_paid = st.number_input("已收金額", min_value=0)
            c_wage = st.number_input("師傅工資", min_value=0)
        
        if st.form_submit_button("✅ 儲存到雲端"):
            new_row = pd.DataFrame([{
                "訂單編號": c_id, "訂單日期": str(c_date), "客戶姓名": c_name,
                "總金額": c_total, "已收金額": c_paid, "師傅工資": c_wage, "狀態": "已接單"
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            # 使用 Service Account 權限進行更新
            conn.update(data=updated_df)
            st.success("資料已永久存入 Google Sheets！")
            st.rerun()
