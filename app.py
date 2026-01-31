import streamlit as st
import requests
import json
import pandas as pd
import time

# --- 页面配置 ---
st.set_page_config(page_title="我的基金私人管家", layout="wide", initial_sidebar_state="expanded")

# --- 自定义样式 ---
st.markdown("""
    <style>
    .metric-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 我的基金私人管家 (自动刷新+盈亏版)")

# --- 侧边栏：设置与自动刷新 ---
with st.sidebar:
    st.header("⚙️ 自动刷新设置")
    refresh_rate = st.slider("刷新频率 (秒)", min_value=10, max_value=300, value=60)
    auto_refresh = st.checkbox("开启自动刷新", value=False)
    
    st.divider()
    st.header("📝 基金池管理")
    input_codes = st.text_area("添加基金代码 (用逗号或换行隔开)", "004812\n012348\n000001")
    fund_codes = [c.strip() for c in input_codes.replace(',', '\n').split('\n') if len(c.strip()) == 6]

# --- 数据获取函数 ---
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
    except:
        return None
    return None

# --- 初始化持仓数据 (使用 Session State 记忆编辑内容) ---
if 'holding_info' not in st.session_state:
    # 默认给一些初始值
    st.session_state.holding_info = pd.DataFrame([
        {"代码": "004812", "持仓份额": 1000.0, "持仓成本": 3.50},
        {"代码": "012348", "持仓份额": 500.0, "持仓成本": 1.20},
    ])

# --- 主界面布局 ---

# 1. 持仓编辑区
st.subheader("📋 我的持仓配置")
st.info("💡 请在下方表格中直接修改你的【持仓份额】和【持仓成本】，计算结果会自动更新。")
edited_df = st.data_editor(
    st.session_state.holding_info, 
    num_rows="dynamic",
    use_container_width=True,
    key="holding_editor"
)
st.session_state.holding_info = edited_df

# 2. 实时行情与盈亏计算
st.divider()
st.subheader("🚀 实时行情与今日盈亏")

if fund_codes:
    all_results = []
    with st.spinner('同步最新行情中...'):
        for code in fund_codes:
            data = get_fund_val(code)
            if data:
                all_results.append(data)
    
    if all_results:
        display_df = pd.DataFrame(all_results)
        
        # 合并用户的持仓数据
        final_df = pd.merge(display_df, edited_df, on="代码", how="left")
        final_df['持仓份额'] = final_df['持仓份额'].fillna(0)
        final_df['持仓成本'] = final_df['持仓成本'].fillna(0)
        
        # 计算逻辑
        # 今日盈亏 = (估算净值 - 昨收净值) * 持仓份额
        final_df['今日收益'] = (final_df['估算净值'] - final_df['昨收净值']) * final_df['持仓份额']
        # 持有盈亏 = (估算净值 - 持仓成本) * 持仓份额
        final_df['总盈亏'] = (final_df['估算净值'] - final_df['持仓成本']) * final_df['持仓份额']
        
        # 汇总信息显示
        total_today_income = final_df['今日收益'].sum()
        total_profit = final_df['总盈亏'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("今日预计总收益", f"¥ {total_today_income:.2f}", delta=f"{total_today_income:.2f}")
        c2.metric("当前自选平均涨幅", f"{final_df['估算涨跌幅'].mean():.2f}%")
        c3.metric("预估总盈亏", f"¥ {total_profit:.2f}", delta=f"{total_profit:.2f}")

        # 表格美化展示
        def color_red_green(val):
            color = 'red' if val >= 0 else 'green'
            return f'color: {color}'

        st.dataframe(
            final_df.style.applymap(color_red_green, subset=['估算涨跌幅', '今日收益', '总盈亏']),
            use_container_width=True
        )
    else:
        st.error("接口数据获取失败，请稍后再试。")

# 3. 自动刷新逻辑
if auto_refresh:
    time.sleep(refresh_rate)
    st.rerun()

st.caption(f"最后更新时间: {time.strftime('%H:%M:%S')}")
