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

# --- 2. 資料處理 ---
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
    # 清洗與補齊欄位
    for df in [df_o, df_d]:
        if "訂單編號" in df.columns: df["訂單編號"] = df["訂單編號"].apply(clean_id)
    if "金額" in df_d.columns: df_d["金額"] = df_d["金額"].apply(to_int)
    return df_o, df_d

df_orders, df_details = load_all()

# --- 3. 主選單 ---
choice = st.sidebar.selectbox("功能選單", ["📇 客戶資料與明細管理", "➕ 新增客戶訂單", "💰 損益與報表中心"])

# --- 功能 1：管理與修改 ---
if choice == "📇 客戶資料與明細管理":
    st.header("📇 客戶資料與明細管理")
    if not df_orders.empty:
        search_list = df_orders.apply(lambda r: f"{r['客戶姓名']} | {r['地址']} |ID| {r['訂單編號']}", axis=1).tolist()
        sel_str = st.selectbox("🔍 搜尋客戶：", search_list)
        target_oid = clean_id(sel_str.split("|ID|")[-1])
        
        # --- 基本資料修改 ---
        order_idx = df_orders[df_orders["訂單編號"] == target_oid].index[0]
        curr_order = df_orders.loc[order_idx]
        with st.expander("🏠 修改客戶基本資料", expanded=False):
            with st.form("edit_main"):
                u_name = st.text_input("姓名", value=curr_order['客戶姓名'])
                u_addr = st.text_input("地址", value=curr_order['地址'])
                u_total = st.number_input("總金額", value=to_int(curr_order['總金額']))
                u_paid = st.number_input("已收", value=to_int(curr_order['已收金額']))
                u_status = st.selectbox("狀態", STATUS_OPTIONS, index=STATUS_OPTIONS.index(curr_order['施工狀態']) if curr_order['施工狀態'] in STATUS_OPTIONS else 0)
                if st.form_submit_button("儲存修改"):
                    df_orders.loc[order_idx, ["客戶姓名", "地址", "總金額", "已收金額", "施工狀態"]] = [u_name, u_addr, u_total, u_paid, u_status]
                    conn.update(worksheet="訂單資料", data=df_orders)
                    st.success("成功更新"); st.rerun()

        st.divider()
        
        # --- 明細管理 (修改/刪除) ---
        st.subheader("📋 施工/叫貨明細管理")
        sub_df = df_details[df_details["訂單編號"] == target_oid].copy()
        if not sub_df.empty:
            st.dataframe(sub_df[["類別", "項目名稱", "金額", "日期", "備註"]], use_container_width=True)
            
            with st.expander("🛠️ 修改或刪除現有明細"):
                edit_list = sub_df.apply(lambda r: f"{r.name} | {r['類別']} | {r['項目名稱']} | ${r['金額']}", axis=1).tolist()
                sel_edit = st.selectbox("選擇要處理的項目", edit_list)
                row_idx = int(sel_edit.split(" | ")[0])
                
                col_e1, col_e2 = st.columns(2)
                new_amt = col_e1.number_input("修改金額", value=to_int(df_details.loc[row_idx, '金額']))
                new_note = col_e2.text_input("修改備註", value=str(df_details.loc[row_idx, '備註']))
                
                c_del1, c_del2 = st.columns(2)
                if c_del1.button("💾 確認修改金額/備註"):
                    df_details.loc[row_idx, ['金額', '備註']] = [new_amt, new_note]
                    conn.update(worksheet="採購明細", data=df_details)
                    st.success("明細已修改"); st.rerun()
                if c_del2.button("🗑️ 刪除此筆明細", type="primary"):
                    df_details = df_details.drop(row_idx)
                    conn.update(worksheet="採購明細", data=df_details)
                    st.warning("明細已刪除"); st.rerun()

        # --- 新增明細 (連動版) ---
        st.write("---")
        st.subheader("➕ 新增明細項目")
        item_type = st.radio("類型：", ["廠商叫貨", "師傅工資"], horizontal=True)
        if item_type == "廠商叫貨":
            sel_cat = st.selectbox("1. 材料類別", list(VENDOR_DATA.keys()))
            sel_list = VENDOR_DATA[sel_cat]
        else:
            sel_cat = st.selectbox("1. 施工工種", list(WORKER_GROUPS.keys()))
            sel_list = WORKER_GROUPS[sel_cat]

        with st.form("add_new_detail"):
            final_name = st.selectbox("2. 名稱", sel_list + ["其他"])
            if final_name == "其他": final_name = st.text_input("手打名稱")
            amt = st.number_input("金額", min_value=0)
            dt = st.date_input("日期", value=datetime.now())
            note = st.text_input("備註")
            if st.form_submit_button("➕ 加入明細"):
                save_cat = "師傅工資" if item_type == "師傅工資" else sel_cat
                new_row = pd.DataFrame([{"訂單編號": target_oid, "類別": save_cat, "項目名稱": final_name, "金額": int(amt), "日期": str(dt), "備註": note}])
                conn.update(worksheet="採購明細", data=pd.concat([df_details, new_row], ignore_index=True))
                st.success("已新增"); st.rerun()

# --- 功能 2：新增訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 新建立訂單")
    with st.form("new_order"):
        oid = st.text_input("訂單編號*", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
        n_name = st.text_input("客戶姓名*")
        n_addr = st.text_input("地址*")
        n_total = st.number_input("合約總額", min_value=0)
        if st.form_submit_button("✅ 建立訂單"):
            new_order = pd.DataFrame([{"訂單編號": clean_id(oid), "訂單日期": str(datetime.now().date()), "客戶姓名": n_name, "地址": n_addr, "總金額": n_total, "已收金額": 0, "施工狀態": "已接單"}])
            conn.update(worksheet="訂單資料", data=pd.concat([df_orders, new_order], ignore_index=True))
            st.success("訂單已建立！")

# --- 功能 3：損益表整合 ---
elif choice == "💰 損益與報表中心":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 損益與支出明細報表")
        
        # 統計支出
        cost_sum = df_details.groupby("訂單編號")["金額"].sum().reset_index().rename(columns={"金額": "總支出"})
        final_rpt = pd.merge(df_orders, cost_sum, on="訂單編號", how="left").fillna(0)
        final_rpt["淨利"] = final_rpt["總金額"].apply(to_int) - final_rpt["總支出"]
        
        # 顯示損益清單
        for _, row in final_rpt.iterrows():
            with st.expander(f"📌 {row['客戶姓名']} | 淨利: ${int(row['淨利']):,.0f} | 狀態: {row['施工狀態']}"):
                c1, c2, c3 = st.columns(3)
                c1.metric("合約金額", f"${int(row['總金額']):,.0f}")
                c2.metric("總支出", f"${int(row['總支出']):,.0f}")
                c3.metric("淨利", f"${int(row['淨利']):,.0f}")
                
                st.write("**🔍 此單詳細支出明細：**")
                this_detail = df_details[df_details["訂單編號"] == row["訂單編號"]]
                if not this_detail.empty:
                    st.dataframe(this_detail[["日期", "類別", "項目名稱", "金額", "備註"]], use_container_width=True)
                else:
                    st.info("此單尚無支出明細。")

        st.divider()
        st.subheader("👷 師傅應付工資匯總")
        worker_df = df_details[df_details["類別"] == "師傅工資"]
        if not worker_df.empty:
            summary = worker_df.groupby("項目名稱")["金額"].sum().reset_index().rename(columns={"項目名稱": "師傅姓名", "金額": "累計應付"})
            st.dataframe(summary.style.format({"累計應付": "${:,.0f}"}), use_container_width=True)
