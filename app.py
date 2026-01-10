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
        for col in ["總金額", "已收金額", "師傅工資"]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        df['dt'] = pd.to_datetime(df['訂單日期'], errors='coerce')
        df = df.sort_values(by='dt', ascending=False)
        df['年份'] = df['dt'].dt.year.fillna(datetime.now().year).astype(int).astype(str)
        df['月份'] = df['dt'].dt.month.fillna(datetime.now().month).astype(int).astype(str)
        return df
    except:
        return pd.DataFrame(columns=["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工日期", "施工師傅", "狀態", "年份", "月份"])

def load_purchases():
    try:
        df = conn.read(worksheet="採購明細", ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=["訂單編號", "廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"])
        df['進貨金額'] = pd.to_numeric(df['進貨金額'], errors='coerce').fillna(0)
        return df
    except:
        return pd.DataFrame(columns=["訂單編號", "廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"])

df_orders = load_orders()
df_purchases = load_purchases()

# --- 側邊欄：年月分類與客戶查詢 ---
st.sidebar.title("📅 訂單分類快查")
selected_id = None

if not df_orders.empty:
    years = sorted(df_orders['年份'].unique(), reverse=True)
    sel_year = st.sidebar.selectbox("📅 選擇年份", years)
    months = sorted(df_orders[df_orders['年份'] == sel_year]['月份'].unique(), key=lambda x: int(x), reverse=True)
    sel_month = st.sidebar.selectbox("🌙 選擇月份", months)
    
    filtered_df = df_orders[(df_orders['年份'] == sel_year) & (df_orders['月份'] == sel_month)]
    
    search = st.sidebar.text_input("🔍 搜尋姓名/單號")
    if search:
        filtered_df = filtered_df[filtered_df['客戶姓名'].astype(str).str.contains(search) | filtered_df['訂單編號'].astype(str).str.contains(search)]
    
    if not filtered_df.empty:
        # 修正：確保顯示字串包含 ID，方便提取
        order_list = filtered_df.apply(lambda r: f"{r['客戶姓名']} ({r['訂單編號']})", axis=1).tolist()
        selected_customer_str = st.sidebar.radio(f"📋 {sel_year}/{sel_month} 名單：", order_list)
        # 精確提取括號內的單號
        selected_id = selected_customer_str.split("(")[-1].split(")")[0]
    else:
        st.sidebar.warning("此月份無資料")
else:
    st.sidebar.info("資料庫目前為空")

st.sidebar.divider()
st.sidebar.title("⚙️ 功能選單")
menu = ["🏠 客戶詳細資料卡", "➕ 新增客戶訂單", "📦 廠商進貨登記", "🏗️ 施工進度管理", "🛠️ 修改/刪除訂單", "💰 財務損益報表"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能 0：客戶詳細資料卡 ---
if choice == "🏠 客戶詳細資料卡":
    # 💡 關鍵修正：先確認是否真的有抓到單號，且該單號在資料庫裡
    if selected_id:
        target_data = df_orders[df_orders["訂單編號"] == selected_id]
        if not target_data.empty:
            order_info = target_data.iloc[0]
            st.header(f"👤 客戶：{order_info['客戶姓名']} 資料詳情")
            
            # 指標顯示
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("訂單狀態", order_info["狀態"])
            c2.metric("總金額", f"${order_info['總金額']:,.0f}")
            c3.metric("已收金額", f"${order_info['已收金額']:,.0f}")
            c4.metric("待收尾款", f"${(order_info['總金額'] - order_info['已收金額']):,.0f}")
            
            st.divider()
            col_l, col_r = st.columns(2)
            with col_l:
                st.write(f"**📌 訂單編號：** {order_info['訂單編號']}")
                st.write(f"**📞 連絡電話：** {order_info['電話']}")
                st.write(f"**📍 施工地址：** {order_info['地址']}")
            with col_r:
                st.write(f"**👷 施工師傅：** {order_info['施工師傅']}")
                st.write(f"**📅 預定施工日：** {order_info['施工日期']}")
                st.info(f"**📝 訂購內容：**\n\n{order_info['訂購內容']}")

            st.divider()
            st.subheader("📦 本案採購明細")
            cust_p = df_purchases[df_purchases["訂單編號"] == selected_id]
            if not cust_p.empty:
                st.table(cust_p[["廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"]])
                total_cost = cust_p["進貨金額"].sum()
                profit = order_info["總金額"] - order_info["師傅工資"] - total_cost
                st.write(f"💰 **材料成本：${total_cost:,.0f}** | **師傅工資：${order_info['師傅工資']:,.0f}**")
                st.success(f"📈 **本案預估純利：${profit:,.0f}**")
            else:
                st.info("此單目前尚無進貨紀錄。")
        else:
            st.error("找不到該訂單資料，請重新整理。")
    else:
        st.info("💡 請在左側選單選擇一位客戶以查看詳細資料。")

# --- 功能 1：新增客戶訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📝 建立新客戶訂單")
    with st.form("new_order", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            c_id = st.text_input("訂單編號", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
            c_name = st.text_input("客戶姓名")
            c_phone = st.text_input("電話")
        with col2:
            c_total = st.number_input("總金額", min_value=0)
            c_wage = st.number_input("師傅工資", min_value=0)
            c_address = st.text_input("施工地址")
        c_content = st.text_area("訂購內容")
        if st.form_submit_button("✅ 儲存訂單"):
            new_data = pd.DataFrame([{"訂單編號": c_id, "訂單日期": str(datetime.now().date()), "客戶姓名": c_name, "電話": c_phone, "地址": c_address, "訂購內容": c_content, "總金額": c_total, "已收金額": 0, "師傅工資": c_wage, "施工日期": "", "施工師傅": "", "狀態": "已接單"}])
            conn.update(worksheet="訂單資料", data=pd.concat([df_orders, new_data], ignore_index=True))
            st.success("儲存成功！")
            st.rerun()

# --- 功能 2：進貨登記 ---
elif choice == "📦 廠商進貨登記":
    st.header("🚚 登記廠商進貨成本")
    if selected_id:
        st.info(f"正在為客戶 【{selected_id}】 登記進貨內容")
        with st.form("p_form", clear_on_submit=True):
            p_vendor = st.selectbox("廠商名稱", VENDORS)
            p_cat = st.selectbox("項目類別", CATEGORIES)
            p_cost = st.number_input("進貨金額", min_value=0)
            p_note = st.text_input("備註 (布號/規格)")
            if st.form_submit_button("➕ 儲存進貨紀錄"):
                new_p = pd.DataFrame([{"訂單編號": selected_id, "廠商名稱": p_vendor, "項目分類": p_cat, "進貨金額": p_cost, "叫貨日期": str(datetime.now().date()), "備註": p_note}])
                conn.update(worksheet="採購明細", data=pd.concat([df_purchases, new_p], ignore_index=True))
                st.success("成本登記成功！")
                st.rerun()
    else:
        st.warning("請先在左側選單選擇一位客戶。")

# --- 功能 5：損益報表 ---
elif choice == "💰 財務損益報表":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📈 經營毛利結算")
        p_sum = df_purchases.groupby("訂單編號")["進貨金額"].sum().reset_index()
        report = pd.merge(df_orders, p_sum, on="訂單編號", how="left").fillna(0)
        report['淨利'] = report['總金額'] - report['師傅工資'] - report['進貨金額']
        
        c1, c2 = st.columns(2)
        c1.metric("當前總業績", f"${report['總金額'].sum():,.0f}")
        c2.metric("結算總利潤", f"${report['淨利'].sum():,.0f}")
        
        st.divider()
        st.dataframe(report[["訂單日期", "客戶姓名", "總金額", "進貨金額", "師傅工資", "淨利", "狀態"]], use_container_width=True)
    elif pwd != "":
        st.error("密碼錯誤")
