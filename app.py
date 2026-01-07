import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 網頁基本設定 ---
st.set_page_config(page_title="窗簾店專業進銷存系統", layout="wide")

# --- 設定常數與廠商名單 ---
ADMIN_PASSWORD = "8888" 
VENDORS = ["東隆", "欣明", "泰安", "慶昇", "勝美", "其餘廠商"]
CATEGORIES = ["布料/紗網", "軌道/五金", "捲簾/調光簾", "百葉窗", "壁紙/地磚", "其他零件"]

# --- 1. 建立雲端連線 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_orders():
    df = conn.read(worksheet="訂單資料", ttl="0s")
    if df is None or df.empty:
        return pd.DataFrame(columns=["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工日期", "施工師傅", "狀態"])
    # 格式轉換
    df['總金額'] = pd.to_numeric(df['總金額'], errors='coerce').fillna(0)
    df['已收金額'] = pd.to_numeric(df['已收金額'], errors='coerce').fillna(0)
    df['師傅工資'] = pd.to_numeric(df['師傅工資'], errors='coerce').fillna(0)
    return df

def load_purchases():
    df = conn.read(worksheet="採購明細", ttl="0s")
    if df is None or df.empty:
        return pd.DataFrame(columns=["訂單編號", "廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"])
    df['進貨金額'] = pd.to_numeric(df['進貨金額'], errors='coerce').fillna(0)
    return df

# 初始化載入
df_orders = load_orders()
df_purchases = load_purchases()

# --- 側邊欄導覽 ---
st.sidebar.title("🏮 窗簾經營管理系統")
menu = ["➕ 新增客戶訂單", "📦 廠商進貨登記", "🏗️ 施工進度管理", "🛠️ 修改/刪除訂單", "💰 財務損益報表"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能 1：新增訂單 ---
if choice == "➕ 新增客戶訂單":
    st.header("📝 建立新客戶訂單")
    with st.form("add_order", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            c_id = st.text_input("訂單編號", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
            c_date = st.date_input("訂單日期", datetime.now())
            c_name = st.text_input("客戶姓名")
            c_phone = st.text_input("電話")
        with col2:
            c_total = st.number_input("訂單總金額", min_value=0)
            c_paid = st.number_input("已收金額 (訂金)", min_value=0)
            c_wage = st.number_input("師傅工資", min_value=0)
            c_worker = st.text_input("施工師傅")
        
        c_address = st.text_input("地址")
        c_content = st.text_area("訂購內容")
        
        if st.form_submit_button("✅ 儲存訂單到雲端"):
            new_row = pd.DataFrame([{
                "訂單編號": c_id, "訂單日期": str(c_date), "客戶姓名": c_name, "電話": c_phone,
                "地址": c_address, "訂購內容": c_content, "總金額": c_total, "已收金額": c_paid,
                "師傅工資": c_wage, "施工日期": str(c_date), "施工師傅": c_worker, "狀態": "已接單"
            }])
            updated_df = pd.concat([df_orders, new_row], ignore_index=True)
            conn.update(worksheet="訂單資料", data=updated_df)
            st.success("訂單存入成功！")
            st.rerun()

# --- 功能 2：進貨成本登記 ---
elif choice == "📦 廠商進貨登記":
    st.header("🚚 進貨成本登記 (進階版)")
    if df_orders.empty:
        st.warning("目前無任何訂單，請先建立訂單。")
    else:
        order_options = df_orders.apply(lambda r: f"{r['訂單編號']} - {r['客戶姓名']}", axis=1).tolist()
        selected_target = st.selectbox("這筆成本屬於哪位客戶？", order_options)
        target_id = selected_target.split(" - ")[0]

        with st.form("purchase_form", clear_on_submit=True):
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                p_vendor = st.selectbox("供應商", VENDORS)
                p_cat = st.selectbox("項目類別", CATEGORIES)
            with p_col2:
                p_cost = st.number_input("進貨金額", min_value=0)
                p_date = st.date_input("叫貨日期", datetime.now())
            p_note = st.text_input("備註 (布號/規格)")
            
            if st.form_submit_button("➕ 儲存進貨記錄"):
                new_p = pd.DataFrame([{
                    "訂單編號": target_id, "廠商名稱": p_vendor, "項目分類": p_cat,
                    "進貨金額": p_cost, "叫貨日期": str(p_date), "備註": p_note
                }])
                updated_p = pd.concat([df_purchases, new_p], ignore_index=True)
                conn.update(worksheet="採購明細", data=updated_p)
                st.success("進貨資料已同步到雲端！")
                st.rerun()
        
        st.divider()
        st.subheader("該筆訂單目前的成本構成")
        this_p = df_purchases[df_purchases["訂單編號"] == target_id]
        if not this_p.empty:
            st.dataframe(this_p[["廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"]])
            st.metric("累計總進貨成本", f"${this_p['進貨金額'].sum():,.0f}")

# --- 功能 3：進度管理 ---
elif choice == "🏗️ 施工進度管理":
    st.header("🏗️ 工程進度管理")
    # 過濾未結案案件
    pending = df_orders[df_orders["狀態"] != "已收款"]
    if not pending.empty:
        st.dataframe(pending[["訂單編號", "客戶姓名", "地址", "施工師傅", "狀態"]])
        u_id = st.selectbox("選擇欲更新的單號", pending["訂單編號"].tolist())
        u_status = st.selectbox("更新為新狀態", ["備貨中", "施工中", "已完工", "已收款"])
        if st.button("更新狀態"):
            df_orders.loc[df_orders["訂單編號"] == u_id, "狀態"] = u_status
            conn.update(worksheet="訂單資料", data=df_orders)
            st.success("狀態已更新！")
            st.rerun()
    else:
        st.success("目前無進行中工程。")

# --- 功能 4：修改/刪除 ---
elif choice == "🛠️ 修改/刪除訂單":
    st.header("🛠️ 編輯雲端訂單內容")
    if not df_orders.empty:
        edit_id = st.selectbox("請選擇要編輯的訂單", df_orders["訂單編號"].tolist())
        idx = df_orders[df_orders["訂單編號"] == edit_id].index[0]
        row = df_orders.loc[idx]

        with st.form("edit_order"):
            e_name = st.text_input("客戶姓名", value=str(row["客戶姓名"]))
            e_total = st.number_input("總金額", value=float(row["總金額"]))
            e_paid = st.number_input("已收金額", value=float(row["已收金額"]))
            e_wage = st.number_input("師傅工資", value=float(row["師傅工資"]))
            e_content = st.text_area("訂購內容", value=str(row["訂購內容"]))
            
            c1, c2 = st.columns(2)
            if c1.form_submit_button("✅ 儲存修改"):
                df_orders.loc[idx, ["客戶姓名", "總金額", "已收金額", "師傅工資", "訂購內容"]] = \
                    [e_name, e_total, e_paid, e_wage, e_content]
                conn.update(worksheet="訂單資料", data=df_orders)
                st.success("修改成功！")
                st.rerun()
            if c2.form_submit_button("🚨 刪除整筆訂單"):
                df_orders = df_orders.drop(idx)
                # 同步刪除該訂單的採購記錄
                df_purchases = df_purchases[df_purchases["訂單編號"] != edit_id]
                conn.update(worksheet="訂單資料", data=df_orders)
                conn.update(worksheet="採購明細", data=df_purchases)
                st.warning("訂單與相關成本已全數刪除。")
                st.rerun()

# --- 功能 5：損益報表 ---
elif choice == "💰 財務損益報表":
    pwd = st.text_input("請輸入管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 店面損益結算")
        
        # 計算每張單的總成本
        p_agg = df_purchases.groupby("訂單編號")["進貨金額"].sum().reset_index()
        report = pd.merge(df_orders, p_agg, on="訂單編號", how="left").fillna(0)
        
        # 淨利計算公式
        report['淨利'] = report['總金額'] - report['師傅工資'] - report['進貨金額']
        report['待收尾款'] = report['總金額'] - report['已收金額']
        
        # 數據視覺化
        total_rev = report['總金額'].sum()
        total_purchases = report['進貨金額'].sum()
        total_wages = report['師師工資'].sum() if '師師工資' in report else report['師傅工資'].sum()
        total_profit = report['淨利'].sum()

        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("總營業額", f"${total_rev:,.0f}")
        c2.metric("總進貨成本", f"${total_purchases:,.0f}")
        c3.metric("總支付工資", f"${total_wages:,.0f}")
        c4.metric("結算總淨利", f"${total_profit:,.0f}")

        st.divider()
        st.subheader("每一案損益明細")
        st.dataframe(report[["訂單日期", "客戶姓名", "總金額", "進貨金額", "師傅工資", "淨利", "狀態", "待收尾款"]])
        
        st.write("---")
        st.write("### 🧮 淨利計算邏輯說明：")
        st.latex(r"\text{淨利} = \text{總金額} - \text{師傅工資} - \sum(\text{該單所有叫貨金額})")
        
    elif pwd != "":
        st.error("密碼錯誤，無法查看財務報表。")
