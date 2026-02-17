import streamlit as st
import os
import google.generativeai as genai

# --- 1. 配置页面 ---
st.set_page_config(
    page_title="龙文中文学校 - 语法挑战",
    page_icon="🐲",
    layout="centered"
)

# --- 2. 获取 API Key ---
api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    st.error("⚠️ API Key missing in Environment Variables.")
    st.stop()

# --- 3. 初始化模型 ---
genai.configure(api_key=api_key)

SYSTEM_PROMPT = """
你是“龙文中文学校”的 HSK1 专属助教。
模式：主动挑战者。
任务：根据 Unit 11 语法点（特殊疑问句、前、时间段）出翻译题。
词汇限制：仅限 HSK1 Unit 1-11。
"""

try:
    # 强制使用你服务器列表里排在第一位的可用模型
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", 
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    st.error(f"Configuration error: {e}")
    st.stop()

# --- 4. 界面逻辑 ---
st.title("🐲 龙文 HSK1 语法挑战者")

if "messages" not in st.session_state:
    st.session_state.messages = []
    # 重要：不再自动发送初始化消息，避免触发 429 限流

# 显示历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 如果还没有对话，显示一个友好的引导
if not st.session_state.messages:
    st.info("👋 你好！我是你的语法挑战助教。请输入 'Hi' 或 'Hola' 开始今天的 Unit 11 特训！")

# 处理用户输入
if prompt := st.chat_input("在此输入..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        try:
            if "chat_session" not in st.session_state:
                st.session_state.chat_session = model.start_chat(history=[])
            
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            if "429" in str(e):
                st.error("🚀 访问太快啦！Google 免费版配额限制，请等待 1 分钟后再试。")
            else:
                st.error(f"Error: {e}")
