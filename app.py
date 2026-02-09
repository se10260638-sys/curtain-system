import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基本設定與專業師傅名單 ---
st.set_page_config(page_title="窗簾專家管理系統 Pro", layout="wide")
ADMIN_PASSWORD = "8888"

# 依照類別細分師傅名單
WORKER_GROUPS = {
    "窗簾類": ["小淯", "小林", "承暘", "袁大哥", "其他"],
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
    "木地板": ["其他"],
    "表布代工": ["禾益"],
}

STATUS_OPTIONS = ["已接單", "備貨中", "施工中", "已完工", "已結案"]

# --- 2. 連線與讀取 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def fix_format(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def to_int(val):
    try: return int(pd.to_numeric(val, errors='coerce') or 0)
    except: return 0

def load_data(sheet_name, cols):
    try:
        df = conn.read(worksheet=sheet_name, ttl=0)
        if df is None or df.empty: return pd.DataFrame(columns=cols)
        for col in cols:
            if col not in df.columns: df[col] = ""
        if "訂單編號" in df.columns: df["訂單編號"] = df["訂單編號"].apply(fix_format)
        if "電話" in df.columns: df["電話"] = df["電話"].apply(fix_format)
        return df
    except:
        return pd.DataFrame(columns=cols)

# 讀取資料
df_orders = load_data("訂單資料", ["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工狀態", "代工師傅", "施工類別"])
df_purchases = load_data("採購明細", ["訂單編號", "廠商類型", "廠商名稱", "進貨金額", "叫貨日期", "備註"])

# 強制整數化
df_orders['總金額'] = df_orders['總金額'].apply(to_int)
df_orders['已收金額'] = df_orders['已收金額'].apply(to_int)
df_orders['師傅工資'] = df_orders['師傅工資'].apply(to_int)
df_purchases['進貨金額'] = df_purchases['進貨金額'].apply(to_int)

# 日期處理
df_orders['訂單日期'] = pd.to_datetime(df_orders['訂單日期'], errors='coerce')
df_orders['年份'] = df_orders['訂單日期'].dt.year.fillna(datetime.now().year).astype(int)
df_orders['月份'] = df_orders['訂單日期'].dt.month.fillna(datetime.now().month).astype(int)

# --- 3. 側邊欄導覽 ---
st.sidebar.title("🏮 窗簾經營管理中心")
choice = st.sidebar.selectbox("切換功能", ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 損益與採購分析"])

# --- 功能 1：客戶資料卡 ---
if choice == "📇 客戶資料卡":
    st.header("📇 客戶資料管理")
    if df_orders.empty:
        st.info("目前尚無資料。")
    else:
        years = sorted(df_orders['年份'].unique().tolist(), reverse=True)
        sel_year = st.sidebar.selectbox("年份", years)
        months = sorted(df_orders[df_orders['年份'] == sel_year]['月份'].unique().tolist(), reverse=True)
        sel_month = st.sidebar.selectbox("月份", months)
        
        filtered_df = df_orders[(df_orders['年份'] == sel_year) & (df_orders['月份'] == sel_month)]
        
        if filtered_df.empty:
            st.warning(f"{sel_year} 年 {sel_month} 月無資料。")
        else:
            search_list = filtered_df.apply(lambda r: f"{r['客戶姓名']} | {r['地址']} |ID|{r['訂單編號']}", axis=1).tolist()
            sel_client_str = st.selectbox("🔍 請選擇客戶：", search_list)
            target_oid = sel_client_str.split("|ID|")[-1] 
            matches = df_orders[df_orders["訂單編號"] == target_oid]
            
            if not matches.empty:
                client_order = matches.iloc[0]
                main_idx = matches.index[0]

                with st.form("edit_form"):
                    st.subheader(f"🛠️ 修改訂單: {target_oid}")
                    new_date = st.date_input("訂單日期", value=client_order['訂單日期'])
                    c1, c2 = st.columns(2)
                    with c1:
                        u_name = st.text_input("客戶姓名", value=str(client_order['客戶姓名']))
                        u_phone = st.text_input("聯絡電話", value=str(client_order['電話']))
                        u_addr = st.text_input("施工地址", value=str(client_order['地址']))
                        s_idx = STATUS_OPTIONS.index(client_order['施工狀態']) if client_order['施工狀態'] in STATUS_OPTIONS else 0
                        u_status = st.selectbox("施工進度", STATUS_OPTIONS, index=s_idx)
                    with c2:
                        # 師傅分類連動修改
                        old_cat = client_order['施工類別'] if client_order['施工類別'] in WORKER_GROUPS else "窗簾類"
                        u_cat = st.selectbox("施工類別", list(WORKER_GROUPS.keys()), index=list(WORKER_GROUPS.keys()).index(old_cat))
                        u_worker = st.selectbox("代工師傅", WORKER_GROUPS[u_cat], 
                                               index=WORKER_GROUPS[u_cat].index(client_order['代工師傅']) if client_order['代工師傅'] in WORKER_GROUPS[u_cat] else 0)
                        u_wage = st.number_input("師傅工資", value=int(client_order['師傅工資']), step=1)
                        u_total = st.number_input("總金額", value=int(client_order['總金額']), step=1)
                        u_paid = st.number_input("已收金額", value=int(client_order['已收金額']), step=1)
                    
                    u_content = st.text_area("訂購內容", value=str(client_order['訂購內容']))
                    
                    if st.form_submit_button("✅ 儲存修改"):
                        df_orders.loc[main_idx, ["訂單日期", "客戶姓名", "電話", "地址", "施工狀態", "總金額", "已收金額", "師傅工資", "代工師傅", "訂購內容", "施工類別"]] = \
                            [str(new_date), u_name, str(u_phone), u_addr, u_status, int(u_total), int(u_paid), int(u_wage), u_worker, u_content, u_cat]
                        df_save = df_orders.drop(columns=['年份', '月份']).copy()
                        df_save['訂單日期'] = pd.to_datetime(df_save['訂單日期']).dt.strftime('%Y-%m-%d')
                        conn.update(worksheet="訂單資料", data=df_save)
                        st.success("更新成功！"); st.rerun()

                st.divider()
                st.subheader("📦 叫貨紀錄")
                this_p = df_purchases[df_purchases["訂單編號"] == target_oid].reset_index()
                if not this_p.empty:
                    st.table(this_p[["廠商類型", "廠商名稱", "進貨金額", "叫貨日期", "備註"]].assign(進貨金額=lambda x: x['進貨金額'].map('{:,.0f}'.format)))
                with st.expander("➕ 新增叫貨"):
                    pt = st.selectbox("類別", list(VENDOR_DATA.keys()))
                    pv = st.selectbox("廠商名", VENDOR_DATA[pt] + ["其他"])
                    final_v = pv if pv != "其他" else st.text_input("輸入名稱")
                    pc = st.number_input("金額", min_value=0, step=1)
                    p_date = st.date_input("叫貨日期", value=datetime.now())
                    if st.button("確認新增"):
                        new_p = pd.DataFrame([{"訂單編號": target_oid, "廠商類型": pt, "廠商名稱": final_v, "進貨金額": int(pc), "叫貨日期": str(p_date), "備註": ""}])
                        conn.update(worksheet="採購明細", data=pd.concat([df_purchases, new_p], ignore_index=True))
                        st.success("已新增！"); st.rerun()

# --- 功能 2：新增客戶訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 建立新客戶資料")
    with st.form("new_order", clear_on_submit=True):
        n_date = st.date_input("訂單日期", value=datetime.now())
        oid = st.text_input("訂單編號 (手寫單號)*", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
        
        c1, c2 = st.columns(2)
        with c1:
            n_name = st.text_input("客戶姓名*")
            n_phone = st.text_input("聯絡電話")
            n_addr = st.text_input("施工地址*")
        with c2:
            n_cat = st.selectbox("施工類別", list(WORKER_GROUPS.keys()))
            n_worker = st.selectbox("指定師傅", WORKER_GROUPS[n_cat])
            n_wage = st.number_input("預估工資", min_value=0, step=1)
            n_total = st.number_input("總金額", min_value=0, step=1)
            n_paid = st.number_input("訂金", min_value=0, step=1)
        
        n_content = st.text_area("訂購內容")
        
        if st.form_submit_button("✅ 儲存建檔"):
            if not n_name or not n_addr or not oid:
                st.error("必填項未填！")
            else:
                new_row = pd.DataFrame([{
                    "訂單編號": str(oid), "訂單日期": str(n_date), "客戶姓名": n_name, "電話": str(n_phone), "地址": n_addr, 
                    "訂購內容": n_content, "總金額": int(n_total), "已收金額": int(n_paid), "師傅工資": int(n_wage), 
                    "施工狀態": "已接單", "代工師傅": n_worker, "施工類別": n_cat
                }])
                df_s = pd.concat([df_orders, new_row], ignore_index=True).drop(columns=['年份', '月份'], errors='ignore')
                df_s['訂單日期'] = pd.to_datetime(df_s['訂單日期']).dt.strftime('%Y-%m-%d')
                conn.update(worksheet="訂單資料", data=df_s)
                st.success(f"存入成功！")

# --- 功能 3：損益與採購分析 ---
elif choice == "💰 損益與採購分析":
    pwd = st.text_input("請輸入管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 經營分析報表")
        
        col_y, col_m = st.columns(2)
        rpt_y = col_y.selectbox("報表年份", sorted(df_orders['年份'].unique().tolist(), reverse=True))
        rpt_m = col_m.selectbox("報表月份", list(range(1, 13)), index=datetime.now().month-1)
        
        # 建立當月資料
        p_sum = df_purchases.groupby("訂單編號")["進貨金額"].sum().reset_index()
        p_sum["訂單編號"] = p_sum["訂單編號"].apply(fix_format)
        full_rpt = pd.merge(df_orders, p_sum, on="訂單編號", how="left").fillna(0)
        full_rpt['淨利'] = full_rpt['總金額'] - full_rpt['師傅工資'] - full_rpt['進貨金額']
        
        monthly_rpt = full_rpt[(full_rpt['年份'] == rpt_y) & (full_rpt['月份'] == rpt_m)]
        
        m1, m2, m3 = st.columns(3)
        m1.metric(f"{rpt_m}月 總業績", f"${int(monthly_rpt['總金額'].sum()):,.0f}")
        m2.metric(f"{rpt_m}月 總支出(含工資)", f"${int(monthly_rpt['師傅工資'].sum() + monthly_rpt['進貨金額'].sum()):,.0f}")
        m3.metric(f"{rpt_m}月 總淨利", f"${int(monthly_rpt['淨利'].sum()):,.0f}")
        
        st.divider()
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader(f"👷 {rpt_m}月 師傅工資清款單")
            if not monthly_rpt.empty:
                worker_pay = monthly_rpt.groupby("代工師傅")["師傅工資"].sum().reset_index()
                worker_pay = worker_pay[worker_pay["師傅工資"] > 0].sort_values(by="師傅工資", ascending=False)
                st.dataframe(worker_pay.style.format({"師傅工資": "${:,.0f}"}), use_container_width=True)
            else:
                st.write("本月無工資。")
        
        with col_b:
            st.subheader(f"🏢 {rpt_m}月 廠商採購統計")
            df_purchases['叫貨日期'] = pd.to_datetime(df_purchases['叫貨日期'])
            p_filtered = df_purchases[(df_purchases['叫貨日期'].dt.year == rpt_y) & (df_purchases['叫貨日期'].dt.month == rpt_m)]
            if not p_filtered.empty:
                v_stats = p_filtered.groupby("廠商名稱")["進貨金額"].sum().reset_index().sort_values(by="進貨金額", ascending=False)
                st.dataframe(v_stats.style.format({"進貨金額": "${:,.0f}"}), use_container_width=True)
            else:
                st.write("本月無採購。")
            
        st.divider()
        st.subheader(f"📝 {rpt_m}月 客戶損益明細")
        st.dataframe(monthly_rpt[["訂單編號", "客戶姓名", "總金額", "進貨金額", "師傅工資", "淨利", "施工狀態", "代工師傅"]].style.format({"總金額": "{:,.0f}", "進貨金額": "{:,.0f}", "師傅工資": "{:,.0f}", "淨利": "{:,.0f}"}))
