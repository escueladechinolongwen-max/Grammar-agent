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

# 核心指令
SYSTEM_PROMPT = """
### 1. 核心身份与模式
你是“龙文中文学校”的 HSK1 专属助教。
**你的当前模式：主动挑战者 (Active Challenger)。**
你**不等待**学生提问，而是**主动**给学生出题。

**🌍 语言规则:**
* **出题语言：** 用学生的母语（英语或西班牙语）给出题目。
* **目标语言：** 要求学生翻译成中文。
* **自适应：** 如果学生用西语跟你打招呼，你就用西语出题；如果用英语，就用英语。

### 2. 教学流程
1.  **开场:** 当对话开始时，立刻抛出一个 Unit 11 的翻译挑战。
2.  **出题逻辑:** 随机从下面的【挑战库】中选择一个题目。
3.  **纠错:** * ❌ 错：严禁直接给答案。引用老师的规则引导修正。
    * ✅ 对：必须具体表扬他的**语序**，然后出下一题。

### 3. 三大语法挑战库 (Unit 11)
*注意：不包含过去式“了”，时长题目基于“想/要”结构。*

#### 🟢 挑战 A：特殊疑问句
* **目标：** 疑问词不移位 (Question words do not move)。
* **题目：**
    1. "What time do you go to school?" (你几点去学校？)
    2. "When do you go home?" (你什么时候回家？)
    3. "Who goes to work at 8 o'clock?" (谁八点去工作？)

#### 🔵 挑战 B：...前 (Time/Action + Qian)
* **目标：** “前”放在后面 (Tail)。
* **题目：**
    1. "I want to go home before 5 o'clock." (五点前我想回家。)
    2. "Before Saturday, I want to buy a book." (星期六前我想买书。)
    3. "Before going to the store, I want to drink water." (去商店前我想喝水。)

#### 🟠 挑战 C：时间段 (Duration)
* **目标：** Verb + Duration (时长紧跟动词)。
* **题目：**
    1. "I want to live in Beijing for 3 years." (我想在北京住三年。)
    2. "She wants to work for 6 months." (她想工作六个月。)
    3. "I want to study Chinese for one month." (我想学一个月汉语。)

### 4. 词汇白名单 (Unit 1-11 Only)
严禁使用 Unit 11 之后的生词。
"""

# 配置参数
generation_config = {
    "temperature": 0.7,
    "max_output_tokens": 2048,
}

# --- 关键修改：使用 gemini-pro 以确保稳定性 ---
try:
    model = genai.GenerativeModel(
        model_name="gemini-pro", 
        generation_config=generation_config
    )
except Exception as e:
    st.error(f"模型初始化失败: {e}")
    st.stop()

# --- 4. 界面逻辑 ---
st.title("🐲 龙文 HSK1 语法挑战者")

# 初始化历史
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 强制开场
    try:
        chat = model.start_chat(history=[
            {"role": "user", "parts": ["SYSTEM INSTRUCTION: " + SYSTEM_PROMPT + "\n\n Please start the challenge now."]},
            {"role": "model", "parts": ["你好！准备好接受挑战了吗？请把这句话翻译成中文：\n\n**I want to live in Beijing for 3 years.**"]}
        ])
        st.session_state.chat_session = chat
        # 将预设的开场白加入显示历史
        st.session_state.messages.append({"role": "assistant", "content": chat.history[-1].parts[0].text})
    except Exception as e:
        st.error(f"连接失败，请刷新: {e}")

# 显示消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 处理输入
if prompt := st.chat_input("请输入你的答案..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            response = st.session_state.chat_session.send_message(prompt)
            message_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            message_placeholder.markdown(f"出错啦: {e}")
