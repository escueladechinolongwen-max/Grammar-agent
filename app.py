import streamlit as st
import os
import google.generativeai as genai
import asyncio
import edge_tts
import tempfile
import re
import random  
from streamlit_mic_recorder import speech_to_text

# --- 1. 页面与全局配置 ---
st.set_page_config(
    page_title="Long Wen Hub",
    page_icon="🐲",
    layout="wide"
)

# ==========================================
# 🔑 核心魔法：智能密钥轮询池 (API Key Pooling)
# ==========================================
raw_keys = os.environ.get("GOOGLE_API_KEY")
if not raw_keys:
    st.error("⚠️ Error: API Key not found. Please set GOOGLE_API_KEY in Render.")
    st.stop()

# 自动把 Render 里用逗号隔开的多把钥匙拆分出来
API_KEYS = [k.strip() for k in raw_keys.split(",") if k.strip()]

if not API_KEYS:
    st.error("⚠️ Error: No valid API Keys found.")
    st.stop()

# 每次发送消息时，随机抽一把钥匙，完美分摊流量防封锁！
selected_key = random.choice(API_KEYS)
genai.configure(api_key=selected_key)

# ==========================================
# 📚 核心知识库 & 剧本库 (Knowledge & Scenarios)
# ==========================================
KNOWLEDGE_BASE = {
    "u1": {"title_en": "Unit 1: Greetings", "title_es": "Unidad 1: Saludos", "grammar": "1. 人称复数加 '们'. 2. 打招呼: 你好, 您好.", "vocab": "我, 你, 他, 她, 您, 们, 好, 再见"},
    "u2": {"title_en": "Unit 2: Names & Apologies", "title_es": "Unidad 2: Nombres y disculpas", "grammar": "1. 对不起 vs 没关系. 2. 什么 (What) 放动词后.", "vocab": "叫, 什么, 名字, 是, 老师, 吗, 学生, 人, 对不起, 没关系"},
    "u3": {"title_en": "Unit 3: Nationality & SVO", "title_es": "Unidad 3: Nacionalidad y Estructura SVO", "grammar": "1. 国家+人. 2. 严格 SVO 结构. 3. 否定词'不'在动词前.", "vocab": "有, 个, 爸爸, 妈妈, 哥哥, 弟弟, 妹妹, 和, 没, 不"},
    "u4": {"title_en": "Unit 4: Particles 'de' & 'ne'", "title_es": "Unidad 4: Partículas 'de' y 'ne'", "grammar": "1. 归属词 '的'. 2. 疑问词 '呢' (你的呢?). 3. 哪国不倒装.", "vocab": "他, 她, 谁, 的, 汉语, 哪, 国, 呢, 同学, 朋友"},
    "u5": {"title_en": "Unit 5: Numbers & Measure Words", "title_es": "Unidad 5: Números y Clasificadores", "grammar": "1. 必须使用量词 (Number+MW+Noun). 2. '几'的用法.", "vocab": "几, 岁, 了, 今年, 多, 大, 两, 个, 口, 狗, 猫, 杯子, 朋友"},
    "u6": {"title_en": "Unit 6: 'hui' & 'zenme'", "title_es": "Unidad 6: 'hui' y 'zenme'", "grammar": "1. 会 (can). 2. 怎么 (how to).", "vocab": "会, 说, 菜, 很, 好吃, 做, 写, 汉字, 字, 怎么, 读"},
    "u7": {"title_en": "Unit 7: Dates & 'qu'", "title_es": "Unidad 7: Fechas y 'qu' (ir)", "grammar": "1. 时间从大到小. 2. 去+地点.", "vocab": "请, 问, 今天, 号, 月, 星期, 昨天, 明天, 去, 学校, 看, 书"},
    "u8": {"title_en": "Unit 8: 'xiang' & Prices", "title_es": "Unidad 8: 'xiang' y Precios", "grammar": "1. 想 (want to). 2. 多少钱 (how much).", "vocab": "想, 喝, 茶, 吃, 米饭, 下午, 商店, 买, 个, 杯子, 这, 多少, 钱, 块, 那"},
    "u9": {"title_en": "Unit 9: Location Words", "title_es": "Unidad 9: Palabras de ubicación", "grammar": "方位词在名词后. 在+地方.", "vocab": "小, 猫, 在, 那儿, 狗, 椅子, 下面, 哪儿, 工作, 儿子, 医院, 医生"},
    "u10_15": {"title_en": "Units 10-15: Comprehensive", "title_es": "Unidades 10-15: Repaso general", "grammar": "综合复习", "vocab": "HSK1 全部词汇"}
}

SCENARIOS = {
    "cafe": {
        "title_en": "☕ At the Cafe", "title_es": "☕ En la cafetería",
        "npc_prompt": "You are a polite barista at a cafe in Beijing. You ONLY sell Tea (茶) and Water (水), NO coffee.",
        "mission_en": "Order a cup of tea and ask how much it costs.", "mission_es": "Pide una taza de té y pregunta cuánto cuesta."
    },
    "taxi": {
        "title_en": "🚕 Taking a Taxi", "title_es": "🚕 Tomar un taxi",
        "npc_prompt": "You are a Beijing taxi driver. You speak fast but use simple words. Ask the passenger where they want to go.",
        "mission_en": "Tell the driver you want to go to the hospital (医院).", "mission_es": "Dile al conductor que quieres ir al hospital (医院)."
    },
    "shop": {
        "title_en": "🍎 Buying Fruit", "title_es": "🍎 Comprando fruta",
        "npc_prompt": "You are a fruit seller. You are very enthusiastic. Apples (苹果) are 5 Kuai (块) each.",
        "mission_en": "Buy 3 apples and ask for the total price. Don't forget the measure word (个)!", "mission_es": "Compra 3 manzanas y pregunta el precio total. ¡No olvides el clasificador (个)!"
    }
}

VOICE_OPTIONS = {
    "🇨🇳 晓晓 (Xiaoxiao - 女声)": "zh-CN-XiaoxiaoNeural",
    "🇨🇳 云希 (Yunxi - 男声)": "zh-CN-YunxiNeural",
    "🇪🇸 Elvira (西班牙语 - 女声)": "es-ES-ElviraNeural",
    "🇪🇸 Álvaro (西班牙语 - 男声)": "es-ES-AlvaroNeural",
    "🇬🇧 Jenny (英语 - 女声)": "en-US-JennyNeural",
    "🇬🇧 Guy (英语 - 男声)": "en-US-GuyNeural"
}

def generate_tts_audio(text, voice_code, rate="+0%"):
    async def _generate():
        communicate = edge_tts.Communicate(text, voice_code, rate=rate)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            temp_path = fp.name
        await communicate.save(temp_path)
        return temp_path
    return asyncio.run(_generate())

# --- 2. 侧边栏 UI 设置 ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/dragon.png", width=80)
    ui_lang = st.radio("🌐 UI Language / Idioma:", ["English", "Español"], horizontal=True)
    
    if ui_lang == "English":
        st.title("🐲 Long Wen Hub")
        btn_clear = "🧹 Clear History"
        lbl_mode = "🎭 Select Mode:"
        mode_options = ["🧑‍🏫 Teacher (Grammar)", "🧑‍🤝‍🧑 Friend (Chat)", "🎬 Roleplay (Scenarios)"]
        lbl_unit = "📖 Select Unit:"
        lbl_level = "📊 Friend's Level:"
        lbl_scenario = "🎬 Select Scenario:"
        lbl_voice = "🗣️ AI Voice:"
        lbl_speed = "⏱️ Voice Speed:"
        level_options = ["HSK 1", "HSK 2", "HSK 3", "🌟 Adaptive Mode"]
    else:
        st.title("🐲 Centro Long Wen")
        btn_clear = "🧹 Borrar historial"
        lbl_mode = "🎭 Elige el modo:"
        mode_options = ["🧑‍🏫 Profesor (Gramática)", "🧑‍🤝‍🧑 Amigo (Chat)", "🎬 Roleplay (Escenarios)"]
        lbl_unit = "📖 Elige la unidad:"
        lbl_level = "📊 Nivel del amigo:"
        lbl_scenario = "🎬 Elige el escenario:"
        lbl_voice = "🗣️ Voz de la IA:"
        lbl_speed = "⏱️ Velocidad de Voz:"
        level_options = ["HSK 1", "HSK 2", "HSK 3", "🌟 Modo Adaptativo"]

    if st.button(btn_clear, use_container_width=True):
        st.session_state.messages = []
        st.rerun()
        
    st.markdown("---")
    
    selected_voice_label = st.selectbox(lbl_voice, options=list(VOICE_OPTIONS.keys()))
    selected_voice_code = VOICE_OPTIONS[selected_voice_label]
    
    speed_labels = ["🐢 Slow / Lento (-25%)", "🚶 Normal", "🏃 Fast / Rápido (+20%)"]
    speed_values = ["-25%", "+0%", "+20%"]
    selected_speed_index = st.selectbox(lbl_speed, range(len(speed_labels)), index=1, format_func=lambda x: speed_labels[x])
    selected_speed_rate = speed_values[selected_speed_index]
    
    st.markdown("---")
    role_mode = st.radio(lbl_mode, mode_options)
    st.markdown("---")
    
    selected_unit_key, hsk_level_text, selected_scenario_key = None, None, None
    
    if "Teacher" in role_mode or "Profesor" in role_mode:
        selected_unit_key = st.selectbox(lbl_unit, options=list(KNOWLEDGE_BASE.keys()), format_func=lambda x: KNOWLEDGE_BASE[x]["title_en"] if ui_lang == "English" else KNOWLEDGE_BASE[x]["title_es"])
    elif "Friend" in role_mode or "Amigo" in role_mode:
        selected_level_index = st.selectbox(lbl_level, options=range(len(level_options)), format_func=lambda x: level_options[x])
        hsk_level_text = level_options[selected_level_index]
    else:
        selected_scenario_key = st.selectbox(lbl_scenario, options=list(SCENARIOS.keys()), format_func=lambda x: SCENARIOS[x]["title_en"] if ui_lang == "English" else SCENARIOS[x]["title_es"])

    current_config = f"{role_mode}_{selected_unit_key}_{hsk_level_text}_{selected_scenario_key}_{ui_lang}"
    if "last_config" not in st.session_state:
        st.session_state.last_config = current_config
    
    if st.session_state.last_config != current_config:
        st.session_state.messages = []
        st.session_state.last_config = current_config
        st.rerun()

# --- 3. 动态构建 AI 大脑 ---
LANGUAGE_PROTOCOL = f"**CRITICAL UI LANGUAGE**: The user's interface is **{ui_lang}**. Communicate with the user in {ui_lang} (except for the Chinese)."

if "Teacher" in role_mode or "Profesor" in role_mode:
    current_unit_data = KNOWLEDGE_BASE[selected_unit_key]
    unit_focus_name = current_unit_data["title_en"] if ui_lang == "English" else current_unit_data["title_es"]
    SYSTEM_PROMPT = f"""
    You are a STRICT Chinese Grammar Teacher. {LANGUAGE_PROTOCOL}
    **Unit Focus**: {unit_focus_name}
    **Grammar Rules**: {current_unit_data['grammar']}
    
    **🛑 STRICT VOCABULARY LIMIT (CRITICAL)**: 
    You are ONLY allowed to use the following words for sentences: {current_unit_data['vocab']}. 
    NEVER use words outside HSK 1. NEVER use words like "chicken" (鸡) or "bird" (鸟). If you need a noun, pick one strictly from the list!
    
    **Workflow**: When user says "Hi", reply in {ui_lang}: "Let's test the grammar. We will do 10 sentences. Sentence 1: [translation challenge]."
    **Penalty**: If they mistake, explain via scaffolding. Generate 2 PENALTY sentences using the same structure. The penalty sentences MUST strictly follow the Vocabulary Limit!
    
    **OUTPUT FORMAT (STRICT 3 LINES RULE)**: 
    Line 1: <audio>[ALL Chinese characters here ONLY]</audio>
    Line 2: [Pinyin here]
    Line 3: [English/Spanish translation here]
    """
    header_text = f"🧑‍🏫 {unit_focus_name}"
    welcome_text = "Say **'Hi'** to start your 10-sentence challenge!" if ui_lang == "English" else "¡Di **'Hola'** para comenzar el reto!"

elif "Friend" in role_mode or "Amigo" in role_mode:
    SYSTEM_PROMPT = f"""
    You are a friendly Chinese Language Partner engaging in a real-time conversation.
    {LANGUAGE_PROTOCOL}
    
    **YOUR TASK (CRITICAL)**:
    1. DO NOT just translate what the user says. You must REPLY to their message logically and keep the conversation going!
    2. ALWAYS end your turn with a follow-up question to keep the chat alive.
    
    **Level Strategy**: {hsk_level_text}. 
    
    **OUTPUT FORMAT (CRITICAL: STRICTLY 3 LINES. NO EXCEPTIONS.)**:
    Line 1: <audio>[ALL of your Chinese characters here, INCLUDING your follow-up question. Do not leave any Chinese outside this tag!]</audio>
    Line 2: [The ENTIRE Pinyin for Line 1]
    Line 3: [The ENTIRE {ui_lang} translation for Line 1]
    """
    header_text = "🧑‍🤝‍🧑 Language Partner" if ui_lang == "English" else "🧑‍🤝‍🧑 Compañero de Idiomas"
    welcome_text = "Say **'Hi'** to chat!" if ui_lang == "English" else "¡Di **'Hola'** para charlar!"

else:
    current_scenario = SCENARIOS[selected_scenario_key]
    scenario_title = current_scenario["title_en"] if ui_lang == "English" else current_scenario["title_es"]
    mission_text = current_scenario["mission_en"] if ui_lang == "English" else current_scenario["mission_es"]
    
    SYSTEM_PROMPT = f"""
    You are playing a role in a simulation. {LANGUAGE_PROTOCOL}
    **Your Persona**: {current_scenario['npc_prompt']}
    **User's Mission**: {mission_text}
    **Rules**: Never break character. Reply to the user logically. End scenario gracefully if mission is completed.
    
    **OUTPUT FORMAT (CRITICAL: STRICTLY 3 LINES. NO EXCEPTIONS.)**:
    Line 1: <audio>[ALL of your Chinese characters here, INCLUDING any questions. Do not leave any Chinese outside this tag!]</audio>
    Line 2: [The ENTIRE Pinyin for Line 1]
    Line 3: [The ENTIRE {ui_lang} translation for Line 1]
    """
    header_text = f"🎬 {scenario_title}"
    welcome_text = f"**Mission / Misión:** {mission_text}\n\nSay **'Hi'** to enter the scenario!" if ui_lang == "English" else f"**Misión:** {mission_text}\n\n¡Di **'Hola'** para entrar al escenario!"

try:
    # 🌟 终极护盾：使用你名单中真实存在且最高级的 gemini-2.5-pro
    model = genai.GenerativeModel(model_name="gemini-2.5-pro", system_instruction=SYSTEM_PROMPT)
except Exception as e:
    st.error(f"Error: {e}")
    st.stop()

# --- 4. 聊天界面渲染 ---
st.header(header_text)

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if "audio_path" in message and message["audio_path"]:
            st.audio(message["audio_path"], format="audio/mp3")

if not st.session_state.messages:
    st.info(welcome_text)

# --- 5. 双向输入区 (文字 + 麦克风) ---
col1, col2 = st.columns([5, 1])
chat_placeholder = "Type here..." if ui_lang == "English" else "Escribe aquí..."
spoken_text = None

with col1:
    written_text = st.chat_input(chat_placeholder)

with col2:
    spoken_text = speech_to_text(
        language='zh-CN',
        start_prompt="🎤",
        stop_prompt="⏹️",
        just_once=True,
        key='STT'
    )

prompt = written_text or spoken_text

if prompt:
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            safe_history = []
            for m in st.session_state.messages[:-1]:
                role_name = "model" if m["role"] == "assistant" else "user"
                safe_history.append({"role": role_name, "parts": [m["content"]]})
                
            chat = model.start_chat(history=safe_history)
            response = chat.send_message(prompt)
            
            # 提取音频标签内的纯中文
            audio_texts = re.findall(r'<audio>(.*?)</audio>', response.text, flags=re.DOTALL)
            display_text = response.text.replace('<audio>', '').replace('</audio>', '')
            
            message_placeholder.markdown(display_text)
            
            audio_file_path = None
            if audio_texts:
                with st.spinner("🎵 Generating voice..." if ui_lang == "English" else "🎵 Generando voz..."):
                    text_to_speak = "。".join(audio_texts)
                    audio_file_path = generate_tts_audio(text_to_speak, selected_voice_code, selected_speed_rate)
                    st.audio(audio_file_path, format="audio/mp3", autoplay=True) 

            st.session_state.messages.append({
                "role": "assistant", 
                "content": display_text,
                "audio_path": audio_file_path
            })
            
        except Exception as e:
            st.error(f"Error: {e}")
