import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import re

# --- 1. 基本設定 ---
st.set_page_config(page_title="窗簾專家管理系統 Pro", layout="wide")
ADMIN_PASSWORD = "8888"

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

df_orders = load_data("訂單資料", ["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工狀態", "代工師傅"])
df_purchases = load_data("採購明細", ["訂單編號", "廠商類型", "廠商名稱", "進貨金額", "叫貨日期", "備註"])

df_orders['總金額'] = df_orders['總金額'].apply(to_int)
df_orders['已收金額'] = df_orders['已收金額'].apply(to_int)
df_orders['師傅工資'] = df_orders['師傅工資'].apply(to_int)
df_purchases['進貨金額'] = df_purchases['進貨金額'].apply(to_int)

df_orders['訂單日期'] = pd.to_datetime(df_orders['訂單日期'], errors='coerce')
df_orders['年份'] = df_orders['訂單日期'].dt.year.fillna(datetime.now().year).astype(int)
df_orders['月份'] = df_orders['訂單日期'].dt.month.fillna(datetime.now().month).astype(int)

# --- 3. 介面與導覽 ---
st.sidebar.title("🏮 窗簾經營管理中心")
choice = st.sidebar.selectbox("切換功能", ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 損益與採購分析"])

# (客戶資料卡與新增訂單邏輯保持不變...)
if choice == "📇 客戶資料卡":
    # [此處保留您原有的客戶資料卡完整代碼...]
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
            st.warning("此月份無資料。")
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
                    c1, c2 = st.columns(2)
                    with c1:
                        u_name = st.text_input("客戶姓名", value=str(client_order['客戶姓名']))
                        u_phone = st.text_input("聯絡電話", value=str(client_order['電話']))
                        u_addr = st.text_input("施工地址", value=str(client_order['地址']))
                        s_idx = STATUS_OPTIONS.index(client_order['施工狀態']) if client_order['施工狀態'] in STATUS_OPTIONS else 0
                        u_status = st.selectbox("施工進度", STATUS_OPTIONS, index=s_idx)
                    with c2:
                        u_total = st.number_input("總金額", value=int(client_order['總金額']), step=1)
                        u_paid = st.number_input("已收金額", value=int(client_order['已收金額']), step=1)
                        u_wage = st.number_input("師傅工資", value=int(client_order['師傅工資']), step=1)
                        w_idx = WORKERS.index(client_order['代工師傅']) if client_order['代工師傅'] in WORKERS else 0
                        u_worker = st.selectbox("代工師傅", WORKERS, index=w_idx)
                    u_content = st.text_area("訂購內容", value=str(client_order['訂購內容']))
                    if st.form_submit_button("✅ 儲存修改"):
                        df_orders.loc[main_idx, ["客戶姓名", "電話", "地址", "施工狀態", "總金額", "已收金額", "師傅工資", "代工師傅", "訂購內容"]] = [u_name, str(u_phone), u_addr, u_status, int(u_total), int(u_paid), int(u_wage), u_worker, u_content]
                        df_save = df_orders.drop(columns=['年份', '月份']).copy()
                        df_save['訂單日期'] = df_save['訂單日期'].dt.strftime('%Y-%m-%d')
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
                    pn = st.text_input("備註")
                    if st.button("確認新增"):
                        new_p = pd.DataFrame([{"訂單編號": target_oid, "廠商類型": pt, "廠商名稱": final_v, "進貨金額": int(pc), "叫貨日期": str(datetime.now().date()), "備註": pn}])
                        conn.update(worksheet="採購明細", data=pd.concat([df_purchases, new_p], ignore_index=True))
                        st.success("已新增！"); st.rerun()

elif choice == "➕ 新增客戶訂單":
    st.header("📋 建立新客戶")
    with st.form("new_order", clear_on_submit=True):
        oid = st.text_input("訂單編號*", value=f"ORD{datetime.now().strftime('%m%d%H%M')}")
        c1, c2 = st.columns(2)
        with c1: n, p, a = st.text_input("姓名*"), st.text_input("電話"), st.text_input("地址*")
        with c2: total, paid, work = st.number_input("總額", min_value=0, step=1), st.number_input("訂金", min_value=0, step=1), st.selectbox("代工師傅", WORKERS)
        cont = st.text_area("內容")
        if st.form_submit_button("✅ 儲存建檔"):
            if not n or not a or not oid: st.error("必填項未填")
            elif oid in df_orders["訂單編號"].apply(fix_format).values: st.error("編號重複")
            else:
                new_row = pd.DataFrame([{"訂單編號": str(oid), "訂單日期": str(datetime.now().date()), "客戶姓名": n, "電話": str(p), "地址": a, "訂購內容": cont, "總金額": int(total), "已收金額": int(paid), "師傅工資": 0, "施工狀態": "已接單", "代工師傅": work}])
                df_s = pd.concat([df_orders, new_row], ignore_index=True).drop(columns=['年份', '月份'], errors='ignore')
                df_s['訂單日期'] = pd.to_datetime(df_s['訂單日期']).dt.strftime('%Y-%m-%d')
                conn.update(worksheet="訂單資料", data=df_s); st.success("成功！")

# --- 功能 4：💰 損益與採購分析 (本次新增重點) ---
elif choice == "💰 損益與採購分析":
    pwd = st.text_input("請輸入管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📊 經營分析報表")
        
        # 1. 客戶損益合併
        p_sum = df_purchases.groupby("訂單編號")["進貨金額"].sum().reset_index()
        p_sum["訂單編號"] = p_sum["訂單編號"].apply(fix_format)
        report = pd.merge(df_orders, p_sum, on="訂單編號", how="left").fillna(0)
        report['淨利'] = report['總金額'] - report['師傅工資'] - report['進貨金額']
        
        # 顯示指標
        m1, m2, m3 = st.columns(3)
        m1.metric("總營業額", f"${int(report['總金額'].sum()):,.0f}")
        m2.metric("總採購+工資支出", f"${int(report['師傅工資'].sum() + report['進貨金額'].sum()):,.0f}")
        m3.metric("總淨利", f"${int(report['淨利'].sum()):,.0f}")
        
        st.divider()
        
        # 2. 廠商採購統計功能
        st.subheader("🏢 廠商採購統計 (核帳與議價用)")
        if not df_purchases.empty:
            # 加入時間篩選
            df_purchases['叫貨日期'] = pd.to_datetime(df_purchases['叫貨日期'])
            p_years = sorted(df_purchases['叫貨日期'].dt.year.unique().tolist(), reverse=True)
            col_y, col_m = st.columns(2)
            sel_p_y = col_y.selectbox("統計年份", p_years)
            sel_p_m = col_m.selectbox("統計月份", list(range(1, 13)), index=datetime.now().month-1)
            
            # 過濾特定月份的採購
            p_filtered = df_purchases[(df_purchases['叫貨日期'].dt.year == sel_p_y) & (df_purchases['叫貨日期'].dt.month == sel_p_m)]
            
            if p_filtered.empty:
                st.info(f"{sel_p_y}年{sel_p_m}月沒有採購記錄。")
            else:
                # 依廠商名稱總計
                vendor_stats = p_filtered.groupby("廠商名稱")["進貨金額"].agg(['sum', 'count']).sort_values(by='sum', ascending=False)
                vendor_stats.columns = ["採購總額", "叫貨筆數"]
                
                st.write(f"#### {sel_p_y} 年 {sel_p_m} 月 廠商排行")
                st.dataframe(vendor_stats.style.format({"採購總額": "${:,.0f}"}))
                
                # 圓餅圖顯示分布
                st.write("#### 採購金額占比")
                st.bar_chart(vendor_stats["採購總額"])
        else:
            st.info("尚無採購資料。")
            
        st.divider()
        st.subheader("📝 客戶損益明細")
        st.dataframe(report[["訂單編號", "客戶姓名", "總金額", "進貨金額", "師傅工資", "淨利", "施工狀態"]].style.format({"總金額": "{:,.0f}", "進貨金額": "{:,.0f}", "師傅工資": "{:,.0f}", "淨利": "{:,.0f}"}))
