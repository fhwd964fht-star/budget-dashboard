import os
import numpy as np
import pandas as pd
import scipy.stats as stats
import plotly.graph_objects as go
import streamlit as st

# ==========================================
# 1. 頁面配置與標題
# ==========================================
st.set_page_config(
    page_title="預算預測與差異分析助手 Budget-Guard AI",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🤖 預算預測與差異分析助手 (Budget-Guard AI)")
st.caption("對接 6-1 競賽題目規格：2021-2025 (110-114年) 歷史數據基準 vs 2026 (115年) 動態預算與實際支出對比")

# ==========================================
# 2. 載入 2021~2025 (110~114年) 歷史資料庫 (背景對照基準)
# ==========================================
@st.cache_data
def load_history_baseline():
    filepaths = [
        "5年5部門月度預算與支出詳細數據表.xlsx",
        "5年5部門月度預算與支出範例表_分部門分頁.xlsx"
    ]
    
    target_path = None
    for fp in filepaths:
        if os.path.exists(fp):
            target_path = fp
            break
            
    if target_path:
        xls = pd.ExcelFile(target_path)
        all_sheets = xls.sheet_names
        dept_sheets = [s for s in all_sheets if s != "年度部門總覽"]
        
        df_list = []
        for s in dept_sheets:
            df_s = pd.read_excel(target_path, sheet_name=s)
            df_list.append(df_s)
        
        df_concat = pd.concat(df_list, ignore_index=True)
        # 排除全空白列
        df_concat = df_concat.dropna(subset=["年份", "月份", "部門"])
        # 年份標準化：如果是 110~114，轉換為西元 2021~2025
        df_concat['年份'] = df_concat['年份'].apply(lambda x: int(x + 1911) if x < 1000 else int(x))
        return df_concat
    else:
        # 防呆自動生成 2021~2025 假資料
        years = [2021, 2022, 2023, 2024, 2025]
        depts = ["業務部", "行銷部", "研發部", "行政管理部", "資訊維運部"]
        data = []
        for y in years:
            for m in range(1, 13):
                for d in depts:
                    b = np.random.randint(500000, 1000000)
                    a = int(b * np.random.normal(1.0, 0.05))
                    data.append([y, m, d, b, a, b*m, a*m])
        df_mock = pd.DataFrame(data, columns=['年份', '月份', '部門', '當月分配預算', '當月實際支出', '累計分配預算', '累計實際支出'])
        return df_mock

df_hist = load_history_baseline()
hist_years = sorted(df_hist['年份'].unique())
current_year = max(hist_years) + 1 if len(hist_years) > 0 else 2026

# ==========================================
# 3. 初始化 2026 年帳本 (Session State 記憶體)
# ==========================================
depts_list = sorted([d for d in df_hist['部門'].unique() if d != "全公司"])

if 'budget_2026' not in st.session_state:
    budget_records = []
    for d in depts_list:
        for m in range(1, 13):
            hist_b = df_hist[(df_hist['部門'] == d) & (df_hist['月份'] == m)]['當月分配預算'].mean()
            val = int(hist_b * 1.05) if not np.isnan(hist_b) else 800000
            budget_records.append({'部門': d, '月份': m, '年度規劃預算': val})
    st.session_state.budget_2026 = pd.DataFrame(budget_records)

if 'actual_2026' not in st.session_state:
    actual_records = []
    for d in depts_list:
        for m in range(1, 13):
            hist_a = df_hist[(df_hist['部門'] == d) & (df_hist['月份'] == m)]['當月實際支出'].mean()
            if m in [1, 2]:
                val = int(hist_a * 1.02) if not np.isnan(hist_a) else 800000
            elif m == 3:
                val = int(hist_a * 1.08) if not np.isnan(hist_a) else 850000
            else:
                val = 0
            actual_records.append({'部門': d, '月份': m, '當月實際支出': val})
    st.session_state.actual_2026 = pd.DataFrame(actual_records)

# ==========================================
# 4. 頂部切換頁籤 (Tabs)
# ==========================================
tab1, tab2 = st.tabs(["💰 功能一：2026 全年度預算修改與設定", "📝 功能二：2026 當前實際支出錄入與風險對照"])

# ──────────────────────────────────────────
# 【功能一】：修改全年度預算
# ──────────────────────────────────────────
with tab1:
    st.header(f"💰 {current_year} 全年度各部門預算配置表")
    st.write("您可以在此處檢視或調整各部門每個月的規劃預算金額：")
    
    edit_dept = st.selectbox("選擇要修改預算的部門", depts_list, key="tab1_dept")
    
    dept_budget_mask = st.session_state.budget_2026['部門'] == edit_dept
    dept_budget_df = st.session_state.budget_2026[dept_budget_mask].copy()
    
    edited_df = st.data_editor(
        dept_budget_df[['月份', '年度規劃預算']],
        num_rows="fixed",
        use_container_width=True,
        key=f"editor_{edit_dept}"
    )
    
    # 更新回到 Session State
    for idx, row in edited_df.iterrows():
        m = int(row['月份'])
        new_val = int(row['年度規劃預算'])
        m_mask = (st.session_state.budget_2026['部門'] == edit_dept) & (st.session_state.budget_2026['月份'] == m)
        st.session_state.budget_2026.loc[m_mask, '年度規劃預算'] = new_val
        
    total_b = st.session_state.budget_2026[dept_budget_mask]['年度規劃預算'].sum()
    st.success(f"✅ 【{edit_dept}】{current_year} 全年總分配預算為：${total_b:,.0f} 元")

# ──────────────────────────────────────────
# 【功能二】：輸入目前實際支出與對比分析
# ──────────────────────────────────────────
with tab2:
    st.header(f"📝 {current_year} 年各月實際支出錄入與風險對照")
    
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader("📥 支出錄入面板")
        selected_dept = st.selectbox("選擇監控部門 / 全公司", ["全公司"] + depts_list, key="tab2_dept")
        selected_month = st.slider("選擇目前記錄的月份", 1, 12, 3)
        
        if selected_dept != "全公司":
            act_mask = (st.session_state.actual_2026['部門'] == selected_dept) & (st.session_state.actual_2026['月份'] == selected_month)
            current_val = st.session_state.actual_2026[act_mask]['當月實際支出'].iloc[0]
            
            new_input = st.number_input(
                f"輸入 {selected_dept} {selected_month} 月實際花費 (元)",
                value=int(current_val),
                step=10000
            )
            
            st.session_state.actual_2026.loc[act_mask, '當月實際支出'] = new_input
            st.caption(f"💡 已自動儲存！系統已記住 1 ~ {selected_month} 月的輸入數字。")
        else:
            st.info("目前選擇「全公司」，顯示數據為全部門自動加總數值。若要輸入單一部門花費，請切換至該部門。")

    # 數據計算
    b_2026 = st.session_state.budget_2026
    a_2026 = st.session_state.actual_2026
    
    if selected_dept == "全公司":
        cur_m_budget = b_2026[b_2026['月份'] == selected_month]['年度規劃預算'].sum()
        cur_m_actual = a_2026[a_2026['月份'] == selected_month]['當月實際支出'].sum()
        cur_ytd_budget = b_2026[b_2026['月份'] <= selected_month]['年度規劃預算'].sum()
        cur_ytd_actual = a_2026[a_2026['月份'] <= selected_month]['當月實際支出'].sum()
    else:
        cur_m_budget = b_2026[(b_2026['部門'] == selected_dept) & (b_2026['月份'] == selected_month)]['年度規劃預算'].iloc[0]
        cur_m_actual = a_2026[(a_2026['部門'] == selected_dept) & (a_2026['月份'] == selected_month)]['當月實際支出'].iloc[0]
        cur_ytd_budget = b_2026[(b_2026['部門'] == selected_dept) & (b_2026['月份'] <= selected_month)]['年度規劃預算'].sum()
        cur_ytd_actual = a_2026[(a_2026['部門'] == selected_dept) & (a_2026['月份'] <= selected_month)]['當月實際支出'].sum()

    cur_m_rate = cur_m_actual / cur_m_budget if cur_m_budget > 0 else 0
    cur_ytd_rate = cur_ytd_actual / cur_ytd_budget if cur_ytd_budget > 0 else 0

    # 歷史數據對比 (2021~2025)
    if selected_dept == "全公司":
        df_h_dept = df_hist.groupby(['年份', '月份']).agg({'當月分配預算': 'sum', '當月實際支出': 'sum'}).reset_index()
    else:
        df_h_dept = df_hist[df_hist['部門'] == selected_dept].copy()
        
    df_h_dept['單月執行率'] = df_h_dept['當月實際支出'] / df_h_dept['當月分配預算']
    hist_m = df_h_dept[df_h_dept['月份'] == selected_month]
    
    m_mean = hist_m['單月執行率'].mean() if len(hist_m) > 0 else 1.0
    m_std = hist_m['單月執行率'].std() if len(hist_m) > 1 else 0.05
    n = max(len(hist_m), 1)
    t_val = stats.t.ppf(0.975, df=n-1) if n > 1 else 2.0
    m_margin = t_val * m_std * np.sqrt(1 + 1/n)
    m_lower, m_upper = m_mean - m_margin, m_mean + m_margin

    if cur_m_rate > m_upper:
        status_str = "🔴 紅燈（嚴重超支警示）"
        status_msg = "支出金額高於過去 5 年 95% 合理安全區間上限！"
    elif cur_m_rate > m_mean + m_std:
        status_str = "🟡 黃燈（偏高警戒）"
        status_msg = "高於歷史平均 1 個標準差，接近合理上限。"
    elif cur_m_rate < m_lower:
        status_str = "🟡 黃燈（進度落後）"
        status_msg = "低於歷史合理下限，可能存在專案執行延宕。"
    else:
        status_str = "🟢 綠燈（控制健康）"
        status_msg = "支出金額落於過去 5 年正常 95% 安全區間內。"

    with col_right:
        st.subheader(f"📊 診斷結果：{current_year} 年 {selected_month} 月 - 【{selected_dept}】")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("當月實際花費", f"${cur_m_actual:,.0f}", f"規劃預算 ${cur_m_budget:,.0f}")
        m2.metric("當月預算執行率", f"{cur_m_rate*100:.2f}%", f"歷史均值 {m_mean*100:.1f}%")
        m3.metric(f"1~{selected_month}月累計花費", f"${cur_ytd_actual:,.0f}")
        
        st.markdown(f"### 當前預警狀態：{status_str}")
        st.caption(f"• **分析診斷**：{status_msg}
• **歷史合理安全範圍**：{m_lower*100:.1f}% ~ {m_upper*100:.1f}%")

    st.markdown("---")

    # 折線圖視覺化
    st.subheader(f"📈 歷史花費走勢對比 (2021-2025 年 vs {current_year} 年現況)")
    
    years_label = [f"{int(y)}年" for y in hist_years] + [f"{current_year}年 (今年現況)"]
    hist_rates = list(hist_m['單月執行率'] * 100) + [cur_m_rate * 100]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years_label, 
        y=hist_rates, 
        mode='lines+markers', 
        name='單月預算執行率 (%)',
        line=dict(color='royalblue', width=3)
    ))
    fig.add_hrect(
        y0=m_lower*100, y1=m_upper*100,
        fillcolor="green", opacity=0.15, line_width=0,
        annotation_text="歷史 95% 合理安全區間", annotation_position="top left"
    )
    fig.update_layout(xaxis_title="年份", yaxis_title="執行率 (%)", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # 白話財務建議報告
    st.subheader("💡 財務處置建議報告（過去・現在・未來）")
    
    dept_drivers = {
        "業務部": "年中/年底業績衝刺獎金與拜訪客戶差旅報銷",
        "行銷部": "第四季雙11/雙12廣告投放與大型宣傳活動",
        "研發部": "雲端伺服器算力測試與階段性外包結案款",
        "行政管理部": "年初開工採購、年度辦公室租約與員工福利",
        "資訊維運部": "資安軟體授權續約與資料庫設備維護"
    }
    driver_text = dept_drivers.get(selected_dept, "專案費用與季節性營運開銷")
    
    st.markdown(f"""
    * **🔍 過去原因追溯 (Past)**：
      比對 **{selected_dept}** 的歷史開支規律，該部門在 {selected_month} 月的花費主因來自於：**{driver_text}**。
    * **🚨 現在處置對策 (Present)**：
      {'⚠️ **啟動【二次審核】**：當前指標偏高/超支，建議財務部門要求該單位針對本月單筆 $10 萬以上報銷單據提供明細說明。' if ('🔴' in status_str or '🟡' in status_str) else '🟢 **維持常態簽核**：當前指標落於綠燈正常區間，維持現有預算授權核銷流程。'}
    * **🔮 未來預算規劃 (Future)**：
      若 1~{selected_month} 月累計花費進度偏高，建議於 Q3/Q4 開會時，從執行率長期較低的部門進行 **3%~5% 的預算微調**，並建立 **±2.5%** 的滾動緩衝金。
    """)
