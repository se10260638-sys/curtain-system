import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- 網頁基本設定 ---
st.set_page_config(page_title="窗簾店管理系統 (穩定本機版)", layout="wide")

# --- 管理密碼設定 ---
ADMIN_PASSWORD = "8888" 

# --- 1. 資料庫初始化 (使用 CSV 確保資料不丟失) ---
DB_FILE = "orders_db.csv"

def load_data():
    if not os.path.exists(DB_FILE):
        # 建立初始欄位
        df_init = pd.DataFrame(columns=[
            "訂單編號", "訂單日期", "客戶姓名", "電話", "地址", 
            "訂購內容", "總金額", "已收金額", "師傅工資", "施工日期", "施工師傅", "狀態"
        ])
        df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')
    
    df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
    # 格式轉換，確保計算與日期顯示正常
    df['訂單日期'] = pd.to_datetime(df['訂單日期']).dt.date.astype(str)
    df['總金額'] = pd.to_numeric(df['總金額'], errors='coerce').fillna(0)
    df['已收金額'] = pd.to_numeric(df['已收金額'], errors='coerce').fillna(0)
    df['師傅工資'] = pd.to_numeric(df['師傅工資'], errors='coerce').fillna(0)
    return df

def save_data(df):
    # 儲存到電腦硬碟中的 CSV 檔案
    df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# 載入資料
df = load_data()

# 建立用於篩選的臨時資料表
df_temp = df.copy()
df_temp['dt'] = pd.to_datetime(df_temp['訂單日期'])
df_temp['年份'] = df_temp['dt'].dt.year.astype(str)
df_temp['月份'] = df_temp['dt'].dt.month.astype(str)
df_temp['待收尾款'] = df_temp['總金額'] - df_temp['已收金額']

# --- 側邊欄：月份分類篩選 ---
st.sidebar.title("📅 月份篩選")
year_list = sorted(df_temp['年份'].unique(), reverse=True)
if not year_list or 'nan' in year_list: year_list = [str(datetime.now().year)]
selected_year = st.sidebar.selectbox("選擇年份", year_list)

month_list = sorted(df_temp[df_temp['年份'] == selected_year]['月份'].unique(), key=lambda x: int(x) if x!='nan' else 0)
if not month_list or 'nan' in month_list: month_list = [str(datetime.now().month)]
selected_month = st.sidebar.selectbox("選擇月份", month_list)

# 過濾出當月資料
mask = (df_temp['年份'] == selected_year) & (df_temp['月份'] == selected_month)
filtered_df = df_temp[mask].drop(columns=['dt', '年份', '月份'])

st.sidebar.divider()
st.sidebar.title("功能選單")
menu = ["➕ 新增訂單", "🏗️ 施工進度管理", "🛠️ 修改/刪除訂單", "💰 財務報表與尾款追蹤"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能 1：新增訂單 ---
if choice == "➕ 新增訂單":
    st.header("📝 填寫新訂單")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            auto_id = f"ORD{datetime.now().strftime('%m%d%H%M')}"
            c_id = st.text_input("訂單編號", value=auto_id)
            c_date = st.date_input("訂單日期", datetime.now())
            c_name = st.text_input("客戶姓名")
            c_phone = st.text_input("電話")
        with col2:
            c_address = st.text_input("地址")
            c_total = st.number_input("訂單總金額", min_value=0)
            c_paid = st.number_input("已收金額 (訂金)", min_value=0)
            c_wage = st.number_input("師傅工資", min_value=0)
            c_worker = st.text_input("施工師傅")
        
        c_content = st.text_area("訂購內容")
        c_install = st.date_input("預定施工日", datetime.now())
        
        if st.form_submit_button("儲存訂單 (存入電腦)"):
            new_row = {
                "訂單編號": c_id, "訂單日期": str(c_date), "客戶姓名": c_name,
                "電話": c_phone, "地址": c_address, "訂購內容": c_content,
                "總金額": c_total, "已收金額": c_paid, "師傅工資": c_wage, 
                "施工日期": str(c_install), "施工師傅": c_worker, "狀態": "已接單"
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_data(df)
            st.success("✅ 資料已安全存入電腦硬碟！")
            st.rerun()

# --- 功能 2：施工進度管理 ---
elif choice == "🏗️ 施工進度管理":
    st.header("工地進度追蹤")
    pending_df = df[df["狀態"] != "已收款"]
    if not pending_df.empty:
        st.write("### 未結案清單")
        st.dataframe(pending_df[["施工日期", "客戶姓名", "地址", "狀態", "施工師傅", "訂單編號"]])
        st.divider()
        u_id = st.selectbox("更新狀態", pending_df["訂單編號"].tolist())
        u_status = st.selectbox("新狀態", ["備貨中", "施工中", "已完工", "已收款"])
        if st.button("確認更新"):
            df.loc[df["訂單編號"] == u_id, "狀態"] = u_status
            save_data(df)
            st.success("狀態已更新")
            st.rerun()
    else:
        st.success("目前無待處理工程。")

# --- 功能 3：修改/刪除訂單 ---
elif choice == "🛠️ 修改/刪除訂單":
    st.header(f"🛠️ 編輯 {selected_month} 月訂單")
    if not filtered_df.empty:
        edit_id = st.selectbox("請選擇要編輯的訂單", filtered_df["訂單編號"].tolist())
        idx = df[df["訂單編號"] == edit_id].index[0]
        row = df.loc[idx]

        with st.form("edit_form"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_name = st.text_input("客戶姓名", value=str(row["客戶姓名"]))
                e_paid = st.number_input("已收金額", value=float(row["已收金額"]))
                e_total = st.number_input("總金額", value=float(row["總金額"]))
            with col_e2:
                e_wage = st.number_input("師傅工資", value=float(row["師傅工資"]))
                e_status = st.selectbox("狀態", ["已接單", "備貨中", "施工中", "已完工", "已收款"], index=["已接單", "備貨中", "施工中", "已完工", "已收款"].index(row["狀態"]))
                e_worker = st.text_input("施工師傅", value=str(row["施工師傅"]))
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ 儲存修改"):
                df.loc[idx, ["客戶姓名", "已收金額", "總金額", "師傅工資", "狀態", "施工師傅"]] = \
                    [e_name, e_paid, e_total, e_wage, e_status, e_worker]
                save_data(df)
                st.success("更新成功！")
                st.rerun()
            if c2.form_submit_button("🚨 刪除訂單"):
                df = df.drop(idx)
                save_data(df)
                st.rerun()
    else:
        st.info("本月尚無資料。")

# --- 功能 4：💰 財務報表與尾款追蹤 (密碼保護) ---
elif choice == "💰 財務報表與尾款追蹤":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header(f"📈 {selected_year} 年 {selected_month} 月 報表")
        rev = filtered_df["總金額"].sum()
        paid = filtered_df["已收金額"].sum()
        unpaid = filtered_df["待收尾款"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("當月業績", f"${rev:,.0f}")
        c2.metric("已收現款", f"${paid:,.0f}")
        c3.metric("待收尾款", f"${unpaid:,.0f}")
        
        st.divider()
        st.subheader("⚠️ 全體未收齊尾款名單")
        # 計算所有訂單的尾款
        all_df = df.copy()
        all_df['待收尾款'] = all_df['總金額'] - all_df['已收金額']
        unpaid_list = all_df[all_df['待收尾款'] > 0]
        st.dataframe(unpaid_list[["訂單日期", "客戶姓名", "電話", "總金額", "已收金額", "待收尾款", "狀態"]])
    elif pwd != "":
        st.error("密碼錯誤")
