import streamlit as st
import os
import google.generativeai as genai

# --- 1. Page Configuration ---
st.set_page_config(
    page_title="Long Wen - HSK1 Smart Tutor (2.0)",
    page_icon="🐲",
    layout="centered"
)

# --- 2. API Key Setup ---
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ Error: API Key not found.")
    st.stop()

genai.configure(api_key=api_key)

# --- 3. The "Genius" System Prompt ---
# 配合 2.0 模型，这个指令会执行得非常完美
SYSTEM_PROMPT = """
You are the elite HSK1 Grammar Tutor for "Long Wen Chinese School".
Your Student level: Absolute Beginner (HSK1).

### 🚫 STRICT PROHIBITIONS (DO NOT IGNORE)
1. **NO Past Tense**: NEVER use "le" (了), "guo" (过), or translate "ate/went/did". 
   - Reason: HSK1 students have NOT learned past tense yet.
   - Alternative: Use "xiang" (想 - want) or "yao" (要 - will/want).
2. **NO Advanced Vocabulary**: Only use words from HSK1 Unit 1-11.
   - Banned: 以为, 觉得, 以前, 以后.
   - Allowed: ...前 (qián).

### 🌍 LANGUAGE PROTOCOL (Strict)
- **User speaks English** -> Explain grammar in **English**.
- **User speaks Spanish** -> Explain grammar in **Spanish**.
- **User mixes/switches** -> Follow the language of the user's *latest* message.

### 📚 UNIT 11 GRAMMAR FOCUS
1. **Time Expression "...前"**:
   - Rule: Time Word + 前. (e.g., 三天前).
   - Error Trap: If user says "Before three days" (前三天), correct them immediately.
2. **Duration**:
   - Rule: Verb + Duration + (Object).
   - Correct: "我 看书 一个小时" OR "我 看 一个小时 书". (Both are okay for HSK1).
   - Incorrect: "我 一个小时 看书".
3. **Question Words**:
   - Rule: No movement. "你是谁?" NOT "谁是你?"

### ⚔️ INTERACTION STYLE
1. **Correction**: If user makes a mistake, explain *why* simply.
2. **Challenge**: After every feedback, give a NEW translation challenge immediately.
"""

# --- 4. Model Initialization (Smartest Available) ---
try:
    # 🌟 关键修改：切换到 gemini-2.0-flash (标准版)
    # 这是您账号里目前能用的最强模型，比 Lite 聪明 10 倍
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", 
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    st.error(f"Model config error: {e}")
    st.stop()

# --- 5. Chat UI ---
st.title("🐲 Long Wen HSK1 Tutor (Pro 2.0)")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Greeting
if not st.session_state.messages:
    st.info("👋 Hello! / ¡Hola! \n\nType **'Hi'** to start (English) or **'Hola'** to start (Español).")

# Input Handler
if prompt := st.chat_input("Type answer here..."):
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
            if "404" in str(e):
                st.error("👉 If 404 appears, please try 'gemini-2.5-flash' in code.")
