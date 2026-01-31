import streamlit as st
import requests
import pandas as pd
import re

st.set_page_config(page_title="私人估值助手", layout="centered")
st.title("📊 私人基金估值助手")

# 获取数据的函数
def get_data(fund_code):
    try:
        # 获取持仓
        url = f"http://fundf10.1234567.com.cn/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
        res = requests.get(url, timeout=5).text
        codes = re.findall(r'(\d{6})\.s[hz]', res)
        weights = re.findall(r'(\d+\.\d+)%', res)
        
        if not codes: return None
        
        # 获取实时行情
        query_codes = ",".join([('sh'+c if c.startswith('6') else 'sz'+c) for c in codes])
        stock_res = requests.get(f"http://qt.gtimg.cn/q={query_codes}").text
        
        total_change = 0
        weight_sum = 0
        details = []
        
        lines = stock_res.split(';')
        for i in range(len(codes)):
            parts = lines[i].split('~')
            if len(parts) > 32:
                name = parts[1]
                change = float(parts[32])
                w = float(weights[i])
                total_change += change * w
                weight_sum += w
                details.append({"股票": name, "涨跌幅": f"{change}%", "占比": f"{w}%"})
        
        return round(total_change / weight_sum, 2), details
    except:
        return None

# 界面输入
code_input = st.text_input("输入基金代码（如：012348）", "")

if code_input:
    with st.spinner('正在计算中...'):
        result = get_data(code_input)
        if result:
            estimate, df_details = result
            color = "red" if estimate >= 0 else "green"
            st.metric("预估涨跌幅", f"{estimate}%", delta=f"{estimate}%", delta_color="normal")
            st.table(df_details)
        else:
            st.error("未找到数据，请检查代码是否正确")

st.info("提示：数据基于季报前十大重仓股计算，仅供参考。")
