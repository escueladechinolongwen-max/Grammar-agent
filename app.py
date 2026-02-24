import streamlit as st
import os
import google.generativeai as genai

# --- 1. 页面与全局配置 ---
st.set_page_config(
    page_title="Long Wen Hub",
    page_icon="🐲",
    layout="wide"
)

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ Error: API Key not found.")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 📚 核心知识库 (带双语标题映射)
# ==========================================
KNOWLEDGE_BASE = {
    "u1": {
        "title_en": "Unit 1: Greetings", "title_es": "Unidad 1: Saludos",
        "grammar": "1. 人称复数加 '们'. 2. 打招呼: 你好, 您好.", "vocab": "我, 你, 他, 她, 您, 们, 好, 再见"
    },
    "u2": {
        "title_en": "Unit 2: Names & Apologies", "title_es": "Unidad 2: Nombres y disculpas",
        "grammar": "1. 对不起 vs 没关系. 2. 什么 (What) 放动词后.", "vocab": "叫, 什么, 名字, 是, 老师, 吗, 学生, 人, 对不起, 没关系"
    },
    "u3": {
        "title_en": "Unit 3: Nationality & SVO", "title_es": "Unidad 3: Nacionalidad y Estructura SVO",
        "grammar": "1. 国家+人. 2. 严格 SVO 结构. 3. 否定词'不'在动词前.", "vocab": "有, 个, 爸爸, 妈妈, 哥哥, 弟弟, 妹妹, 和, 没, 不"
    },
    "u4": {
        "title_en": "Unit 4: Particles 'de' & 'ne'", "title_es": "Unidad 4: Partículas 'de' y 'ne'",
        "grammar": "1. 归属词 '的'. 2. 疑问词 '呢' (你的呢?). 3. 哪国不倒装.", "vocab": "他, 她, 谁, 的, 汉语, 哪, 国, 呢, 同学, 朋友"
    },
    "u5": {
        "title_en": "Unit 5: Numbers & Measure Words", "title_es": "Unidad 5: Números y Clasificadores",
        "grammar": "1. 必须使用量词 (Number+MW+Noun). 2. '几'的用法.", "vocab": "几, 岁, 了, 今年, 多, 大, 两, 个, 口"
    },
    "u6": {
        "title_en": "Unit 6: 'hui' & 'zenme'", "title_es": "Unidad 6: 'hui' y 'zenme'",
        "grammar": "1. 会 (can). 2. 怎么 (how to).", "vocab": "会, 说, 菜, 很, 好吃, 做, 写, 汉字, 字, 怎么, 读"
    },
    "u7": {
        "title_en": "Unit 7: Dates & 'qu' (to go)", "title_es": "Unidad 7: Fechas y 'qu' (ir)",
        "grammar": "1. 时间从大到小 (月+号+星期). 2. 去+地点.", "vocab": "请, 问, 今天, 号, 月, 星期, 昨天, 明天, 去, 学校, 看, 书"
    },
    "u8": {
        "title_en": "Unit 8: 'xiang' & Prices", "title_es": "Unidad 8: 'xiang' y Precios",
        "grammar": "1. 想 (want to). 2. 多少钱 (how much).", "vocab": "想, 喝, 茶, 吃, 米饭, 下午, 商店, 买, 个, 杯子, 这, 多少, 钱, 块, 那"
    },
    "u9": {
        "title_en": "Unit 9: Location Words", "title_es": "Unidad 9: Palabras de ubicación",
        "grammar": "方位词在名词后 (桌子上). 在+地方.", "vocab": "小, 猫, 在, 那儿, 狗, 椅子, 下面, 哪儿, 工作, 儿子, 医院, 医生"
    },
    "u10_15": {
        "title_en": "Units 10-15: Comprehensive Review", "title_es": "Unidades 10-15: Repaso general",
        "grammar": "综合复习 (能/有, 离合词, 天气, 正在呢, 后/都, 是...的).", "vocab": "HSK1 全部词汇"
    }
}

# --- 2. 侧边栏 UI 设置 ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/dragon.png", width=80)
    
    # 全局语言切换器
    ui_lang = st.radio("🌐 UI Language / Idioma:", ["English", "Español"], horizontal=True)
    
    # 根据语言定义界面文本
    if ui_lang == "English":
        st.title("🐲 Long Wen Hub")
        btn_clear = "🧹 Clear History"
        lbl_mode = "🎭 Select Mode:"
        mode_options = ["🧑‍🏫 Teacher (Grammar)", "🧑‍🤝‍🧑 Friend (Chat)"]
        lbl_unit = "📖 Select Unit:"
        lbl_level = "📊 Friend's Level:"
        level_options = ["HSK 1 (Beginner)", "HSK 2 (Basic)", "HSK 3 (Intermediate)", "HSK 4 (Fluent)", "🌟 Adaptive Mode"]
    else:
        st.title("🐲 Centro Long Wen")
        btn_clear = "🧹 Borrar historial"
        lbl_mode = "🎭 Elige el modo:"
        mode_options = ["🧑‍🏫 Profesor (Gramática)", "🧑‍🤝‍🧑 Amigo (Chat)"]
        lbl_unit = "📖 Elige la unidad:"
        lbl_level = "📊 Nivel del amigo:"
        level_options = ["HSK 1 (Principiante)", "HSK 2 (Básico)", "HSK 3 (Intermedio)", "HSK 4 (Fluido)", "🌟 Modo Adaptativo"]

    # 一键清空按钮
    if st.button(btn_clear, use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")
    
    role_mode = st.radio(lbl_mode, mode_options)
    
    st.markdown("---")
    
    # 动态显示下拉菜单 (利用 format_func 映射纯净的语言标题)
    if "Teacher" in role_mode or "Profesor" in role_mode:
        selected_unit_key = st.selectbox(
            lbl_unit,
            options=list(KNOWLEDGE_BASE.keys()), 
            format_func=lambda x: KNOWLEDGE_BASE[x]["title_en"] if ui_lang == "English" else KNOWLEDGE_BASE[x]["title_es"]
        )
        hsk_level_text = "HSK 1" 
    else:
        selected_level_index = st.selectbox(lbl_level, options=range(len(level_options)), format_func=lambda x: level_options[x])
        hsk_level_text = level_options[selected_level_index]
        selected_unit_key = "u10_15" # 朋友模式默认全图鉴

    # 切换配置自动清空历史
    current_config = f"{role_mode}_{selected_unit_key}_{hsk_level_text}_{ui_lang}"
    if "last_config" not in st.session_state:
        st.session_state.last_config = current_config
    
    if st.session_state.last_config != current_config:
        st.session_state.messages = []
        st.session_state.last_config = current_config
        st.rerun()

# --- 3. 动态构建 AI 大脑 ---
current_unit_data = KNOWLEDGE_BASE[selected_unit_key]
unit_focus_name = current_unit_data["title_en"] if ui_lang == "English" else current_unit_data["title_es"]

LANGUAGE_PROTOCOL = f"""
**CRITICAL UI LANGUAGE**: 
The user's interface is currently set to **{ui_lang}**. 
You MUST communicate with the user entirely in {ui_lang} (except for the Chinese you are teaching).
If the user speaks a different language, switch to their language naturally, but default your system messages to {ui_lang}.
"""

if "Teacher" in role_mode or "Profesor" in role_mode:
    SYSTEM_PROMPT = f"""
    You are a STRICT but encouraging Chinese Grammar Teacher.
    {LANGUAGE_PROTOCOL}
    
    **Unit Focus**: {unit_focus_name}
    **Grammar Rules**: {current_unit_data['grammar']}
    **Vocabulary Limit**: {current_unit_data['vocab']}
    
    **WORKFLOW (THE 10-SENTENCE TEST)**:
    1. When the user says "Hi" or "Hola", reply in {ui_lang}: 
       "Let's test the grammar of this unit together. We will do 10 sentences. Sentence 1: [Provide translation challenge]."
       (Translate this intro naturally into {ui_lang}).
    2. Track progress visually: [1/10], [2/10].
    3. **THE PENALTY RULE**: If they make a mistake, explain gently via scaffolding. Once fixed, generate 2 ADDITIONAL penalty practice sentences using the EXACT SAME structure before advancing.
    """
else:
    SYSTEM_PROMPT = f"""
    You are a friendly Chinese native speaker (Language Partner).
    {LANGUAGE_PROTOCOL}
    
    **Current Level Strategy**: {hsk_level_text}
    - If "HSK 1" or "HSK 2": Use very short sentences, simple vocab, emojis.
    - If "HSK 3" or "HSK 4": Normal conversational speed, natural idioms.
    - **If "Adaptive Mode"**: Start at HSK 1. SILENTLY analyze input. Upgrade to HSK 2/3 if they use complex structures. Downgrade instantly if they struggle. DO NOT announce changes.
    
    **OUTPUT FORMATTING (CRITICAL)**:
    When speaking Chinese, output EXACTLY this 3-line format:
    [Chinese Characters]
    ([Pinyin with tone marks])
    [{ui_lang} translation]
    """

# --- 4. 初始化模型 ---
try:
    model = genai.GenerativeModel(model_name="gemini-2.0-flash", system_instruction=SYSTEM_PROMPT)
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 5. 聊天界面 ---
if "Teacher" in role_mode or "Profesor" in role_mode:
    header_text = f"🧑‍🏫 {unit_focus_name}"
    welcome_text = "Say **'Hi'** to start your 10-sentence challenge!" if ui_lang == "English" else "¡Di **'Hola'** para comenzar tu reto de 10 frases!"
else:
    header_text = "🧑‍🤝‍🧑 Language Partner" if ui_lang == "English" else "🧑‍🤝‍🧑 Compañero de Idiomas"
    welcome_text = "Say **'Hi'** to chat!" if ui_lang == "English" else "¡Di **'Hola'** para charlar!"

st.header(header_text)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if not st.session_state.messages:
    st.info(welcome_text)

chat_placeholder = "Type here..." if ui_lang == "English" else "Escribe aquí..."

if prompt := st.chat_input(chat_placeholder):
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
            st.error(f"Error: {e}")
