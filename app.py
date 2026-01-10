import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 1. 基本設定與廠商清單 ---
st.set_page_config(page_title="窗簾專家管理系統", layout="wide")

ADMIN_PASSWORD = "8888"

# 廠商資料庫
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
        return df
    except:
        return pd.DataFrame(columns=cols)

df_orders = load_data("訂單資料", ["訂單編號", "訂單日期", "客戶姓名", "電話", "地址", "訂購內容", "總金額", "已收金額", "師傅工資", "施工狀態", "代工師傅"])
df_purchases = load_data("採購明細", ["訂單編號", "廠商類型", "廠商名稱", "進貨金額", "叫貨日期", "備註"])

# --- 3. 側邊欄導覽 ---
st.sidebar.title("🏮 窗簾經營管理中心")
menu = ["📇 客戶資料卡", "➕ 新增客戶訂單", "💰 財務損益報表"]
choice = st.sidebar.selectbox("切換功能", menu)

# --- 功能 1：客戶資料卡 (核心查看中心) ---
if choice == "📇 客戶資料卡":
    st.header("📇 客戶資料與訂單詳情")
    
    if df_orders.empty:
        st.info("目前尚無客戶資料，請先新增訂單。")
    else:
        # 搜尋與選擇客戶
        search_list = df_orders.apply(lambda r: f"{r['客戶姓名']} | {r['地址']}", axis=1).tolist()
        selected_client = st.selectbox("請選擇客戶：", search_list)
        
        # 抓取該客戶的訂單資料
        c_name = selected_client.split(" | ")[0]
        client_order = df_orders[df_orders["客戶姓名"] == c_name].iloc[0]
        order_id = client_order["訂單編號"]

        # 顯示資料卡
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🏠 客戶基本資料")
            st.write(f"**客戶姓名：** {client_order['客戶姓名']}")
            st.write(f"**電話：** {client_order['電話']}")
            st.write(f"**地址：** {client_order['地址']}")
            st.write(f"**工程狀態：** {client_order['施工狀態']}")
        with col2:
            st.subheader("📝 訂單明細")
            st.info(f"訂購內容：\n{client_order['訂購內容']}")
            st.write(f"**總金額：** ${float(client_order['總金額']):,.0f}")
            st.write(f"**已收金額：** ${float(client_order['已收金額']):,.0f}")

        st.divider()

        # 叫貨明細區塊
        st.subheader("📦 廠商叫貨明細")
        this_p = df_purchases[df_purchases["訂單編號"] == order_id]
        if not this_p.empty:
            st.table(this_p[["廠商類型", "廠商名稱", "進貨金額", "叫貨日期", "備註"]])
            st.write(f"**總叫貨成本：${this_p['進貨金額'].astype(float).sum():,.0f}**")
        else:
            st.caption("目前暫無此訂單的進貨記錄。")

        # 進貨登記按鈕 (直接在資料卡下方新增)
        with st.expander("➕ 新增一筆叫貨登記"):
            with st.form("quick_purchase"):
                p_type = st.selectbox("廠商類別", list(VENDOR_DATA.keys()))
                p_vendor_list = VENDOR_DATA[p_type] + ["(自行輸入)"]
                p_vendor = st.selectbox("選擇廠商", p_vendor_list)
                if p_vendor == "(自行輸入)":
                    p_vendor = st.text_input("請輸入廠商名稱")
                
                p_cost = st.number_input("金額", min_value=0)
                p_note = st.text_input("備註 (布號/規格)")
                if st.form_submit_button("確認新增"):
                    new_p = pd.DataFrame([{"訂單編號": order_id, "廠商類型": p_type, "廠商名稱": p_vendor, "進貨金額": p_cost, "叫貨日期": str(datetime.now().date()), "備註": p_note}])
                    updated_p = pd.concat([df_purchases, new_p], ignore_index=True)
                    conn.update(worksheet="採購明細", data=updated_p)
                    st.success("進貨記錄已更新！")
                    st.rerun()

        # 修改與刪除區塊
        st.divider()
        with st.expander("🛠️ 修改或刪除此客戶訂單"):
            u_status = st.selectbox("更新施工進度", STATUS_OPTIONS, index=STATUS_OPTIONS.index(client_order['施工狀態']))
            u_wage = st.number_input("修改代工師傅工資", value=float(client_order['師傅工資']))
            u_worker = st.selectbox("修改代工師傅", WORKERS, index=0)
            
            c1, c2 = st.columns(2)
            if c1.button("✅ 儲存修改"):
                df_orders.loc[df_orders["訂單編號"] == order_id, ["施工狀態", "師傅工資", "代工師傅"]] = [u_status, u_wage, u_worker]
                conn.update(worksheet="訂單資料", data=df_orders)
                st.success("資料已修改！")
                st.rerun()
            if c2.button("🚨 刪除此客戶訂單"):
                df_orders = df_orders[df_orders["訂單編號"] != order_id]
                df_purchases = df_purchases[df_purchases["訂單編號"] != order_id]
                conn.update(worksheet="訂單資料", data=df_orders)
                conn.update(worksheet="採購明細", data=df_purchases)
                st.warning("客戶資料已刪除！")
                st.rerun()

# --- 功能 2：新增訂單 ---
elif choice == "➕ 新增客戶訂單":
    st.header("📋 建立客戶資料卡")
    with st.form("new_order", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            c_name = st.text_input("客戶姓名*")
            c_phone = st.text_input("聯絡電話")
            c_address = st.text_input("施工地址*")
        with col2:
            c_total = st.number_input("訂單金額", min_value=0)
            c_paid = st.number_input("已付金額", min_value=0)
            c_worker = st.selectbox("代工師傅", WORKERS)
        
        c_content = st.text_area("訂購詳細內容")
        
        if st.form_submit_button("✅ 存入客戶資料卡"):
            if not c_name or not c_address:
                st.error("姓名與地址為必填項目！")
            else:
                new_id = f"ORD{datetime.now().strftime('%m%d%H%M')}"
                new_row = pd.DataFrame([{
                    "訂單編號": new_id, "訂單日期": str(datetime.now().date()), "客戶姓名": c_name,
                    "電話": c_phone, "地址": c_address, "訂購內容": c_content,
                    "總金額": c_total, "已收金額": c_paid, "師傅工資": 0, "施工狀態": "已接單", "代工師傅": c_worker
                }])
                updated_df = pd.concat([df_orders, new_row], ignore_index=True)
                conn.update(worksheet="訂單資料", data=updated_df)
                st.success("客戶已成功建檔！可至『客戶資料卡』查看細節。")

# --- 功能 3：財務損益報表 ---
elif choice == "💰 財務損益報表":
    pwd = st.text_input("請輸入管理密碼", type="password")
    if pwd == ADMIN_PASSWORD:
        st.header("📈 經營損益分析")
        p_agg = df_purchases.groupby("訂單編號")["進貨金額"].sum().reset_index()
        report = pd.merge(df_orders, p_agg, on="訂單編號", how="left").fillna(0)
        report['進貨金額'] = report['進貨金額'].astype(float)
        report['淨利'] = report['總金額'].astype(float) - report['師傅工資'].astype(float) - report['進貨金額']

        c1, c2, c3 = st.columns(3)
        c1.metric("總業績", f"${report['總金額'].sum():,.0f}")
        c2.metric("總支出(工資+材料)", f"${(report['師傅工資'].sum() + report['進貨金額'].sum()):,.0f}")
        c3.metric("結算淨利", f"${report['淨利'].sum():,.0f}")

        st.subheader("明細清單")
        st.dataframe(report[["客戶姓名", "總金額", "進貨金額", "師傅工資", "淨利", "施工狀態"]])
