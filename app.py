import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 網頁基本設定 ---
st.set_page_config(page_title="窗簾店雲端管理系統 V5", layout="wide")

# --- 設定管理密碼 ---
ADMIN_PASSWORD = "8888" 

# --- 1. 建立雲端連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # 讀取 Google Sheets 最新資料
    return conn.read(ttl="0s")

# 載入資料
df = load_data()

# 預防萬一：如果表是空的，建立空表格
if df.empty:
    df = pd.DataFrame(columns=[
        "訂單編號", "訂單日期", "客戶姓名", "電話", "地址", 
        "訂購內容", "總金額", "已收金額", "師傅工資", "施工日期", "施工師傅", "狀態"
    ])

# 轉換與計算
df['總金額'] = pd.to_numeric(df['總金額'], errors='coerce').fillna(0)
df['已收金額'] = pd.to_numeric(df['已收金額'], errors='coerce').fillna(0)
df['師傅工資'] = pd.to_numeric(df['師傅工資'], errors='coerce').fillna(0)
df['待收尾款'] = df['總金額'] - df['已收金額']

# 用於篩選的年月
df_view = df.copy()
df_view['dt'] = pd.to_datetime(df_view['訂單日期'], errors='coerce')
df_view['年份'] = df_view['dt'].dt.year.fillna(0).astype(int).astype(str)
df_view['月份'] = df_view['dt'].dt.month.fillna(0).astype(int).astype(str)

# --- 側邊欄：月份篩選 ---
st.sidebar.title("📅 月份篩選")
year_list = sorted(df_view['年份'].unique(), reverse=True)
if '0' in year_list: year_list.remove('0')
selected_year = st.sidebar.selectbox("選擇年份", year_list if year_list else [str(datetime.now().year)])

month_list = sorted(df_view[df_view['年份'] == selected_year]['月份'].unique(), key=lambda x: int(x))
if '0' in month_list: month_list.remove('0')
selected_month = st.sidebar.selectbox("選擇月份", month_list if month_list else [str(datetime.now().month)])

# 過濾出當月資料
filtered_df = df_view[(df_view['年份'] == selected_year) & (df_view['月份'] == selected_month)]

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
            c_total = st.number_input("總金額", min_value=0)
            c_paid = st.number_input("已收金額 (訂金)", min_value=0)
            c_wage = st.number_input("師傅工資", min_value=0)
            c_worker = st.text_input("施工師傅")
        
        c_content = st.text_area("訂購內容")
        c_install = st.date_input("預定施工日", datetime.now())
        
        if st.form_submit_button("儲存並同步到 Google Sheets"):
            new_row = pd.DataFrame([{
                "訂單編號": c_id, "訂單日期": str(c_date), "客戶姓名": c_name,
                "電話": c_phone, "地址": c_address, "訂購內容": c_content,
                "總金額": c_total, "已收金額": c_paid, "師傅工資": c_wage, 
                "施工日期": str(c_install), "施工師傅": c_worker, "狀態": "已接單"
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(data=updated_df)
            st.success(f"訂單已永久存入雲端！")
            st.rerun()

# --- 功能 2：施工進度管理 ---
elif choice == "🏗️ 施工進度管理":
    st.header("工地進度追蹤")
    pending_df = df[df["狀態"] != "已收款"]
    if not pending_df.empty:
        st.dataframe(pending_df[["施工日期", "客戶姓名", "狀態", "施工師傅", "地址"]])
        st.divider()
        u_id = st.selectbox("更新狀態", pending_df["訂單編號"].tolist())
        u_status = st.selectbox("新狀態", ["備貨中", "施工中", "已完工", "已收款"])
        if st.button("確認更新"):
            df.loc[df["訂單編號"] == u_id, "狀態"] = u_status
            conn.update(data=df)
            st.success("雲端狀態已更新")
            st.rerun()
    else:
        st.success("目前所有案件皆已結案。")

# --- 功能 3：修改/刪除訂單 ---
elif choice == "🛠️ 修改/刪除訂單":
    st.header(f"🛠️ 編輯 {selected_month} 月訂單")
    if not filtered_df.empty:
        edit_id = st.selectbox("選擇訂單", filtered_df["訂單編號"].tolist())
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
            
            if st.form_submit_button("✅ 儲存雲端修改"):
                df.loc[idx, ["客戶姓名", "已收金額", "總金額", "師傅工資", "狀態", "施工師傅"]] = \
                    [e_name, e_paid, e_total, e_wage, e_status, e_worker]
                conn.update(data=df)
                st.success("雲端資料已更新！")
                st.rerun()
            if st.form_submit_button("🚨 刪除訂單"):
                df = df.drop(idx)
                conn.update(data=df)
                st.rerun()
    else:
        st.info("尚無資料。")

# --- 功能 4：💰 財務報表 (密碼保護) ---
elif choice == "💰 財務報表與尾款追蹤":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header(f"📈 {selected_year} 年 {selected_month} 月 財務分析")
        rev = filtered_df["總金額"].sum()
        paid = filtered_df["已收金額"].sum()
        unpaid = filtered_df["待收尾款"].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("當月業績", f"${rev:,.0f}")
        c2.metric("已收現款", f"${paid:,.0f}")
        c3.metric("待收尾款", f"${unpaid:,.0f}")
        
        st.divider()
        st.subheader("⚠️ 全體未清尾款清單")
        unpaid_all = df[df["總金額"] > df["已收金額"]]
        st.dataframe(unpaid_all[["訂單日期", "客戶姓名", "電話", "總金額", "已收金額", "狀態"]])
