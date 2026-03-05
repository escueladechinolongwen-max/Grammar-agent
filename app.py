import streamlit as st
import json
import os
import re
import asyncio
import time
import random
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
        "transcribing": "Transcribing audio...",
        "analyzing": "Analyzing...",
        "progress": "Progress",
        "scaffold_mw": "⚠️ Reminder: Don't forget the measure word after '几' (e.g., 个, 只, 本)!",
        "scaffold_de": "⚠️ Reminder: The description goes BEFORE '的'."
    }
}

# ==========================================
# 2. 🔑 大模型 API 接入点 (含防崩溃合并算法)
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
    
    # 极度安全的消息合并机制，防止 API 抛出 400 Alternating History Error
    gemini_history = []
    for msg in messages_history[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        content = msg["content"]
        # 清理掉带有干扰的音频标签
        content = re.sub(r'<audio[^>]*>.*?</audio>', '', content)
        
        if not gemini_history:
            gemini_history.append({"role": role, "parts": [content]})
        else:
            if gemini_history[-1]["role"] == role:
                # 合并连续相同身份的消息
                gemini_history[-1]["parts"][0] += f"\n{content}"
            else:
                gemini_history.append({"role": role, "parts": [content]})
            
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
    display_text = re.sub(r'<audio[^>]*>.*?</audio>', '', display_text)
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
    if 'qa_correct_count' not in st.session_state:
        st.session_state.qa_correct_count = 0

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

    elif st.session_state.current_view == "master":
        st.sidebar.button("⬅️ Back", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        unit = st.sidebar.selectbox("Unit", list(KNOWLEDGE_BASE.keys()), format_func=lambda x: KNOWLEDGE_BASE[x]["title"])
        st.header(f"{DRAGON_MASTER} - {KNOWLEDGE_BASE[unit]['title']}")
        
        if 'current_unit' not in st.session_state or st.session_state.current_unit != unit:
            st.session_state.current_unit = unit
            st.session_state.master_idx = 0
            st.session_state.master_mode = "training"
            st.session_state.failed_current = False
            st.session_state.qa_correct_count = 0
            st.session_state.pool_seed = int(time.time()) # 牢牢锁死该单元的随机种子
            
            all_sentences = KNOWLEDGE_BASE[unit].get("sentences", [])
            sample_size = min(10, len(all_sentences))
            if sample_size > 0:
                sampled_questions = random.sample(all_sentences, sample_size)
            else:
                sampled_questions = []
                
            st.session_state.active_questions = sampled_questions
            
            grammar_data = KNOWLEDGE_BASE[unit].get("grammar", {})
            grammar_points = grammar_data.get(lang_key, "- Core grammar\n- Basic sentence structures")
            
            # 充满仪式感的开场白宣导
            if lang_key == "es":
                welcome_msg = f"👋 **¡Hola! Soy {DRAGON_MASTER}.**\n\nEn esta clase, repasaremos juntos los siguientes puntos gramaticales:\n\n{grammar_points}\n\n**Nuestro plan de entrenamiento:**\n1. Traduciremos juntos algunas oraciones clave.\n2. Si hay un error gramatical, tendremos 1 o 2 oraciones extra para consolidar el punto.\n3. Luego, tendremos unas 5 preguntas de situación.\n\n**¿Estás listo/a para el desafío? (¡Puedes empezar a traducir la oración de arriba directamente!)**"
            else:
                welcome_msg = f"👋 **Hello! I am {DRAGON_MASTER}.**\n\nIn this class, we will review the following grammar points together:\n\n{grammar_points}\n\n**Our training plan:**\n1. We will translate some key sentences together.\n2. If a grammar mistake occurs, we will have 1 to 2 extra sentences to consolidate the point.\n3. Then, we will have about 5 scenario-based questions.\n\n**Are you ready for the challenge? (You can start translating the first sentence above directly!)**"
            
            st.session_state.messages = [{"role": "assistant", "content": welcome_msg, "audio": None}]
        
        questions = st.session_state.active_questions
        total_q = len(questions)
        
        # === 阶段 1：翻译特训 ===
        if st.session_state.master_mode == "training":
            current_q = st.session_state.master_idx
            
            st.progress(current_q / total_q if total_q > 0 else 0)
            st.caption(f"{T['progress']}: {current_q}/{total_q}")
            
            # 【完美无缝转场】：全通关后立刻后台抛出第一道情景题
            if current_q >= total_q:
                st.session_state.master_mode = "dialogue_pool"
                st.session_state.qa_correct_count = 0
                st.balloons()
                
                if lang_key == "es":
                    transition_msg = f"🎉 **¡Felicidades por completar el desafío de traducción!**\n\n**{DRAGON_MASTER}:** ¡Ahora pasemos a la sesión de preguntas y respuestas! Te haré unas 5 preguntas basadas en situaciones reales. ¡Aquí vamos!"
                else:
                    transition_msg = f"🎉 **Congratulations on completing the translation challenge!**\n\n**{DRAGON_MASTER}:** Now let's move on to the Q&A session! I will ask you about 5 questions based on real-life scenarios. Here we go!"
                
                st.session_state.messages.append({"role": "assistant", "content": transition_msg, "audio": None})
                
                with st.spinner(T['analyzing']):
                    pool = KNOWLEDGE_BASE[unit].get("dialogues", [])
                    if pool:
                        random.seed(st.session_state.pool_seed)
                        shuffled_pool = random.sample(pool, min(len(pool), 10))
                    else:
                        shuffled_pool = []
                    
                    first_q_prompt = f"You are {DRAGON_MASTER}. The translation phase is over. Pick ONE question from this pool {json.dumps(shuffled_pool, ensure_ascii=False)} and ask the student in {ui_lang}. DO NOT provide any hints or greetings. SHUT UP AND WAIT for their answer."
                    
                    # 使用隐形指引让 AI 稳定开球，防止把系统的恭喜词当成学生的输入
                    trigger_messages = st.session_state.messages + [{"role": "user", "content": "Please start the first question of the dialogue phase immediately."}]
                    raw_ai_reply = get_ai_response(trigger_messages, first_q_prompt, audio_bytes=None)
                    txt, aud = asyncio.run(handle_audio_logic(raw_ai_reply))
                    st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
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
                                consolidation_qs = random.sample(remaining_pool, min(2, len(remaining_pool))) 
                                for q in reversed(consolidation_qs):
                                    st.session_state.active_questions.insert(st.session_state.master_idx + 1, q)
                                consol_msg = "💡 **大龙人:** 刚才这道题卡了一下，我们趁热打铁抽两道题巩固一下！(请直接看上方的新挑战)" if lang_key == 'es' else "💡 **DA LONGREN:** Let's consolidate! (Check the new challenge above)"
                                st.session_state.messages.append({"role": "assistant", "content": consol_msg, "audio": None})
                        
                        st.session_state.master_idx += 1 
                        st.session_state.failed_current = False
                        # 丝滑切换下一题，干掉废话。
                    else:
                        st.session_state.failed_current = True
                        with st.spinner(T['analyzing']):
                            da_longren_translation_prompt = f"""
                            You are {DRAGON_MASTER}, a strict HSK 1 grammar tutor acting as a "ruthless sentence scanner".
                            The student is translating: "{display_foreign}". 
                            The EXACT TARGET ANSWER required by the system is: "{target_zh}".
                            
                            ABSOLUTE BOUNDARIES (DO NOT VIOLATE):
                            1. DO NOT teach alternative conversational ways. Guide exclusively towards the exact "{target_zh}".
                            2. DO NOT say goodbye, wrap up, or ask if they have questions. The class is NOT over yet.
                            3. THE CLOSING LOOP: If they build the parts correctly but haven't put them together, your ONLY instruction is: "Now, please type the full, complete Chinese sentence together in one line."
                            
                            CRITICAL ALGORITHM ("Diagnose First, Teach Later"):
                            1. IF FOREIGN WORD ORDER DETECTED (e.g., question word at the beginning):
                               - Say: "This is typical foreign language thinking. Let's switch to Chinese thinking. Let's think about the answer to this question first."
                               - Ask for the declarative answer.
                               - Once provided, apply CRITICAL PRECISION RULE: Guide replacement of the exact keyword(s). If multiple numbers need replacing, guide them to replace ALL relevant numbers with '几' (e.g., "replace 八 with 几, and 十五 with 几"). 
                               - SHUT UP AND WAIT.
                               
                            2. IF NORMAL MISTAKE (1st time): Provide ONLY the basic grammar structure scaffold. Ask to try again. SHUT UP AND WAIT.
                            
                            3. IF NORMAL MISTAKE (2nd time+): Comfort patiently. Provide a similar example sentence. Guide observation. Ask to try again. SHUT UP AND WAIT.
                            """
                            ai_feedback = get_ai_response(st.session_state.messages, da_longren_translation_prompt)
                            st.session_state.messages.append({"role": "assistant", "content": ai_feedback, "audio": None})
                st.rerun()

        # === 阶段 2：智能问答池 ===
        elif st.session_state.master_mode == "dialogue_pool":
            pool = KNOWLEDGE_BASE[unit].get("dialogues", [])
            if pool:
                random.seed(st.session_state.pool_seed)
                shuffled_pool = random.sample(pool, min(len(pool), 10))
            else:
                shuffled_pool = []
                
            # 判断是否满分通关（控制 UI 的文本/语音框上锁状态）
            is_class_dismissed = st.session_state.get('qa_correct_count', 0) >= 5

            da_longren_dialogue_prompt = f"""
            You are {DRAGON_MASTER} in the 'Dialogue & Review' phase. 
            Output <audio> tags ONLY when the student's answer is perfectly correct.
            
            STRICT RULE: ONLY ask questions from this pool: {json.dumps(shuffled_pool, ensure_ascii=False)}. Pick a different one each time.
            
            PROGRESS TRACKER: The student has currently answered {st.session_state.get('qa_correct_count', 0)} out of 5 questions correctly.
            
            CRITICAL ALGORITHM:
            1. NEVER PREEMPT: Ask ONE question from the pool. SHUT UP AND WAIT.
            2. IF CORRECT: 
               - Praise in {ui_lang}, output the correct Chinese sentence in an <audio> tag.
               - IF this correct answer brings their total to 5 (meaning they just answered the 5th one correctly), you MUST enthusiastically congratulate them, announce that the class is successfully completed ("恭喜你攻克了所有难关，下课啦！"), and give a warm, emotional farewell. DO NOT ask a 6th question.
               - IF their total is less than 5, pick a NEW question from the pool.
            3. IF FOREIGN WORD ORDER: Trigger "Answer-First" -> Ask for declarative answer -> Tell them exactly which word/number to replace with '几' or question word -> SHUT UP AND WAIT.
            4. IF NORMAL MISTAKE: 1st time scaffold only. 2nd time example and guide.
            5. CONSOLIDATION REWARD: If right AFTER making mistakes, ask a similar follow-up.
            """
            
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): 
                    st.markdown(m["content"])
                    if m.get("audio"): 
                        st.audio(m["audio"], format="audio/mp3", autoplay=False)
            
            col_input, col_mic = st.columns([9, 1])
            with col_input:
                user_input = st.chat_input(T['input_placeholder'], disabled=is_class_dismissed)
            with col_mic:
                if not is_class_dismissed:
                    audio_input = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_pool")
                else:
                    audio_input = None
                    st.success("🎉 Class Dismissed! Perfect Score! / ¡Clase terminada con puntaje perfecto!")
                
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
                    
                    # 计分板核心：大模型抛出 <audio> 意味着这题对了
                    if "<audio>" in raw_ai_reply:
                        st.session_state.qa_correct_count += 1
                        
                    txt, aud = asyncio.run(handle_audio_logic(raw_ai_reply))
                    st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
                st.rerun()

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
                system_prompt = f"当前身份是'{DRAGON_PAL}'，一个热情、幽默的中文语伴。请务必使用简单的 HSK 1 词汇。每次回复都要在最后加上 <audio>发音的中文句子</audio> 标签。"
            
            with st.spinner("Analyzing..."):
                audio_bytes = audio_input['bytes'] if audio_input else None
                raw_ai_reply = get_ai_response(st.session_state.messages, system_prompt, audio_bytes=audio_bytes)
                txt, audio = asyncio.run(handle_audio_logic(raw_ai_reply))
                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": audio})
            st.rerun()

if __name__ == "__main__":
    main()
