import streamlit as st
import os
import google.generativeai as genai

# --- 1. 页面与全局配置 (Bilingual UI) ---
st.set_page_config(
    page_title="Long Wen - Smart Hub / Centro Inteligente",
    page_icon="🐲",
    layout="wide"
)

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ Error: API Key not found / Clave API no encontrada.")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 📚 核心知识库 (HSK1 Grammar Rules)
# ==========================================
KNOWLEDGE_BASE = {
    "Unit 1: 打招呼 (Hello)": {"grammar": "1. 人称复数加 '们'. 2. 打招呼: 你好, 您好.", "vocab": "我, 你, 他, 她, 您, 们, 好, 再见"},
    "Unit 2: 名字与道歉": {"grammar": "1. 对不起 vs 没关系. 2. 什么 (What) 放动词后.", "vocab": "叫, 什么, 名字, 是, 老师, 吗, 学生, 人, 对不起, 没关系"},
    "Unit 3: 国籍与 SVO 结构": {"grammar": "1. 国家+人. 2. 严格 SVO 结构. 3. 否定词'不'在动词前.", "vocab": "有, 个, 爸爸, 妈妈, 哥哥, 弟弟, 妹妹, 和, 没, 不"},
    "Unit 4: 的 & 呢": {"grammar": "1. 归属词 '的'. 2. 疑问词 '呢' (你的呢?). 3. 哪国不倒装.", "vocab": "他, 她, 谁, 的, 汉语, 哪, 国, 呢, 同学, 朋友"},
    "Unit 5: 数字与量词": {"grammar": "1. 必须使用量词 (Number+MW+Noun). 2. '几'的用法.", "vocab": "几, 岁, 了, 今年, 多, 大, 两, 个, 口"},
    "Unit 6: 会 & 怎么": {"grammar": "1. 会 (can). 2. 怎么 (how to).", "vocab": "会, 说, 菜, 很, 好吃, 做, 写, 汉字, 字, 怎么, 读"},
    "Unit 7: 日期与去": {"grammar": "1. 时间从大到小 (月+号+星期). 2. 去+地点.", "vocab": "请, 问, 今天, 号, 月, 星期, 昨天, 明天, 去, 学校, 看, 书"},
    "Unit 8: 想 & 多少钱": {"grammar": "1. 想 (want to). 2. 多少钱 (how much).", "vocab": "想, 喝, 茶, 吃, 米饭, 下午, 商店, 买, 个, 杯子, 这, 多少, 钱, 块, 那"},
    "Unit 9: 方位词": {"grammar": "方位词在名词后 (桌子上). 在+地方.", "vocab": "小, 猫, 在, 那儿, 狗, 椅子, 下面, 哪儿, 工作, 儿子, 医院, 医生"},
    "Unit 10-15: 综合 (Comprehensive)": {"grammar": "综合复习 (能/有, 离合词, 天气, 正在呢, 后/都, 是...的).", "vocab": "HSK1 全部词汇"}
}

# --- 2. 侧边栏双语 UI (Sidebar) ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/dragon.png", width=80)
    st.title("🐲 Long Wen Hub")
    st.markdown("---")
    
    # 模式选择
    role_mode = st.radio(
        "🎭 Select Mode / Elige el modo:",
        ["🧑‍🏫 Teacher / Profesor (Grammar)", "🧑‍🤝‍🧑 Friend / Amigo (Chat)"]
    )
    
    st.markdown("---")
    
    # 动态二级菜单
    if "Teacher" in role_mode:
        selected_unit_name = st.selectbox(
            "📖 Select Unit / Elige la unidad:",
            options=list(KNOWLEDGE_BASE.keys()), 
            index=0
        )
        hsk_level = "HSK 1" # 老师模式锁定在单元级别
    else:
        hsk_level = st.selectbox(
            "📊 Friend's Level / Nivel del amigo:",
            ["HSK 1 (Beginner/Principiante)", 
             "HSK 2 (Basic/Básico)", 
             "HSK 3 (Intermediate/Medio)", 
             "HSK 4 (Fluent/Fluido)", 
             "🌟 Adaptive Mode / Modo Adaptativo"]
        )
        selected_unit_name = "Global HSK"

    # 切换模式清空历史
    current_config = f"{role_mode}_{selected_unit_name}_{hsk_level}"
    if "last_config" not in st.session_state:
        st.session_state.last_config = current_config
    
    if st.session_state.last_config != current_config:
        st.session_state.messages = []
        st.session_state.last_config = current_config
        st.rerun()

# --- 3. 大脑指令 (Dynamic System Prompts) ---

# 通用语言法则
LANGUAGE_PROTOCOL = """
**LANGUAGE PROTOCOL**:
- If the user speaks Spanish -> You MUST explain/chat in Spanish.
- If the user speaks English -> You MUST explain/chat in English.
- If the user speaks Chinese -> You reply in Chinese.
"""

if "Teacher" in role_mode:
    current_unit_data = KNOWLEDGE_BASE[selected_unit_name]
    SYSTEM_PROMPT = f"""
    You are a STRICT but encouraging Chinese Grammar Teacher.
    {LANGUAGE_PROTOCOL}
    
    **Unit Focus**: {selected_unit_name}
    **Grammar Rules**: {current_unit_data['grammar']}
    **Vocabulary Limit**: {current_unit_data['vocab']}
    
    **WORKFLOW (THE 10-SENTENCE TEST)**:
    1. When the user first says "Hi" or "Hola", you MUST reply exactly with this translation in the user's language: 
       "Let's test the grammar of this unit together. We will do 10 sentences. Sentence 1: [Give them the 1st sentence to translate into Chinese based on the Unit's grammar]."
    2. Visually track progress like this: [1/10], [2/10].
    3. **THE PENALTY RULE**: If the user makes a grammar mistake:
       - Explain the mistake gently using scaffolding (ask guiding questions).
       - Once they fix it, you MUST generate 2 ADDITIONAL penalty practice sentences using the EXACT SAME grammar structure before moving to the next main sentence.
    """
else:
    SYSTEM_PROMPT = f"""
    You are a Chinese native speaker acting as a language partner (Friend Mode).
    {LANGUAGE_PROTOCOL}
    
    **Current Level Strategy**: {hsk_level}
    - If "HSK 1" or "HSK 2": Use very short sentences, simple vocab, lots of emojis.
    - If "HSK 3" or "HSK 4": Normal conversational speed, natural idioms, discuss hobbies/life.
    - **If "Adaptive Mode"**: Start at HSK 1. SILENTLY analyze the user's input. If they use complex sentences/conjunctions, dynamically upgrade your vocabulary to HSK 2/3. If they make basic errors or say they don't understand, instantly downgrade back to HSK 1. DO NOT announce level changes.
    
    **Rule**: NEVER act like a teacher. Do not correct minor mistakes unless communication totally breaks down. Focus on keeping the conversation flowing naturally.
    
    **OUTPUT FORMATTING (CRITICAL)**:
    Whenever you speak Chinese, you MUST output in this exact 3-line format:
    [Chinese Characters]
    ([Pinyin with tone marks])
    [Spanish/English translation depending on user's preference]
    """

# --- 4. 初始化模型 ---
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", 
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 5. 聊天界面 ---
if "Teacher" in role_mode:
    st.header(f"🧑‍🏫 Grammar Test / Prueba de Gramática: {selected_unit_name.split(':')[0]}")
else:
    st.header(f"🧑‍🤝‍🧑 Language Partner / Compañero de Idiomas")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if not st.session_state.messages:
    if "Teacher" in role_mode:
        st.info("Say **'Hi'** or **'Hola'** to start your 10-sentence challenge! / ¡Di 'Hola' para comenzar tu reto de 10 frases!")
    else:
        st.info("Say **'Hi'** or **'Hola'** to chat! / ¡Di 'Hola' para charlar!")

if prompt := st.chat_input("Type here... / Escribe aquí..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            chat = model.start_chat(history=[
                {"role": m["role"], "parts": [m["content"]]} 
                for m in st.session_state.messages[:-1]
            ])
            
            response = chat.send_message(prompt)
            message_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Connection Error: {e}")
