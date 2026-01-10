import streamlit as st
import pandas as pd
from datetime import datetime
import os

# 設定網頁標題
st.set_page_config(page_title="窗簾店管理系統 V2", layout="wide")

# 初始化資料庫
DB_FILE = "orders_db.csv"
if not os.path.exists(DB_FILE):
    df_init = pd.DataFrame(columns=[
        "訂單編號", "訂單日期", "客戶姓名", "電話", "地址", 
        "訂購內容", "總金額", "施工日期", "施工師傅", "狀態"
    ])
    df_init.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

def load_data():
    df = pd.read_csv(DB_FILE, encoding='utf-8-sig')
    # 確保日期欄位格式正確
    df['訂單日期'] = df['訂單日期'].astype(str)
    df['施工日期'] = df['施工日期'].astype(str)
    return df

def save_data(df):
    df.to_csv(DB_FILE, index=False, encoding='utf-8-sig')

# 側邊欄導覽
menu = ["新增訂單", "施工調度與狀態更新", "修改/刪除訂單", "客戶統計與營業額"]
choice = st.sidebar.selectbox("功能選單", menu)

# --- 功能 1：新增訂單 ---
if choice == "新增訂單":
    st.header("📋 新增客戶訂單")
    with st.form("order_form"):
        col1, col2 = st.columns(2)
        with col1:
            order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
            st.write(f"**建議訂單編號:** {order_id}")
            order_date = st.date_input("訂單日期", datetime.now())
            cust_name = st.text_input("客戶姓名")
            cust_phone = st.text_input("聯絡電話")
        with col2:
            cust_address = st.text_input("施工地址")
            install_date = st.date_input("預定施工日期", datetime.now())
            worker = st.text_input("安排師傅")
            total_price = st.number_input("訂單總金額", min_value=0)
        
        order_content = st.text_area("訂購內容")
        submit = st.form_submit_button("儲存訂單")

        if submit:
            new_data = {
                "訂單編號": order_id, "訂單日期": str(order_date),
                "客戶姓名": cust_name, "電話": cust_phone, "地址": cust_address,
                "訂購內容": order_content, "總金額": total_price,
                "施工日期": str(install_date), "施工師傅": worker, "狀態": "已接單"
            }
            df = load_data()
            df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            save_data(df)
            st.success(f"訂單 {order_id} 已儲存！")

# --- 功能 2：施工調度與狀態更新 ---
elif choice == "施工調度與狀態更新":
    st.header("🏗️ 施工管理")
    df = load_data()
    if not df.empty:
        # 快速更新狀態
        st.subheader("快速更新施工狀態")
        order_to_update = st.selectbox("選擇訂單編號", df["訂單編號"].tolist())
        new_status = st.selectbox("更改狀態為", ["已接單", "備貨中", "施工中", "已完工", "已收款"])
        if st.button("更新狀態"):
            df.loc[df["訂單編號"] == order_to_update, "狀態"] = new_status
            save_data(df)
            st.success(f"訂單 {order_to_update} 狀態已更新為 {new_status}")
        
        st.divider()
        st.write("目前所有排程：")
        st.dataframe(df[["施工日期", "施工師傅", "客戶姓名", "地址", "狀態", "訂單編號"]])
    else:
        st.info("尚無訂單。")

# --- 功能 3：修改/刪除訂單 ---
elif choice == "修改/刪除訂單":
    st.header("🛠️ 編輯或刪除現有訂單")
    df = load_data()
    if not df.empty:
        target_id = st.selectbox("選擇要處理的訂單編號", df["訂單編號"].tolist())
        target_row = df[df["訂單編號"] == target_id].iloc[0]

        with st.expander("點擊展開 - 修改資料"):
            with st.form("edit_form"):
                new_content = st.text_area("訂購內容", value=target_row["訂購內容"])
                new_price = st.number_input("總金額", value=int(target_row["總金額"]))
                new_worker = st.text_input("施工師傅", value=target_row["施工師傅"])
                new_address = st.text_input("地址", value=target_row["地址"])
                
                col_save, col_del = st.columns([1, 1])
                if col_save.form_submit_button("確認修改"):
                    df.loc[df["訂單編號"] == target_id, ["訂購內容", "總金額", "施工師傅", "地址"]] = [new_content, new_price, new_worker, new_address]
                    save_data(df)
                    st.success("資料已更新！")
                    st.rerun()

        st.divider()
        if st.button("🚨 刪除此筆訂單 (不可復原)", help="請謹慎使用"):
            df = df[df["訂單編號"] != target_id]
            save_data(df)
            st.warning(f"訂單 {target_id} 已刪除。")
            st.rerun()
    else:
        st.info("尚無資料可修改。")

# --- 功能 4：客戶統計與營業額 ---
elif choice == "客戶統計與營業額":
    st.header("📈 數據報表")
    df = load_data()
    if not df.empty:
        total_rev = df["總金額"].sum()
        st.metric("總營業額 (累積)", f"NT$ {total_rev:,.0f}")
        
        st.subheader("客戶資料清單")
        st.dataframe(df)
        
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("匯出 Excel 檔 (CSV)", data=csv, file_name="窗簾店客戶資料.csv")
    else:
        st.info("尚無營業數據。")
