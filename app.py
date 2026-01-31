import streamlit as st
import requests
import json
import pandas as pd
import time
from datetime import datetime

# --- 页面配置 ---
st.set_page_config(page_title="私人理财管家", layout="wide")

# --- 消息推送函数 (PushDeer版) ---
def send_push(key, text, desp=""):
    if not key: return
    url = "https://api2.pushdeer.com/message/push"
    params = {"pushkey": key, "text": text, "desp": desp}
    try:
        requests.get(url, params=params)
    except:
        st.error("推送失败，请检查网络或Key")

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

# --- 侧边栏设置 ---
with st.sidebar:
    st.header("🔔 推送设置")
    push_key = st.text_input("输入 PushDeer Key", type="password", help="在此填入 PDU 开头的 Key")
    alert_on = st.checkbox("开启暴跌预警 (-2%)", value=True)
    report_on = st.checkbox("开启收盘战报 (14:55)", value=True)
    
    st.divider()
    st.header("⚙️ 监控开关")
    auto_refresh = st.checkbox("开启自动刷新", value=False)
    refresh_rate = st.slider("刷新频率 (秒)", 30, 600, 60)

# --- 主界面 ---
st.title("📊 基金实时监控与推送系统")

# 1. 持仓管理 (使用 Session State 保持数据)
if 'holding_info' not in st.session_state:
    st.session_state.holding_info = pd.DataFrame([{"代码": "004812", "持仓份额": 1000.0, "持仓成本": 2.90}])

st.subheader("持仓配置")
edited_df = st.data_editor(st.session_state.holding_info, num_rows="dynamic", use_container_width=True)
st.session_state.holding_info = edited_df

# 2. 核心逻辑
fund_codes = edited_df['代码'].tolist()

if fund_codes:
    results = []
    for code in fund_codes:
        if len(str(code)) == 6:
            data = get_fund_val(code)
            if data: results.append(data)
    
    if results:
        df = pd.merge(pd.DataFrame(results), edited_df, on="代码", how="left")
        df['今日收益'] = (df['估算净值'] - df['昨收净值']) * df['持仓份额']
        df['总盈亏'] = (df['估算净值'] - df['持仓成本']) * df['持仓份额']
        
        # 统计指标
        t_income = df['今日收益'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("今日预估收益", f"¥{t_income:.2f}", delta=f"{t_income:.2f}")
        c2.metric("自选均幅", f"{df['估算涨跌幅'].mean():.2f}%")
        c3.metric("最后同步时间", datetime.now().strftime("%H:%M:%S"))

        st.dataframe(df.style.highlight_max(axis=0, subset=['估算涨跌幅'], color='#ffcccc'), use_container_width=True)

        # 3. 逻辑触发：预警与战报
        current_time = datetime.now().strftime("%H:%M")
        
        # 暴跌预警逻辑
        if alert_on and push_key:
            for _, row in df.iterrows():
                if row['估算涨跌幅'] <= -2.0:
                    send_push(push_key, f"🚨 暴跌预警：{row['名称']}", f"当前跌幅：{row['估算涨跌幅']}%，建议关注。")
        
        # 收盘战报逻辑 (只在14:55触发一次)
        if report_on and push_key and current_time == "14:55":
            report_text = f"💰 今日收盘战报\n今日总收益：{t_income:.2f}元\n当前时间：{current_time}"
            send_push(push_key, "📈 每日基金收盘战报", report_text)
            st.toast("今日战报已推送到微信/手机")

# 4. 自动刷新
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()
