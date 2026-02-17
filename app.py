import streamlit as st
import os
import google.generativeai as genai

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="Long Wen - HSK1 Grammar (Lite)",
    page_icon="🐲",
    layout="centered"
)

# --- 2. 获取 API Key ---
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ Error: API Key not found.")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. 核心指令 (双语版) ---
SYSTEM_PROMPT = """
You are the elite HSK1 Grammar Teaching Assistant for "Long Wen Chinese School".
Your sole purpose is to challenge students on **Unit 11 Grammar Points**.

### 🌍 LANGUAGE PROTOCOL
1. **DETECT**: If student uses English -> You use English.
2. **DETECT**: If student uses Spanish -> You use Spanish.

### 🎯 TEACHING RULES
1. **Active Challenger**: Always end with a translation question.
2. **Vocabulary**: STRICTLY HSK1 Unit 1-11 only.
3. **Scope**: 
   - Time "...qian" (Before...)
   - Duration (Verb + Time)
   - Question Words (No movement)
"""

# --- 4. 关键修改：使用您名单里存在的 2.0 Lite 模型 ---
# 既然 1.5 不在您的列表里，我们用这个！
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash-lite-001", 
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    st.error(f"Model config error: {e}")
    st.stop()

# --- 5. 界面逻辑 ---
st.title("🐲 Long Wen HSK1 Challenge")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if not st.session_state.messages:
    st.info("👋 Ready! Please type **'Hi'** or **'Hola'**.")

if prompt := st.chat_input("Type your answer here..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            if "chat_session" not in st.session_state:
                st.session_state.chat_session = model.start_chat(history=[])
            
            response = st.session_state.chat_session.send_message(prompt)
            message_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Error: {e}")
            if "429" in str(e):
                st.warning("🚦 Speed limit! Please wait 10 seconds.")
