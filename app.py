import streamlit as st
import requests
import json
import pandas as pd

st.set_page_config(page_title="私人估值助手", layout="centered")
st.title("📊 基金实时估值 (强力接口版)")

def get_valuation(fund_code):
    try:
        # 1. 尝试直接获取天天基金的实时估值接口（这比算重仓股更准，且更稳）
        url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js"
        res = requests.get(url, timeout=10)
        
        if res.status_code == 200:
            content = res.text
            # 提取 JSON 数据
            json_str = content[content.find('{'):content.rfind('}')+1]
            data = json.loads(json_str)
            
            # 提取关键信息
            name = data['name']
            gz = data['gsz']      # 估算净值
            gz_rate = data['gszzl'] # 估算涨跌幅
            time = data['gztime']   # 估值时间
            
            return {
                "name": name,
                "rate": gz_rate,
                "price": gz,
                "time": time
            }, None
        else:
            return None, "接口暂时无法访问"
    except Exception as e:
        return None, str(e)

# --- 界面展示 ---
code = st.text_input("请输入6位基金代码 (如: 004812)", "").strip()

if code and len(code) == 6:
    with st.spinner('正在调取实时数据...'):
        result, error = get_valuation(code)
        
        if result:
            color = "red" if float(result['rate']) >= 0 else "green"
            st.success(f"✅ 已找到基金：{result['name']}")
            st.markdown(f"### 实时估值涨跌幅: :{color}[{result['rate']}%]")
            
            # 展示详细卡片
            col1, col2 = st.columns(2)
            col1.metric("估算净值", result['price'])
            col2.metric("更新时间", result['time'])
            
            st.info("💡 提示：此数据为实时估值，比手动计算重仓股更接近最终净值。")
        else:
            st.error(f"❌ 还是拿不到数据。错误原因: {error}")
            st.warning("这说明 Streamlit 服务器 IP 可能被封了。")
else:
    st.info("请输入6位数字代码开始查询。")
