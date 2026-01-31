import streamlit as st
import requests
import json
import pandas as pd
import time
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="我的私人理财管家", layout="wide")

# --- 获取数据函数 ---
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

# --- 核心：你的固定持仓数据 (已根据截图金额校准) ---
if 'holding_info' not in st.session_state:
    st.session_state.holding_info = pd.DataFrame([
        {"代码": "017193", "持仓份额": 1130.66, "持仓成本": 2.3191}, # 天弘有色: 2622.11 / 2.3191
        {"代码": "021534", "持仓份额": 1209.53, "持仓成本": 2.3731}, # 华夏有色: 2870.34 / 2.3731
        {"代码": "019005", "持仓份额": 65.53,   "持仓成本": 3.2777}, # 国投白银: 214.79 / 3.2777
        {"代码": "012922", "持仓份额": 566.33,  "持仓成本": 2.7066}, # 易方达全球: 1532.83 / 2.7066
    ])

st.title("📈 我的私人基金持仓监控")

# --- 侧边栏 ---
with st.sidebar:
    st.header("⚙️ 设置")
    auto_refresh = st.checkbox("自动刷新 (60秒)", value=True)
    push_key = st.text_input("PushDeer Key (可选)", type="password")

# --- 主界面 ---
st.subheader("📋 我的持仓配置")
# 如果你在网页上修改了份额，刷新前它会生效；刷新后会回到上面的默认值
edited_df = st.data_editor(
    st.session_state.holding_info, 
    num_rows="dynamic", 
    use_container_width=True
)

# 计算逻辑
fund_codes = edited_df['代码'].tolist()
if fund_codes:
    results = []
    with st.spinner('同步行情中...'):
        for code in fund_codes:
            data = get_fund_val(str(code))
            if data: results.append(data)
    
    if results:
        display_df = pd.merge(pd.DataFrame(results), edited_df, on="代码", how="left")
        
        # 计算盈亏
        display_df['今日收益'] = (display_df['估算净值'] - display_df['昨收净值']) * display_df['持仓份额']
        display_df['持有盈亏'] = (display_df['估算净值'] - display_df['持仓成本']) * display_df['持仓份额']
        display_df['当前估值'] = display_df['估算净值'] * display_df['持仓份额']
        
        # 显示大卡片
        t_income = display_df['今日收益'].sum()
        t_value = display_df['当前估值'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("今日预计总损益", f"¥ {t_income:.2f}", delta=f"{t_income:.2f}")
        c2.metric("持仓总估值", f"¥ {t_value:.2f}")
        c3.metric("最后更新", datetime.now().strftime("%H:%M:%S"))

        # 修复后的变色逻辑
        def color_df(val):
            if isinstance(val, (int, float)):
                if val > 0: return 'color: red'
                elif val < 0: return 'color: green'
            return ''

        st.dataframe(
            display_df.style.applymap(color_df, subset=['估算涨跌幅', '今日收益', '持有盈亏']),
            use_container_width=True
        )

# 自动刷新逻辑
if auto_refresh:
    time.sleep(60)
    st.rerun()
