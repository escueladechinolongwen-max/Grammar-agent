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
# 1. 核心配置与形象设定
# ==========================================
DRAGON_MASTER = "🐲 **大龙人 (DA LONGREN)**"
DRAGON_PAL = "🐉 **小龙人 (XIAO LONGREN)**"

def load_knowledge_base():
    file_path = "hsk1_corpus.json"
    if not os.path.exists(file_path):
        st.error("Error: hsk1_corpus.json not found.")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error parsing JSON: {e}")
        return {}

KNOWLEDGE_BASE = load_knowledge_base()

SCENARIO_DB = {
    "☕ Cafe Order": {"goal_en": "Order a drink.", "goal_es": "Pide una bebida.", "prompt": "咖啡馆服务员，第一句：你好，想喝点什么？", "ai_start_zh": "你好，想喝点什么？"},
    "🏥 At Hospital": {"goal_en": "Find Dr. Zhang.", "goal_es": "Encuentra al Dr. Zhang.", "prompt": "医院前台，第一句：你好，请问你找谁？", "ai_start_zh": "你好，请问你找谁？"},
    "🎓 University": {"goal_en": "Talk about university.", "goal_es": "Habla de la universidad.", "prompt": "你现在是我的大学同学。请用HSK1词汇和我闲聊。第一句请说：'我们是在哪里认识的？'", "ai_start_zh": "我们是在哪里认识的？"},
    "📞 Phone Call": {"goal_en": "Answer a call.", "goal_es": "Contesta una llamada.", "prompt": "你现在是我的好朋友，在给我打电话。请用HSK1词汇。第一句请说：'喂？你在做什么呢？'", "ai_start_zh": "喂？你在做什么呢？"},
    "🛒 Shopping": {"goal_en": "Buy clothes.", "goal_es": "Compra ropa.", "prompt": "你是服装店的老板。请用HSK1词汇。第一句请说：'欢迎光临，你想买什么？'", "ai_start_zh": "欢迎光临，你想买什么？"}
}

UI_TEXT = {
    "Español": {
        "title": "Aprendizaje de Chino AI",
        "m1": "👨‍🏫 Maestro Académico", "m2": "🤝 Compañero Fluido", "m3": "🗺️ Misiones",
        "translate_prompt": "Traduce al chino:",
        "input_placeholder": "Escribe o usa el micrófono...",
        "correct": "✨ ¡Excelente! Puntería perfecta.", 
        "incorrect": "⚠️ Incorrecto. La expresión estándar es:",
        "finish_msg": "🏆 ¡Felicidades! Has completado la traducción. ¡Ahora pasemos al desafío de conversación (5 preguntas)!",
        "transcribing": "Transcribiendo audio...",
        "analyzing": "Analizando...",
        "progress": "Progreso",
        "scaffold_mw": "⚠️ Recordatorio: ¡No olvides el clasificador después de '几' (ej. 个, 只, 本)!",
        "scaffold_de": "⚠️ Recordatorio: La descripción debe ir ANTES de '的'."
    },
    "English": {
        "title": "AI Chinese Speaking",
        "m1": "👨‍🏫 Academic Master", "m2": "🤝 Fluent Pal", "m3": "🗺️ Quests",
        "translate_prompt": "Translate to Chinese:",
        "input_placeholder": "Type or use the mic...",
        "correct": "✨ Perfect! You nailed it.", 
        "incorrect": "⚠️ Incorrect. The standard expression is:",
        "finish_msg": "🏆 Congratulations! You've finished the translations. Let's move to the Conversation Challenge (5 questions)!",
        "transcribing": "Transcribing audio...",
        "analyzing": "Analyzing...",
        "progress": "Progress",
        "scaffold_mw": "⚠️ Reminder: Don't forget the measure word after '几' (e.g., 个, 只, 本)!",
        "scaffold_de": "⚠️ Reminder: The description goes BEFORE '的'."
    }
}

# ==========================================
# 2. 🔑 大模型 API 接入点 (万能钥匙版)
# ==========================================
# 自动匹配你在 Render 设置的 GOOGLE_API_KEY 或 GEMINI_API_KEY，都不行就用硬编码兜底
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "AIzaSyADkYbH7ZIH2I09-oguQFtyLmqs8nOxqrs"

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

def get_ai_response(messages_history, system_prompt="", audio_bytes=None):
    if not API_KEY: return "⚠️ 系统错误：找不到 API Key！请配置 GEMINI_API_KEY。"
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_prompt)
    gemini_history = []
    
    for msg in messages_history[:-1]:
        if isinstance(msg["content"], str) and not msg["content"].startswith("🎤") and not msg["content"].startswith("✨") and not msg["content"].startswith("🎯"):
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
# 3. 鹰架逻辑与 Edge-TTS 音频引擎
# ==========================================
def clean_punctuation(text):
    return re.sub(r'[^\w\s\u4e00-\u9fff]', '', text).strip()

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
    if 'master_idx' not in st.session_state: st.session_state.master_idx = 0
    if 'master_mode' not in st.session_state: st.session_state.master_mode = "training"

    # ------------------------------------------
    # Landing 主页
    # ------------------------------------------
    if st.session_state.current_view == "landing":
        st.markdown(f"<h1 style='text-align: center;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.write("") 
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button(T["m1"], use_container_width=True):
                st.session_state.current_view = "master"
                st.session_state.messages = []
                st.session_state.current_unit = None 
                st.session_state.master_idx = 0
                st.session_state.master_mode = "training"
                st.rerun()
        with c2:
            if st.button(T["m2"], use_container_width=True):
                st.session_state.current_view = "pal"
                if lang_key == "es":
                    welcome_pal = f"👋 ¡Hola! Soy tu compañero de práctica, {DRAGON_PAL}.\n\n¿De qué te gustaría hablar hoy? Podemos charlar de forma relajada, ¡sin presiones!\n\n**小龙人:** 你好！今天想聊点什么？<audio>你好！我是小龙人。今天想聊点什么？</audio>"
                else:
                    welcome_pal = f"👋 Hello! I'm your language partner, {DRAGON_PAL}.\n\nWhat would you like to talk about today? We can just chat casually, no pressure!\n\n**小龙人:** 你好！今天想聊点什么？<audio>你好！我是小龙人。今天想聊点什么？</audio>"
                    
                txt, audio = asyncio.run(handle_audio_logic(welcome_pal))
                st.session_state.messages = [{"role": "assistant", "content": txt, "audio": audio}]
                st.rerun()
        with c3:
            if st.button(T["m3"], use_container_width=True):
                st.session_state.current_view = "quest"
                st.session_state.active_quest = None
                st.session_state.messages = []
                st.rerun()

    # ------------------------------------------
    # 模式 1: 👨‍🏫 Maestro Académico
    # ------------------------------------------
    elif st.session_state.current_view == "master":
        st.sidebar.button("⬅️ Back", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        unit = st.sidebar.selectbox("Unit", list(KNOWLEDGE_BASE.keys()), format_func=lambda x: KNOWLEDGE_BASE[x]["title"])
        st.header(f"{DRAGON_MASTER} - {KNOWLEDGE_BASE[unit]['title']}")
        
        sentences = KNOWLEDGE_BASE[unit]["sentences"]
        total_q = len(sentences)
        
        if 'current_unit' not in st.session_state or st.session_state.current_unit != unit:
            st.session_state.current_unit = unit
            st.session_state.master_idx = 0
            st.session_state.master_mode = "training"
            grammar_data = KNOWLEDGE_BASE[unit].get("grammar", {})
            grammar_points = grammar_data.get(lang_key, "- Core grammar\n- Basic sentence structures")
            
            if lang_key == "es":
                welcome_msg = f"👋 **Hola, soy tu tutor de gramática, {DRAGON_MASTER}.**\n\nVamos a repasar la gramática de esta unidad:\n\n{grammar_points}\n\n**¡Empecemos!**"
            else:
                welcome_msg = f"👋 **Hello, I'm your grammar tutor, {DRAGON_MASTER}.**\n\nLet's review the grammar for this unit:\n\n{grammar_points}\n\n**Let's get started!**"
            st.session_state.messages = [{"role": "assistant", "content": welcome_msg, "audio": None}]
        
        # === 阶段 1：翻译特训 (Answer-First Substitution) ===
        if st.session_state.master_mode == "training":
            current_q = st.session_state.master_idx
            st.progress(current_q / total_q if total_q > 0 else 0)
            st.caption(f"{T['progress']}: {current_q}/{total_q}")
            
            if current_q >= total_q:
                st.session_state.master_mode = "dialogue_pool"
                st.balloons()
                transition_msg = f"✨ {T['finish_msg']}\n\n**{DRAGON_MASTER}:** Are you ready? (Type 'yes' or speak to start!)"
                st.session_state.messages.append({"role": "assistant", "content": transition_msg, "audio": None})
                st.rerun()
            
            target_zh = sentences[current_q]["zh"]
            display_foreign = sentences[current_q][lang_key]
            st.info(f"**{T['translate_prompt']}** {display_foreign}")
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): 
                    st.markdown(msg["content"])
                    if msg.get("audio"): st.audio(msg["audio"], format="audio/mp3", autoplay=False)
            
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

                passed, scaffold_msg = apply_scaffolding(user_text_clean, target_zh, T)
                if not passed:
                    st.session_state.messages.append({"role": "assistant", "content": scaffold_msg, "audio": None})
                else:
                    if user_text_clean == clean_punctuation(target_zh):
                        correct_response = f"{T['correct']} <audio>{target_zh}</audio>"
                        txt, audio = asyncio.run(handle_audio_logic(correct_response))
                        st.session_state.messages.append({"role": "assistant", "content": txt, "audio": audio})
                        st.session_state.master_idx += 1 
                        st.session_state.messages.append({"role": "assistant", "content": "🎯 **Next Challenge / Siguiente Reto:**", "audio": None})
                    else:
                        with st.spinner(T['analyzing']):
                            da_longren_translation_prompt = f"""
                            You are {DRAGON_MASTER}, a strict but patient HSK 1 grammar tutor.
                            The student is trying to translate: "{display_foreign}" into Chinese. 
                            The exact target answer from the HSK 1 knowledge base is: "{target_zh}".
                            
                            CRITICAL RULES FOR SCAFFOLDING:
                            1. NEVER give them the full target sentence "{target_zh}" directly.
                            2. Speak entirely in {ui_lang}, but use Simplified Chinese for target words. Use **bold** to highlight Chinese keywords.
                            3. The "Answer-First Substitution" Method: If the student uses English/Spanish word order for questions (e.g., starting with "Where", "What", "How many"), STOP THEM. 
                               - Step A: Ask them to translate a declarative answer first (e.g., if target is 'Where are you from?', ask 'How do you say: I am from China?').
                               - Step B: Once they answer that correctly, ask them to identify the keyword in Chinese.
                               - Step C: Then ask how to say the question word (e.g., 'which country' -> **哪国**, 'how many' -> **几**).
                               - Step D: Guide them to replace ONLY the keyword with the question word, keeping the exact same word order.
                            4. If they miss measure words or drop verbs, gently point it out and ask them to fix it.
                            5. Ask ONE question or give ONE instruction at a time. Wait for their reply.
                            """
                            ai_feedback = get_ai_response(st.session_state.messages, da_longren_translation_prompt)
                            st.session_state.messages.append({"role": "assistant", "content": ai_feedback, "audio": None})
                st.rerun()

        # === 阶段 2：智能问答池 (基于 Knowledge Base) ===
        elif st.session_state.master_mode == "dialogue_pool":
            st.success("🔥 **Review Phase Activated! / ¡Fase de Revisión Activada!**")
            pool = KNOWLEDGE_BASE[unit].get("dialogues", [])
            
            da_longren_prompt = f"""
            You are {DRAGON_MASTER}, a professional and patient Chinese HSK 1 grammar tutor. 
            You are currently in the 'Dialogue & Review' phase. 
            Communicate with the student entirely in {ui_lang}, but use Simplified Chinese ONLY for target words/sentences. Never use Chinese for your explanations. Only output <audio> tags when the student's answer is perfectly correct.

            STRICT VOCABULARY AND CONTENT RULE:
            You must ONLY ask questions from this exact knowledge base pool to ensure you do not use vocabulary outside of HSK 1: {json.dumps(pool, ensure_ascii=False)}. 
            DO NOT invent your own questions outside of this provided list. 

            Strict Teaching Protocol:
            1. Ask ONE question at a time from the provided pool. DO NOT provide the structure or examples initially. Just wait for the reply.
            2. If CORRECT on the first try: Praise them in {ui_lang}, output the correct Chinese sentence in an <audio> tag, and pick a new question from the pool.
            3. If INCORRECT (1st time): Provide the basic grammar structure (scaffold) in {ui_lang} without giving the direct answer. Ask them to try again.
            4. If INCORRECT (2nd time): Comfort them patiently. Explicitly guide them to observe the structure. Explain that in Chinese, we only replace the target word. Provide a similar example, then ask them to try the original question again.
            5. Consolidation: If the student gets it right AFTER making mistakes, IMMEDIATELY ask a similar follow-up question (changing only a small detail like a number or day) to consolidate.
            6. Goal: Complete exactly 5 different questions. When 5 are done, congratulate them.
            """
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): 
                    st.markdown(msg["content"])
                    if msg.get("audio"): st.audio(msg["audio"], format="audio/mp3", autoplay=False)
            
            col_input, col_mic = st.columns([9, 1])
            with col_input:
                user_input = st.chat_input(T['input_placeholder'])
            with col_mic:
                audio_input = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_pool")
                
            if user_input or audio_input:
                if audio_input:
                    with st.spinner(T['transcribing']):
                        transcribed_text = transcribe_audio_to_text(audio_input['bytes'])
                        st.session_state.messages.append({"role": "user", "content": f"🎤 {transcribed_text}"})
                else:
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                with st.spinner(T['analyzing']):
                    audio_bytes = audio_input['bytes'] if audio_input else None
                    raw_ai_reply = get_ai_response(st.session_state.messages, da_longren_prompt, audio_bytes=audio_bytes)
                    txt, audio = asyncio.run(handle_audio_logic(raw_ai_reply))
                    st.session_state.messages.append({"role": "assistant", "content": txt, "audio": audio})
                st.rerun()

    # ------------------------------------------
    # 模式 2 & 3: 小龙人语伴与场景实战
    # ------------------------------------------
    elif st.session_state.current_view in ["pal", "quest"]:
        st.sidebar.button("⬅️ Back", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.selectbox("HSK Level", ["HSK 1", "HSK 2", "HSK 3"])
        
        is_quest = (st.session_state.current_view == "quest")
        st.header(T['m3_title'] if is_quest else f"{DRAGON_PAL} - Friend Chat")
        
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
                system_prompt = f"你现在的身份是'{DRAGON_PAL}'，一个热情、幽默的中文语伴。请务必使用简单的 HSK 1 词汇。每次回复都要在最后加上 <audio>你要发音的中文句子</audio> 标签。"
            
            with st.spinner("AI 正在思考..."):
                audio_bytes = audio_input['bytes'] if audio_input else None
                raw_ai_reply = get_ai_response(st.session_state.messages, system_prompt, audio_bytes=audio_bytes)
                txt, audio = asyncio.run(handle_audio_logic(raw_ai_reply))
                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": audio})
            st.rerun()

if __name__ == "__main__":
    main()
