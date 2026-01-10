import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基本設定與廠商清單 ---
st.set_page_config(page_title="窗簾專家管理系統 Pro", layout="wide")

ADMIN_PASSWORD = "8888"

# 廠商資料庫連動設定
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

# 強制轉換格式與時間處理
df_orders['總金額'] = pd.to_numeric(df_orders['總金額'], errors='coerce').fillna(0)
df_orders['已收金額'] = pd.to_numeric(df_orders['已收金額'], errors='coerce').fillna(0)
df_orders['師傅工資'] = pd.to_numeric(df_orders['師傅工資'], errors='coerce').fillna(0)
df_purchases['進貨金額'] = pd.to_numeric(df_purchases['進貨金額'], errors='coerce').fillna(0)

# 處理日期與分群欄位
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
        # --- 年月份雙層篩選 ---
        st.sidebar.markdown("---")
        st.sidebar.subheader("📅 時間快速篩選")
        
        # 年份選單
        years = sorted(df_orders['年份'].unique().tolist(), reverse=True)
        selected_year = st.sidebar.selectbox("1. 選擇年份", years)
        
        # 根據年份抓取對應的月份
        months = sorted(df_orders[df_orders['年份'] == selected_year]['月份'].unique().tolist(), reverse=True)
        selected_month = st.sidebar.selectbox("2. 選擇月份", months)
        
        # 根據年+月過濾客戶
        filtered_df = df_orders[(df_orders['年份'] == selected_year) & (df_orders['月份'] == selected_month)]
        
        if filtered_df.empty:
            st.warning(f"⚠️ {selected_year} 年 {selected_month} 月查無客戶資料。")
        else:
            search_list = filtered_df.apply(lambda r: f"{r['客戶姓名']} | {r['地址']}", axis=1).tolist()
            selected_client_str = st.selectbox(f"🔍 請選擇客戶 ({selected_year} / {selected_month}月)：", search_list)
            
            # 抓取該客戶資料
            target_name = selected_client_str.split(" | ")[0]
            target_address = selected_client_str.split(" | ")[1]
            client_order = filtered_df[(filtered_df["客戶姓名"] == target_name) & (filtered_df["地址"] == target_address)].iloc[0]
            order_id = client_order["訂單編號"]
            # 找到在原始 df 中的 index 以便修改
            idx = df_orders[df_orders["訂單編號"] == order_id].index[0]

            # --- 顯示與修改區域 ---
            with st.form("edit_client_form"):
                st.subheader("🛠️ 修改客戶與訂單資料")
                col1, col2 = st.columns(2)
                with col1:
                    u_name = st.text_input("客戶姓名", value=str(client_order['客戶姓名']))
                    u_phone = st.text_input("聯絡電話", value=str(client_order['電話']))
                    u_addr = st.text_input("施工地址", value=str(client_order['地址']))
                    status_idx = STATUS_OPTIONS.index(client_order['施工狀態']) if client_order['施工狀態'] in STATUS_OPTIONS else 0
                    u_status = st.selectbox("施工進度", STATUS_OPTIONS, index=status_idx)
                with col2:
                    u_total = st.number_input("訂單總金額", value=float(client_order['總金額']))
                    u_paid = st.number_input("已收金額", value=float(client_order['已收金額']))
                    u_wage = st.number_input("代工師傅工資", value=float(client_order['師傅工資']))
                    worker_idx = WORKERS.index(client_order['代工師傅']) if client_order['代工師傅'] in WORKERS else 0
                    u_worker = st.selectbox("指定代工師傅", WORKERS, index=worker_idx)
                
                u_content = st.text_area("訂購內容", value=str(client_order['訂購內容']), height=150)
                
                c1, c2 = st.columns([1, 1])
                if c1.form_submit_button("✅ 儲存所有修改"):
                    # 準備存檔，排除掉為了 UI 建立的臨時欄位
                    df_to_save = df_orders.copy()
                    df_to_save.loc[idx, ["客戶姓名", "電話", "地址", "施工狀態", "總金額", "已收金額", "師傅工資", "代工師傅", "訂購內容"]] = \
                        [u_name, u_phone, u_addr, u_status, u_total, u_paid, u_wage, u_worker, u_content]
                    
                    # 存檔前轉回字串日期並移除臨時欄位
                    df_to_save['訂單日期'] = df_to_save['訂單日期'].dt.strftime('%Y-%m-%d')
                    final_save_df = df_to_save.drop(columns=['年份', '月份'])
                    conn.update(worksheet="訂單資料", data=final_save_df)
                    st.success("資料已成功更新到雲端！")
                    st.rerun()
                
                if c2.form_submit_button("🚨 刪除此客戶訂單"):
                    df_to_save = df_orders.drop(idx)
                    df_to_save['訂單日期'] = df_to_save['訂單日期'].dt.strftime('%Y-%m-%d')
                    final_save_df = df_to_save.drop(columns=['年份', '月份'])
                    
                    df_purchases_new = df_purchases[df_purchases["訂單編號"] != order_id]
                    
                    conn.update(worksheet="訂單資料", data=final_save_df)
                    conn.update(worksheet="採購明細", data=df_purchases_new)
                    st.warning("已刪除該客戶及其所有進貨記錄。")
                    st.rerun()

            st.divider()

            # --- 叫貨明細區塊 ---
            st.subheader("📦 廠商叫貨明細")
            this_p = df_purchases[df_purchases["訂單編號"] == order_id]
            if not this_p.empty:
                st.table(this_p[["廠商類型", "廠商名稱", "進貨金額", "叫貨日期", "備註"]])
                st.write(f"**總叫貨成本：${this_p['進貨金額'].sum():,.0f}**")
            
            # --- 連動廠商登記 ---
            with st.expander("➕ 新增一筆叫貨記錄 (此訂單)"):
                p_type = st.selectbox("1. 選擇廠商類別", list(VENDOR_DATA.keys()))
                p_vendor_options = VENDOR_DATA[p_type] + ["其他(自行輸入)"]
                p_vendor = st.selectbox("2. 選擇廠商名稱", p_vendor_options)
                
                final_v = p_vendor
                if p_vendor == "其他(自行輸入)":
                    final_v = st.text_input("請輸入自訂廠商名稱")
                
                p_cost = st.number_input("進貨金額", min_value=0)
                p_note = st.text_input("進貨備註 (布號/尺寸)")
                
                if st.button("確認提交進貨登記"):
                    new_p = pd.DataFrame([{"訂單編號": order_id, "廠商類型": p_type, "廠商名稱": final_v, "進貨金額": p_cost, "叫貨日期": str(datetime.now().date()), "備註": p_note}])
                    updated_p = pd.concat([df_purchases, new_p], ignore_index=True)
                    conn.update(worksheet="採購明細", data=updated_p)
                    st.success("進貨記錄已更新！")
                    st.rerun()

# --- 功能 2：新增訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 建立新客戶資料卡")
    with st.form("new_order", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("客戶姓名*")
            c_phone = st.text_input("聯絡電話")
            c_address = st.text_input("施工地址*")
        with col2:
            c_total = st.number_input("訂單金額", min_value=0)
            c_paid = st.number_input("已付金額 (訂金)", min_value=0)
            c_worker = st.selectbox("預計代工師傅", WORKERS)
        
        c_content = st.text_area("訂購詳細內容")
        
        if st.form_submit_button("✅ 存入客戶資料卡"):
            if not c_name or not c_address:
                st.error("姓名與地址為必填項目！")
            else:
                new_id = f"ORD{datetime.now().strftime('%m%d%H%M%S')}" # 加入秒數防止編號重複
                new_row = pd.DataFrame([{
                    "訂單編號": new_id, "訂單日期": str(datetime.now().date()), "客戶姓名": c_name,
                    "電話": c_phone, "地址": c_address, "訂購內容": c_content,
                    "總金額": c_total, "已收金額": c_paid, "師傅工資": 0, "施工狀態": "已接單", "代工師傅": c_worker
                }])
                
                # 存檔處理：確保不包含臨時欄位
                df_to_save = pd.concat([df_orders, new_row], ignore_index=True)
                df_to_save['訂單日期'] = pd.to_datetime(df_to_save['訂單日期']).dt.strftime('%Y-%m-%d')
                if '年份' in df_to_save.columns: df_to_save = df_to_save.drop(columns=['年份', '月份'])
                
                conn.update(worksheet="訂單資料", data=df_to_save)
                st.success("客戶已建檔成功！請至『客戶資料卡』查看。")

# --- 功能 3：財務損益報表 ---
elif choice == "💰 財務損益報表":
    pwd = st.text_input("請輸入管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📈 經營損益分析")
        p_agg = df_purchases.groupby("訂單編號")["進貨金額"].sum().reset_index()
        report = pd.merge(df_orders, p_agg, on="訂單編號", how="left").fillna(0)
        
        # 轉數值計算
        report['總金額'] = report['總金額'].astype(float)
        report['師傅工資'] = report['師傅工資'].astype(float)
        report['進貨金額'] = report['進貨金額'].astype(float)
        report['淨利'] = report['總金額'] - report['師傅工資'] - report['進貨金額']

        col1, col2, col3 = st.columns(3)
        col1.metric("歷史總業績", f"${report['總金額'].sum():,.0f}")
        col2.metric("累積總支出", f"${(report['師傅工資'].sum() + report['進貨金額'].sum()):,.0f}")
        col3.metric("累積總淨利", f"${report['淨利'].sum():,.0f}")

        st.divider()
        st.subheader("每一案損益清單")
        st.dataframe(report[["客戶姓名", "總金額", "進貨金額", "師傅工資", "淨利", "施工狀態"]])
