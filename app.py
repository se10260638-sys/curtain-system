import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import re

# --- 1. 基本設定與廠商清單 ---
st.set_page_config(page_title="窗簾專家管理系統 Pro", layout="wide")

ADMIN_PASSWORD = "8888"

# 廠商資料庫連動設定 (老闆提供名單)
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

# 讀取資料
df_orders = load_data("訂單資料", ["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工狀態", "代工師傅"])
df_purchases = load_data("採購明細", ["訂單編號", "廠商類型", "廠商名稱", "進貨金額", "叫貨日期", "備註"])

# 強制數值轉換 (確保整數)
def to_int(val):
    try:
        return int(pd.to_numeric(val, errors='coerce') or 0)
    except:
        return 0

df_orders['總金額'] = df_orders['總金額'].apply(to_int)
df_orders['已收金額'] = df_orders['已收金額'].apply(to_int)
df_orders['師傅工資'] = df_orders['師傅工資'].apply(to_int)
df_purchases['進貨金額'] = df_purchases['進貨金額'].apply(to_int)

# 處理日期與分群
df_orders['訂單日期'] = pd.to_datetime(df_orders['訂單日期'], errors='coerce')
df_orders['年份'] = df_orders['訂單日期'].dt.year.fillna(datetime.now().year).astype(int)
df_orders['月份'] = df_orders['訂單日期'].dt.month.fillna(datetime.now().month).astype(int)

# --- 3. 側邊欄導覽 ---
st.sidebar.title("🏮 窗簾經營管理中心")
menu = ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 財務損益報表"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能 1：客戶資料卡 (查看/修改/叫貨管理) ---
if choice == "📇 客戶資料卡":
    st.header("📇 客戶資料與訂單詳情")
    
    if df_orders.empty:
        st.info("目前尚無客戶資料。")
    else:
        # --- 年月份篩選 ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 時間篩選")
        years = sorted(df_orders['年份'].unique().tolist(), reverse=True)
        sel_year = st.sidebar.selectbox("1. 選擇年份", years)
        months = sorted(df_orders[df_orders['年份'] == sel_year]['月份'].unique().tolist(), reverse=True)
        sel_month = st.sidebar.selectbox("2. 選擇月份", months)
        
        filtered_df = df_orders[(df_orders['年份'] == sel_year) & (df_orders['月份'] == sel_month)]
        
        if filtered_df.empty:
            st.warning(f"⚠️ {sel_year}年{sel_month}月無資料")
        else:
            search_list = filtered_df.apply(lambda r: f"{r['客戶姓名']} | {r['地址']}", axis=1).tolist()
            sel_client_str = st.selectbox(f"🔍 請選擇客戶：", search_list)
            
            target_name = sel_client_str.split(" | ")[0]
            target_addr = sel_client_str.split(" | ")[1]
            client_order = filtered_df[(filtered_df["客戶姓名"] == target_name) & (filtered_df["地址"] == target_addr)].iloc[0]
            order_id = client_order["訂單編號"]
            main_idx = df_orders[df_orders["訂單編號"] == order_id].index[0]

            # --- A. 修改客戶訂單資料表單 ---
            with st.form("edit_order_form"):
                st.subheader("🛠️ 修改基本資料")
                col1, col2 = st.columns(2)
                with col1:
                    u_name = st.text_input("客戶姓名", value=str(client_order['客戶姓名']))
                    u_phone = st.text_input("聯絡電話 (自動過濾符號)", value=re.sub(r'\D', '', str(client_order['電話'])))
                    u_addr = st.text_input("施工地址", value=str(client_order['地址']))
                    st_idx = STATUS_OPTIONS.index(client_order['施工狀態']) if client_order['施工狀態'] in STATUS_OPTIONS else 0
                    u_status = st.selectbox("施工進度", STATUS_OPTIONS, index=st_idx)
                with col2:
                    u_total = st.number_input("訂單總金額", value=int(client_order['總金額']), step=1)
                    u_paid = st.number_input("已收金額", value=int(client_order['已收金額']), step=1)
                    u_wage = st.number_input("代工工資", value=int(client_order['師傅工資']), step=1)
                    wk_idx = WORKERS.index(client_order['代工師傅']) if client_order['代工師傅'] in WORKERS else 0
                    u_worker = st.selectbox("指定代工師傅", WORKERS, index=wk_idx)
                
                u_content = st.text_area("訂購內容", value=str(client_order['訂購內容']), height=100)
                
                if st.form_submit_button("✅ 儲存資料修改"):
                    df_orders.loc[main_idx, ["客戶姓名", "電話", "地址", "施工狀態", "總金額", "已收金額", "師傅工資", "代工師傅", "訂購內容"]] = \
                        [u_name, re.sub(r'\D', '', u_phone), u_addr, u_status, int(u_total), int(u_paid), int(u_wage), u_worker, u_content]
                    df_save = df_orders.drop(columns=['年份', '月份']).copy()
                    df_save['訂單日期'] = df_save['訂單日期'].dt.strftime('%Y-%m-%d')
                    conn.update(worksheet="訂單資料", data=df_save)
                    st.success("雲端資料已成功更新！")
                    st.rerun()

            st.divider()

            # --- B. 叫貨明細管理 (含修改打錯功能) ---
            st.subheader("📦 叫貨明細管理")
            this_p = df_purchases[df_purchases["訂單編號"] == order_id].copy()
            
            if not this_p.empty:
                # 顯示表格 (整數化格式)
                st.table(this_p[["廠商名稱", "項目分類", "進貨金額", "叫貨日期", "備註"]].assign(進貨金額=lambda x: x['進貨金額'].map('{:,.0f}'.format)))
                st.write(f"**累計材料成本：${int(this_p['進貨金額'].sum()):,.0f}**")
                
                # 修改/刪除特定叫貨紀錄
                with st.expander("📝 修改或刪除叫貨記錄"):
                    p_edit_list = this_p.index.tolist()
                    sel_p_idx = st.selectbox("請選擇要修正的記錄：", p_edit_list, format_func=lambda i: f"{this_p.loc[i, '廠商名稱']} | 金額:{this_p.loc[i, '進貨金額']}")
                    
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        new_p_cost = st.number_input("修正金額", value=int(this_p.loc[sel_p_idx, '進貨金額']), step=1)
                    with ec2:
                        new_p_note = st.text_input("修正備註", value=str(this_p.loc[sel_p_idx, '備註']))
                    
                    b1, b2 = st.columns(2)
                    if b1.button("💾 儲存此進貨修改"):
                        df_purchases.loc[sel_p_idx, ["進貨金額", "備註"]] = [int(new_p_cost), new_p_note]
                        conn.update(worksheet="採購明細", data=df_purchases)
                        st.success("進貨紀錄已修正！")
                        st.rerun()
                    if b2.button("🗑️ 刪除此進貨紀錄"):
                        df_purchases = df_purchases.drop(sel_p_idx)
                        conn.update(worksheet="採購明細", data=df_purchases)
                        st.warning("進貨紀錄已刪除。")
                        st.rerun()
            else:
                st.caption("目前暫無叫貨記錄。")

            # 新增叫貨 (連動選單)
            with st.expander("➕ 新增一筆叫貨"):
                p_t = st.selectbox("選擇類別", list(VENDOR_DATA.keys()))
                p_v = st.selectbox("選擇廠商", VENDOR_DATA[p_t] + ["其他"])
                final_v = p_v if p_v != "其他" else st.text_input("輸入自訂廠商名稱")
                p_c = st.number_input("金額 (整數)", min_value=0, step=1)
                p_n = st.text_input("叫貨備註")
                if st.button("確認新增叫貨"):
                    new_p = pd.DataFrame([{"訂單編號": order_id, "廠商類型": p_t, "廠商名稱": final_v, "進貨金額": int(p_c), "叫貨日期": str(datetime.now().date()), "備註": p_n}])
                    conn.update(worksheet="採購明細", data=pd.concat([df_purchases, new_p], ignore_index=True))
                    st.success("進貨成功登記！")
                    st.rerun()

            st.divider()
            if st.button("🚨 刪除整筆客戶訂單"):
                df_save = df_orders.drop(main_idx).drop(columns=['年份', '月份'])
                df_save['訂單日期'] = df_save['訂單日期'].dt.strftime('%Y-%m-%d')
                p_save = df_purchases[df_purchases["訂單編號"] != order_id]
                conn.update(worksheet="訂單資料", data=df_save)
                conn.update(worksheet="採購明細", data=p_save)
                st.warning("客戶資料已全數移除。")
                st.rerun()

# --- 功能 2：新增客戶訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 建立新客戶資料卡")
    with st.form("new_order_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            n_name = st.text_input("客戶姓名*")
            n_phone = st.text_input("聯絡電話 (純數字)")
            n_address = st.text_input("施工地址*")
        with col2:
            n_total = st.number_input("訂單總金額", min_value=0, step=1)
            n_paid = st.number_input("已付訂金", min_value=0, step=1)
            n_worker = st.selectbox("指定師傅", WORKERS)
        n_content = st.text_area("訂購內容細節")
        
        if st.form_submit_button("✅ 確認建檔"):
            if not n_name or not n_address:
                st.error("姓名與地址不能留空！")
            else:
                new_oid = f"ORD{datetime.now().strftime('%m%d%H%M%S')}"
                new_row = pd.DataFrame([{
                    "訂單編號": new_oid, "訂單日期": str(datetime.now().date()), "客戶姓名": n_name,
                    "電話": re.sub(r'\D', '', n_phone), "地址": n_address, "訂購內容": n_content,
                    "總金額": int(n_total), "已收金額": int(n_paid), "師傅工資": 0, "施工狀態": "已接單", "代工師傅": n_worker
                }])
                df_save = pd.concat([df_orders, new_row], ignore_index=True).drop(columns=['年份', '月份'], errors='ignore')
                df_save['訂單日期'] = pd.to_datetime(df_save['訂單日期']).dt.strftime('%Y-%m-%d')
                conn.update(worksheet="訂單資料", data=df_save)
                st.success("客戶資料已成功建檔！")

# --- 功能 3：財務損益報表 ---
elif choice == "💰 財務損益報表":
    pwd = st.text_input("請輸入管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 經營損益分析報表")
        # 計算每筆訂單的總進貨
        p_sum = df_purchases.groupby("訂單編號")["進貨金額"].sum().reset_index()
        report = pd.merge(df_orders, p_sum, on="訂單編號", how="left").fillna(0)
        report['淨利'] = report['總金額'] - report['師傅工資'] - report['進貨金額']

        col1, col2, col3 = st.columns(3)
        col1.metric("歷史總營業額", f"${int(report['總金額'].sum()):,.0f}")
        col2.metric("累積總支出", f"${int(report['師傅工資'].sum() + report['進貨金額'].sum()):,.0f}")
        col3.metric("結算總淨利", f"${int(report['淨利'].sum()):,.0f}")

        st.divider()
        st.dataframe(report[["客戶姓名", "總金額", "進貨金額", "師傅工資", "淨利", "施工狀態"]].style.format({
            "總金額": "{:,.0f}", "進貨金額": "{:,.0f}", "師傅工資": "{:,.0f}", "淨利": "{:,.0f}"
        }))
        }))
