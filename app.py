import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基本設定與清單 ---
st.set_page_config(page_title="窗簾專家管理系統 Pro", layout="wide")
ADMIN_PASSWORD = "8888"

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
    "其他項目": ["其他"]
}

STATUS_OPTIONS = ["已接單", "備貨中", "施工中", "已完工", "已結案"]

# --- 2. 資料清洗與讀取 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_id(val):
    if pd.isna(val) or val == "": return ""
    s = str(val).strip()
    if s.endswith('.0'): s = s[:-2]
    return s

def to_int(val):
    try: return int(pd.to_numeric(val, errors='coerce') or 0)
    except: return 0

def load_all():
    df_o = conn.read(worksheet="訂單資料", ttl=0)
    df_d = conn.read(worksheet="採購明細", ttl=0)
    for df in [df_o, df_d]:
        if "訂單編號" in df.columns: df["訂單編號"] = df["訂單編號"].apply(clean_id)
    return df_o, df_d

df_orders, df_details = load_all()

# --- 3. 功能選單 ---
st.sidebar.title("🏮 窗簾經營管理中心")
choice = st.sidebar.selectbox("功能導覽", ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 損益中心"])

# --- 功能 1：客戶資料卡 (包含訂購內容與明細) ---
if choice == "📇 客戶資料卡":
    st.header("📇 客戶資料卡管理")
    if not df_orders.empty:
        # 客戶搜尋下拉選單
        search_list = df_orders.apply(lambda r: f"{r['客戶姓名']} | {r['地址']} |ID| {r['訂單編號']}", axis=1).tolist()
        sel_str = st.selectbox("🔍 請選取要查看的客戶：", search_list)
        target_oid = clean_id(sel_str.split("|ID|")[-1])
        order_idx = df_orders[df_orders["訂單編號"] == target_oid].index[0]
        curr_order = df_orders.loc[order_idx]

        # --- 客戶基本資料區 ---
        with st.form("edit_customer_form"):
            st.subheader(f"🛠️ 客戶基本資料：{target_oid}")
            col1, col2 = st.columns(2)
            u_name = col1.text_input("客戶姓名", value=str(curr_order.get('客戶姓名', '')))
            u_phone = col1.text_input("電話", value=str(curr_order.get('電話', '')))
            u_addr = col1.text_input("施工地址", value=str(curr_order.get('地址', '')))
            
            u_total = col2.number_input("合約總金額", value=to_int(curr_order.get('總金額', 0)))
            u_paid = col2.number_input("已收訂金", value=to_int(curr_order.get('已收金額', 0)))
            u_status = col2.selectbox("施工狀態", STATUS_OPTIONS, 
                                     index=STATUS_OPTIONS.index(curr_order['施工狀態']) if curr_order.get('施工狀態') in STATUS_OPTIONS else 0)
            
            # 重要的訂購內容回歸
            u_content = st.text_area("📦 訂購內容 (尺寸、材質、備註)", value=str(curr_order.get('訂購內容', '')))
            
            if st.form_submit_button("💾 儲存主資料修改"):
                df_orders.loc[order_idx, ["客戶姓名", "電話", "地址", "總金額", "已收金額", "施工狀態", "訂購內容"]] = \
                    [u_name, u_phone, u_addr, u_total, u_paid, u_status, u_content]
                conn.update(worksheet="訂單資料", data=df_orders)
                st.success("基本資料更新成功！"); st.rerun()

        st.divider()
        
        # --- 叫貨與工資明細區 ---
        st.subheader("📋 施工與叫貨明細")
        sub_df = df_details[df_details["訂單編號"] == target_oid].copy()
        if not sub_df.empty:
            st.table(sub_df[["類別", "項目名稱", "金額", "日期", "備註"]].assign(金額=lambda x: x['金額'].map('{:,.0f}'.format)))
            
            with st.expander("🛠️ 修改/刪除明細項目"):
                edit_list = sub_df.apply(lambda r: f"{r.name} | {r['項目名稱']} | ${r['金額']}", axis=1).tolist()
                sel_edit = st.selectbox("選取要處理的明細", edit_list)
                row_idx = int(sel_edit.split(" | ")[0])
                if st.button("🗑️ 刪除這筆明細", type="primary"):
                    df_details = df_details.drop(row_idx)
                    conn.update(worksheet="採購明細", data=df_details)
                    st.warning("已刪除！"); st.rerun()

        # --- 新增明細 (連動選單) ---
        st.write("---")
        st.write("#### ➕ 新增明細 (叫貨/工資)")
        item_type = st.radio("類別：", ["廠商叫貨", "師傅工資"], horizontal=True)
        if item_type == "廠商叫貨":
            sel_cat = st.selectbox("1. 材料類別", list(VENDOR_DATA.keys()))
            sel_list = VENDOR_DATA[sel_cat]
        else:
            sel_cat = st.selectbox("1. 施工工種", list(WORKER_GROUPS.keys()))
            sel_list = WORKER_GROUPS[sel_cat]

        with st.form("add_detail_quick", clear_on_submit=True):
            f_name = st.selectbox("2. 項目名稱", sel_list + ["其他"])
            if f_name == "其他": f_name = st.text_input("手打名稱")
            f_amt = st.number_input("金額", min_value=0)
            f_dt = st.date_input("日期", value=datetime.now())
            f_note = st.text_input("備註")
            if st.form_submit_button("確認加入明細"):
                save_cat = "師傅工資" if item_type == "師傅工資" else sel_cat
                new_row = pd.DataFrame([{"訂單編號": target_oid, "類別": save_cat, "項目名稱": f_name, "金額": int(f_amt), "日期": str(f_dt), "備註": f_note}])
                conn.update(worksheet="採購明細", data=pd.concat([df_details, new_row], ignore_index=True))
                st.success("明細已加入"); st.rerun()

# --- 功能 2：新增訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 新客戶建檔")
    with st.form("new_order_main", clear_on_submit=True):
        oid = st.text_input("訂單編號 (單號)*", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
        n_name = st.text_input("客戶姓名*")
        n_phone = st.text_input("聯絡電話")
        n_addr = st.text_input("施工地址*")
        n_total = st.number_input("總合約金額", min_value=0)
        n_content = st.text_area("訂購內容備註")
        if st.form_submit_button("✅ 建立訂單並儲存"):
            new_order = pd.DataFrame([{
                "訂單編號": clean_id(oid), "訂單日期": str(datetime.now().date()), "客戶姓名": n_name, 
                "電話": n_phone, "地址": n_addr, "總金額": n_total, "已收金額": 0, "施工狀態": "已接單", "訂購內容": n_content
            }])
            conn.update(worksheet="訂單資料", data=pd.concat([df_orders, new_order], ignore_index=True))
            st.success("訂單建檔成功！請至客戶資料卡新增細節。")

# --- 功能 3：損益中心 (回歸大表格方式) ---
elif choice == "💰 損益中心":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 經營損益報表")
        
        # 計算每筆單支出
        cost_sum = df_details.groupby("訂單編號")["金額"].sum().reset_index().rename(columns={"金額": "總支出"})
        final_rpt = pd.merge(df_orders, cost_sum, on="訂單編號", how="left").fillna(0)
        final_rpt["淨利"] = final_rpt["總金額"].apply(to_int) - final_rpt["總支出"]
        
        st.subheader("📈 全體訂單損益一覽表")
        st.dataframe(
            final_rpt[["訂單編號", "客戶姓名", "總金額", "總支出", "淨利", "施工狀態"]].style.format({
                "總金額": "${:,.0f}", "總支出": "${:,.0f}", "淨利": "${:,.0f}"
            }), use_container_width=True
        )

        st.divider()
        st.subheader("👷 師傅應付工資匯總")
        worker_df = df_details[df_details["類別"] == "師傅工資"]
        if not worker_df.empty:
            w_summary = worker_df.groupby("項目名稱")["金額"].sum().reset_index().rename(columns={"項目名稱": "師傅", "金額": "累計金額"})
            st.dataframe(w_summary.style.format({"累計金額": "${:,.0f}"}), use_container_width=True)
