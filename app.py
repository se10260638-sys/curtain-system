import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基本設定與師傅名單 ---
st.set_page_config(page_title="窗簾專家管理系統 Pro", layout="wide")
ADMIN_PASSWORD = "8888"

# 師傅分類名單
WORKER_GROUPS = {
    "窗簾類": ["小淯", "小林", "承暘", "袁大哥", "其他"],
    "壁紙類": ["期", "其他"],
    "地磚地毯類": ["永鑫", "祥", "郭師傅", "其他"],
    "玻璃紙類": ["宏名"],
    "其他施工": ["其他"]
}

# 廠商資料
VENDOR_DATA = {
    "窗簾布類": ["大晉", "創世紀", "可愛", "程祥", "聚合", "萊茵", "海淇", "凱薩", "德克力", "施小姐"],
    "捲簾五金類": ["彩樺", "和發", "大晉", "萊茵", "可愛", "高仕", "大瀚", "將元", "宏易", "莊小姐"],
    "壁紙類": ["竑美", "優格", "全球", "高仕"],
    "地磚地毯類": ["旺宏", "皇家", "三凱", "富銘"],
    "師傅工資": ["(請由下方選單選擇)"], 
    "其他": ["其他"]
}

STATUS_OPTIONS = ["已接單", "備貨中", "施工中", "已完工", "已結案"]

# --- 2. 資料連線與格式清洗邏輯 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_id(val):
    """處理 Google Sheets 常見的編號格式問題"""
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
        # 強制清洗編號格式
        if "訂單編號" in df.columns:
            df["訂單編號"] = df["訂單編號"].apply(clean_id)
        return df
    except:
        return pd.DataFrame(columns=cols)

# 載入主表與明細
df_orders = load_data("訂單資料", ["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "施工狀態"])
df_details = load_data("採購明細", ["訂單編號", "類別", "項目名稱", "金額", "日期", "備註"])

# 金額處理
df_orders['總金額'] = df_orders['總金額'].apply(to_int)
df_orders['已收金額'] = df_orders['已收金額'].apply(to_int)
df_details['金額'] = df_details['金額'].apply(to_int)
if not df_details.empty:
    df_details["訂單編號"] = df_details["訂單編號"].apply(clean_id)

# --- 3. 介面導覽 ---
st.sidebar.title("🏮 窗簾經營管理中心")
choice = st.sidebar.selectbox("功能選單", ["📇 客戶資料與明細", "➕ 新增客戶訂單", "💰 損益與清款報表"])

# --- 功能 1：客戶資料與明細 ---
if choice == "📇 客戶資料與明細":
    st.header("📇 客戶資料與施工明細")
    if not df_orders.empty:
        search_list = df_orders.apply(lambda r: f"{r['客戶姓名']} | {r['地址']} |ID| {r['訂單編號']}", axis=1).tolist()
        sel_str = st.selectbox("🔍 搜尋客戶：", search_list)
        
        # 提取編號並再次清洗
        target_oid = clean_id(sel_str.split("|ID|")[-1])
        
        # 搜尋資料並增加檢查
        matches = df_orders[df_orders["訂單編號"] == target_oid]
        
        if matches.empty:
            st.error(f"找不到訂單編號: {target_oid}，請確認試算表內編號是否正確。")
        else:
            order_idx = matches.index[0]
            curr_order = df_orders.loc[order_idx]

            with st.form("edit_main"):
                st.subheader(f"🏠 基本資料: {target_oid}")
                c1, c2 = st.columns(2)
                u_name = c1.text_input("客戶姓名", value=curr_order['客戶姓名'])
                u_addr = c1.text_input("地址", value=curr_order['地址'])
                u_total = c2.number_input("合約總金額", value=int(curr_order['總金額']))
                u_paid = c2.number_input("已收金額", value=int(curr_order['已收金額']))
                u_status = st.selectbox("狀態", STATUS_OPTIONS, index=STATUS_OPTIONS.index(curr_order['施工狀態']) if curr_order['施工狀態'] in STATUS_OPTIONS else 0)
                if st.form_submit_button("✅ 更新基本資料"):
                    df_orders.loc[order_idx, ["客戶姓名", "地址", "總金額", "已收金額", "施工狀態"]] = [u_name, u_addr, u_total, u_paid, u_status]
                    conn.update(worksheet="訂單資料", data=df_orders)
                    st.success("基本資料已更新"); st.rerun()

            st.divider()
            st.subheader("📋 施工與叫貨明細 (含師傅工資)")
            sub_df = df_details[df_details["訂單編號"] == target_oid]
            if not sub_df.empty:
                st.table(sub_df[["類別", "項目名稱", "金額", "日期", "備註"]].assign(金額=lambda x: x['金額'].map('{:,.0f}'.format)))
            
            with st.expander("➕ 新增明細項目 (叫貨 或 師傅工資)"):
                item_type = st.radio("請選擇新增類型：", ["廠商叫貨", "師傅工資"], horizontal=True)
                with st.form("add_detail_form", clear_on_submit=True):
                    if item_type == "廠商叫貨":
                        cat = st.selectbox("材料類別", [k for k in VENDOR_DATA.keys() if k != "師傅工資"])
                        name = st.selectbox("廠商名稱", VENDOR_DATA[cat] + ["其他"])
                        final_name = name if name != "其他" else st.text_input("手寫廠商名")
                    else:
                        work_cat = st.selectbox("施工工種", list(WORKER_GROUPS.keys()))
                        final_name = st.selectbox("施工師傅", WORKER_GROUPS[work_cat])
                        cat = "師傅工資"
                    
                    amt = st.number_input("金額", min_value=0, step=1)
                    dt = st.date_input("日期", value=datetime.now())
                    note = st.text_input("備註")
                    
                    if st.form_submit_button("➕ 加入明細"):
                        new_item = pd.DataFrame([{"訂單編號": target_oid, "類別": cat, "項目名稱": final_name, "金額": int(amt), "日期": str(dt), "備註": note}])
                        conn.update(worksheet="採購明細", data=pd.concat([df_details, new_item], ignore_index=True))
                        st.success(f"已記錄 {final_name} 的項目"); st.rerun()
    else:
        st.info("尚無客戶資料，請先新增訂單。")

# --- 其餘功能 (新增訂單 & 報表) 保留原邏輯 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 新建立訂單")
    with st.form("new_order"):
        oid = st.text_input("訂單編號 (單號)*", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
        n_name = st.text_input("客戶姓名*")
        n_addr = st.text_input("地址*")
        n_total = st.number_input("合約總額", min_value=0)
        if st.form_submit_button("✅ 建立訂單"):
            new_order = pd.DataFrame([{"訂單編號": clean_id(oid), "訂單日期": str(datetime.now().date()), "客戶姓名": n_name, "地址": n_addr, "總金額": n_total, "已收金額": 0, "施工狀態": "已接單"}])
            conn.update(worksheet="訂單資料", data=pd.concat([df_orders, new_order], ignore_index=True))
            st.success("訂單已建立！")

elif choice == "💰 損益與清款報表":
    pwd = st.text_input("密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 經營分析報表")
        st.subheader("👷 師傅工資清款統計")
        worker_df = df_details[df_details["類別"] == "師傅工資"]
        if not worker_df.empty:
            summary = worker_df.groupby("項目名稱")["金額"].sum().reset_index().rename(columns={"項目名稱": "師傅姓名", "金額": "本月累計應付"})
            st.dataframe(summary.style.format({"本月累計應付": "${:,.0f}"}), use_container_width=True)
        
        st.divider()
        st.subheader("📈 損益一覽")
        cost_sum = df_details.groupby("訂單編號")["金額"].sum().reset_index().rename(columns={"金額": "總支出"})
        final_rpt = pd.merge(df_orders, cost_sum, on="訂單編號", how="left").fillna(0)
        final_rpt["淨利"] = final_rpt["總金額"] - final_rpt["總支出"]
        st.dataframe(final_rpt[["訂單編號", "客戶姓名", "總金額", "總支出", "淨利", "施工狀態"]].style.format("{:,.0f}", subset=["總金額", "總支出", "淨利"]))
