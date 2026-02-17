import streamlit as st
import os
import google.generativeai as genai

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="Long Wen - HSK1 Grammar (Pro)",
    page_icon="🐲",
    layout="centered"
)

# --- 2. 安全获取 API Key ---
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ Error: API Key not found. Please check Render Environment Variables.")
    st.stop()

# 配置 Google AI
genai.configure(api_key=api_key)

# --- 3. 核心大脑指令 (双语自适应版) ---
SYSTEM_PROMPT = """
You are the elite HSK1 Grammar Teaching Assistant for "Long Wen Chinese School" (龙文中文学校).
Your sole purpose is to challenge students on **Unit 11 Grammar Points**.

### 🌍 LANGUAGE PROTOCOL (CRITICAL)
1. **DETECT**: Instantly identify if the student is using **English** or **Spanish**.
2. **ADAPT**: 
   - IF student uses **English**: Your entire response (feedback, explanations, next question) MUST be in **English**.
   - IF student uses **Spanish**: Your entire response (feedback, explanations, next question) MUST be in **Spanish**.

### 🎯 TEACHING RULES
1. **Active Challenger**: Do not wait for questions. Always end your turn by assigning a new **Translation Challenge** (e.g., "Translate this to Chinese: ...").
2. **Vocabulary Limit**: STRICTLY limit Chinese vocabulary to **HSK1 Unit 1-11**. Do not use words from Unit 12+.
3. **Correction Style**: 
   - If WRONG: Do not give the answer immediately. Give a hint about the grammar rule.
   - If RIGHT: Praise the specific grammar point used correctly, then give the next question.

### 📚 UNIT 11 GRAMMAR SCOPE
1. **Time Expression "...前" ( ... qián)**
   - Rule: Placed AFTER the time/action (e.g., "Three days ago" -> "San tian qian").
   - Challenge: "Before 5 o'clock", "Before going home".
2. **Duration (Time Spent)**
   - Rule: Verb + Duration (e.g., "Sleep for 8 hours" -> "Shui ba ge xiaoshi").
   - Challenge: "I want to live in Beijing for 3 years."
3. **Special Question Questions**
   - Rule: Question words do NOT move to the front.
   - Challenge: "What time do you go?", "When do you return?".
"""

# --- 4. 初始化模型 (使用稳定版 -001) ---
try:
    # 使用 -001 后缀，这在美国节点上是最稳定的版本
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-001", 
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    st.error(f"Model configuration error: {e}")
    st.stop()

# --- 5. 聊天界面逻辑 ---
st.title("🐲 Long Wen HSK1 Challenge (Pro)")

# 初始化历史记录
if "messages" not in st.session_state:
    st.session_state.messages = []

# 显示历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 开场白 (不消耗配额)
if not st.session_state.messages:
    st.info("👋 Welcome! / ¡Bienvenido! \n\nPlease type **'Hi'** or **'Hola'** to start!")

# 处理用户输入
if prompt := st.chat_input("Type your answer here..."):
    # 1. 显示用户的话
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. 调用 AI
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            # 如果是第一次对话，建立 session
            if "chat_session" not in st.session_state:
                st.session_state.chat_session = model.start_chat(history=[])
            
            # 发送给 Google
            response = st.session_state.chat_session.send_message(prompt)
            
            # 显示回答
            message_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            # 错误处理
            st.error(f"Connection Error: {e}")
            if "404" in str(e):
                st.warning("👉 Tip: If you see 404, please try 'Manual Deploy -> Clear build cache' in Render.")
