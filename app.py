import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 網頁基本設定 ---
st.set_page_config(page_title="窗簾店雲端管理系統", layout="wide")

st.title("🏮 窗簾店雲端數位管理系統")

# --- 1. 建立雲端連結 ---
# 請確保你在 Streamlit Cloud 的 Secrets 設定中加入了你的 Google Sheets 網址
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(ttl="0s")
except Exception as e:
    st.error("連線錯誤：請確認 Google Sheets 網址已正確設定於 Secrets 中。")
    st.stop()

# --- 側邊欄選單 ---
st.sidebar.title("功能選單")
menu = ["➕ 新增訂單", "🏗️ 施工進度管理", "🛠️ 修改/刪除訂單", "📊 財務與客戶統計"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能 1：新增訂單 ---
if choice == "➕ 新增訂單":
    st.header("📋 填寫新訂單")
    with st.form("order_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            auto_id = f"ORD{datetime.now().strftime('%m%d%H%M')}"
            c_id = st.text_input("訂單編號 (可自訂)", value=auto_id)
            c_date = st.date_input("訂單日期", datetime.now())
            c_name = st.text_input("客戶姓名")
            c_phone = st.text_input("聯絡電話")
        with col2:
            c_address = st.text_input("施工地址")
            c_install_date = st.date_input("預定施工日期", datetime.now())
            c_worker = st.text_input("安排師傅")
            c_total = st.number_input("訂單總金額", min_value=0)
            c_wage = st.number_input("師傅工資", min_value=0)
        
        c_content = st.text_area("訂購內容 (產品尺寸、布料等)")
        
        submit = st.form_submit_button("儲存並同步到雲端")

        if submit:
            if c_id in df["訂單編號"].astype(str).values:
                st.error("此訂單編號已存在！")
            else:
                new_row = pd.DataFrame([{
                    "訂單編號": c_id, "訂單日期": str(c_date), "客戶姓名": c_name,
                    "電話": c_phone, "地址": c_address, "訂購內容": c_content,
                    "總金額": c_total, "師傅工資": c_wage, "施工日期": str(c_install_date),
                    "施工師傅": c_worker, "狀態": "已接單"
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(data=updated_df)
                st.success(f"訂單 {c_id} 已存入雲端！")
                st.rerun()

# --- 功能 2：施工進度管理 ---
elif choice == "🏗️ 施工進度管理":
    st.header("施工調度與狀態")
    if not df.empty:
        col_up1, col_up2 = st.columns(2)
        target_id = col_up1.selectbox("選擇要更新的訂單", df["訂單編號"].tolist())
        new_status = col_up2.selectbox("更改狀態", ["已接單", "備貨中", "施工中", "已完工", "已收款"])
        
        if st.button("更新施工狀態"):
            df.loc[df["訂單編號"] == target_id, "狀態"] = new_status
            conn.update(data=df)
            st.success("狀態更新成功！")
            st.rerun()
            
        st.divider()
        st.write("### 施工進度表")
        st.dataframe(df[["施工日期", "施工師傅", "客戶姓名", "地址", "狀態", "訂單編號"]])
    else:
        st.info("尚無資料。")

# --- 功能 3：修改/刪除訂單 ---
elif choice == "🛠️ 修改/刪除訂單":
    st.header("編輯現有訂單")
    if not df.empty:
        edit_id = st.selectbox("選擇要編輯或刪除的訂單", df["訂單編號"].tolist())
        target_row = df[df["訂單編號"] == edit_id].iloc[0]

        with st.form("edit_form"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                e_name = st.text_input("客戶姓名", value=target_row["客戶姓名"])
                e_address = st.text_input("地址", value=target_row["地址"])
                e_content = st.text_area("訂購內容", value=target_row["訂購內容"])
            with col_e2:
                e_total = st.number_input("總金額", value=int(target_row["總金額"]))
                e_wage = st.number_input("師傅工資", value=int(target_row["師傅工資"]))
                e_worker = st.text_input("施工師傅", value=target_row["施工師傅"])
            
            if st.form_submit_button("儲存修改"):
                df.loc[df["訂單編號"] == edit_id, ["客戶姓名", "地址", "訂購內容", "總金額", "師傅工資", "施工師傅"]] = [e_name, e_address, e_content, e_total, e_wage, e_worker]
                conn.update(data=df)
                st.success("資料已更新！")
                st.rerun()

        st.divider()
        if st.button("🚨 刪除此筆訂單"):
            df = df[df["訂單編號"] != edit_id]
            conn.update(data=df)
            st.warning("訂單已刪除。")
            st.rerun()
    else:
        st.info("尚無資料可修改。")

# --- 功能 4：財務與客戶統計 ---
elif choice == "📊 財務與客戶統計":
    st.header("數據統計報表")
    if not df.empty:
        # 財務指標
        col_m1, col_m2, col_m3 = st.columns(3)
        rev = df["總金額"].sum()
        wage = df["師傅工資"].sum()
        col_m1.metric("累積總營業額", f"${rev:,.0f}")
        col_m2.metric("累積應付工資", f"${wage:,.0f}")
        col_m3.metric("預估淨利", f"${(rev - wage):,.0f}")
        
        st.divider()
        
        # 師傅工資摘要
        st.subheader("👷 師傅薪資統計")
        wage_df = df.groupby("施工師傅")["師傅工資"].sum().reset_index()
        st.table(wage_df)
        
        # 完整清單
        st.subheader("👥 完整客戶資料清單")
        st.dataframe(df)
        
        # 下載按鈕
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("下載備份檔案 (CSV)", data=csv, file_name="窗簾店資料備份.csv")
    else:
        st.info("尚無資料。")
