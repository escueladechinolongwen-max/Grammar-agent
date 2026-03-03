import streamlit as st
import json
import os
import re
import asyncio
import time
import google.generativeai as genai

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
    "☕ Cafe Order": {
        "goal_en": "Order a drink and pay.", 
        "goal_es": "Pide una bebida y paga.", 
        "prompt": "你现在是北京一家咖啡馆的服务员。请用符合HSK1水平的中文和客人对话。第一句请说：'你好，想喝点什么？'",
        "ai_start_zh": "你好，想喝点什么？"
    },
    "🏥 At Hospital": {
        "goal_en": "Find Dr. Zhang.", 
        "goal_es": "Encuentra al Dr. Zhang.", 
        "prompt": "你现在是医院的前台。请用HSK1词汇对话。第一句请说：'你好，请问你找谁？'",
        "ai_start_zh": "你好，请问你找谁？"
    },
    "🎓 University": {
        "goal_en": "Talk about university.", 
        "goal_es": "Habla de la universidad.", 
        "prompt": "你现在是我的大学同学。请用HSK1词汇和我闲聊。第一句请说：'我们是在哪里认识的？'",
        "ai_start_zh": "我们是在哪里认识的？"
    },
    "📞 Phone Call": {
        "goal_en": "Answer a call.", 
        "goal_es": "Contesta una llamada.", 
        "prompt": "你现在是我的好朋友，在给我打电话。请用HSK1词汇。第一句请说：'喂？你在做什么呢？'",
        "ai_start_zh": "喂？你在做什么呢？"
    },
    "🛒 Shopping": {
        "goal_en": "Buy clothes.", 
        "goal_es": "Compra ropa.", 
        "prompt": "你是服装店的老板。请用HSK1词汇。第一句请说：'欢迎光临，你想买什么？'",
        "ai_start_zh": "欢迎光临，你想买什么？"
    }
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
        "input_placeholder": "Escribe tu traducción...",
        "btn_check": "Comprobar",
        "correct": "¡Perfecto! Muy bien hecho.",
        "incorrect": "¡Uy, casi lo tienes! 😉 Vamos a ver la expresión estándar:",
        "unit": "Unidad",
        "level": "Nivel HSK",
        "scaffold_mw": "⚠️ Recordatorio: ¡No olvides el clasificador después de '几' (ej. 个, 只, 本)!",
        "scaffold_de": "⚠️ Recordatorio: La descripción debe ir ANTES de '的'. [Ubicación] + 的 + [Sustantivo]."
    },
    "English": {
        "title": "AI Chinese Speaking",
        "subtitle": "Choose your learning mode",
        "back": "Back to Home",
        "m1_title": "👨‍🏫 Academic Master",
        "m2_title": "🤝 Fluent Pal",
        "m3_title": "🗺️ Immersive Quests",
        "translate_prompt": "Translate to Chinese:",
        "input_placeholder": "Type your translation...",
        "btn_check": "Check Answer",
        "correct": "Perfect! Great job.",
        "incorrect": "Oops, almost there! 😉 Let's look at the standard expression:",
        "unit": "Unit",
        "level": "HSK Level",
        "scaffold_mw": "⚠️ Reminder: Don't forget the measure word after '几' (e.g., 个, 只, 本)!",
        "scaffold_de": "⚠️ Reminder: The description goes BEFORE '的'. [Location] + 的 + [Noun]."
    }
}

# ==========================================
# 2. 🔑 大模型对话引擎 (Gemini API 接入点)
# ==========================================
def get_ai_response(messages_history, system_prompt=""):
    # 填入你截图里的真实 API Key
    genai.configure(api_key="AIzaSyADkYbH7ZIH2I09-oguQFtyLmqs8nOxqrs")
    
    # 初始化 Gemini 模型，注入大龙人/小龙人/场景提示词
    model = genai.GenerativeModel('gemini-1.5-flash', system_instruction=system_prompt)
    
    # 转换聊天记录格式 (Streamlit 格式转为 Gemini 认识的格式)
    gemini_history = []
    for msg in messages_history[:-1]: 
        role = "user" if msg["role"] == "user" else "model"
        gemini_history.append({"role": role, "parts": [msg["content"]]})
        
    # 发起真实的 API 请求
    try:
        chat = model.start_chat(history=gemini_history)
        response = chat.send_message(messages_history[-1]["content"])
        return response.text
    except Exception as e:
        return f"网络好像有点问题！错误信息: {e}"

# ==========================================
# 3. 鹰架逻辑与 TTS 音频引擎
# ==========================================
def apply_scaffolding(student_input, target_sentence, lang_dict):
    if "几" in student_input:
        mws = ["个", "口", "只", "本", "岁", "块", "件"]
        if not any(mw in student_input.split("几")[1][:2] for mw in mws if len(student_input.split("几")) > 1):
            return False, lang_dict["scaffold_mw"]
            
    if "的" in target_sentence and any(p in target_sentence for p in ["上", "下", "前", "后", "里"]):
        if "的" in student_input:
            for noun in ["书", "水果", "电脑", "猫", "狗", "衣服"]:
                if noun in student_input and student_input.find(noun) < student_input.find("的"):
                    return False, lang_dict["scaffold_de"]
    return True, ""

def generate_tts_audio(text):
    # 此处对接真实的 TTS 语音生成接口
    return "temp.mp3" 

async def handle_audio_logic(full_response):
    display_text = re.sub(r'</?p>', '', full_response)
    display_text = re.sub(r'<audio[^>]*>.*?</audio>', '', display_text).replace('</audio>', '')
    audio_texts = re.findall(r'<audio[^>]*>(.*?)</audio>', full_response, flags=re.DOTALL)
    if audio_texts:
        return display_text, generate_tts_audio(" ".join(audio_texts))
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
    if 'master_idx' not in st.session_state: st.session_state.master_idx = 0

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
                st.session_state.messages = [{"role": "assistant", "content": welcome_pal}]
                st.rerun()
        with c3:
            st.warning(f"### {T['m3_title']}")
            if st.button("Start / Iniciar", key="b3", use_container_width=True):
                st.session_state.current_view = "quest"
                st.session_state.active_quest = None
                st.session_state.messages = []
                st.rerun()

    # ------------------------------------------
    # 模式 1: 👨‍🏫 Maestro Académico (大龙人)
    # ------------------------------------------
    elif st.session_state.current_view == "master":
        st.sidebar.button(f"⬅️ {T['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.selectbox(T['level'], ["HSK 1", "HSK 2", "HSK 3"])
        unit = st.sidebar.selectbox(T['unit'], list(KNOWLEDGE_BASE.keys()), format_func=lambda x: KNOWLEDGE_BASE[x]["title"])
        
        st.header(f"{T['m1_title']} - {KNOWLEDGE_BASE[unit]['title']}")
        
        if 'current_unit' not in st.session_state or st.session_state.current_unit != unit:
            st.session_state.current_unit = unit
            st.session_state.master_idx = 0
            
            grammar_data = KNOWLEDGE_BASE[unit].get("grammar", {})
            grammar_points = grammar_data.get(lang_key, "- Core grammar\n- Basic sentence structures")
            
            if lang_key == "es":
                welcome_msg = f"👋 **Hola, soy tu tutor de gramática, Da Longren.**\n\nVamos a repasar la gramática de esta unidad:\n\n{grammar_points}\n\n**¡Empecemos!**"
            else:
                welcome_msg = f"👋 **Hello, I'm your grammar tutor, Da Longren.**\n\nLet's review the grammar for this unit:\n\n{grammar_points}\n\n**Let's get started!**"
                
            st.session_state.messages = [{"role": "assistant", "content": welcome_msg}]
        
        sentences = KNOWLEDGE_BASE[unit]["sentences"]
        current_data = sentences[st.session_state.master_idx % len(sentences)]
        
        target_zh = current_data["zh"]
        display_foreign = current_data[lang_key]
        
        st.info(f"**{T['translate_prompt']}** {display_foreign}")
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
        
        user_input = st.chat_input(T['input_placeholder'])
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            passed, scaffold_msg = apply_scaffolding(user_input, target_zh, T)
            
            if not passed:
                st.session_state.messages.append({"role": "assistant", "content": scaffold_msg})
            else:
                if user_input.strip() == target_zh:
                    txt, audio = asyncio.run(handle_audio_logic(f"{T['correct']} <audio>{target_zh}</audio>"))
                    st.session_state.messages.append({"role": "assistant", "content": txt})
                    st.session_state.master_idx += 1 
                else:
                    st.session_state.messages.append({"role": "assistant", "content": f"{T['incorrect']} **{target_zh}**"})
            st.rerun()

    # ------------------------------------------
    # 模式 2 & 3: 聊天模式 (小龙人语伴 & 情景实战)
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
                            st.session_state.messages = [{"role": "assistant", "content": txt}]
                            st.rerun()
            st.stop()
            
        if is_quest:
            st.subheader(st.session_state.active_quest)
            if st.button("End Mission"):
                st.session_state.active_quest = None
                st.rerun()
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        user_input = st.chat_input(T['input_placeholder'])
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            if is_quest:
                system_prompt = SCENARIO_DB[st.session_state.active_quest]["prompt"]
            else:
                system_prompt = (
                    "你现在的身份是'小龙人'，一个热情、幽默的中文语伴。你正在和学生进行朋友间的闲聊。"
                    "请务必使用极其简单的 HSK 1 词汇。如果学生说得好，请自然地夸奖他们。"
                    "每次回复不要超过两句话，并且要用一个简单的问题引导学生继续说话。"
                )
            
            with st.spinner("AI is thinking..."):
                raw_ai_reply = get_ai_response(st.session_state.messages, system_prompt)
                txt, audio = asyncio.run(handle_audio_logic(raw_ai_reply))
                st.session_state.messages.append({"role": "assistant", "content": txt})
            st.rerun()

if __name__ == "__main__":
    main()
