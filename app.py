import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基本設定 ---
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

# --- 2. 強化版資料讀取與清洗 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def clean_id(val):
    """強力清洗單號，防止因格式問題導致明細消失"""
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
    
    if df_o is None or df_o.empty:
        df_o = pd.DataFrame(columns=["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "施工狀態"])
    if df_d is None or df_d.empty:
        df_d = pd.DataFrame(columns=["訂單編號", "類別", "項目名稱", "金額", "日期", "備註"])
    
    # 強制清洗所有單號欄位
    df_o["訂單編號"] = df_o["訂單編號"].apply(clean_id)
    if "訂單編號" in df_d.columns:
        df_d["訂單編號"] = df_d["訂單編號"].apply(clean_id)
    else:
        df_d["訂單編號"] = ""

    # 日期與年月處理
    df_o['訂單日期'] = pd.to_datetime(df_o['訂單日期'], errors='coerce')
    df_o['年份'] = df_o['訂單日期'].dt.year.fillna(datetime.now().year).astype(int)
    df_o['月份'] = df_o['訂單日期'].dt.month.fillna(datetime.now().month).astype(int)
    
    # 依單號從小到大排序
    df_o = df_o.sort_values(by="訂單編號").reset_index(drop=True)
    return df_o, df_d

df_orders, df_details = load_all()

# --- 3. 介面 ---
st.sidebar.title("🏮 窗簾經營管理中心")
choice = st.sidebar.selectbox("功能導覽", ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 損益中心"])

if choice == "📇 客戶資料卡":
    st.header("📇 客戶資料管理")
    if not df_orders.empty:
        # 月份切換 (請確認您選對月份)
        c_f1, c_f2 = st.columns([1, 2])
        y_list = sorted(df_orders['年份'].unique().tolist(), reverse=True)
        f_y = c_f1.selectbox("年份", y_list)
        f_m = c_f2.selectbox("月份", list(range(1, 13)), index=datetime.now().month-1)
        
        filtered_orders = df_orders[(df_orders['年份'] == f_y) & (df_orders['月份'] == f_m)]
        
        if not filtered_orders.empty:
            # 顯示格式：單號 | 日期 | 姓名 | 地址
            search_list = filtered_orders.apply(
                lambda r: f"{r['訂單編號']} | {r['訂單日期'].strftime('%Y/%m/%d') if pd.notnull(r['訂單日期']) else '無日期'} | {r['客戶姓名']} | {r['地址']}", 
                axis=1
            ).tolist()
            
            sel_client = st.selectbox("🔍 選擇客戶：", search_list)
            this_oid = clean_id(sel_client.split(" | ")[0])
            
            # 抓取主資料
            idx = df_orders[df_orders["訂單編號"] == this_oid].index[0]
            curr = df_orders.loc[idx]

            with st.form("edit_customer"):
                st.subheader(f"🛠️ 編輯單號：{this_oid}")
                c1, c2, c3 = st.columns(3)
                u_oid = c1.text_input("訂單單號", value=str(curr['訂單編號']))
                u_name = c1.text_input("客戶姓名", value=str(curr.get('客戶姓名', '')))
                u_date = c2.date_input("訂購日期", value=curr['訂單日期'] if pd.notnull(curr['訂單日期']) else datetime.now())
                u_addr = c2.text_input("施工地址", value=str(curr.get('地址', '')))
                u_total = c3.number_input("總金額", value=to_int(curr.get('總金額', 0)))
                u_status = st.selectbox("狀態", STATUS_OPTIONS, index=STATUS_OPTIONS.index(curr['施工狀態']) if curr['施工狀態'] in STATUS_OPTIONS else 0)
                u_content = st.text_area("📦 訂購內容", value=str(curr.get('訂購內容', '')))
                
                if st.form_submit_button("💾 儲存修改"):
                    df_orders.loc[idx, ["訂單編號", "客戶姓名", "訂單日期", "地址", "總金額", "施工狀態", "訂購內容"]] = \
                        [u_oid, u_name, str(u_date), u_addr, u_total, u_status, u_content]
                    conn.update(worksheet="訂單資料", data=df_orders)
                    # 如果改了單號，明細也要跟著改
                    if u_oid != this_oid:
                        df_details.loc[df_details["訂單編號"] == this_oid, "訂單編號"] = u_oid
                        conn.update(worksheet="採購明細", data=df_details)
                    st.success("已更新！"); st.rerun()

            st.divider()
            # --- 顯示明細 ---
            st.subheader("📋 施工與叫貨明細")
            # 這裡用強力比對
            this_details = df_details[df_details["訂單編號"] == this_oid].copy()
            
            if not this_details.empty:
                st.table(this_details[["類別", "項目名稱", "金額", "日期", "備註"]].assign(金額=lambda x: x['金額'].map('{:,.0f}'.format)))
                if st.button("🗑️ 刪除最後一筆明細"):
                    df_details = df_details.drop(this_details.index[-1])
                    conn.update(worksheet="採購明細", data=df_details)
                    st.rerun()
            else:
                st.info(f"單號 {this_oid} 目前尚無明細紀錄。")

            # 新增明細... (省略重複部分，邏輯已包含在內)
            # [新增明細表單會出現在這裡]
            st.write("#### ➕ 新增明細")
            item_t = st.radio("類型：", ["廠商叫貨", "師傅工資"], horizontal=True)
            sel_c = st.selectbox("類別", list(VENDOR_DATA.keys()) if item_t == "廠商叫貨" else list(WORKER_GROUPS.keys()))
            sel_l = VENDOR_DATA[sel_c] if item_t == "廠商叫貨" else WORKER_GROUPS[sel_c]
            with st.form("add_d", clear_on_submit=True):
                f_name = st.selectbox("名稱", sel_l + ["其他"])
                other_n = st.text_input("自定義名稱") if f_name == "其他" else ""
                f_amt = st.number_input("金額", min_value=0, step=1)
                f_dt = st.date_input("日期", value=datetime.now())
                if st.form_submit_button("確認加入"):
                    final_n = other_n if f_name == "其他" else f_name
                    new_r = pd.DataFrame([{"訂單編號": this_oid, "類別": "師傅工資" if item_t == "師傅工資" else sel_c, "項目名稱": final_n, "金額": int(f_amt), "日期": str(f_dt)}])
                    conn.update(worksheet="採購明細", data=pd.concat([df_details, new_r], ignore_index=True))
                    st.rerun()
        else:
            st.warning(f"📅 {f_y}年{f_m}月 沒有找到任何客戶資料。")

# --- 其他功能 (新增訂單 & 損益) 保留 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 新客戶建檔")
    with st.form("new_o"):
        o_id = st.text_input("訂單單號*")
        o_name = st.text_input("客戶姓名*")
        o_date = st.date_input("訂購日期", value=datetime.now())
        o_addr = st.text_input("地址")
        o_total = st.number_input("合約總額", min_value=0)
        if st.form_submit_button("✅ 建立"):
            if o_id and o_name:
                new_row = pd.DataFrame([{"訂單編號": clean_id(o_id), "訂單日期": str(o_date), "客戶姓名": o_name, "地址": o_addr, "總金額": o_total, "施工狀態": "已接單"}])
                conn.update(worksheet="訂單資料", data=pd.concat([df_orders, new_row], ignore_index=True))
                st.success("建立成功！")
            else: st.error("必填欄位請填寫")

elif choice == "💰 損益中心":
    st.header("📊 經營損益")
    # (損益中心邏輯保持不變...)
    if st.text_input("密碼", type="password") == ADMIN_PASSWORD:
        cost_sum = df_details.groupby("訂單編號")["金額"].sum().reset_index().rename(columns={"金額": "總支出"})
        final = pd.merge(df_orders, cost_sum, on="訂單編號", how="left").fillna(0)
        final["淨利"] = final["總金額"].apply(to_int) - final["總支出"]
        st.dataframe(final[["訂單編號", "客戶姓名", "總金額", "總支出", "淨利", "施工狀態"]].style.format("{:,.0f}", subset=["總金額", "總支出", "淨利"]))
