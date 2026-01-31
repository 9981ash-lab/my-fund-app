import streamlit as st
import requests
import re
import pandas as pd

st.set_page_config(page_title="私人估值助手", layout="centered")
st.title("📊 基金实时估值 (新浪数据源)")

def get_data(fund_code):
    clean_code = re.sub(r'\D', '', fund_code)
    if len(clean_code) != 6: return "invalid", None
    
    try:
        # 1. 改用新浪接口获取持仓（对海外服务器更友好）
        url = f"https://fund.eastmoney.com/f10/FundArchivesDatas.aspx?type=jjcc&code={clean_code}&topline=10"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url, headers=headers, timeout=10).text
        
        codes = re.findall(r'(\d{6})\.s[hz]', res.lower())
        weights = re.findall(r'(\d+\.\d+)%', res)
        
        if not codes: return "no_data", None
        
        # 2. 抓取行情
        query = ",".join([('sh'+c if c.startswith('6') else 'sz'+c) for c in codes])
        # 使用腾讯/新浪混合接口增加成功率
        price_res = requests.get(f"http://qt.gtimg.cn/q={query}", timeout=10).text
        
        total_chg, weight_sum, details = 0, 0, []
        lines = price_res.strip().split(';')
        for i in range(len(codes)):
            if i < len(lines) and len(lines[i]) > 20:
                parts = lines[i].split('~')
                change = float(parts[32])
                w = float(weights[i])
                total_chg += change * w
                weight_sum += w
                details.append({"股票": parts[1], "涨跌": f"{change}%", "占比": f"{w}%"})
        
        return round(total_chg / weight_sum, 2), details
    except:
        return "error", None

# --- 界面 ---
code = st.text_input("输入代码 (测试请用 004812)", "").strip()
if code:
    with st.spinner('正在跨境调取行情...'):
        res, table = get_data(code)
        if res == "invalid": st.warning("请输入6位代码")
        elif res == "no_data": st.error("❌ 该基金暂无公开持仓数据")
        elif res == "error": st.error("❌ 跨境连接超时，请多点几次回车重试")
        else:
            color = "red" if res >= 0 else "green"
            st.markdown(f"## 预估涨跌: :{color}[{res}%]")
            st.table(pd.DataFrame(table))
