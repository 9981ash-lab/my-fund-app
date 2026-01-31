import streamlit as st
import requests
import re
import pandas as pd

st.set_page_config(page_title="私人估值助手", layout="centered")
st.title("📊 我的私人基金估值")

def get_data(fund_code):
    # 自动清理输入
    clean_code = re.sub(r'\D', '', fund_code)
    if len(clean_code) != 6:
        return "invalid", None
    
    try:
        # 1. 模拟浏览器访问（这是解决“无法获取”的关键）
        url = f"http://fundf10.1234567.com.cn/FundArchivesDatas.aspx?type=jjcc&code={clean_code}&topline=10"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        res = requests.get(url, headers=headers, timeout=10).text
        
        # 2. 提取股票代码和占比
        codes = re.findall(r'(\d{6})\.s[hz]', res.lower())
        weights = re.findall(r'(\d+\.\d+)%', res)
        
        if not codes or not weights:
            # 备选匹配方案
            codes = re.findall(r'stockcode=(\d{6})', res.lower())
            if not codes: return "no_data", None
        
        # 3. 抓取行情
        query_list = [('sh'+c if c.startswith('6') else 'sz'+c) for c in codes[:10]]
        stock_res = requests.get(f"http://qt.gtimg.cn/q={','.join(query_list)}").text
        
        total_change, weight_sum, details = 0, 0, []
        lines = stock_res.strip().split(';')
        
        for i in range(len(codes[:10])):
            if i < len(lines) and len(lines[i]) > 20:
                parts = lines[i].split('~')
                change = float(parts[32])
                w = float(weights[i])
                total_change += change * w
                weight_sum += w
                details.append({"股票": parts[1], "涨跌幅": f"{change}%", "持仓占比": f"{w}%"})
        
        estimate = round(total_change / weight_sum, 2) if weight_sum > 0 else 0
        return estimate, details
    except Exception as e:
        return "error", str(e)

# --- 界面 ---
raw_input = st.text_input("请输入6位基金代码", placeholder="例如: 004812")

if raw_input:
    with st.spinner('正在调取数据...'):
        res, details = get_data(raw_input)
        
        if res == "invalid":
            st.warning("⚠️ 请输入6位数字代码。")
        elif res == "no_data":
            st.error("❌ 暂时无法获取持仓。该基金可能近期未披露持仓，或非权益类基金。")
        elif res == "error":
            st.error("❌ 网络请求超时，请稍后重试。")
        else:
            color = "red" if res >= 0 else "green"
            st.markdown(f"## 实时预估涨跌: :{color}[{res}%]")
            st.table(pd.DataFrame(details))
            st.caption("数据基于最新季报重仓股。")
