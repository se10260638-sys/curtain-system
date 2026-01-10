import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 網頁基本設定 ---
st.set_page_config(page_title="窗簾店專業雲端管理系統", layout="wide")

# --- 設定常數與管理密碼 ---
ADMIN_PASSWORD = "8888" 
VENDORS = ["東隆", "欣明", "泰安", "慶昇", "勝美", "其餘廠商"]
CATEGORIES = ["布料/紗網", "軌道/五金", "捲簾/調光簾", "百葉窗", "壁紙/地磚", "其他零件"]

# --- 1. 建立雲端連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_orders():
    try:
        df = conn.read(worksheet="訂單資料", ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工日期", "施工師傅", "狀態"])
        
        # 格式轉換與預處理
        for col in ["總金額", "已收金額", "師傅工資"]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        # --- 核心：日期排序 ---
        # 建立一個臨時的日期欄位來排序，確保最新的在最上面
        df['temp_date'] = pd.to_datetime(df['訂單日期'], errors='coerce')
        df = df.sort_values(by='temp_date', ascending=False).drop(columns=['temp_date'])
        
        return df
    except:
        return pd.DataFrame(columns=["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工日期", "施工師傅", "狀態"])

def load_purchases():
    try:
        df = conn.read(worksheet="採購明細", ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=["訂單編號", "廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"])
        df['進貨金額'] = pd.to_numeric(df['進貨金額'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=["訂單編號", "廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"])

# 初始化載入資料
df_orders = load_orders()
df_purchases = load_purchases()

# --- 側邊欄：客戶快速查詢 ---
st.sidebar.title("🔍 客戶快查 (最新優先)")
if not df_orders.empty:
    search_query = st.sidebar.text_input("輸入關鍵字搜尋")
    
    # 過濾名單
    display_df = df_orders.copy()
    if search_query:
        display_df = display_df[display_df['客戶姓名'].str.contains(search_query) | display_df['訂單編號'].str.contains(search_query)]
    
    # 建立清單顯示格式：[日期] 姓名 - 編號
    order_list = display_df.apply(lambda r: f"[{r['訂單日期']}] {r['客戶姓名']} - {r['訂單編號']}", axis=1).tolist()
    selected_customer_str = st.sidebar.radio("請選擇客戶查看詳情：", order_list)
    selected_id = selected_customer_str.split(" - ")[-1] if selected_customer_str else None
else:
    st.sidebar.info("目前尚無客戶資料")
    selected_id = None

st.sidebar.divider()
st.sidebar.title("⚙️ 功能選單")
menu = ["🏠 客戶詳細資料卡", "➕ 新增客戶訂單", "📦 廠商進貨登記", "🏗️ 施工進度管理", "🛠️ 修改/刪除訂單", "💰 財務損益報表"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能 0：客戶詳細資料卡 ---
if choice == "🏠 客戶詳細資料卡":
    if selected_id:
        order_info = df_orders[df_orders["訂單編號"] == selected_id].iloc[0]
        st.header(f"👤 客戶：{order_info['客戶姓名']} ({order_info['訂單編號']})")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("訂單狀態", order_info["狀態"])
        c2.metric("總金額", f"${order_info['總金額']:,.0f}")
        c3.metric("已收金額", f"${order_info['已收金額']:,.0f}")
        c4.metric("待收尾款", f"${(order_info['總金額'] - order_info['已收金額']):,.0f}")
        
        st.divider()
        col_left, col_right = st.columns(2)
        with col_left:
            st.write(f"**📞 電話：** {order_info['電話']}")
            st.write(f"**📍 地址：** {order_info['地址']}")
            st.write(f"**📅 訂單日期：** {order_info['訂單日期']}")
        with col_right:
            st.write(f"**👷 施工師傅：** {order_info['施工師傅']}")
            st.write(f"**🛠️ 施工日期：** {order_info['施工日期']}")
            st.info(f"**📝 訂購內容：**\n\n{order_info['訂購內容']}")

        st.divider()
        st.subheader("📦 叫貨成本明細")
        cust_purchases = df_purchases[df_purchases["訂單編號"] == selected_id]
        if not cust_purchases.empty:
            st.dataframe(cust_purchases[["廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"]], use_container_width=True)
            t_cost = cust_purchases["進貨金額"].sum()
            profit = order_info["總金額"] - order_info["師傅工資"] - t_cost
            st.write(f"💰 總進貨：${t_cost:,.0f} | 師傅工資：${order_info['師傅工資']:,.0f} | **預估純利：${profit:,.0f}**")
        else:
            st.warning("此單尚無進貨紀錄。")
    else:
        st.info("請在左側選擇客戶。")

# --- 功能 1：新增客戶訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📝 建立新訂單")
    with st.form("new_order"):
        c_id = st.text_input("訂單編號", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
        c_name = st.text_input("客戶姓名")
        c_phone = st.text_input("電話")
        c_address = st.text_input("地址")
        c_total = st.number_input("總金額", min_value=0)
        c_wage = st.number_input("師傅工資", min_value=0)
        c_content = st.text_area("訂購內容")
        if st.form_submit_button("✅ 儲存訂單"):
            new_data = pd.DataFrame([{"訂單編號": c_id, "訂單日期": str(datetime.now().date()), "客戶姓名": c_name, "電話": c_phone, "地址": c_address, "訂購內容": c_content, "總金額": c_total, "已收金額": 0, "師傅工資": c_wage, "施工日期": "", "施工師傅": "", "狀態": "已接單"}])
            conn.update(worksheet="訂單資料", data=pd.concat([df_orders, new_data], ignore_index=True))
            st.success("儲存成功！")
            st.rerun()

# --- 功能 2：進貨登記 ---
elif choice == "📦 廠商進貨登記":
    st.header("🚚 廠商進貨登記")
    if selected_id:
        st.info(f"為客戶 【{selected_id}】 登記成本")
        with st.form("p_form"):
            p_vendor = st.selectbox("廠商", VENDORS)
            p_cat = st.selectbox("類別", CATEGORIES)
            p_cost = st.number_input("金額", min_value=0)
            p_note = st.text_input("備註")
            if st.form_submit_button("➕ 儲存"):
                new_p = pd.DataFrame([{"訂單編號": selected_id, "廠商名稱": p_vendor, "項目分類": p_cat, "進貨金額": p_cost, "叫貨日期": str(datetime.now().date()), "備註": p_note}])
                conn.update(worksheet="採購明細", data=pd.concat([df_purchases, new_p], ignore_index=True))
                st.success("登記成功！")
                st.rerun()
    else:
        st.warning("請先從左側選擇客戶。")

# --- 功能 3：進度管理 ---
elif choice == "🏗️ 施工進度管理":
    st.header("🏗️ 進度更新")
    pending = df_orders[df_orders["狀態"] != "已收款"]
    if not pending.empty:
        u_id = st.selectbox("選擇案號", pending["訂單編號"].tolist())
        u_status = st.selectbox("狀態", ["備貨中", "施工中", "已完工", "已收款"])
        u_worker = st.text_input("施工師傅")
        u_date = st.date_input("施工日期")
        if st.button("確認更新"):
            df_orders.loc[df_orders["訂單編號"] == u_id, ["狀態", "施工師傅", "施工日期"]] = [u_status, u_worker, str(u_date)]
            conn.update(worksheet="訂單資料", data=df_orders)
            st.success("已更新狀態！")
            st.rerun()
    else:
        st.success("目前無進行中案件。")

# --- 功能 4：修改/刪除 ---
elif choice == "🛠️ 修改/刪除訂單":
    st.header("🛠️ 編輯訂單")
    if selected_id:
        idx = df_orders[df_orders["訂單編號"] == selected_id].index[0]
        row = df_orders.loc[idx]
        with st.form("edit"):
            e_name = st.text_input("客戶姓名", value=str(row["客戶姓名"]))
            e_total = st.number_input("總金額", value=float(row["總金額"]))
            e_paid = st.number_input("已收金額", value=float(row["已收金額"]))
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ 儲存修改"):
                df_orders.loc[idx, ["客戶姓名", "總金額", "已收金額"]] = [e_name, e_total, e_paid]
                conn.update(worksheet="訂單資料", data=df_orders)
                st.success("已更新！")
                st.rerun()
            if c2.form_submit_button("🚨 刪除整筆訂單"):
                df_orders = df_orders.drop(idx)
                conn.update(worksheet="訂單資料", data=df_orders)
                st.rerun()

# --- 功能 5：損益報表 ---
elif choice == "💰 財務損益報表":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        p_sum = df_purchases.groupby("訂單編號")["進貨金額"].sum().reset_index()
        report = pd.merge(df_orders, p_sum, on="訂單編號", how="left").fillna(0)
        report['淨利'] = report['總金額'] - report['師傅工資'] - report['進貨金額']
        st.metric("累計總淨利", f"${report['淨利'].sum():,.0f}")
        st.dataframe(report[["訂單日期", "客戶姓名", "總金額", "進貨金額", "師傅工資", "淨利", "狀態"]])
