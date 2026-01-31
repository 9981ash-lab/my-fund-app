import streamlit as st
import requests
import json
import pandas as pd
import time
from datetime import datetime

# --- 1. 页面配置：优化移动端显示 ---
st.set_page_config(
    page_title="我的私人基金管家", 
    layout="wide", 
    initial_sidebar_state="collapsed" # 手机端默认隐藏侧边栏，节省空间
)

# 自定义 CSS：让数据卡片在手机上更显眼
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem !important; }
    .stDataFrame { font-size: 12px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据获取与推送函数 ---
def get_fund_val(code):
    """从天天基金接口获取实时估值"""
    try:
        url = f"https://fundgz.1234567.com.cn/js/{code}.js"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            content = res.text
            # 提取 JSON 部分
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
    except:
        return None
    return None

def send_push(key, text, desp=""):
    """PushDeer 消息推送"""
    if not key: return
    url = "https://api2.pushdeer.com/message/push"
    params = {"pushkey": key, "text": text, "desp": desp}
    try:
        requests.get(url, params=params, timeout=5)
    except:
        pass

# --- 3. 核心持仓数据：永久固定你的份额与成本 ---
# 这些数字是根据你提供的支付宝截图精准计算的，刷新也不会丢失
if 'holding_info' not in st.session_state:
    st.session_state.holding_info = pd.DataFrame([
        {"代码": "017193", "持仓份额": 1130.66, "持仓成本": 2.3191}, # 天弘有色
        {"代码": "021534", "持仓份额": 1209.53, "持仓成本": 2.3731}, # 华夏有色
        {"代码": "019005", "持仓份额": 65.53,   "持仓成本": 3.2777}, # 国投白银
        {"代码": "012922", "持仓份额": 566.33,  "持仓成本": 2.7066}, # 易方达全球
    ])

# --- 4. 侧边栏设置 ---
with st.sidebar:
    st.header("🔔 监控设置")
    push_key = st.text_input("PushDeer Key", type="password", help="填入 PDU 开头的 Key")
    auto_refresh = st.checkbox("开启自动刷新 (60s)", value=True)
    st.divider()
    st.caption("建议在手机浏览器中选择‘添加到主屏幕’以获得 App 体验")

# --- 5. 主界面内容 ---
st.title("📂 我的私人基金持仓")

# 持仓编辑区（折叠起来，手机端看更清爽）
with st.expander("📝 修改持仓份额/成本"):
    edited_df = st.data_editor(
        st.session_state.holding_info, 
        num_rows="dynamic", 
        use_container_width=True
    )
    st.session_state.holding_info = edited_df

# 数据处理
fund_codes = edited_df['代码'].tolist()
if fund_codes:
    all_results = []
    with st.spinner('数据同步中...'):
        for code in fund_codes:
            data = get_fund_val(str(code))
            if data:
                all_results.append(data)
    
    if all_results:
        # 合并实时行情与个人持仓
        df = pd.merge(pd.DataFrame(all_results), edited_df, on="代码", how="left")
        
        # 核心计算逻辑
        df['今日收益'] = (df['估算净值'] - df['昨收净值']) * df['持仓份额']
        df['当前价值'] = df['估算净值'] * df['持仓份额']
        df['累计盈亏'] = (df['估算净值'] - df['持仓成本']) * df['持仓份额']
        
        # 顶部看板
        t_today = df['今日收益'].sum()
        t_value = df['当前价值'].sum()
        
        col1, col2 = st.columns(2)
        col1.metric("今日预估损益", f"¥ {t_today:.2f}", delta=f"{t_today:.2f}")
        col2.metric("持仓总估值", f"¥ {t_value:.2f}")
        
        # 表格变色美化
        def color_style(val):
            if isinstance(val, (int, float)):
                if val > 0: return 'color: #ef5350; font-weight: bold' # 红色
                if val < 0: return 'color: #26a69a; font-weight: bold' # 绿色
            return ''

        # 手机端只显示核心列，避免横向滚动太厉害
        show_cols = ['名称', '估算涨跌幅', '今日收益', '累计盈亏']
        st.dataframe(
            df[show_cols].style.applymap(color_style, subset=['估算涨跌幅', '今日收益', '累计盈亏']),
            use_container_width=True,
            height=300
        )
        
        st.caption(f"数据更新于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # 6. 推送触发逻辑
        # 示例：如果今日总亏损超过 200 元，自动发推送
        if push_key and t_today < -200:
            send_push(push_key, "⚠️ 基金大跌提醒", f"今日已亏损 ¥{t_today:.2f}，请知晓。")

# --- 7. 自动刷新控制 ---
if auto_refresh:
    time.sleep(60)
    st.rerun()
