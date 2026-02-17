import streamlit as st
import os
import google.generativeai as genai

# --- 1. 配置页面 ---
st.set_page_config(
    page_title="龙文中文学校 - HSK1 语法挑战",
    page_icon="🐲",
    layout="centered"
)

# --- 2. 获取 API Key ---
api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    st.error("⚠️ 未检测到 API Key。请在 Render 后台设置。")
    st.stop()

# --- 3. 初始化模型 ---
genai.configure(api_key=api_key)

# 核心指令
SYSTEM_PROMPT = """
你是“龙文中文学校”的 HSK1 专属助教。
目标：引导学生完成 Unit 11 语法挑战。
规则：
1. 始终先给出一个翻译挑战（中/英/西自适应）。
2. 做对时表扬语序。
3. 做错时引用老师的规则引导。
4. 严禁使用 Unit 11 之后的词汇。
"""

# 配置参数
generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 2048,
}

# --- 关键修改：使用诊断列表中确认可用的 2.0 模型 ---
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", 
        generation_config=generation_config,
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    st.error(f"模型配置错误: {e}")
    st.stop()

# --- 4. 界面逻辑 ---
st.title("🐲 龙文 HSK1 语法挑战者")

if "messages" not in st.session_state:
    st.session_state.messages = []
    try:
        chat = model.start_chat(history=[])
        st.session_state.chat_session = chat
        # 主动触发开场白
        response = chat.send_message("Please start the challenge now.")
        st.session_state.messages.append({"role": "assistant", "content": response.text})
    except Exception as e:
        st.error(f"连接失败: {e}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("请输入你的答案..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.markdown(f"出错啦: {e}")
