import streamlit as st
import google.generativeai as genai
import os

st.set_page_config(page_title="系统诊断模式", page_icon="🛠️")
st.title("🛠️ 龙文 AI 故障诊断")

# 1. 检查 API Key
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    st.error("❌ 严重错误：API Key 未找到！请检查 Render 环境变量。")
    st.stop()
else:
    # 只显示前几位，确保安全
    st.success(f"✅ API Key 已检测到 (开头: {api_key[:4]}...)")

# 2. 检查 Google 库版本
try:
    version = genai.__version__
    st.info(f"📦 Google 工具包版本: {version}")
    if version < "0.7.2":
        st.warning("⚠️ 警告：版本过旧！Render 缓存可能未清除成功。")
except:
    st.warning("⚠️ 无法检测版本号")

# 3. 核心测试：列出可用模型
st.markdown("### 📋 服务器能看到的模型列表：")
st.write("正在连接 Google 服务器查询...")

try:
    genai.configure(api_key=api_key)
    # 获取所有模型
    models = list(genai.list_models())
    
    found_chat_model = False
    
    for m in models:
        # 只要是支持“生成内容”的模型，都列出来
        if 'generateContent' in m.supported_generation_methods:
            st.code(f"可用: {m.name}")
            found_chat_model = True
            
    if not found_chat_model:
        st.error("❌ 连接成功，但没有找到任何可用模型！")
        st.error("👉 诊断结论：这通常是因为 Render 服务器在【欧洲(Frankfurt)】，被 Google 限制了。请尝试重建一个在美国 (Oregon) 的 Render 服务。")
    else:
        st.balloons()
        st.success("✅ 测试通过！请把上面列表里绿色的名字发给 Gemini，修改代码即可。")

except Exception as e:
    st.error(f"❌ 连接彻底失败。错误信息：\n{e}")
