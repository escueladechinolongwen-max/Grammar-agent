import streamlit as st
import os
import google.generativeai as genai

st.set_page_config(page_title="Model Diagnostics", page_icon="🔍")
st.title("🔍 Google API 照妖镜：查看真正可用的模型")

# 1. 获取你的钥匙（兼容单钥匙和逗号分隔的多钥匙）
raw_keys = os.environ.get("GOOGLE_API_KEY", "")
api_keys = [k.strip() for k in raw_keys.split(",") if k.strip()]

if not api_keys:
    st.error("⚠️ 没有在 Render 环境变量中找到 GOOGLE_API_KEY。")
    st.stop()

# 用第一把钥匙去叩门
test_key = api_keys[0]
genai.configure(api_key=test_key)
st.write(f"🔑 正在使用以 **{test_key[-4:]}** 结尾的钥匙向 Google 申请可用模型清单...")

# 2. 拉取白名单
try:
    models = genai.list_models()
    
    # 筛选出能用来聊天的模型 (支持 generateContent)
    chat_models = [m.name for m in models if 'generateContent' in m.supported_generation_methods]
    
    if chat_models:
        st.success(f"🎉 恭喜！你的账号当前有权限使用以下 {len(chat_models)} 个聊天模型：")
        for model_name in chat_models:
            # 突出显示模型名称，方便复制
            st.code(model_name.replace("models/", ""))
    else:
        st.warning("⚠️ 你的账号能连上 Google，但没有分配任何聊天模型的权限。")

except Exception as e:
    st.error(f"❌ 连线失败或被墙拦截，报错信息：\n{e}")
