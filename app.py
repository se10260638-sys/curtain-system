import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基本設定與清單 ---
st.set_page_config(page_title="窗簾專家管理系統 Pro", layout="wide")
ADMIN_PASSWORD = "8888"

# 師傅清單新增「禾益」
WORKER_GROUPS = {
    "窗簾類": ["小淯", "小林", "承暘", "袁大哥", "禾益", "其他"],
    "壁紙類": ["期", "其他"],
    "地磚地毯類": ["永鑫", "祥", "郭師傅", "其他"],
    "玻璃紙類": ["宏名"],
    "其他施工": ["其他"]
}

VENDOR_DATA = {
    "窗簾布類": ["大晉", "創世紀", "可愛", "程祥", "聚合", "萊茵", "海淇", "凱薩", "德克力", "施小姐"],
    "捲簾五金類": ["彩樺", "和發", "大晉", "萊茵", "可愛", "高仕", "大瀚", "將元", "宏易", "莊小姐"],
    "壁紙類": ["竑美", "優格", "全球", "高仕"],
    "地磚地毯類": ["旺宏", "皇家", "三凱", "富銘"],
    "其他項目": ["其他"]
}

STATUS_OPTIONS = ["已接單", "備貨中", "施工中", "已完工", "已結案"]

# --- 2. 穩定化資料處理 ---
@st.cache_data(ttl=2)
def get_data_from_gsheets(sheet_name):
    conn = st.connection("gsheets", type=GSheetsConnection)
    return conn.read(worksheet=sheet_name)

def clean_id(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def to_int(val):
    try: return int(pd.to_numeric(val, errors='coerce') or 0)
    except: return 0

def load_all():
    try:
        df_o = get_data_from_gsheets("訂單資料")
        df_d = get_data_from_gsheets("採購明細")
        
        if df_o is None or df_o.empty:
            df_o = pd.DataFrame(columns=["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "施工狀態"])
        if df_d is None or df_d.empty:
            df_d = pd.DataFrame(columns=["訂單編號", "類別", "項目名稱", "金額", "日期", "備註"])
            
        if "訂單編號" in df_o.columns: df_o["訂單編號"] = df_o["訂單編號"].apply(clean_id)
        if "訂單編號" in df_d.columns: df_d["訂單編號"] = df_d["訂單編號"].apply(clean_id)
        
        # 轉換日期格式以便分類
        df_o['訂單日期'] = pd.to_datetime(df_o['訂單日期'], errors='coerce')
        df_o['年份'] = df_o['訂單日期'].dt.year.fillna(datetime.now().year).astype(int)
        df_o['月份'] = df_o['訂單日期'].dt.month.fillna(datetime.now().month).astype(int)
        
        return df_o, df_d
    except Exception as e:
        st.error(f"❌ 連線失敗：{e}")
        return pd.DataFrame(), pd.DataFrame()

df_orders, df_details = load_all()

# --- 3. 功能選單 ---
st.sidebar.title("🏮 窗簾經營管理中心")
choice = st.sidebar.selectbox("功能導覽", ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 損益中心"])

# --- 功能 1：客戶資料卡 (新增月份分類) ---
if choice == "📇 客戶資料卡":
    st.header("📇 客戶資料卡管理")
    
    if not df_orders.empty:
        # 月份篩選器
        col_f1, col_f2 = st.columns([1, 2])
        filter_y = col_f1.selectbox("年份篩選", sorted(df_orders['年份'].unique().tolist(), reverse=True))
        filter_m = col_f2.selectbox("月份篩選", list(range(1, 13)), index=datetime.now().month-1)
        
        # 根據月份過濾後的清單
        filtered_df = df_orders[(df_orders['年份'] == filter_y) & (df_orders['月份'] == filter_m)]
        
        if not filtered_df.empty:
            search_list = filtered_df.apply(lambda r: f"{r['客戶姓名']} | {r['地址']} |ID| {r['訂單編號']}", axis=1).tolist()
            sel_str = st.selectbox("🔍 請選取客戶：", search_list)
            target_oid = clean_id(sel_str.split("|ID|")[-1])
            order_idx = df_orders[df_orders["訂單編號"] == target_oid].index[0]
            curr_order = df_orders.loc[order_idx]

            with st.form("edit_customer_form"):
                st.subheader(f"🛠️ 資料修改：{target_oid}")
                c1, c2, c3 = st.columns(3)
                u_name = c1.text_input("客戶姓名", value=str(curr_order.get('客戶姓名', '')))
                u_phone = c1.text_input("電話", value=str(curr_order.get('電話', '')))
                
                # 新增訂購日期修改
                orig_date = curr_order['訂單日期'] if pd.notnull(curr_order['訂單日期']) else datetime.now()
                u_date = c2.date_input("訂購日期", value=orig_date)
                u_addr = c2.text_input("施工地址", value=str(curr_order.get('地址', '')))
                
                u_total = c3.number_input("總金額", value=to_int(curr_order.get('總金額', 0)))
                u_paid = c3.number_input("已收訂金", value=to_int(curr_order.get('已收金額', 0)))
                u_status = st.selectbox("施工狀態", STATUS_OPTIONS, index=STATUS_OPTIONS.index(curr_order['施工狀態']) if curr_order.get('施工狀態') in STATUS_OPTIONS else 0)
                u_content = st.text_area("📦 訂購內容", value=str(curr_order.get('訂購內容', '')))
                
                if st.form_submit_button("💾 儲存修改"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_orders.loc[order_idx, ["客戶姓名", "電話", "訂單日期", "地址", "總金額", "已收金額", "施工狀態", "訂購內容"]] = \
                        [u_name, u_phone, str(u_date), u_addr, u_total, u_paid, u_status, u_content]
                    conn.update(worksheet="訂單資料", data=df_orders)
                    st.success("更新成功！"); st.cache_data.clear(); st.rerun()
            
            # (明細顯示與新增邏輯與先前相同...)
            st.divider()
            st.subheader("📋 施工與叫貨明細")
            sub_df = df_details[df_details["訂單編號"] == target_oid].copy()
            if not sub_df.empty:
                st.table(sub_df[["類別", "項目名稱", "金額", "日期", "備註"]].assign(金額=lambda x: x['金額'].map('{:,.0f}'.format)))
                if st.button("🗑️ 刪除最後一筆明細"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_details_new = df_details.drop(sub_df.index[-1])
                    conn.update(worksheet="採購明細", data=df_details_new)
                    st.cache_data.clear(); st.rerun()
            
            # 新增明細表單
            st.write("#### ➕ 新增明細")
            item_type = st.radio("類型：", ["廠商叫貨", "師傅工資"], horizontal=True)
            sel_cat = st.selectbox("類別", list(VENDOR_DATA.keys()) if item_type == "廠商叫貨" else list(WORKER_GROUPS.keys()))
            sel_list = VENDOR_DATA[sel_cat] if item_type == "廠商叫貨" else WORKER_GROUPS[sel_cat]
            with st.form("add_det", clear_on_submit=True):
                f_name = st.selectbox("名稱", sel_list + ["其他"])
                if f_name == "其他": f_name = st.text_input("手打名稱")
                f_amt = st.number_input("金額", min_value=0)
                f_dt = st.date_input("日期", value=datetime.now())
                if st.form_submit_button("確認加入"):
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    new_row = pd.DataFrame([{"訂單編號": target_oid, "類別": "師傅工資" if item_type == "師傅工資" else sel_cat, "項目名稱": f_name, "金額": int(f_amt), "日期": str(f_dt)}])
                    conn.update(worksheet="採購明細", data=pd.concat([df_details, new_row], ignore_index=True))
                    st.cache_data.clear(); st.rerun()
        else:
            st.info(f"📅 {filter_y}年{filter_m}月 尚無客戶訂單。")

# --- 功能 2：新增訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 新客戶建檔")
    with st.form("new_order_main", clear_on_submit=True):
        oid = st.text_input("訂單編號*", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
        n_name = st.text_input("客戶姓名*")
        n_phone = st.text_input("聯絡電話")
        n_date = st.date_input("訂購日期", value=datetime.now())
        n_addr = st.text_input("施工地址*")
        n_total = st.number_input("總合約金額", min_value=0)
        n_content = st.text_area("訂購內容備註")
        if st.form_submit_button("✅ 建立訂單"):
            conn = st.connection("gsheets", type=GSheetsConnection)
            new_row = pd.DataFrame([{
                "訂單編號": clean_id(oid), "訂單日期": str(n_date), "客戶姓名": n_name, 
                "電話": n_phone, "地址": n_addr, "總金額": n_total, "已收金額": 0, "施工狀態": "已接單", "訂購內容": n_content
            }])
            conn.update(worksheet="訂單資料", data=pd.concat([df_orders, new_row], ignore_index=True))
            st.success("建檔成功！"); st.cache_data.clear()

# --- 功能 3：損益中心 (維持原本大表格與月份統計) ---
elif choice == "💰 損益中心":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 經營損益報表")
        col_y, col_m = st.columns(2)
        rpt_y = col_y.selectbox("報表年份", sorted(df_orders['年份'].unique().tolist(), reverse=True))
        rpt_m = col_m.selectbox("報表月份", list(range(1, 13)), index=datetime.now().month-1)
        
        cost_sum = df_details.groupby("訂單編號")["金額"].sum().reset_index().rename(columns={"金額": "總支出"})
        final_rpt = pd.merge(df_orders, cost_sum, on="訂單編號", how="left").fillna(0)
        final_rpt["淨利"] = final_rpt["總金額"].apply(to_int) - final_rpt["總支出"]
        monthly_df = final_rpt[(final_rpt['年份'] == rpt_y) & (final_rpt['月份'] == rpt_m)]
        
        st.write(f"### 📅 {rpt_y} 年 {rpt_m} 月 經營結算")
        m1, m2, m3 = st.columns(3)
        m1.metric("當月總業績", f"${int(monthly_df['總金額'].sum()):,.0f}")
        m2.metric("當月總支出", f"${int(monthly_df['總支出'].sum()):,.0f}")
        m3.metric("當月總毛利", f"${int(monthly_df['淨利'].sum()):,.0f}")
        
        st.divider()
        st.subheader("📋 當月訂單損益表")
        st.dataframe(monthly_df[["訂單編號", "客戶姓名", "總金額", "總支出", "淨利", "施工狀態"]].style.format({"總金額": "${:,.0f}", "總支出": "${:,.0f}", "淨利": "${:,.0f}"}), use_container_width=True)
