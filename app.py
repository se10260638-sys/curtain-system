import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 網頁基本設定 ---
st.set_page_config(page_title="窗簾店雲端進階版", layout="wide")

# --- 設定管理密碼與常數 ---
ADMIN_PASSWORD = "8888" 
VENDORS = ["東隆", "欣明", "泰安", "慶昇", "勝美", "其他"]
CATEGORIES = ["布料", "軌道/五金", "捲簾/調光簾", "百葉窗", "壁紙/地磚", "其他"]

# --- 1. 建立雲端連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_orders():
    df = conn.read(worksheet="訂單資料", ttl="0s")
    if df is None or df.empty:
        return pd.DataFrame(columns=["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工日期", "施工師傅", "狀態"])
    return df

def load_purchases():
    df = conn.read(worksheet="採購明細", ttl="0s")
    if df is None or df.empty:
        return pd.DataFrame(columns=["訂單編號", "廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"])
    return df

# 載入所有資料
df_orders = load_orders()
df_purchases = load_purchases()

# --- 側邊欄選單 ---
st.sidebar.title("🏮 窗簾店管理系統")
menu = ["➕ 新增訂單", "📦 進貨成本管理", "🏗️ 施工進度管理", "🛠️ 修改/刪除訂單", "💰 財務損益報表"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能 1：新增訂單 ---
if choice == "➕ 新增訂單":
    st.header("📋 建立新客戶訂單")
    with st.form("add_order_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            c_id = st.text_input("訂單編號", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
            c_date = st.date_input("訂單日期", datetime.now())
            c_name = st.text_input("客戶姓名")
        with col2:
            c_total = st.number_input("訂單總金額", min_value=0)
            c_paid = st.number_input("已收金額 (訂金)", min_value=0)
            c_wage = st.number_input("師傅工資", min_value=0)
        
        c_address = st.text_input("施工地址")
        c_content = st.text_area("訂購內容 (如：客廳布簾*1, 臥室捲簾*2)")
        
        if st.form_submit_button("✅ 儲存訂單到雲端"):
            new_row = pd.DataFrame([{
                "訂單編號": c_id, "訂單日期": str(c_date), "客戶姓名": c_name,
                "電話": "", "地址": c_address, "訂購內容": c_content,
                "總金額": c_total, "已收金額": c_paid, "師傅工資": c_wage, 
                "施工日期": str(c_date), "施工師傅": "", "狀態": "已接單"
            }])
            updated_df = pd.concat([df_orders, new_row], ignore_index=True)
            conn.update(worksheet="訂單資料", data=updated_df)
            st.success("訂單已存入雲端！")
            st.rerun()

# --- 功能 2：📦 進貨成本管理 (進階版核心) ---
elif choice == "📦 進貨成本管理":
    st.header("🚚 廠商叫貨成本登記")
    
    # 建立一個選項讓老闆選是對應哪張單
    if not df_orders.empty:
        order_options = df_orders.apply(lambda r: f"{r['訂單編號']} - {r['客戶姓名']}", axis=1).tolist()
        selected_order_str = st.selectbox("這筆進貨是對應哪張訂單？", order_options)
        selected_order_id = selected_order_str.split(" - ")[0]
    else:
        st.warning("請先建立客戶訂單，才能記錄進貨成本。")
        st.stop()

    with st.form("purchase_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            p_vendor = st.selectbox("供應商", VENDORS)
            p_cat = st.selectbox("項目分類", CATEGORIES)
            p_date = st.date_input("叫貨日期", datetime.now())
        with col2:
            p_cost = st.number_input("進貨成本金額", min_value=0)
            p_note = st.text_input("備註 (如：布號, 尺寸)")
        
        if st.form_submit_button("➕ 增加這筆叫貨記錄"):
            new_p = pd.DataFrame([{
                "訂單編號": selected_order_id, "廠商名稱": p_vendor,
                "項目分類": p_cat, "進貨金額": p_cost, "叫貨日期": str(p_date), "備註": p_note
            }])
            updated_p = pd.concat([df_purchases, new_p], ignore_index=True)
            conn.update(worksheet="採購明細", data=updated_p)
            st.success(f"已記錄 {p_vendor} 的進貨成本！")
            st.rerun()
            
    st.divider()
    st.subheader(f"🔍 該訂單 ({selected_order_id}) 已有成本明細")
    this_order_p = df_purchases[df_purchases["訂單編號"] == selected_order_id]
    if not this_order_p.empty:
        st.table(this_order_p[["廠商名稱", "項目分類", "進貨金額", "備註"]])
        st.write(f"**目前累計總成本：${this_order_p['進貨金額'].sum():,.0f}**")
    else:
        st.info("該訂單目前尚未記錄任何進貨成本。")

# --- 功能 5：💰 財務損益報表 ---
elif choice == "💰 財務損益報表":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 店面綜合損益分析")
        
        # 合併計算：將每張訂單的採購成本加總
        cost_sum = df_purchases.groupby("訂單編號")["進貨金額"].sum().reset_index()
        report_df = pd.merge(df_orders, cost_sum, on="訂單編號", how="left").fillna(0)
        report_df['毛利'] = report_df['總金額'] - report_df['師傅工資'] - report_df['進貨金額']
        
        # 顯示關鍵指標
        c1, c2, c3, c4 = st.columns(4)
        total_rev = report_df["總金額"].sum()
        total_wage = report_df["師傅工資"].sum()
        total_cost = report_df["進貨金額"].sum()
        total_profit = report_df["毛利"].sum()
        
        c1.metric("累積總業績", f"${total_rev:,.0f}")
        c2.metric("師傅總工資", f"${total_wage:,.0f}")
        c3.metric("材料總成本", f"${total_cost:,.0f}")
        c4.metric("累計純利", f"${total_profit:,.0f}", delta=f"{total_profit/total_rev:.1%}" if total_rev > 0 else "0%")
        
        st.divider()
        st.subheader("📝 詳細訂單損益清單")
        st.dataframe(report_df[["訂單日期", "客戶姓名", "總金額", "師傅工資", "進貨金額", "毛利", "狀態"]])
    elif pwd != "":
        st.error("密碼錯誤")

# --- (其餘 施工管理 與 修改/刪除 功能邏輯相同，僅需確保對應到 '訂單資料' 表) ---
        st.error("密碼錯誤，請重新輸入！")
