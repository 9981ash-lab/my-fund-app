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
        # 尝试获取持仓的接口
        url = f"http://fundf10.1234567.com.cn/FundArchivesDatas.aspx?type=jjcc&code={clean_code}&topline=10"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        res = requests.get(url, headers=headers, timeout=10).text
        
        # 改进的正则匹配：兼容更多格式
        codes = re.findall(r'(\d{6})\.s[hz]', res.lower())
        weights = re.findall(r'(\d+\.\d+)%', res)
        
        # 如果还是没找到，尝试另一种正则（兼容部分老旧网页）
        if not codes:
            codes = re.findall(r'stockcode=(\d{6})', res.lower())
        
        if not codes or not weights:
            return "no_data", None
        
        # 构造行情查询
        query_list = [('sh'+c if c.startswith('6') else 'sz'+c) for c in codes]
        stock_res = requests.get(f"http://qt.gtimg.cn/q={','.join(query_list)}").text
        
        total_change, weight_sum, details = 0, 0, []
        lines = stock_res.strip().split(';')
        
        for i in range(len(codes)):
            if i < len(lines) and len(lines[i]) > 20:
                parts = lines[i].split('~')
                change = float(parts[32])
                w = float(weights[i])
                total_change += change * w
                weight_sum += w
                details.append({"股票": parts[1], "涨跌幅": f"{change}%", "持仓占比": f"{w}%"})
        
        if weight_sum == 0: return "no_data", None
        estimate = round(total_change / weight_sum, 2)
        return estimate, details
    except Exception as e:
        return "error", str(e)

# --- 界面 ---
raw_input = st.text_input("请输入6位基金代码", placeholder="示例: 004812 (中欧医疗)")

if raw_input:
    with st.spinner('正在同步最新行情...'):
        res, details = get_data(raw_input)
        
        if res == "invalid":
            st.warning("⚠️ 基金代码必须是6位数字哦。")
        elif res == "no_data":
            st.error("❌ 暂时无法获取该基金的重仓股明细。")
            st.info("💡 建议测试一下：004812 (中欧医疗) 或 000001 (华夏成长)，这两个通常有稳定数据。")
        elif res == "error":
            st.error(f"❌ 网络开小差了，请刷新重试。")
        else:
            color = "red" if res >= 0 else "green"
            st.success(f"✅ 查询成功！")
            st.markdown(f"## 实时预估涨跌: :{color}[{res}%]")
            st.table(pd.DataFrame(details))
            st.caption("注：估值基于最新公开的十大重仓股加权计算。")
