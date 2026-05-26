import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基本設定與清單資料 ---
st.set_page_config(page_title="窗簾專家管理系統 專業安全版", layout="wide")
ADMIN_PASSWORD = "8888"

# 師傅清單
WORKER_GROUPS = {
    "窗簾類": ["小淯", "小林", "承暘", "袁大哥", "禾益", "其他"],
    "壁紙類": ["期", "其他"],
    "地磚地毯類": ["永鑫", "祥", "郭師傅", "其他"],
    "玻璃紙類": ["宏名"],
    "其他施工": ["其他"]
}

# 廠商清單
VENDOR_DATA = {
    "窗簾布類": ["大晉", "創世紀", "可愛", "程祥", "聚合", "萊茵", "海淇", "凱薩", "德克力", "施小姐"],
    "捲簾五金類": ["彩樺", "和發", "大晉", "萊茵", "可愛", "高仕", "大瀚", "將元", "宏易", "莊小姐"],
    "壁紙類": ["竑美", "優格", "全球", "高仕"],
    "地磚地毯類": ["旺宏", "皇家", "三凱", "富銘"],
    "其他項目": ["其他"]
}

STATUS_OPTIONS = ["已接單", "備貨中", "施工中", "已完工", "已結案"]

# --- 2. 核心資料處理與安全防護 ---
def clean_id(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def to_int(val):
    try: return int(pd.to_numeric(val, errors='coerce') or 0)
    except: return 0

def load_all():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        df_o = conn.read(worksheet="訂單資料", ttl=0)
        df_d = conn.read(worksheet="採購明細", ttl=0)
        
        # 欄位安全檢查
        if df_o is None or df_o.empty:
            df_o = pd.DataFrame(columns=["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "施工狀態"])
        if df_d is None or df_d.empty:
            df_d = pd.DataFrame(columns=["訂單編號", "類別", "項目名稱", "金額", "日期", "備註"])
            
        # 清洗與格式轉換
        df_o["訂單編號"] = df_o["訂單編號"].apply(clean_id)
        if "訂單編號" in df_d.columns:
            df_d["訂單編號"] = df_d["訂單編號"].apply(clean_id)
        
        # 日期索引建立
        df_o['訂單日期'] = pd.to_datetime(df_o['訂單日期'], errors='coerce')
        df_o['年份'] = df_o['訂單日期'].dt.year.fillna(datetime.now().year).astype(int)
        df_o['月份'] = df_o['訂單日期'].dt.month.fillna(datetime.now().month).astype(int)
        
        # 依單號從小到大排序
        df_o = df_o.sort_values(by="訂單編號").reset_index(drop=True)
        return df_o, df_d
    except Exception as e:
        st.error(f"⚠️ 資料讀取異常：{e}")
        return pd.DataFrame(), pd.DataFrame()

# 執行讀取
df_orders, df_details = load_all()

# 安全更新函式
def safe_update(sheet_name, data):
    if data is None or data.empty:
        st.error(f"❌ 警告：嘗試寫入空的資料到 {sheet_name}，系統已自動攔截防止清空資料表！")
        return False
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        conn.update(worksheet=sheet_name, data=data)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ 寫入失敗：{e}")
        return False

# --- 3. 介面導覽 ---
st.sidebar.title("🏮 窗簾經營管理中心")
choice = st.sidebar.selectbox("功能導覽", ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 損益中心"])

# --- 功能 1：客戶資料卡 ---
if choice == "📇 客戶資料卡":
    st.header("📇 客戶資料管理")
    if not df_orders.empty:
        c1, c2 = st.columns([1, 2])
        f_y = c1.selectbox("年份", sorted(df_orders['年份'].unique().tolist(), reverse=True))
        f_m = c2.selectbox("月份", list(range(1, 13)), index=datetime.now().month-1)
        
        f_df = df_orders[(df_orders['年份'] == f_y) & (df_orders['月份'] == f_m)]
        
        if not f_df.empty:
            search_list = f_df.apply(lambda r: f"{r['訂單編號']} | {r['訂單日期'].strftime('%Y/%m/%d') if pd.notnull(r['訂單日期']) else '無日期'} | {r['客戶姓名']} | {r['地址']}", axis=1).tolist()
            sel_str = st.selectbox("🔍 選擇客戶：", search_list)
            this_oid = clean_id(sel_str.split(" | ")[0])
            
            idx = df_orders[df_orders["訂單編號"] == this_oid].index[0]
            curr = df_orders.loc[idx]

            with st.form("edit_form"):
                st.subheader(f"🛠️ 編輯客戶資料 (單號：{this_oid})")
                cl1, cl2, cl3 = st.columns(3)
                u_oid = cl1.text_input("訂單單號", value=str(curr['訂單編號']))
                u_name = cl1.text_input("客戶姓名", value=str(curr.get('客戶姓名', '')))
                u_phone = cl1.text_input("電話", value=str(curr.get('電話', '')))
                
                u_date = cl2.date_input("訂購日期", value=curr['訂單日期'] if pd.notnull(curr['訂單日期']) else datetime.now())
                u_addr = cl2.text_input("施工地址", value=str(curr.get('地址', '')))
                
                u_total = cl3.number_input("總合約金額", value=to_int(curr.get('總金額', 0)))
                u_paid = cl3.number_input("已收訂金", value=to_int(curr.get('已收金額', 0)))
                u_status = cl3.selectbox("狀態", STATUS_OPTIONS, index=STATUS_OPTIONS.index(curr['施工狀態']) if curr['施工狀態'] in STATUS_OPTIONS else 0)
                u_content = st.text_area("📦 訂購內容 (尺寸、材質)", value=str(curr.get('訂購內容', '')))
                
                if st.form_submit_button("💾 儲存所有修改"):
                    # 【核心修復點】：9個欄位對齊9個變數，解決 TypeError
                    df_orders.loc[idx, ["訂單編號", "客戶姓名", "電話", "訂單日期", "地址", "總金額", "已收金額", "施工狀態", "訂購內容"]] = \
                        [u_oid, u_name, u_phone, str(u_date), u_addr, u_total, u_paid, u_status, u_content]
                    
                    if safe_update("訂單資料", df_orders):
                        if u_oid != this_oid:
                            df_details.loc[df_details["訂單編號"] == this_oid, "訂單編號"] = u_oid
                            safe_update("採購明細", df_details)
                        st.success("✅ 修改已儲存！"); st.rerun()

            with st.expander("🔴 刪除整筆訂單"):
                del_pwd = st.text_input("管理密碼", type="password", key="del_pwd")
                if st.button("確認完全刪除此訂單"):
                    if del_pwd == ADMIN_PASSWORD:
                        df_orders = df_orders.drop(idx)
                        df_details = df_details[df_details["訂單編號"] != this_oid]
                        if safe_update("訂單資料", df_orders) and safe_update("採購明細", df_details):
                            st.error("訂單已刪除！"); st.rerun()
                    else: st.warning("密碼錯誤")

            st.divider()
            st.subheader("📋 施工與叫貨支出明細")
            this_details = df_details[df_details["訂單編號"] == this_oid].copy()
            if not this_details.empty:
                st.table(this_details[["類別", "項目名稱", "金額", "日期", "備註"]].assign(金額=lambda x: x['金額'].map('{:,.0f}'.format)))
                if st.button("🗑️ 刪除最後一筆明細"):
                    new_details = df_details.drop(this_details.index[-1])
                    safe_update("採購明細", new_details); st.rerun()
            
            st.write("#### ➕ 新增支出明細")
            it_type = st.radio("類型：", ["廠商叫貨", "師傅工資"], horizontal=True)
            s_cat = st.selectbox("類別", list(VENDOR_DATA.keys()) if it_type == "廠商叫貨" else list(WORKER_GROUPS.keys()))
            s_list = VENDOR_DATA[s_cat] if it_type == "廠商叫貨" else WORKER_GROUPS[s_cat]
            with st.form("add_det_form", clear_on_submit=True):
                f_name = st.selectbox("名稱", s_list + ["其他"])
                other_n = st.text_input("自定義名稱 (選其他才填)") if f_name == "核心" or f_name == "其他" else ""
                f_amt = st.number_input("金額", min_value=0, step=1)
                f_dt = st.date_input("日期", value=datetime.now())
                f_note = st.text_input("備註")
                if st.form_submit_button("確認加入"):
                    final_n = other_n if f_name == "其他" else f_name
                    new_r = pd.DataFrame([{"訂單編號": this_oid, "類別": "師傅工資" if it_type == "師傅工資" else s_cat, "項目名稱": final_n, "金額": int(f_amt), "日期": str(f_dt), "備註": f_note}])
                    safe_update("採購明細", pd.concat([df_details, new_r], ignore_index=True)); st.rerun()
        else: st.info(f"📅 {f_y}年{f_m}月 尚無資料")

# --- 功能 2：新增訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 新客戶建檔")
    with st.form("new_order_form", clear_on_submit=True):
        oid = st.text_input("訂單單號 (必填)*")
        n_name = st.text_input("客戶姓名*")
        n_phone = st.text_input("聯絡電話")
        n_date = st.date_input("訂購日期", value=datetime.now())
        n_addr = st.text_input("施工地址*")
        n_total = st.number_input("總金額", min_value=0)
        n_content = st.text_area("訂購內容")
        if st.form_submit_button("✅ 建立訂單"):
            if not oid or not n_name: st.error("❌ 必填欄位請填寫！")
            elif clean_id(oid) in df_orders["訂單編號"].values: st.error("❌ 單號已存在！")
            else:
                new_row = pd.DataFrame([{
                    "訂單編號": clean_id(oid), "訂單日期": str(n_date), "客戶姓名": n_name, 
                    "電話": n_phone, "地址": n_addr, "總金額": n_total, "已收金額": 0, "施工狀態": "已接單", "訂購內容": n_content
                }])
                safe_update("訂單資料", pd.concat([df_orders, new_row], ignore_index=True))
                st.success(f"🎊 單號 {oid} 建立成功！")

# --- 功能 3：損益中心 ---
elif choice == "💰 損益中心":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 經營損益月報表")
        c1, c2 = st.columns(2)
        r_y = c1.selectbox("統計年份", sorted(df_orders['年份'].unique().tolist(), reverse=True))
        r_m = c2.selectbox("統計月份", list(range(1, 13)), index=datetime.now().month-1)
        
        # 計算每筆單支出
        cost_sum = df_details.groupby("訂單編號")["金額"].sum().reset_index().rename(columns={"金額": "總支出"})
        final_rpt = pd.merge(df_orders, cost_sum, on="訂單編號", how="left").fillna(0)
        final_rpt["淨利"] = final_rpt["總金額"].apply(to_int) - final_rpt["總支出"]
        m_df = final_rpt[(final_rpt['年份'] == r_y) & (final_rpt['月份'] == r_m)]
        
        st.write(f"### 📅 {r_y} 年 {r_m} 月 營運結算")
        m1, m2, m3 = st.columns(3)
        m1.metric("當月業績", f"${int(m_df['總金額'].sum()):,.0f}")
        m2.metric("當月成本", f"${int(m_df['總支出'].sum()):,.0f}")
        m3.metric("當月毛利 (淨利)", f"${int(m_df['淨利'].sum()):,.0f}")
        
        st.divider()
        st.subheader("📋 訂單損益明細表格")
        st.dataframe(m_df[["訂單編號", "客戶姓名", "總金額", "總支出", "淨利", "施工狀態"]].style.format({"總金額": "${:,.0f}", "總支出": "${:,.0f}", "淨利": "${:,.0f}"}), use_container_width=True)

        st.divider()
        st.subheader("季度/月度 師傅工資匯總")
        w_df = df_details[df_details["類別"] == "師傅工資"]
        if not w_df.empty:
            w_df['日期'] = pd.to_datetime(w_df['日期'], errors='coerce')
            m_w = w_df[(w_df['日期'].dt.year == r_y) & (w_df['日期'].dt.month == r_m)]
            if not m_w.empty:
                st.dataframe(m_w.groupby("項目名稱")["金額"].sum().reset_index().rename(columns={"項目名稱": "師傅", "金額": "工資金額"}).style.format({"工資金額": "${:,.0f}"}))
