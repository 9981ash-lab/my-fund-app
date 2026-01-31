import streamlit as st
import requests
import re
import pandas as pd

st.set_page_config(page_title="私人估值助手", layout="centered")
st.title("📊 私人基金估值助手")

def get_data(fund_code):
    try:
        # 1. 抓取持仓数据 (改用另一个更稳的数据接口)
        url = f"http://fundf10.1234567.com.cn/FundArchivesDatas.aspx?type=jjcc&code={fund_code}&topline=10"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10).text
        
        # 匹配股票代码和比例
        codes = re.findall(r'(\d{6})\.s[hz]', res)
        weights = re.findall(r'(\d+\.\d+)%', res)
        
        if not codes:
            return "no_data", None
        
        # 2. 构造查询代码 (上海6开头用sh，其他用sz)
        query_list = []
        for c in codes:
            prefix = 'sh' if c.startswith('6') else 'sz'
            query_list.append(prefix + c)
            
        # 3. 抓取实时行情
        stock_url = f"http://qt.gtimg.cn/q={','.join(query_list)}"
        stock_res = requests.get(stock_url).text
        
        total_change = 0
        weight_sum = 0
        details = []
        
        lines = stock_res.strip().split(';')
        for i in range(len(codes)):
            if i < len(lines):
                parts = lines[i].split('~')
                if len(parts) > 32:
                    name = parts[1]
                    change = float(parts[32])
                    w = float(weights[i])
                    total_change += change * w
                    weight_sum += w
                    details.append({"股票": name, "今日涨跌": f"{change}%", "仓位占比": f"{w}%"})
        
        estimate = round(total_change / weight_sum, 2) if weight_sum > 0 else 0
        return estimate, details
    except Exception as e:
        return "error", str(e)

# --- 界面部分 ---
fund_code = st.text_input("输入基金代码 (如: 004812)", "").strip()

if fund_code:
    if len(fund_code) != 6:
        st.warning("请输入6位基金代码")
    else:
        with st.spinner('正在计算实时估值...'):
            res, detail_data = get_data(fund_code)
            
            if res == "no_data":
                st.error("❌ 未找到该基金的季度重仓数据。原因可能是：1.代码错误；2.该基金是新成立的；3.该基金非股票型/混合型。")
            elif res == "error":
                st.error(f"❌ 系统连接超时，请重试。")
            else:
                color = "red" if res >= 0 else "green"
                st.markdown(f"### 预估涨跌幅: :{color}[{res}%]")
                st.table(pd.DataFrame(detail_data))
                st.caption("注：估值基于最近一季报前十大重仓股计算，仅供参考。")
