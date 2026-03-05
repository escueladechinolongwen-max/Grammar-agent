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
        st.error("Error: hsk1_corpus.json not found. 请确保文件在同目录下。")
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
        "finish_msg": "🏆 ¡Felicidades! Has completado la traducción. ¡Ahora pasemos al desafío de conversación!",
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
        "finish_msg": "🏆 Congratulations! You've finished the translations. Let's move to the Conversation Challenge!",
        "transcribing": "Transcribing audio...",
        "analyzing": "Analyzing...",
        "progress": "Progress",
        "scaffold_mw": "⚠️ Reminder: Don't forget the measure word after '几' (e.g., 个, 只, 本)!",
        "scaffold_de": "⚠️ Reminder: The description goes BEFORE '的'."
    }
}

# ==========================================
# 2. 🔑 大模型 API 接入点
# ==========================================
API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "AIzaSyADkYbH7ZIH2I09-oguQFtyLmqs8nOxqrs"

def transcribe_audio_to_text(audio_bytes):
    if not API_KEY: 
        return "API Key Error"
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
    if not API_KEY: 
        return "⚠️ 系统错误：找不到 API Key！请配置 API 密钥。"
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
# 3. 鹰架逻辑与音频引擎
# ==========================================
def clean_punctuation(text):
    return re.sub(r'[^\w\s\u4e00-\u9fff]', '', text).strip()

def apply_scaffolding(student_input, target_sentence, lang_dict):
    if "几" in student_input:
        if any(keyword in student_input for keyword in ["几月", "几号", "星期几"]):
            return True, ""
            
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
# 4. 核心路由与 UI
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

    if 'current_view' not in st.session_state: 
        st.session_state.current_view = "landing"
    if 'messages' not in st.session_state: 
        st.session_state.messages = []
    if 'master_idx' not in st.session_state: 
        st.session_state.master_idx = 0
    if 'master_mode' not in st.session_state: 
        st.session_state.master_mode = "training"

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
        
        if 'current_unit' not in st.session_state or st.session_state.current_unit != unit:
            st.session_state.current_unit = unit
            st.session_state.master_idx = 0
            st.session_state.master_mode = "training"
            st.session_state.failed_current = False
            
            all_sentences = KNOWLEDGE_BASE[unit].get("sentences", [])
            sample_size = min(10, len(all_sentences))
            if sample_size > 0:
                step = max(1, len(all_sentences) // sample_size)
                sampled_questions = [all_sentences[i] for i in range(0, len(all_sentences), step)][:sample_size]
            else:
                sampled_questions = []
                
            st.session_state.active_questions = sampled_questions
            
            grammar_data = KNOWLEDGE_BASE[unit].get("grammar", {})
            grammar_points = grammar_data.get(lang_key, "- Core grammar\n- Basic sentence structures")
            
            if lang_key == "es":
                welcome_msg = f"👋 **Hola, soy tu tutor de gramática, {DRAGON_MASTER}.**\n\nVamos a repasar la gramática de esta unidad:\n\n{grammar_points}\n\n**¡Empecemos!**"
            else:
                welcome_msg = f"👋 **Hello, I'm your grammar tutor, {DRAGON_MASTER}.**\n\nLet's review the grammar for this unit:\n\n{grammar_points}\n\n**Let's get started!**"
            st.session_state.messages = [{"role": "assistant", "content": welcome_msg, "audio": None}]
        
        questions = st.session_state.active_questions
        total_q = len(questions)
        
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
            
            target_zh = questions[current_q]["zh"]
            display_foreign = questions[current_q].get(lang_key, questions[current_q].get("en", "Translate this"))
            st.info(f"**{T['translate_prompt']}** {display_foreign}")
            
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])
                    if m.get("audio"): 
                        st.audio(m["audio"], format="audio/mp3", autoplay=False)
            
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
                    st.session_state.failed_current = True
                    st.session_state.messages.append({"role": "assistant", "content": scaffold_msg, "audio": None})
                else:
                    if user_text_clean == clean_punctuation(target_zh):
                        correct_response = f"{T['correct']} <audio>{target_zh}</audio>"
                        txt, aud = asyncio.run(handle_audio_logic(correct_response))
                        st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
                        
                        if getattr(st.session_state, 'failed_current', False):
                            all_unit_sentences = KNOWLEDGE_BASE[unit].get("sentences", [])
                            active_zhs = [q["zh"] for q in st.session_state.active_questions]
                            remaining_pool = [q for q in all_unit_sentences if q["zh"] not in active_zhs]
                            
                            if remaining_pool:
                                consolidation_qs = remaining_pool[:2] 
                                for q in reversed(consolidation_qs):
                                    st.session_state.active_questions.insert(st.session_state.master_idx + 1, q)
                                consol_msg = "💡 **大龙人:** 刚才这道题卡了一下，我们趁热打铁，从题库里再抽两道题巩固一下！" if lang_key == 'es' else "💡 **DA LONGREN:** Let's consolidate with more questions from our boutique pool!"
                                st.session_state.messages.append({"role": "assistant", "content": consol_msg, "audio": None})
                        
                        st.session_state.master_idx += 1 
                        st.session_state.failed_current = False
                        st.session_state.messages.append({"role": "assistant", "content": "🎯 **Next Challenge / Siguiente Reto:**", "audio": None})
                    else:
                        st.session_state.failed_current = True
                        with st.spinner(T['analyzing']):
                            # 【核心升级：基于诊断的拦截逻辑】
                            da_longren_translation_prompt = f"""
                            You are {DRAGON_MASTER}, a strict HSK 1 grammar tutor.
                            The student is translating: "{display_foreign}". Target: "{target_zh}".
                            
                            CRITICAL ALGORITHM ("Diagnose First, Teach Later"):
                            1. EVALUATE THE MISTAKE FIRST: Did the student use English/Spanish word order? (e.g., putting question words like 什么, 几, 哪儿 at the very beginning of the sentence, like "什么天是昨天").
                            
                            2. IF FOREIGN WORD ORDER DETECTED:
                               - IMMEDIATELY INTERVENE and say (translated naturally to {ui_lang}): "This is typical foreign language thinking. Let's switch to Chinese thinking. Let's think about the answer to this question first, and then build the question on top of that."
                               - Ask them to provide the declarative answer (e.g., "I am from China" or "Yesterday was August 15th").
                               - Once they provide it, use the CRITICAL PRECISION RULE: guide them to replace ONLY the exact, single keyword (e.g., "replace 四 with 几"). DO NOT replace chunks.
                               - SHUT UP AND WAIT.
                               
                            3. IF IT IS A NORMAL MISTAKE (1st time): Provide ONLY the basic grammar structure (scaffold) in {ui_lang}. DO NOT use the Answer-First method. Ask them to try again. SHUT UP AND WAIT.
                            
                            4. IF IT IS A NORMAL MISTAKE (2nd time+): Comfort them. Provide a similar example sentence. Guide them to observe the structure. Ask them to try again. SHUT UP AND WAIT.
                            
                            GENERAL RULES:
                            - NEVER give the full target sentence directly.
                            - Speak in {ui_lang}, use **bold** Simplified Chinese for keywords.
                            - If they use Arabic numerals, explicitly demand Chinese characters.
                            - Ask ONE question or give ONE instruction at a time.
                            """
                            ai_feedback = get_ai_response(st.session_state.messages, da_longren_translation_prompt)
                            st.session_state.messages.append({"role": "assistant", "content": ai_feedback, "audio": None})
                st.rerun()

        # === 阶段 2：智能问答池 ===
        elif st.session_state.master_mode == "dialogue_pool":
            st.success("🔥 **Review Phase Activated! / ¡Fase de Revisión Activada!**")
            pool = KNOWLEDGE_BASE[unit].get("dialogues", [])
            
            # 【问答池同样执行诊断拦截逻辑】
            da_longren_dialogue_prompt = f"""
            You are {DRAGON_MASTER} in the 'Dialogue & Review' phase. 
            Output <audio> tags ONLY when the student's answer is perfectly correct.
            
            STRICT RULE: ONLY ask questions from this pool: {json.dumps(pool, ensure_ascii=False)}. Do NOT invent new questions.
            
            CRITICAL ALGORITHM ("Diagnose First, Teach Later"):
            1. NEVER PREEMPT: Ask ONE question from the pool. DO NOT provide structure or hints before they answer. SHUT UP AND WAIT.
            
            2. IF CORRECT: Praise in {ui_lang}, output the correct Chinese sentence in an <audio> tag, and pick a new question from the pool.
            
            3. IF FOREIGN WORD ORDER DETECTED (e.g., question word at the beginning):
               - IMMEDIATELY INTERVENE and say (translated naturally to {ui_lang}): "This is typical foreign language thinking. Let's switch to Chinese thinking. Let's think about the answer to this question first."
               - Ask them to state the declarative answer first.
               - CRITICAL PRECISION RULE: Tell them to replace the exact, single keyword (e.g., "replace 四 with 几").
               - SHUT UP AND WAIT.
               
            4. IF NORMAL MISTAKE (1st time): Provide ONLY the basic grammar structure (scaffold) in {ui_lang}. Ask them to try again. SHUT UP AND WAIT.
            
            5. IF NORMAL MISTAKE (2nd time+): Comfort them patiently. Provide a similar example, then ask them to try the original question again. SHUT UP AND WAIT.
            
            6. CONSOLIDATION REWARD: If the student gets it right AFTER making mistakes, IMMEDIATELY ask a similar follow-up question.
            7. Stop after exactly 5 base questions.
            """
            
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): 
                    st.markdown(m["content"])
                    if m.get("audio"): 
                        st.audio(m["audio"], format="audio/mp3", autoplay=False)
            
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
                    raw_ai_reply = get_ai_response(st.session_state.messages, da_longren_dialogue_prompt, audio_bytes=audio_bytes)
                    txt, aud = asyncio.run(handle_audio_logic(raw_ai_reply))
                    st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
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
