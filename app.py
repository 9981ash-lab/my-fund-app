import streamlit as st
import requests
import json
import pandas as pd
import time
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="我的基金管家", layout="wide")

# --- 消息推送函数 (PushDeer) ---
def send_push(key, text, desp=""):
    if not key: return
    url = "https://api2.pushdeer.com/message/push"
    params = {"pushkey": key, "text": text, "desp": desp}
    try: requests.get(url, params=params, timeout=5)
    except: pass

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

# --- 初始化持仓数据 (根据你的截图) ---
# 这样即使刷新，这几只基金也会默认存在
initial_data = [
    {"代码": "007413", "持仓份额": 1120.0, "持仓成本": 1.36}, # 易方达全球
    {"代码": "012348", "持仓份额": 2450.0, "持仓成本": 1.07}, # 天弘有色
    {"代码": "013508", "持仓份额": 3200.0, "持仓成本": 0.89}, # 华夏有色
    {"代码": "161226", "持仓份额": 250.0,  "持仓成本": 0.85}  # 国投白银
]

if 'holding_info' not in st.session_state:
    st.session_state.holding_info = pd.DataFrame(initial_data)

# --- 界面展示 ---
st.title("📈 我的私人基金持仓监控")

with st.sidebar:
    st.header("🔔 预警推送")
    push_key = st.text_input("PushDeer Key", type="password")
    auto_refresh = st.checkbox("实时监控 (每分钟刷新)", value=True)
    st.info("提示：请在下方表格中微调你的实际‘份额’和‘成本’")

# 1. 持仓编辑器
st.subheader("我的持仓明细")
edited_df = st.data_editor(
    st.session_state.holding_info, 
    num_rows="dynamic", 
    use_container_width=True,
    key="data_editor"
)
# 保存修改到 session
st.session_state.holding_info = edited_df

# 2. 计算实时盈亏
fund_codes = edited_df['代码'].tolist()
if fund_codes:
    results = []
    with st.spinner('正在同步最新估值...'):
        for code in fund_codes:
            data = get_fund_val(code)
            if data: results.append(data)
    
    if results:
        # 合并实时数据和用户持仓数据
        display_df = pd.merge(pd.DataFrame(results), edited_df, on="代码", how="left")
        
        # 计算逻辑
        display_df['今日收益'] = (display_df['估算净值'] - display_df['昨收净值']) * display_df['持仓份额']
        display_df['持有盈亏'] = (display_df['估算净值'] - display_df['持仓成本']) * display_df['持仓份额']
        
        # 顶部指标卡
        c1, c2, c3 = st.columns(3)
        total_income = display_df['今日收益'].sum()
        c1.metric("今日预估总收益", f"¥ {total_income:.2f}", delta=f"{total_income:.2f}")
        c2.metric("当前时间", datetime.now().strftime("%H:%M:%S"))
        c3.success("数据来源：实时估值接口")

        # 数据表格展示
        st.dataframe(
            display_df.style.format({
                "昨收净值": "{:.4f}", "估算净值": "{:.4f}", 
                "估算涨跌幅": "{:.2f}%", "今日收益": "¥ {:.2f}", "持有盈亏": "¥ {:.2f}"
            }).highlight_between(left=-100, right=-2, subset=['估算涨跌幅'], color='#ffcccc'),
            use_container_width=True
        )

        # 3. 预警逻辑
        if push_key and total_income < -100: # 假设总亏损超过100元就报警
            send_push(push_key, "⚠️ 基金账户跌幅过大", f"当前今日总收益为: {total_income:.2f}")

# 自动刷新
if auto_refresh:
    time.sleep(60)
    st.rerun()
