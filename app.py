import streamlit as st
import os
import google.generativeai as genai

# --- 1. 页面基本配置 ---
st.set_page_config(
    page_title="龙文中文 - 语法挑战",
    page_icon="🐲",
    layout="centered"
)

# --- 2. 安全获取 API Key ---
api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    st.error("⚠️ 错误：未在 Render 环境变量中检测到 GOOGLE_API_KEY。")
    st.stop()

# --- 3. 初始化 Google AI ---
genai.configure(api_key=api_key)

# 核心教学逻辑 (基于 Unit 11 设计)
SYSTEM_PROMPT = """
你是“龙文中文学校”的 HSK1 专属助教。
任务：通过翻译挑战引导学生练习 Unit 11 语法（特殊疑问句、前、时间段）。
规则：
1. 语言自适应：学生用西语你用西语，用英语你用英语。
2. 简洁有力：不要长篇大论，一次只给一个挑战。
3. 纠错不给答案：引导学生思考位置（位置词在后、时长跟动词）。
4. 严格限制词汇：仅限 HSK1 Unit 1-11。
"""

# 选择最稳健的 1.5-flash 模型
try:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash", 
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    st.error(f"模型初始化失败: {e}")
    st.stop()

# --- 4. 界面展示 ---
st.title("🐲 龙文 HSK1 语法挑战者")

# 初始化对话历史
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示聊天历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 首页引导语 (非 API 调用，不占配额)
if not st.session_state.messages:
    st.info("👋 你好！我是你的 Unit 11 语法助教。请输入 'Hi' 或 'Hola' 开启挑战！")

# --- 5. 对话处理逻辑 ---
if prompt := st.chat_input("在此输入你的答案..."):
    # 显示用户消息
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用 AI 获取回复
    with st.chat_message("assistant"):
        try:
            # 如果是第一次对话，初始化会话
            if "chat_session" not in st.session_state:
                st.session_state.chat_session = model.start_chat(history=[])
            
            # 发送消息
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            if "429" in str(e):
                st.error("🚀 哎呀，大家练习太踊跃了！(配额限制) 请等待 60 秒后再输入。")
            else:
                st.error(f"发生错误: {e}")
