import streamlit as st
import requests
import re
import pandas as pd

# 设置网页标题
st.set_page_config(page_title="基金估值助手", layout="centered")
st.title("📊 基金实时估值 (重仓股版)")

def get_fund_estimate(fund_code):
    # 自动清理非数字字符
    fund_code = re.sub(r'\D', '', fund_code)
    if len(fund_code) != 6:
        return "invalid", None

    try:
        # 1. 获取持仓明细 (使用东方财富网页接口)
        url = f"http://fundf10.1234567.com.cn/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124'}
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        html = response.text

        # 正则匹配股票代码和比例
        stock_codes = re.findall(r'(\d{6})\.s[hz]', html.lower())
        weights = re.findall(r'(\d+\.\d+)%', html)

        if not stock_codes:
            return "no_data", None

        # 2. 批量获取实时行情 (腾讯接口)
        query = ",".join([('sh'+c if c.startswith('6') else 'sz'+c) for c in stock_codes])
        price_url = f"http://qt.gtimg.cn/q={query}"
        price_res = requests.get(price_url, timeout=10).text
        
        total_chg = 0
        total_weight = 0
        details = []
        
        lines = price_res.strip().split(';')
        for i in range(len(stock_codes)):
            if i < len(lines) and len(lines[i]) > 20:
                p = lines[i].split('~')
                name = p[1] # 股票名称
                change = float(p[32]) # 涨跌幅
                w = float(weights[i]) # 持仓占比
                
                total_chg += change * w
                total_weight += w
                details.append({"股票": name, "今日涨跌": f"{change}%", "占比": f"{w}%"})

        if total_weight == 0: return "no_data", None
        
        # 计算加权平均涨跌
        estimate = round(total_chg / total_weight, 2)
        return estimate, details

    except Exception as e:
        return "error", str(e)

# --- 界面 ---
user_input = st.text_input("输入6位基金代码测试", placeholder="例如: 004812")

if user_input:
    with st.spinner('正在调取境内实时行情...'):
        res, table = get_fund_estimate(user_input)
        
        if res == "invalid":
            st.warning("请输入正确的6位数字代码。")
        elif res == "no_data":
            st.error("抱歉，该基金暂未披露重仓股，或数据接口暂时无法访问。")
        elif res == "error":
            st.error("网络连接超时，请检查网络或重试。")
        else:
            color = "red" if res >= 0 else "green"
            st.markdown(f"### 预估今日涨跌幅: :{color}[{res}%]")
            st.table(pd.DataFrame(table))
            st.info("数据说明：基于最近一季报披露的前十大重仓股计算，不代表最终净值。")
