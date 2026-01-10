import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import re

# --- 1. 基本設定與廠商清單 ---
st.set_page_config(page_title="窗簾專家管理系統 Pro", layout="wide")

ADMIN_PASSWORD = "8888"

VENDOR_DATA = {
    "窗簾布類": ["大晉", "創世紀", "可愛", "程祥", "聚合", "萊茵", "海淇", "凱薩", "德克力", "施小姐"],
    "捲簾五金類": ["彩樺", "和發", "大晉", "萊茵", "可愛", "高仕", "大瀚", "將元", "宏易", "莊小姐"],
    "壁紙類": ["竑美", "優格", "全球", "高仕"],
    "地磚地毯類": ["旺宏", "皇家", "三凱", "富銘"],
    "木地板": ["其他"],
    "表布代工": ["禾益"],
}
WORKERS = ["小淯", "小林", "阿期", "小鑫", "小祥", "其他"]
STATUS_OPTIONS = ["已接單", "備貨中", "施工中", "已完工", "已結案"]

# --- 2. 雲端連線與讀取 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data(sheet_name, cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl="0s")
        if df is None or df.empty:
            return pd.DataFrame(columns=cols)
        for col in cols:
            if col not in df.columns:
                df[col] = ""
        return df
    except:
        return pd.DataFrame(columns=cols)

df_orders = load_data("訂單資料", ["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工狀態", "代工師傅"])
df_purchases = load_data("採購明細", ["訂單編號", "廠商類型", "廠商名稱", "進貨金額", "叫貨日期", "備註"])

# 強制整數化
def to_int(val):
    try:
        return int(pd.to_numeric(val, errors='coerce') or 0)
    except:
        return 0

df_orders['總金額'] = df_orders['總金額'].apply(to_int)
df_orders['已收金額'] = df_orders['已收金額'].apply(to_int)
df_orders['師傅工資'] = df_orders['師傅工資'].apply(to_int)
df_purchases['進貨金額'] = df_purchases['進貨金額'].apply(to_int)

df_orders['訂單日期'] = pd.to_datetime(df_orders['訂單日期'], errors='coerce')
df_orders['年份'] = df_orders['訂單日期'].dt.year.fillna(datetime.now().year).astype(int)
df_orders['月份'] = df_orders['訂單日期'].dt.month.fillna(datetime.now().month).astype(int)

# --- 3. 側邊欄導覽 ---
st.sidebar.title("🏮 窗簾經營管理中心")
menu = ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 財務損益報表"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能 1：客戶資料卡 ---
if choice == "📇 客戶資料卡":
    st.header("📇 客戶資料管理中心")
    
    if df_orders.empty:
        st.info("目前尚無客戶資料。")
    else:
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 時間快速篩選")
        years = sorted(df_orders['年份'].unique().tolist(), reverse=True)
        selected_year = st.sidebar.selectbox("1. 選擇年份", years)
        months = sorted(df_orders[df_orders['年份'] == selected_year]['月份'].unique().tolist(), reverse=True)
        selected_month = st.sidebar.selectbox("2. 選擇月份", months)
        
        filtered_df = df_orders[(df_orders['年份'] == selected_year) & (df_orders['月份'] == selected_month)]
        
        if filtered_df.empty:
            st.warning(f"⚠️ {selected_year} 年 {selected_month} 月查無資料。")
        else:
            search_list = filtered_df.apply(lambda r: f"{r['客戶姓名']} | {r['地址']}", axis=1).tolist()
            selected_client_str = st.selectbox(f"🔍 請選擇客戶：", search_list)
            
            target_name = selected_client_str.split(" | ")[0]
            target_address = selected_client_str.split(" | ")[1]
            client_order = filtered_df[(filtered_df["客戶姓名"] == target_name) & (filtered_df["地址"] == target_address)].iloc[0]
            order_id = client_order["訂單編號"]
            idx = df_orders[df_orders["訂單編號"] == order_id].index[0]

            with st.form("edit_client_form"):
                st.subheader("🛠️ 修改客戶與訂單資料")
                col1, col2 = st.columns(2)
                with col1:
                    u_name = st.text_input("客戶姓名", value=str(client_order['客戶姓名']))
                    u_phone = st.text_input("聯絡電話", value=re.sub(r'\D', '', str(client_order['電話'])))
                    u_addr = st.text_input("施工地址", value=str(client_order['地址']))
                    status_idx = STATUS_OPTIONS.index(client_order['施工狀態']) if client_order['施工狀態'] in STATUS_OPTIONS else 0
                    u_status = st.selectbox("施工進度", STATUS_OPTIONS, index=status_idx)
                with col2:
                    u_total = st.number_input("訂單總金額", value=int(client_order['總金額']), step=1)
                    u_paid = st.number_input("已收金額", value=int(client_order['已收金額']), step=1)
                    u_wage = st.number_input("代工師傅工資", value=int(client_order['師傅工資']), step=1)
                    worker_idx = WORKERS.index(client_order['代工師傅']) if client_order['代工師傅'] in WORKERS else 0
                    u_worker = st.selectbox("指定代工師傅", WORKERS, index=worker_idx)
                u_content = st.text_area("訂購內容", value=str(client_order['訂購內容']), height=100)
                
                if st.form_submit_button("✅ 儲存修改內容"):
                    df_orders.loc[idx, ["客戶姓名", "電話", "地址", "施工狀態", "總金額", "已收金額", "師傅工資", "代工師傅", "訂購內容"]] = \
                        [u_name, u_phone, u_addr, u_status, int(u_total), int(u_paid), int(u_wage), u_worker, u_content]
                    df_save = df_orders.drop(columns=['年份', '月份']).copy()
                    df_save['訂單日期'] = df_save['訂單日期'].dt.strftime('%Y-%m-%d')
                    conn.update(worksheet="訂單資料", data=df_save)
                    st.success("訂單修改成功！")
                    st.rerun()

            st.divider()
            
            # --- 叫貨明細與修改區塊 ---
            st.subheader("📦 叫貨明細管理")
            this_p = df_purchases[df_purchases["訂單編號"] == order_id].reset_index()
            
            if not this_p.empty:
                st.table(this_p[["廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"]].assign(進貨金額=lambda x: x['進貨金額'].map('{:,.0f}'.format)))
                
                # --- 修改/刪除特定叫貨單 ---
                with st.expander("🛠️ 修改或刪除叫貨明細"):
                    p_to_edit_idx = st.selectbox("選擇要處理的叫貨記錄：", this_p.index, format_func=lambda i: f"{this_p.loc[i, '廠商名稱']} - {this_p.loc[i, '進貨金額']}")
                    original_idx = this_p.loc[p_to_edit_idx, 'index'] # 抓回在原本 df_purchases 的位置
                    
                    edit_col1, edit_col2 = st.columns(2)
                    with edit_col1:
                        new_p_cost = st.number_input("修改金額", value=int(this_p.loc[p_to_edit_idx, '進貨金額']), step=1)
                    with edit_col2:
                        new_p_note = st.text_input("修改備註", value=str(this_p.loc[p_to_edit_idx, '備註']))
                    
                    b1, b2 = st.columns(2)
                    if b1.button("💾 儲存此筆叫貨修改"):
                        df_purchases.loc[original_idx, ["進貨金額", "備註"]] = [int(new_p_cost), new_p_note]
                        conn.update(worksheet="採購明細", data=df_purchases)
                        st.success("進貨記錄已修正！")
                        st.rerun()
                    if b2.button("🗑️ 刪除此筆叫貨"):
                        df_purchases_new = df_purchases.drop(original_idx)
                        conn.update(worksheet="採購明細", data=df_purchases_new)
                        st.warning("進貨記錄已刪除。")
                        st.rerun()
            else:
                st.caption("目前暫無此訂單的進貨記錄。")

            with st.expander("➕ 新增叫貨"):
                p_type = st.selectbox("類別", list(VENDOR_DATA.keys()))
                p_vendor = st.selectbox("廠商", VENDOR_DATA[p_type] + ["其他"])
                final_v = p_vendor if p_vendor != "其他" else st.text_input("輸入名稱")
                p_cost = st.number_input("金額", min_value=0, step=1)
                p_note = st.text_input("備註")
                if st.button("確認新增叫貨"):
                    new_p = pd.DataFrame([{"訂單編號": order_id, "廠商類型": p_type, "廠商名稱": final_v, "進貨金額": int(p_cost), "叫貨日期": str(datetime.now().date()), "備註": p_note}])
                    conn.update(worksheet="採購明細", data=pd.concat([df_purchases, new_p], ignore_index=True))
                    st.success("進貨已記錄！")
                    st.rerun()

            st.divider()
            if st.button("🚨 刪除整筆客戶訂單 (含所有叫貨記錄)"):
                df_save = df_orders.drop(idx).drop(columns=['年份', '月份'])
                df_save['訂單日期'] = df_save['訂單日期'].dt.strftime('%Y-%m-%d')
                df_purchases_new = df_purchases[df_purchases["訂單編號"] != order_id]
                conn.update(worksheet="訂單資料", data=df_save)
                conn.update(worksheet="採購明細", data=df_purchases_new)
                st.warning("已全數刪除。")
                st.rerun()

# (其餘 新增訂單 與 財務報表 邏輯不變...)
