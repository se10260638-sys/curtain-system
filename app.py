import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基本設定與清單 ---
st.set_page_config(page_title="窗簾專家管理系統 Pro", layout="wide")
ADMIN_PASSWORD = "8888"

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
    
    # 處理日期與年月分類
    df_o['訂單日期'] = pd.to_datetime(df_o['訂單日期'], errors='coerce')
    df_o['年份'] = df_o['訂單日期'].dt.year.fillna(datetime.now().year).astype(int)
    df_o['月份'] = df_o['訂單日期'].dt.month.fillna(datetime.now().month).astype(int)
    
    # 根據單號排序 (從小到大)
    df_o = df_o.sort_values(by="訂單編號").reset_index(drop=True)
    return df_o, df_d

df_orders, df_details = load_all()

# --- 3. 功能選單 ---
st.sidebar.title("🏮 窗簾經營管理中心")
choice = st.sidebar.selectbox("功能導覽", ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 損益中心"])

# --- 功能 1：客戶資料卡 ---
if choice == "📇 客戶資料卡":
    st.header("📇 客戶資料管理")
    
    if not df_orders.empty:
        # 1. 月份篩選區
        col_f1, col_f2 = st.columns([1, 2])
        filter_y = col_f1.selectbox("年份", sorted(df_orders['年份'].unique().tolist(), reverse=True))
        filter_m = col_f2.selectbox("月份", list(range(1, 13)), index=datetime.now().month-1)
        
        # 過濾該年該月的資料
        f_df = df_orders[(df_orders['年份'] == filter_y) & (df_orders['月份'] == filter_m)]
        
        if not f_df.empty:
            # 修改排序顯示格式：『單號｜訂購日期（年/月/日）｜姓名｜住址｜』
            search_list = f_df.apply(
                lambda r: f"{r['訂單編號']} | {r['訂單日期'].strftime('%Y/%m/%d') if pd.notnull(r['訂單日期']) else '無日期'} | {r['客戶姓名']} | {r['地址']}", 
                axis=1
            ).tolist()
            
            sel_str = st.selectbox("🔍 請選擇客戶：", search_list)
            # 從選單文字中抓取單號
            selected_oid = clean_id(sel_str.split(" | ")[0])
            
            # 找到該筆資料在主表中的位置
            order_idx = df_orders[df_orders["訂單編號"] == selected_oid].index[0]
            curr_order = df_orders.loc[order_idx]

            # --- 基本資料修改區 ---
            with st.form("edit_form"):
                st.subheader(f"🛠️ 客戶資料編輯")
                c1, c2, c3 = st.columns(3)
                
                # 這裡就是您可以修改「單號」的地方
                u_oid = c1.text_input("訂單單號", value=str(curr_order['訂單編號']))
                u_name = c1.text_input("客戶姓名", value=str(curr_order.get('客戶姓名', '')))
                u_phone = c1.text_input("電話", value=str(curr_order.get('電話', '')))
                
                # 確保修改時預設是原本的訂購日
                u_date = c2.date_input("訂購日期", value=curr_order['訂單日期'] if pd.notnull(curr_order['訂單日期']) else datetime.now())
                u_addr = c2.text_input("施工地址", value=str(curr_order.get('地址', '')))
                
                u_total = c3.number_input("總金額", value=to_int(curr_order.get('總金額', 0)))
                u_paid = c3.number_input("已收訂金", value=to_int(curr_order.get('已收金額', 0)))
                u_status = st.selectbox("狀態", STATUS_OPTIONS, index=STATUS_OPTIONS.index(curr_order['施工狀態']) if curr_order.get('施工狀態') in STATUS_OPTIONS else 0)
                
                u_content = st.text_area("📦 訂購內容 (尺寸、規格等)", value=str(curr_order.get('訂購內容', '')))
                
                if st.form_submit_button("💾 儲存修改"):
                    # 檢查新單號是否重複 (如果改了單號的話)
                    if u_oid != selected_oid and u_oid in df_orders["訂單編號"].values:
                        st.error(f"❌ 單號 {u_oid} 已存在，請確認後再儲存！")
                    else:
                        # 1. 更新主表
                        df_orders.loc[order_idx, ["訂單編號", "客戶姓名", "電話", "訂單日期", "地址", "總金額", "已收金額", "施工狀態", "訂購內容"]] = \
                            [u_oid, u_name, u_phone, str(u_date), u_addr, u_total, u_paid, u_status, u_content]
                        conn.update(worksheet="訂單資料", data=df_orders)
                        
                        # 2. 如果單號有變，明細表的單號也要同步更新，才不會找不到明細
                        if u_oid != selected_oid:
                            df_details.loc[df_details["訂單編號"] == selected_oid, "訂單編號"] = u_oid
                            conn.update(worksheet="採購明細", data=df_details)
                            
                        st.success("✅ 修改成功！"); st.rerun()

            # --- 刪除功能 ---
            with st.expander("🔴 刪除整筆訂單 (慎用)"):
                del_pwd = st.text_input("輸入管理密碼確認刪除", type="password", key="del_pwd")
                if st.button("確認刪除此訂單的所有資料"):
                    if del_pwd == ADMIN_PASSWORD:
                        # 移除主表與明細
                        df_orders = df_orders.drop(order_idx)
                        df_details = df_details[df_details["訂單編號"] != selected_oid]
                        conn.update(worksheet="訂單資料", data=df_orders)
                        conn.update(worksheet="採購明細", data=df_details)
                        st.error("訂單已完全刪除！"); st.rerun()
                    else:
                        st.warning("密碼不正確")

            st.divider()
            # --- 明細管理區 ---
            st.subheader("📋 施工與叫貨明細")
            sub_df = df_details[df_details["訂單編號"] == selected_oid].copy()
            if not sub_df.empty:
                st.table(sub_df[["類別", "項目名稱", "金額", "日期", "備註"]].assign(金額=lambda x: x['金額'].map('{:,.0f}'.format)))
                if st.button("🗑️ 刪除最後一筆明細"):
                    df_details = df_details.drop(sub_df.index[-1])
                    conn.update(worksheet="採購明細", data=df_details)
                    st.rerun()
            
            # 新增明細連動
            st.write("#### ➕ 新增支出項目")
            item_type = st.radio("類型：", ["廠商叫貨", "師傅工資"], horizontal=True)
            sel_cat = st.selectbox("類別", list(VENDOR_DATA.keys()) if item_type == "廠商叫貨" else list(WORKER_GROUPS.keys()))
            sel_list = VENDOR_DATA[sel_cat] if item_type == "廠商叫貨" else WORKER_GROUPS[sel_cat]
            
            with st.form("add_det", clear_on_submit=True):
                f_name = st.selectbox("名稱", sel_list + ["其他"])
                other_name = ""
                if f_name == "其他":
                    other_name = st.text_input("請輸入自定義名稱")
                
                f_amt = st.number_input("金額", min_value=0, step=1)
                f_dt = st.date_input("支出日期", value=datetime.now())
                f_note = st.text_input("備註")
                if st.form_submit_button("確認加入"):
                    final_name = other_name if f_name == "其他" else f_name
                    new_row = pd.DataFrame([{"訂單編號": selected_oid, "類別": "師傅工資" if item_type == "師傅工資" else sel_cat, "項目名稱": final_name, "金額": int(f_amt), "日期": str(f_dt), "備註": f_note}])
                    conn.update(worksheet="採購明細", data=pd.concat([df_details, new_row], ignore_index=True))
                    st.rerun()
        else:
            st.info(f"📅 {filter_y}年{filter_m}月 尚無訂單資料")

# --- 功能 2：新增訂單 (手動輸入單號) ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 新客戶建檔")
    with st.form("new_order", clear_on_submit=True):
        oid = st.text_input("訂單單號 (必填)*")
        n_name = st.text_input("客戶姓名*")
        n_phone = st.text_input("聯絡電話")
        n_date = st.date_input("訂購日期", value=datetime.now())
        n_addr = st.text_input("施工地址*")
        n_total = st.number_input("總金額", min_value=0)
        n_content = st.text_area("訂購內容")
        
        if st.form_submit_button("✅ 建立訂單"):
            if not oid or not n_name:
                st.error("❌ 單號與姓名為必填欄位！")
            elif clean_id(oid) in df_orders["訂單編號"].values:
                st.error(f"❌ 單號 {oid} 已存在，請檢查是否重覆輸入！")
            else:
                new_row = pd.DataFrame([{
                    "訂單編號": clean_id(oid), "訂單日期": str(n_date), "客戶姓名": n_name, 
                    "電話": n_phone, "地址": n_addr, "總金額": n_total, "已收金額": 0, "施工狀態": "已接單", "訂購內容": n_content
                }])
                conn.update(worksheet="訂單資料", data=pd.concat([df_orders, new_row], ignore_index=True))
                st.success(f"🎊 單號 {oid} 建立成功！")

# --- 功能 3：損益中心 ---
elif choice == "💰 損益中心":
    pwd = st.text_input("管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 經營損益報表")
        col_y, col_m = st.columns(2)
        rpt_y = col_y.selectbox("年份", sorted(df_orders['年份'].unique().tolist(), reverse=True))
        rpt_m = col_m.selectbox("月份", list(range(1, 13)), index=datetime.now().month-1)
        
        cost_sum = df_details.groupby("訂單編號")["金額"].sum().reset_index().rename(columns={"金額": "總支出"})
        final_rpt = pd.merge(df_orders, cost_sum, on="訂單編號", how="left").fillna(0)
        final_rpt["淨利"] = final_rpt["總金額"].apply(to_int) - final_rpt["總支出"]
        m_df = final_rpt[(final_rpt['年份'] == rpt_y) & (final_rpt['月份'] == rpt_m)]
        
        st.write(f"### 📅 {rpt_y} 年 {rpt_m} 月 營運統計")
        m1, m2, m3 = st.columns(3)
        m1.metric("總業績", f"${int(m_df['總金額'].sum()):,.0f}")
        m2.metric("總成本", f"${int(m_df['總支出'].sum()):,.0f}")
        m3.metric("總毛利", f"${int(m_df['淨利'].sum()):,.0f}")
        
        st.dataframe(
            m_df[["訂單編號", "客戶姓名", "總金額", "總支出", "淨利", "施工狀態"]].style.format({
                "總金額": "${:,.0f}", "總支出": "${:,.0f}", "淨利": "${:,.0f}"
            }), use_container_width=True
        )
