
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
    st.error("⚠️ 未检测到 API Key。请在 Render 后台 Settings -> Environment Variables 中设置 GOOGLE_API_KEY。")
    st.stop()

# --- 3. 初始化模型 ---
genai.configure(api_key=api_key)

# 核心指令：基于老师的教学文档打磨
SYSTEM_PROMPT = """
### 1. 核心身份与模式
你是“龙文中文学校”的 HSK1 专属助教。你的当前模式是：主动挑战者 (Active Challenger)。
你主动给学生出题，检测 Unit 11 语法。

**🌍 语言规则:**
* 根据学生使用的语言（英语或西班牙语）进行引导和出题。
* 严禁使用 Unit 11 之后的生词。

### 2. 教学流程
1. **开场:** 立刻抛出一个翻译挑战。
2. **纠错:** - 错：引导修正，不给答案。
   - 对：表扬语序 (Word Order)，出下一题。

### 3. 三大语法挑战库 (Unit 11)
*注意：不包含“了”，使用“想/要”结构。*
- **特殊疑问句:** 疑问词不移位（如：你几点去？）。
- **...前:** “前”放在后面（如：回家前）。
- **时间段:** Verb + Duration（如：住三年）。
"""

# 配置参数
generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 2048,
}

# --- 关键修复：换用 1.5-flash-8b 避开 429 配额限制 ---
try:
    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-8b", 
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
        # 发送指令让 AI 开始第一题
        response = chat.send_message("Please start the challenge now.")
        st.session_state.messages.append({"role": "assistant", "content": response.text})
    except Exception as e:
        # 如果还是报 429 错误，显示冷静提示
        if "429" in str(e):
            st.warning("☕ 助教正在休息（Google API 配额限制），请等待 1-2 分钟后刷新页面重试。")
        else:
            st.error(f"连接失败: {e}")

# 显示历史
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 处理输入
if prompt := st.chat_input("请输入你的答案..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        try:
            response = st.session_state.chat_session.send_message(prompt)
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.markdown(f"助教忙碌中，请稍后再试。错误: {e}")
