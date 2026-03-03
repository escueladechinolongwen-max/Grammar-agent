import streamlit as st
import json
import os
import re
import asyncio
import time
import google.generativeai as genai
import edge_tts
from streamlit_mic_recorder import mic_recorder

# ==========================================
# 1. 数据加载与核心配置
# ==========================================
def load_knowledge_base():
    file_path = "hsk1_corpus.json"
    if not os.path.exists(file_path):
        st.error("Error: 找不到 hsk1_corpus.json 数据文件。请确保它与 app.py 在同一目录下。")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error 解析 JSON: {e}")
        return {}

KNOWLEDGE_BASE = load_knowledge_base()

SCENARIO_DB = {
    "☕ Cafe Order": {"goal_en": "Order a drink and pay.", "goal_es": "Pide una bebida y paga.", "prompt": "你现在是北京一家咖啡馆的服务员。请用符合HSK1水平的中文和客人对话。第一句请说：'你好，想喝点什么？'", "ai_start_zh": "你好，想喝点什么？"},
    "🏥 At Hospital": {"goal_en": "Find Dr. Zhang.", "goal_es": "Encuentra al Dr. Zhang.", "prompt": "你现在是医院的前台。请用HSK1词汇对话。第一句请说：'你好，请问你找谁？'", "ai_start_zh": "你好，请问你找谁？"},
    "🎓 University": {"goal_en": "Talk about university.", "goal_es": "Habla de la universidad.", "prompt": "你现在是我的大学同学。请用HSK1词汇和我闲聊。第一句请说：'我们是在哪里认识的？'", "ai_start_zh": "我们是在哪里认识的？"},
    "📞 Phone Call": {"goal_en": "Answer a call.", "goal_es": "Contesta una llamada.", "prompt": "你现在是我的好朋友，在给我打电话。请用HSK1词汇。第一句请说：'喂？你在做什么呢？'", "ai_start_zh": "喂？你在做什么呢？"},
    "🛒 Shopping": {"goal_en": "Buy clothes.", "goal_es": "Compra ropa.", "prompt": "你是服装店的老板。请用HSK1词汇。第一句请说：'欢迎光临，你想买什么？'", "ai_start_zh": "欢迎光临，你想买什么？"}
}

UI_TEXT = {
    "Español": {
        "title": "Aprendizaje de Chino AI",
        "subtitle": "Elige tu modo de aprendizaje",
        "back": "Volver al Inicio",
        "m1_title": "👨‍🏫 Maestro Académico",
        "m2_title": "🤝 Compañero Fluido",
        "m3_title": "🗺️ Misiones Inmersivas",
        "translate_prompt": "Traduce al chino:",
        "input_placeholder": "Escribe tu traducción o usa el micrófono...",
        "btn_check": "Comprobar",
        "correct": "¡Perfecto! Muy bien hecho.",
        "incorrect": "Incorrecto. La expresión estándar es:",
        "unit": "Unidad",
        "level": "Nivel HSK",
        "transcribing": "Transcribiendo audio...",
        "analyzing": "Analizando gramática...",
        "progress": "Progreso"
    },
    "English": {
        "title": "AI Chinese Speaking",
        "subtitle": "Choose your learning mode",
        "back": "Back to Home",
        "m1_title": "👨‍🏫 Academic Master",
        "m2_title": "🤝 Fluent Pal",
        "m3_title": "🗺️ Immersive Quests",
        "translate_prompt": "Translate to Chinese:",
        "input_placeholder": "Type your translation or use the mic...",
        "btn_check": "Check Answer",
        "correct": "Perfect! Great job.",
        "incorrect": "Incorrect. The standard expression is:",
        "unit": "Unit",
        "level": "HSK Level",
        "transcribing": "Transcribing audio...",
        "analyzing": "Analyzing grammar...",
        "progress": "Progress"
    }
}

# ==========================================
# 2. 🔑 大模型 API 接入点 (安全读取环境变量)
# ==========================================
# 不再硬编码，从服务器环境读取 Key
API_KEY = os.environ.get("GEMINI_API_KEY")

def transcribe_audio_to_text(audio_bytes):
    if not API_KEY: return "API Key Error"
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    try:
        response = model.generate_content([
            {"mime_type": "audio/wav", "data": audio_bytes},
            "Please transcribe the Chinese speech in this audio. Output ONLY the Simplified Chinese text, no punctuation, no translations."
        ])
        return response.text.strip()
    except Exception:
        return ""

def get_dynamic_grammar_feedback(student_input, target_sentence, ui_lang):
    """大龙人的动态语法诊断引擎"""
    if not API_KEY: return "System Error: Missing API Key."
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    The student is learning HSK 1 Chinese. 
    The target correct translation is: "{target_sentence}".
    The student wrote: "{student_input}".
    
    Analyze the student's mistake. Provide a brief, 1-2 sentence explanation of the grammatical error in {ui_lang}. 
    Focus on basic HSK 1 rules (like word order, missing measure words, wrong verbs). Do not use Chinese characters in your explanation except for citing the specific wrong/correct words. Do not give away the full correct sentence directly, just explain the rule they broke.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Grammar analysis failed: {e}"

def get_ai_response(messages_history, system_prompt="", audio_bytes=None):
    if not API_KEY: return "⚠️ 系统错误：找不到 API Key！请配置 GEMINI_API_KEY。"
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_prompt)
    gemini_history = []
    
    for msg in messages_history[:-1]:
        if isinstance(msg["content"], str) and not msg["content"].startswith("🎤"):
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})
        
    try:
        chat = model.start_chat(history=gemini_history)
        if audio_bytes:
            audio_part = {"mime_type": "audio/wav", "data": audio_bytes}
            response = chat.send_message([audio_part, "请听这段录音并回复我。"])
        else:
            response = chat.send_message(messages_history[-1]["content"])
        return response.text
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 3. 基础逻辑与音频引擎
# ==========================================
def clean_punctuation(text):
    return re.sub(r'[^\w\s\u4e00-\u9fff]', '', text).strip()

async def generate_tts_audio(text, voice_code="zh-CN-XiaoxiaoNeural"):
    output_file = f"temp_audio_{int(time.time())}.mp3"
    communicate = edge_tts.Communicate(text, voice_code)
    await communicate.save(output_file)
    return output_file

async def handle_audio_logic(full_response):
    display_text = re.sub(r'</?p>', '', full_response)
    display_text = re.sub(r'<audio[^>]*>.*?</audio>', '', display_text).replace('</audio>', '')
    audio_texts = re.findall(r'<audio[^>]*>(.*?)</audio>', full_response, flags=re.DOTALL)
    
    if audio_texts:
        audio_path = await generate_tts_audio(" ".join(audio_texts))
        return display_text, audio_path
    return display_text, None

# ==========================================
# 4. 核心路由与 Streamlit UI
# ==========================================
def main():
    if not KNOWLEDGE_BASE:
        st.stop()

    st.set_page_config(page_title="AI Chinese Speaking", layout="wide")
    
    col_empty, col_lang = st.columns([8, 2])
    with col_lang:
        ui_lang = st.selectbox("Language / Idioma", ["English", "Español"], label_visibility="collapsed")
    
    T = UI_TEXT[ui_lang]
    lang_key = "es" if ui_lang == "Español" else "en"

    if 'current_view' not in st.session_state: st.session_state.current_view = "landing"
    if 'messages' not in st.session_state: st.session_state.messages = []

    # ------------------------------------------
    # Landing 主页
    # ------------------------------------------
    if st.session_state.current_view == "landing":
        st.markdown(f"<h1 style='text-align: center;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align: center; color: gray; margin-bottom: 40px;'>{T['subtitle']}</h4>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info(f"### {T['m1_title']}")
            if st.button("Start / Iniciar", key="b1", use_container_width=True):
                st.session_state.current_view = "master"
                st.session_state.messages = []
                st.session_state.current_unit = None 
                st.rerun()
        with c2:
            st.success(f"### {T['m2_title']}")
            if st.button("Start / Iniciar", key="b2", use_container_width=True):
                st.session_state.current_view = "pal"
                welcome_pal = "👋 你好！我是你的专属语伴**小龙人**！\n\n今天想和我聊点什么？我们可以随便聊聊，不要有压力哦！<audio>你好！我是小龙人。今天想聊点什么？</audio>"
                txt, audio = asyncio.run(handle_audio_logic(welcome_pal))
                st.session_state.messages = [{"role": "assistant", "content": txt, "audio": audio}]
                st.rerun()
        with c3:
            st.warning(f"### {T['m3_title']}")
            if st.button("Start / Iniciar", key="b3", use_container_width=True):
                st.session_state.current_view = "quest"
                st.session_state.active_quest = None
                st.session_state.messages = []
                st.rerun()

    # ------------------------------------------
    # 模式 1: 👨‍🏫 Maestro Académico
    # ------------------------------------------
    elif st.session_state.current_view == "master":
        st.sidebar.button(f"⬅️ {T['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.selectbox(T['level'], ["HSK 1", "HSK 2", "HSK 3"])
        unit = st.sidebar.selectbox(T['unit'], list(KNOWLEDGE_BASE.keys()), format_func=lambda x: KNOWLEDGE_BASE[x]["title"])
        
        st.header(f"{T['m1_title']} - {KNOWLEDGE_BASE[unit]['title']}")
        
        sentences = KNOWLEDGE_BASE[unit]["sentences"]
        total_q = len(sentences)
        
        if 'current_unit' not in st.session_state or st.session_state.current_unit != unit:
            st.session_state.current_unit = unit
            st.session_state.master_idx = 0
            
            grammar_data = KNOWLEDGE_BASE[unit].get("grammar", {})
            grammar_points = grammar_data.get(lang_key, "- Core grammar\n- Basic sentence structures")
            
            if lang_key == "es":
                welcome_msg = f"👋 **Hola, soy tu tutor de gramática, Da Longren.**\n\nVamos a repasar la gramática de esta unidad:\n\n{grammar_points}\n\n**¡Empecemos!**"
            else:
                welcome_msg = f"👋 **Hello, I'm your grammar tutor, Da Longren.**\n\nLet's review the grammar for this unit:\n\n{grammar_points}\n\n**Let's get started!**"
                
            st.session_state.messages = [{"role": "assistant", "content": welcome_msg, "audio": None}]
        
        # UI 渲染进度条
        current_q = st.session_state.master_idx % total_q
        st.progress(current_q / total_q if total_q > 0 else 0)
        st.caption(f"{T['progress']}: {current_q}/{total_q}")
        
        current_data = sentences[current_q]
        target_zh = current_data["zh"]
        display_foreign = current_data[lang_key]
        
        st.info(f"**{T['translate_prompt']}** {display_foreign}")
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): 
                st.markdown(msg["content"])
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/mp3", autoplay=False)
        
        col_input, col_mic = st.columns([9, 1])
        with col_input:
            user_input_text = st.chat_input(T['input_placeholder'])
        with col_mic:
            audio_input = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_master")
            
        if user_input_text or audio_input:
            user_text_clean = ""
            
            if audio_input:
                with st.spinner(T['transcribing']):
                    transcribed_text = transcribe_audio_to_text(audio_input['bytes'])
                    st.session_state.messages.append({"role": "user", "content": f"🎤 {transcribed_text}"})
                    user_text_clean = clean_punctuation(transcribed_text)
            else:
                st.session_state.messages.append({"role": "user", "content": user_input_text})
                user_text_clean = clean_punctuation(user_input_text)

            # 答案比对与动态诊断拦截
            if user_text_clean == clean_punctuation(target_zh):
                correct_response = f"{T['correct']} <audio>{target_zh}</audio>"
                txt, audio = asyncio.run(handle_audio_logic(correct_response))
                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": audio})
                st.session_state.master_idx += 1 
            else:
                with st.spinner(T['analyzing']):
                    # 调用大模型动态生成语法诊断
                    ai_feedback = get_dynamic_grammar_feedback(user_text_clean, target_zh, ui_lang)
                    error_msg = f"{T['incorrect']} **{target_zh}**\n\n💡 **Da Longren:** {ai_feedback}"
                    st.session_state.messages.append({"role": "assistant", "content": error_msg, "audio": None})
            st.rerun()

    # ------------------------------------------
    # 模式 2 & 3: 聊天模式 (保持不变)
    # ------------------------------------------
    elif st.session_state.current_view in ["pal", "quest"]:
        st.sidebar.button(f"⬅️ {T['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.selectbox(T['level'], ["HSK 1", "HSK 2", "HSK 3"])
        
        is_quest = (st.session_state.current_view == "quest")
        st.header(T['m3_title'] if is_quest else T['m2_title'])
        
        if is_quest and not st.session_state.get('active_quest'):
            cols = st.columns(2)
            for idx, (title, data) in enumerate(SCENARIO_DB.items()):
                with cols[idx % 2]:
                    with st.container(border=True):
                        st.subheader(title)
                        st.write(f"**Goal:** {data[f'goal_{lang_key}']}")
                        if st.button("Start Mission", key=f"btn_{title}"):
                            st.session_state.active_quest = title
                            start_msg = f"{data['ai_start_zh']}<audio>{data['ai_start_zh']}</audio>"
                            txt, audio = asyncio.run(handle_audio_logic(start_msg))
                            st.session_state.messages = [{"role": "assistant", "content": txt, "audio": audio}]
                            st.rerun()
            st.stop()
            
        if is_quest:
            st.subheader(st.session_state.active_quest)
            if st.button("End Mission"):
                st.session_state.active_quest = None
                st.rerun()
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/mp3", autoplay=False)
            
        col_input, col_mic = st.columns([9, 1])
        with col_input:
            user_input = st.chat_input(T['input_placeholder'])
        with col_mic:
            audio_input = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_pal")
            
        if user_input or audio_input:
            if audio_input:
                st.session_state.messages.append({"role": "user", "content": "🎤 [Voice Message]"})
            else:
                st.session_state.messages.append({"role": "user", "content": user_input})
            
            if is_quest:
                system_prompt = SCENARIO_DB[st.session_state.active_quest]["prompt"] + " 每次回复都要在最后加上 <audio>你要发音的中文句子</audio> 标签。"
            else:
                system_prompt = "你现在的身份是'小龙人'，一个热情、幽默的中文语伴。请务必使用简单的 HSK 1 词汇。每次回复都要在最后加上 <audio>你要发音的中文句子</audio> 标签。"
            
            with st.spinner("AI 正在思考..."):
                audio_bytes = audio_input['bytes'] if audio_input else None
                raw_ai_reply = get_ai_response(st.session_state.messages, system_prompt, audio_bytes=audio_bytes)
                txt, audio = asyncio.run(handle_audio_logic(raw_ai_reply))
                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": audio})
            st.rerun()

if __name__ == "__main__":
    main()
