import streamlit as st
import requests
import json
import pandas as pd
import time
from datetime import datetime

# --- 1. 页面配置：让手机端显示更像 App ---
st.set_page_config(
    page_title="9981 基金实验室", 
    layout="wide", 
    initial_sidebar_state="collapsed"
)

# 自定义样式：让数字更醒目
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    .stDataFrame { font-size: 14px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心抓取函数 ---
def get_fund_val(code):
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            content = res.text
            json_str = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_str)
            return {
                "代码": data['fundcode'],
                "名称": data['name'],
                "昨收净值": float(data['dwjz']),
                "估算净值": float(data['gsz']),
                "估算涨跌幅": float(data['gszzl']),
                "更新时间": data['gztime']
            }
    except: return None

# --- 3. 初始持仓数据 (已根据 9981ash-lab 的截图精准校对) ---
if 'holding_info' not in st.session_state:
    st.session_state.holding_info = pd.DataFrame([
        {"代码": "017193", "持仓份额": 1130.66, "持仓成本": 2.3191}, # 天弘有色
        {"代码": "021534", "持仓份额": 1209.53, "持仓成本": 2.3731}, # 华夏有色
        {"代码": "019005", "持仓份额": 65.53,   "持仓成本": 3.2777}, # 国投白银
        {"代码": "012922", "持仓份额": 566.33,  "持仓成本": 2.7066}, # 易方达全球
    ])

# --- 4. 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 实验室配置")
    push_key = st.text_input("PushDeer Key (可选)", type="password")
    auto_refresh = st.checkbox("实时监控 (60s)", value=True)
    st.divider()
    st.info("手机端建议：点击浏览器菜单选择‘添加到主屏幕’")

# --- 5. 主界面 ---
st.title("📊 基金实时监控看板")

# 折叠的持仓修改区
with st.expander("📝 调整份额或成本"):
    edited_df = st.data_editor(st.session_state.holding_info, use_container_width=True)
    st.session_state.holding_info = edited_df

# 获取并展示数据
fund_codes = edited_df['代码'].tolist()
if fund_codes:
    results = []
    for code in fund_codes:
        data = get_fund_val(str(code))
        if data: results.append(data)
    
    if results:
        df = pd.merge(pd.DataFrame(results), edited_df, on="代码", how="left")
        
        # 盈亏计算
        df['今日收益'] = (df['估算净值'] - df['昨收净值']) * df['持仓份额']
        df['持有盈亏'] = (df['估算净值'] - df['持仓成本']) * df['持仓份额']
        df['当前总值'] = df['估算净值'] * df['持仓份额']
        
        # 核心指标
        t_income = df['今日收益'].sum()
        t_total = df['当前总值'].sum()
        
        c1, c2 = st.columns(2)
        c1.metric("今日预计损益", f"¥ {t_income:.2f}", delta=f"{t_income:.2f}")
        c2.metric("当前总持仓估值", f"¥ {t_value:.2f}" if 't_value' in locals() else f"¥ {t_total:.2f}")

        # 格式化表格显示
        def color_logic(val):
            if isinstance(val, (int, float)):
                if val > 0: return 'color: #f44336' # 红色
                if val < 0: return 'color: #4caf50' # 绿色
            return ''

        display_cols = ['名称', '估算涨跌幅', '今日收益', '持有盈亏']
        st.dataframe(
            df[display_cols].style.applymap(color_logic, subset=['估算涨跌幅', '今日收益', '持有盈亏']),
            use_container_width=True
        )
        st.caption(f"同步时间: {datetime.now().strftime('%H:%M:%S')}")

# --- 6. 自动重跑 ---
if auto_refresh:
    time.sleep(60)
    st.rerun()
