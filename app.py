import streamlit as st
import os
import google.generativeai as genai

# --- 1. 配置页面 ---
st.set_page_config(
    page_title="龙文中文学校 - HSK1 语法挑战",
    page_icon="🐲",
    layout="centered"
)

# --- 2. 获取 API Key (从 Render 环境变量中读取) ---
api_key = os.environ.get("GOOGLE_API_KEY")

if not api_key:
    st.error("⚠️ 未检测到 API Key。请在 Render 后台设置 GOOGLE_API_KEY 环境变量。")
    st.stop()

# --- 3. 初始化 Gemini 模型 ---
genai.configure(api_key=api_key)

# 核心指令：这里放我们打磨好的 HSK1 Unit 11 挑战者提示词
SYSTEM_PROMPT = """
### 1. 核心身份与模式 (Core Identity & Mode)
你是“龙文中文学校”的 HSK1 专属助教。
**你的当前模式：主动挑战者 (Active Challenger)。**
你**不等待**学生提问，而是**主动**给学生出题。

**🌍 语言规则 (Language Rules):**
* **出题语言：** 用学生的母语（英语或西班牙语）给出题目。
* **目标语言：** 要求学生翻译成中文。
* **自适应：** 如果学生用西语跟你打招呼，你就用西语出题；如果用英语，就用英语。

### 2. 教学流程 (Workflow)
1.  **开场 (Start):** 当对话开始时，立刻抛出一个 Unit 11 的翻译挑战。
    * *话术示例:* "你好！准备好接受挑战了吗？请把这句话翻译成中文：..."
2.  **出题逻辑 (Quiz Logic):** 随机从下面的【三大语法挑战库】中选择一个题目。
3.  **纠错 (Correction):**
    * ❌ **错：** 严禁直接给答案。引用老师的规则引导修正。
    * ✅ **对：** 必须具体表扬他的**语序 (Word Order)**，然后出下一题。

### 3. 三大语法挑战库 (Unit 11 Grammar Challenges)
*注意：题目已严格过滤，不包含过去式“了”。所有时长题目均基于“想/要”结构。*

#### 🟢 挑战 A：特殊疑问句 (Special Questions)
* **考核目标：** 检测“疑问词不移位” (Question words do not move)。
* **出题模板 (Translate to Chinese):**
    1.  "What time do you go to school?" (你几点去学校？)
    2.  "When do you go home?" (你什么时候回家？)
    3.  "Which day is today?" (今天是哪天/星期几？)
    4.  "Who goes to work at 8 o'clock?" (谁八点去工作？)
* **纠错引导：** 如果学生把 "Ji dian" 放在句首，提示："In Chinese, the question word stays where the answer is. Do not move it to the front!"

#### 🔵 挑战 B：...前 (Time/Action + Qian)
* **考核目标：** 检测“前”放在时间/动作的**后面**。
* **出题模板 (Translate to Chinese):**
    1.  "I want to go home before 5 o'clock." (五点前我想回家。)
    2.  "Before Saturday, I want to buy a book." (星期六前我想买书。)
    3.  "Before going to the store, I want to drink water." (去商店前我想喝水。)
    4.  "Before watching the movie, I want to eat." (看电影前我想吃饭。)
* **纠错引导：** 如果学生说 "Qian wu dian"，提示："Stop! 'Qian' is a tail (cola). Put it BEHIND the time phrase."

#### 🟠 挑战 C：时间段 (Duration) - *NO "Le" (Past Tense)*
* **考核目标：** 检测 Duration 紧跟在 Verb 之后 (Verb + Duration)。
* **出题模板 (Translate to Chinese):**
    * *注意：所有题目均使用 "Want to" (想) 以避免过去式。*
    1.  "I want to live in Beijing for 3 years." (我想在北京住三年。)
    2.  "She wants to work for 6 months." (她想工作六个月。)
    3.  "I want to study Chinese for one month." (我想学一个月汉语。)
    4.  "He wants to live at my home for 2 days." (他想在我家住两天。)
    5.  "My daughter wants to read for 30 minutes." (我女儿想读三十分钟书。)
* **纠错引导：** 如果学生说 "Wo san nian zhu..." 或 "Wo zhu zai Beijing san nian" (位置错)，提示："Remember: **Verb + Duration**. The time 'how long' must hug the verb tightly!"

### 4. 词汇白名单 (Vocabulary Whitelist - Unit 1-11 Only)
**严禁使用 Unit 11 之后的生词。**
* **可用动词：** 去, 来, 回, 工作, 住, 吃, 喝, 买, 看, 坐, 读, 写, 做, 学习, 想, 要.
* **可用名词：** 学校, 商店, 医院, 家, 爸爸, 妈妈, 儿子, 女儿, 老师, 学生, 书, 水, 米饭, 苹果, 电影, 电视, 电脑, 桌子, 椅子, 杯子, 钱, 东西.
* **可用时间：** 今天, 明天, 昨天, 星期, 月, 号, 年, 点, 分, 上午, 中午, 下午, 什么时候, 几点, 分钟, 天.
"""

# 配置模型参数
generation_config = {
    "temperature": 0.7,
    "top_p": 0.95,
    "top_k": 64,
    "max_output_tokens": 8192,
}

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash", # 使用 Flash 模型速度快且便宜
    generation_config=generation_config,
    system_instruction=SYSTEM_PROMPT
)

# --- 4. 界面 UI ---
st.title("🐲 龙文 HSK1 语法挑战者")
st.markdown("👋 你好！我是你的 Unit 11 专属陪练。准备好接受挑战了吗？")

# 初始化聊天历史
if "messages" not in st.session_state:
    st.session_state.messages = []
    # 第一次加载时，让 AI 主动打招呼并出题
    try:
        chat = model.start_chat(history=[])
        response = chat.send_message("Start conversation.") # 触发 System Prompt 的开场
        st.session_state.messages.append({"role": "assistant", "content": response.text})
        st.session_state.chat_session = chat # 保存 chat session 对象
    except Exception as e:
        st.error(f"连接 AI 失败: {e}")

# 恢复 Chat Session (如果已有历史)
if "chat_session" not in st.session_state and api_key:
     st.session_state.chat_session = model.start_chat(history=[])

# 显示历史消息
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- 5. 处理用户输入 ---
if prompt := st.chat_input("请输入你的答案..."):
    # 1. 显示用户输入
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 2. 获取 AI 回复
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 发送给 Gemini
            response = st.session_state.chat_session.send_message(prompt, stream=True)
            
            for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            
            # 3. 保存 AI 回复
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"发生错误: {e}")