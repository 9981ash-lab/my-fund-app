import streamlit as st
import requests
import re
import pandas as pd

st.set_page_config(page_title="私人估值助手", layout="centered")
st.title("📊 基金估值助手 (新浪增强版)")

def get_data(fund_code):
    fund_code = re.sub(r'\D', '', fund_code)
    if len(fund_code) != 6: return "invalid", None
    
    try:
        # 1. 获取持仓 (改用新浪财经的爬取逻辑)
        url = f"http://vip.stock.finance.sina.com.cn/fund_center/index.html#jjzcgf_{fund_code}"
        # 注意：实际上新浪的持仓数据是通过另一个 JS 接口获取的，为了简单稳定，我们还是用天天基金的原始数据接口，但加上“面具”
        api_url = f"https://fundf10.1234567.com.cn/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Referer': 'https://fund.eastmoney.com/'
        }
        
        res = requests.get(api_url, headers=headers, timeout=15)
        res.encoding = 'utf-8'
        html = res.text
        
        # 匹配股票代码和比例
        codes = re.findall(r'(\d{6})\.s[hz]', html.lower())
        weights = re.findall(r'(\d+\.\d+)%', html)
        
        if not codes:
            return "no_data", None
        
        # 2. 获取实时行情 (新浪财经行情接口)
        query = ",".join([('sh'+c if c.startswith('6') else 'sz'+c) for c in codes])
        price_url = f"https://hq.sinajs.cn/list={query}"
        
        # 新浪接口需要特殊的 Referer
        price_headers = {'Referer': 'http://finance.sina.com.cn'}
        price_res = requests.get(price_url, headers=price_headers, timeout=10).text
        
        total_chg, weight_sum, details = 0, 0, []
        lines = price_res.strip().split('\n')
        
        for i in range(len(codes)):
            line = lines[i]
            if '"' in line:
                data = line.split('"')[1].split(',')
                if len(data) > 3:
                    name = data[0]
                    curr = float(data[3])
                    prev = float(data[2])
                    if prev > 0:
                        change = round(((curr - prev) / prev) * 100, 2)
                        w = float(weights[i])
                        total_chg += change * w
                        weight_sum += w
                        details.append({"股票": name, "今日涨跌": f"{change}%", "占比": f"{w}%"})
        
        if weight_sum == 0: return "no_data", None
        return round(total_chg / weight_sum, 2), details
    except Exception as e:
        return "error", str(e)

# --- 界面 ---
user_input = st.text_input("输入6位基金代码", placeholder="例如: 004812")

if user_input:
    with st.spinner('正在跨境同步行情...'):
        res, table = get_data(user_input)
        if res == "invalid": st.warning("请输入6位数字")
        elif res == "no_data": st.error("❌ 无法获取持仓。可能该基金暂未披露或接口受限。")
        elif res == "error": st.error("❌ 连接超时，请稍后重试。")
        else:
            color = "red" if res >= 0 else "green"
            st.markdown(f"### 预估今日涨跌幅: :{color}[{res}%]")
            st.table(pd.DataFrame(table))
            st.info("注：估值基于最新季报前十大重仓股计算。")
