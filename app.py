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
    "🎓 University": {"goal_en": "Talk about university.", "goal_es": "Habla de la universidad.", "prompt": "现在的身份是大学同学。请用HSK1词汇闲聊。第一句请说：'我们是在哪里认识的？'", "ai_start_zh": "我们是在哪里认识的？"},
    "📞 Phone Call": {"goal_en": "Answer a call.", "goal_es": "Contesta una llamada.", "prompt": "现在的身份是好朋友，在打电话。请用HSK1词汇。第一句请说：'喂？你在做什么呢？'", "ai_start_zh": "喂？你在做什么呢？"},
    "🛒 Shopping": {"goal_en": "Buy clothes.", "goal_es": "Compra ropa.", "prompt": "现在的身份是服装店的老板。请用HSK1词汇。第一句请说：'欢迎光临，你想买什么？'", "ai_start_zh": "欢迎光临，你想买什么？"}
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
        "scaffold_mw": "💡 **Pista:** En chino, al preguntar 'cuántos' con '几', normalmente necesitas un clasificador (como 个, 口, 本) justo después. ¡Inténtalo de nuevo!",
        "scaffold_de": "💡 **Pista:** Cuando usas palabras de posición (como 上/下/里), normalmente se unen directamente al sustantivo sin '的' (ej. 桌子上, no 桌子的上). ¡Inténtalo de nuevo!"
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
        "scaffold_mw": "💡 **Hint:** In Chinese, when asking 'how many' with '几', you usually need a measure word (like 个, 口, 本) right after it. Try again!",
        "scaffold_de": "💡 **Hint:** When using position words (like 上/下/里), they usually attach directly to the noun without '的' (e.g., 桌子上, not 桌子的上). Try again!"
    }
}

# ==========================================
# 2. API 接入点与防崩溃合并算法
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
        role = "user" if msg["role"] == "user" else "model"
        content = msg["content"]
        content = re.sub(r'<audio[^>]*>.*?</audio>', '', content)
        
        if not gemini_history:
            gemini_history.append({"role": role, "parts": [content]})
        else:
            if gemini_history[-1]["role"] == role:
                gemini_history[-1]["parts"][0] += f"\n{content}"
            else:
                gemini_history.append({"role": role, "parts": [content]})
            
    try:
        chat = model.start_chat(history=gemini_history)
        if audio_bytes:
            audio_part = {"mime_type": "audio/wav", "data": audio_bytes}
            response = chat.send_message([audio_part, "请听这段录音并回复。"])
        else:
            response = chat.send_message(messages_history[-1]["content"])
        return response.text
    except Exception as e:
        return f"Error: {e}"

# ==========================================
# 3. 智能宽容判分、安全文本提取 & 音频引擎
# ==========================================
def get_question_text(q_item):
    if isinstance(q_item, str):
        return q_item
    if isinstance(q_item, dict):
        for key in ['zh', 'cn', 'question', 'q', 'text']:
            if key in q_item:
                return str(q_item[key])
        for v in q_item.values():
            if isinstance(v, str) and re.search(r'[\u4e00-\u9fff]', v):
                return v
        if q_item:
            return str(list(q_item.values())[0])
    return str(q_item)

def get_foreign_text(q_item, lang_key):
    if isinstance(q_item, dict):
        return q_item.get(lang_key, q_item.get("en", "Translate this"))
    return "Translate this"

def is_translation_match(user_input, target):
    def clean(t):
        return re.sub(r'[^\w\u4e00-\u9fff]', '', t).strip()

    u_clean = clean(user_input)
    t_clean = clean(target)

    if u_clean == t_clean:
        return True

    # 敬语单复数等价
    u_temp = u_clean.replace("你们", "你").replace("您们", "你").replace("您", "你")
    t_temp = t_clean.replace("你们", "你").replace("您们", "你").replace("您", "你")
    
    # 年龄提问等价
    u_temp = u_temp.replace("多大了", "几岁").replace("几岁了", "几岁").replace("多大", "几岁")
    t_temp = t_temp.replace("多大了", "几岁").replace("几岁了", "几岁").replace("多大", "几岁")
    
    # 块和块钱等价
    u_temp = u_temp.replace("块钱", "块")
    t_temp = t_temp.replace("块钱", "块")
    
    # 多少 + 量词 豁免
    u_temp = re.sub(r'多少[个口只本块件]', '多少', u_temp)
    t_temp = re.sub(r'多少[个口只本块件]', '多少', t_temp)
    
    # 学习 = 学
    u_temp = u_temp.replace("学习", "学")
    t_temp = t_temp.replace("学习", "学")
    
    if u_temp == t_temp:
        return True

    close_nouns = ["妈妈", "爸爸", "哥哥", "姐姐", "弟弟", "妹妹", "朋友", "家", "学校", "老师", "名字"]
    u_de = u_temp
    t_de = t_temp
    for noun in close_nouns:
        u_de = u_de.replace(f"的{noun}", noun)
        t_de = t_de.replace(f"的{noun}", noun)
    if u_de == t_de:
        return True

    # 时态词倒装豁免
    time_words = ["今天", "明天", "昨天", "今年", "明年", "去年", "上午", "下午", "晚上", "早上", "现在"]
    pronouns = ["我", "你", "他", "她", "我们", "你们", "他们", "她们"]
    for t_word in time_words:
        for p in pronouns:
            if (p + t_word) in u_de:
                if u_de.replace(p + t_word, t_word + p) == t_de: return True
            if (t_word + p) in u_de:
                if u_de.replace(t_word + p, p + t_word) == t_de: return True

    # 主语补全豁免
    for p in ["你", "我", "他", "她", "你们", "我们", "他们", "她们"]:
        if u_temp == p + t_temp: 
            return True
        if t_temp.startswith("在") and u_temp == t_temp.replace("在", p + "在", 1):
            return True

    u_time = u_de.replace("哪天", "几号")
    t_time = t_de.replace("哪天", "几号")
    
    if any(k in t_time for k in ["岁", "今年", "现在", "几岁"]):
        u_time = u_time.replace("了", "")
        t_time = t_time.replace("了", "")
        if u_time == t_time:
            return True

    # 包含时间、点、分词汇的“是”字豁免
    date_keywords = ["月", "号", "日", "星期", "今天", "明天", "昨天", "今年", "明年", "去年", "几", "点", "分", "现在"]
    if any(k in t_time for k in date_keywords):
        u_shi = u_time.replace("是", "")
        t_shi = t_time.replace("是", "")
        if u_shi == t_shi:
            return True

    return False

def apply_scaffolding(student_input, target_sentence, lang_dict):
    # 1. 检查 "几" 后面是否漏了量词
    if "几" in student_input:
        # 添加绝对豁免名单（包括几点、几分等本身无需额外量词的时间单位）
        exemptions = ["几月", "几号", "几日", "星期几", "几岁", "几点", "几分", "几天", "几年", "几点钟"]
        if not any(keyword in student_input for keyword in exemptions):
            mws = ["个", "口", "只", "本", "岁", "块", "件", "瓶", "杯", "碗"]
            parts = student_input.split("几")
            if len(parts) > 1 and parts[1]:
                if not any(mw in parts[1][:2] for mw in mws):
                    return False, lang_dict.get("scaffold_mw", "💡 Hint: In Chinese, when asking 'how many' with '几', you usually need a measure word (like 个, 口, 本) right after it. Try again!")

    # 2. 检查方位词是否误加了 "的"
    if "的" in target_sentence and any(p in target_sentence for p in ["上", "下", "前", "后", "里"]):
        if "的" in student_input:
            for noun in ["书", "水果", "电脑", "猫", "狗", "衣服", "桌子", "椅子", "杯子"]:
                if noun in student_input and student_input.find(noun) < student_input.find("的"):
                    return False, lang_dict.get("scaffold_de", "💡 Hint: Position words (like 上/下/里) usually attach directly to the noun without '的'. Try again!")
    return True, ""

async def generate_tts_audio(text, voice_code="zh-CN-XiaoxiaoNeural"):
    # 强制击穿浏览器音频缓存
    output_file = f"temp_audio_{int(time.time())}_{random.randint(100,999)}.mp3"
    communicate = edge_tts.Communicate(text, voice_code)
    await communicate.save(output_file)
    return output_file

async def handle_audio_logic(full_response):
    clean_text = re.sub(r'<audio[^>]*>.*?</audio>', '', full_response, flags=re.DOTALL).strip()
    audio_match = re.search(r'<audio[^>]*>(.*?)</audio>', full_response, flags=re.DOTALL)
    
    if audio_match:
        raw_audio_text = audio_match.group(1)
        safe_audio_text = re.sub(r'<[^>]+>', '', raw_audio_text).strip()
        if safe_audio_text:
            audio_path = await generate_tts_audio(safe_audio_text)
            return clean_text, audio_path
    return clean_text, None

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
    if 'qa_idx' not in st.session_state: 
        st.session_state.qa_idx = 0
    if 'qa_retry_count' not in st.session_state: 
        st.session_state.qa_retry_count = 0
    if 'consolidation_count' not in st.session_state: 
        st.session_state.consolidation_count = 0
    if 'asked_questions' not in st.session_state: 
        st.session_state.asked_questions = []
    if 'last_audio_hash' not in st.session_state:
        st.session_state.last_audio_hash = None
    if 'q_start_idx' not in st.session_state:
        st.session_state.q_start_idx = 0
    if 'qa_start_idx' not in st.session_state:
        st.session_state.qa_start_idx = 0
    if 'pool_seed' not in st.session_state:
        st.session_state.pool_seed = int(time.time())

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
                    welcome_pal = f"👋 ¡Hola! Soy tu compañero de práctica, {DRAGON_PAL}.\n\n¿De qué te gustaría hablar hoy? ¡Sin presiones!\n\n**小龙人:** 你好！今天想聊点什么？<audio>你好！我是小龙人。今天想聊点什么？</audio>"
                else:
                    welcome_pal = f"👋 Hello! I am your language partner, {DRAGON_PAL}.\n\nWhat would you like to talk about today? No pressure!\n\n**小龙人:** 你好！今天想聊点什么？<audio>你好！我是小龙人。今天想聊点什么？</audio>"
                
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
            st.session_state.consolidation_count = 0 
            st.session_state.qa_idx = 0
            st.session_state.qa_retry_count = 0
            st.session_state.asked_questions = []
            st.session_state.pool_seed = int(time.time())
            st.session_state.last_audio_hash = None
            
            all_sentences_raw = KNOWLEDGE_BASE[unit].get("sentences", [])
            all_sentences = [s for s in all_sentences_raw if "属" not in get_question_text(s)]
            
            target_count = 10
            
            if len(all_sentences) <= target_count:
                sampled_questions = list(all_sentences)
            else:
                step = len(all_sentences) / target_count
                sampled_questions = [all_sentences[int(i * step)] for i in range(target_count)]
                
            st.session_state.active_questions = sampled_questions
            
            all_dialogues_raw = KNOWLEDGE_BASE[unit].get("dialogues", [])
            all_dialogues = [d for d in all_dialogues_raw if "属" not in get_question_text(d)]
            raw_qa_pool = []
            seen_qa = set()
            
            for item in all_dialogues:
                text = get_question_text(item)
                if text not in seen_qa:
                    raw_qa_pool.append(item)
                    seen_qa.add(text)
                    
            for item in all_sentences:
                zh_text = get_question_text(item)
                if ("？" in zh_text or "?" in zh_text) and zh_text not in seen_qa:
                    raw_qa_pool.append(item)
                    seen_qa.add(zh_text)
                    
            translation_texts = {get_question_text(q) for q in sampled_questions}
            primary_qa = [q for q in raw_qa_pool if get_question_text(q) not in translation_texts]
            fallback_qa = [q for q in raw_qa_pool if get_question_text(q) in translation_texts]
            
            random.seed(st.session_state.pool_seed)
            random.shuffle(primary_qa)
            random.shuffle(fallback_qa)
            
            final_qa_pool = (primary_qa + fallback_qa)[:5]
            
            st.session_state.full_qa_pool = final_qa_pool
            qa_count = len(final_qa_pool)
            
            grammar_data = KNOWLEDGE_BASE[unit].get("grammar", {})
            grammar_points = grammar_data.get(lang_key, "- Core grammar\n- Basic sentence structures")
            
            if lang_key == "es":
                qa_step = f"3. Luego, {qa_count} pregunta(s) de situación." if qa_count > 0 else "3. (Sin preguntas de situación en esta unidad)."
                welcome_msg = f"👋 **¡Hola! Soy {DRAGON_MASTER}.**\n\nEn esta clase repasaremos:\n\n{grammar_points}\n\n**Plan:**\n1. Traduciremos {len(sampled_questions)} oraciones clave.\n2. Si hay error, tendremos 1-2 oraciones extra para consolidar.\n{qa_step}\n\n**¿Listo/a? (¡Empieza a traducir abajo!)**"
            else:
                qa_step = f"3. Finally, {qa_count} scenario question(s)." if qa_count > 0 else "3. (No scenario questions in this unit)."
                welcome_msg = f"👋 **Hello! I am {DRAGON_MASTER}.**\n\nIn this class we'll review:\n\n{grammar_points}\n\n**Plan:**\n1. Translate {len(sampled_questions)} key sentences.\n2. If a mistake occurs, 1-2 extra sentences to consolidate.\n{qa_step}\n\n**Ready? (Start translating below!)**"
            
            st.session_state.messages = [{"role": "assistant", "content": welcome_msg, "audio": None}]
            st.session_state.q_start_idx = len(st.session_state.messages)
        
        questions = st.session_state.active_questions
        total_q = len(questions)
        
        if st.session_state.master_mode == "training":
            current_q = st.session_state.master_idx
            
            st.progress(current_q / total_q if total_q > 0 else 0)
            st.caption(f"{T.get('progress', 'Progress')}: {current_q}/{total_q}")
            
            if current_q >= total_q:
                st.session_state.master_mode = "dialogue_pool"
                st.session_state.qa_idx = 0
                st.session_state.qa_retry_count = 0
                st.balloons()
                
                st.session_state.qa_pool = st.session_state.get('full_qa_pool', [])
                qa_count = len(st.session_state.qa_pool)
                
                if qa_count > 0:
                    first_q = get_question_text(st.session_state.qa_pool[0])
                    if lang_key == "es":
                        transition_msg = f"🎉 **¡Felicidades por completar la traducción!**\n\n**{DRAGON_MASTER}:** ¡Ahora pasemos a la sesión de preguntas! Atención: ESTO NO ES TRADUCCIÓN. Por favor, **RESPONDE** a la siguiente pregunta según tu situación real.\n\n🎯 **Pregunta 1:** {first_q} <audio>{first_q}</audio>"
                    else:
                        transition_msg = f"🎉 **Congratulations on completing the translation challenge!**\n\n**{DRAGON_MASTER}:** Now let's move to Q&A! Attention: THIS IS NOT A TRANSLATION. Please **ANSWER** the question logically.\n\n🎯 **Question 1:** {first_q} <audio>{first_q}</audio>"
                else:
                    st.session_state.qa_idx = 1
                    st.session_state.qa_pool = []
                    if lang_key == "es":
                        transition_msg = f"🎉 **¡Felicidades por completar la traducción!**\n\n**{DRAGON_MASTER}:** Esta unidad no tiene preguntas de situación. ¡La clase ha terminado, excelente trabajo! 💪 <audio>恭喜你攻克了所有难关，下课啦！</audio>"
                    else:
                        transition_msg = f"🎉 **Congratulations on completing the translation!**\n\n**{DRAGON_MASTER}:** This unit has no scenario questions. The class is over, excellent work! 💪 <audio>恭喜你攻克了所有难关，下课啦！</audio>"
                
                txt, aud = asyncio.run(handle_audio_logic(transition_msg))
                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
                st.session_state.qa_start_idx = len(st.session_state.messages)
                st.rerun()
            
            target_zh = get_question_text(questions[current_q])
            display_foreign = get_foreign_text(questions[current_q], lang_key)
            
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])
                    if m.get("audio"): 
                        st.audio(m["audio"], format="audio/mp3", autoplay=False)
            
            st.info(f"🎯 **Current Challenge:** Translate to Chinese: **{display_foreign}**")
            
            col_input, col_mic = st.columns([9, 1])
            with col_input: 
                user_input_text = st.chat_input(T.get('input_placeholder', 'Type or use the mic...'))
            with col_mic: 
                audio_input = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_master")
            
            audio_hash = hash(audio_input['bytes']) if audio_input else None
            is_new_audio = audio_input and (audio_hash != st.session_state.last_audio_hash)

            if user_input_text or is_new_audio:
                user_text_clean = ""
                if is_new_audio:
                    st.session_state.last_audio_hash = audio_hash
                    with st.spinner(T.get('transcribing', 'Transcribing audio...')):
                        transcribed_text = transcribe_audio_to_text(audio_input['bytes'])
                        st.session_state.messages.append({"role": "user", "content": f"🎤 {transcribed_text}"})
                        user_text_clean = transcribed_text
                else:
                    st.session_state.messages.append({"role": "user", "content": user_input_text})
                    user_text_clean = user_input_text

                passed, scaffold_msg = apply_scaffolding(user_text_clean, target_zh, T)
                
                if not passed:
                    st.session_state.failed_current = True
                    st.session_state.messages.append({"role": "assistant", "content": scaffold_msg, "audio": None})
                else:
                    if is_translation_match(user_text_clean, target_zh):
                        correct_response = f"{T.get('correct', '✨ Perfect!')} <audio>{target_zh}</audio>"
                        txt, aud = asyncio.run(handle_audio_logic(correct_response))
                        st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
                        
                        if getattr(st.session_state, 'failed_current', False) and st.session_state.consolidation_count < 2:
                            all_unit_sentences = KNOWLEDGE_BASE[unit].get("sentences", [])
                            active_zhs = [get_question_text(q) for q in st.session_state.active_questions]
                            remaining_pool = [q for q in all_unit_sentences if get_question_text(q) not in active_zhs and "属" not in get_question_text(q)]
                            
                            if remaining_pool:
                                st.session_state.consolidation_count += 1
                                consolidation_q = random.choice(remaining_pool)
                                st.session_state.active_questions.insert(st.session_state.master_idx + 1, consolidation_q)
                                consol_msg = "💡 **DA LONGREN:** Let's consolidate! (See the new challenge below)"
                                st.session_state.messages.append({"role": "assistant", "content": consol_msg, "audio": None})
                        
                        st.session_state.master_idx += 1 
                        st.session_state.failed_current = False
                        st.session_state.q_start_idx = len(st.session_state.messages)
                    else:
                        st.session_state.failed_current = True
                        with st.spinner(T.get('analyzing', 'Analyzing...')):
                            current_context = st.session_state.messages[st.session_state.q_start_idx:]
                            
                            da_longren_translation_prompt = f"""
                            You are {DRAGON_MASTER}, an enthusiastic, patient, and deeply encouraging HSK 1 grammar tutor.
                            The student is translating: "{display_foreign}". 
                            Target answer: "{target_zh}".
                            Student's actual input: "{user_text_clean}".
                            
                            LANGUAGE & TONE RULE:
                            1. Speak to the student entirely in {ui_lang}. ONLY the target Chinese words/sentences should be in Simplified Chinese.
                            2. TONE: Be gentle, friendly, enthusiastic, and deeply encouraging! Use emojis (🌟, 💪, 🎉). BUT keep your responses EXTREMELY SHORT, clear, and punchy. DO NOT write long paragraphs.
                            3. VISUAL CLARITY: You MUST use heavy brackets 【 】 whenever you refer to specific Chinese words to replace or use.
                            
                            CRITICAL ALGORITHM (Check these conditions in order):
                            
                            0. MULTIPLE STRUCTURAL ERRORS (The 3-step Combo):
                               IF the student's input has 2 or more distinct errors (e.g., missing measure word AND wrong position word AND foreign word order):
                               - Output: "Great try! 🌟 But this sentence has a few typical errors (like measure words or word order). Let's use this ultimate formula: 【[Provide the correct structural formula here, e.g., Place + 有 + Noun]】. Can you try putting your words into this formula?"
                               - Stop generating.

                            1. ACTION AT A PLACE (Foreign Thinking):
                               IF the target uses "Subject + 在 + Place + Verb", but the student puts the place at the end (e.g., 我工作在医院):
                               - Output: "Oops, this is foreign language thinking! 🌟 In Chinese, the location comes BEFORE the action."
                               - Give the formula: 【Someone/Subject】 + 【在】 + 【Place】 + 【Verb/Action】.
                               - Stop generating.

                            2. MISSING MEASURE WORD WITH THIS/THAT (这/那):
                               IF the target has "这/那" + Measure Word + Noun, and the student wrote 这/那 + Noun:
                               - Output: "Great try! 🌟 But in Chinese, when we say 'this [noun]' or 'that [noun]', we MUST use a measure word."
                               - Give the formula: 【这 / 那】 + 【Measure Word】 + 【Noun】.
                               - Stop generating.

                            3. PLACE + 有 + NOUN (There is/are...):
                               IF the target uses "Place + 有 + Noun", and the student wrote "Noun + 在 + Place":
                               - Output: "You are so close! 💪 To say 'There is/are [something] in [a place]', Chinese uses a special fixed structure."
                               - Give the formula: 【Place】 + 【有】 + 【Something/Someone】.
                               - Stop generating.
                            
                            4. QUESTION WITH "什么", "做/干什么", "几", "哪", OR "谁的" (WHOSE):
                               IF the student puts the question word at the beginning (foreign word order):
                               - STEP A (If they haven't provided a simple declarative statement yet):
                                 You MUST output exactly this logic in {ui_lang}: "🌟 Oops, this is foreign language thinking! Let's think of a natural declarative answer to THIS sentence first. For example, how do you say: '[Insert an English declarative sentence answering the target question from a 1st-person perspective]?'"
                                 CRITICAL LOGIC RULE FOR YOUR EXAMPLE:
                                 - Change 2nd person pronouns (you/your) from the target question to 1st person (I/my) for the answer.
                                 - If the target asks 哪国, answer with 中国.
                                 - If the target asks 谁的, answer with 我的.
                                 - If the target asks with 几 (including 几点, 几个, 几岁, 几分), answer using a simple number between 1 and 10 (like 一, 二, 三, 五, 八) (e.g., 五点, 三个, 八岁).
                                 - If the target asks 什么, answer with 米饭 or 茶.
                                 Wait for their reply. Stop generating.
                                 
                               - STEP B (If they already provided the statement):
                                 You MUST output exactly this logic in {ui_lang}: "Excellent! 🎉 Now, let's turn it back into the question! Keep the exact same word order, but replace the answer word 【[e.g., 中国 / 我的 / 八]】 with the question word 【[Target Question Word, e.g., 哪国 / 谁的 / 几]】! (Also remember to change 【我/我的】 back to 【你/你的】 if needed for the final question)."
                                 *CRITICAL EXCEPTION FOR "几"*: If the target uses 几 (e.g., 几点, 几个, 几岁), explicitly instruct them to ONLY replace the specific number they used (e.g., 【三】 or 【八】) with 【几】. Do NOT replace the unit/measure word (e.g., say "replace 【八】 with 【几】", NEVER say "replace 【八点】 with 【几点】").
                                 *CRITICAL FOR "DO WHAT"*: If asking what to DO (做什么), explicitly tell them to replace the action with 【做什么】, not just 【什么】.
                                 Stop generating.

                            5. SIMPLE "谁" (WHO) QUESTION WITHOUT "的" (e.g. 他们是谁？):
                               - Output: "Good try! 🌟 In Chinese, even for questions, we stick to the simplest declarative structure: 【Subject】 + 【Verb】 + 【Object】. The question word 【谁】 just sits in the Object or Subject position."
                               - Stop generating.
                               
                            6. TARGET IS A STATEMENT:
                               - Output: "Almost there! 💪 In Chinese, the structure is simpler: 【Subject】 + 【Verb】 + 【Object】 (e.g., 【我】 + 【叫】 + 【Lucia】)."
                               - Stop generating.
                               
                            7. NORMAL MISTAKES (Wrong character, etc.):
                               - Point out the specific mistake using 【 】 warmly. Keep it to one short sentence.
                               - Note: Measure words are OPTIONAL after '多少'. Do NOT correct them if they just say '多少' + Noun without a measure word.
                            
                            8. STRICTEST RULE 1 (NO FORCED OMISSIONS): NEVER tell a student to omit a subject (like 你 or 我). Having a subject is ALWAYS correct in Chinese. If their subject is in the wrong place, guide them to move it (usually to the very beginning), but DO NOT tell them to delete it.
                            9. STRICTEST RULE 2 (NO CHEATING): NEVER give the full correct target sentence ("{target_zh}") directly! NEVER output "✨ Perfect! You nailed it." or pretend the user passed if they failed.
                            """
                            ai_feedback = get_ai_response(current_context, da_longren_translation_prompt)
                            st.session_state.messages.append({"role": "assistant", "content": ai_feedback, "audio": None})
                st.rerun()

        elif st.session_state.master_mode == "dialogue_pool":
            total_qa = len(st.session_state.qa_pool)
            is_class_dismissed = total_qa == 0 or st.session_state.qa_idx >= total_qa

            for m in st.session_state.messages:
                with st.chat_message(m["role"]): 
                    st.markdown(m["content"])
                    if m.get("audio"): 
                        st.audio(m["audio"], format="audio/mp3", autoplay=False)
            
            if not is_class_dismissed:
                st.info(f"🎯 **Q&A Challenge ({st.session_state.qa_idx + 1}/{total_qa}):** Please **ANSWER** the question above.")
            else:
                st.success("🎉 Class Dismissed! Excellent Job!")
            
            col_input, col_mic = st.columns([9, 1])
            with col_input:
                user_input = st.chat_input(T.get('input_placeholder', 'Type or use the mic...'), disabled=is_class_dismissed)
            with col_mic:
                if not is_class_dismissed:
                    audio_input = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_pool")
                else:
                    audio_input = None
            
            audio_hash = hash(audio_input['bytes']) if audio_input else None
            is_new_audio = audio_input and (audio_hash != st.session_state.last_audio_hash)

            if user_input or is_new_audio:
                if is_new_audio:
                    st.session_state.last_audio_hash = audio_hash
                    with st.spinner(T.get('transcribing', 'Transcribing audio...')):
                        transcribed_text = transcribe_audio_to_text(audio_input['bytes'])
                        st.session_state.messages.append({"role": "user", "content": f"🎤 {transcribed_text}"})
                else:
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                with st.spinner(T.get('analyzing', 'Analyzing...')):
                    current_q_zh = get_question_text(st.session_state.qa_pool[st.session_state.qa_idx])
                    
                    current_context = st.session_state.messages[st.session_state.qa_start_idx:]
                    
                    da_longren_qa_prompt = f"""
                    You are {DRAGON_MASTER}, a warm, encouraging, and highly supportive HSK 1 grammar tutor conducting a Q&A test. 
                    You just asked the student: "{current_q_zh}"
                    The student replied with the latest message.
                    
                    LANGUAGE & TONE RULE:
                    1. You MUST speak to the student entirely in {ui_lang}. ONLY output Chinese for the student's correct sentence in the <audio> tag. Do NOT explain grammar in Chinese.
                    2. TONE: Be extremely positive and friendly! Use emojis to celebrate their success. Keep it concise.
                    3. CRITICAL AUDIO FORMAT RULE: You MUST output EXACTLY <audio>中文句子</audio>. Do NOT put emojis, URLs, or HTML attributes like <source src="..."> inside the tag!
                    
                    YOUR TASK:
                    1. Check if they are merely TRANSLATING. If they translated the question instead of answering it, tell them gently: "Oops! This is not a translation exercise. Please answer the question based on a real situation! 💡"
                    2. Check their ANSWER. If it makes logical sense as a response to "{current_q_zh}" and uses acceptable HSK1 grammar, you MUST include the exact secret flag "[PASS]" anywhere in the response. Praise them enthusiastically in {ui_lang} and output their correct sentence in <audio>.
                    3. If their answer is wrong or unnatural, comfort them, gently correct the grammar in {ui_lang} and ask them to try answering again. 
                    4. DO NOT ASK THE NEXT QUESTION. UNDER NO CIRCUMSTANCES should you invent or ask a follow-up question.
                    """
                    
                    raw_ai_reply = get_ai_response(current_context, da_longren_qa_prompt)
                    
                    if "[PASS]" in raw_ai_reply:
                        st.session_state.qa_idx += 1
                        st.session_state.qa_retry_count = 0 
                        
                        display_reply = raw_ai_reply.replace("[PASS]", "").strip()
                        txt, aud = asyncio.run(handle_audio_logic(display_reply))
                        st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
                        
                        if st.session_state.qa_idx < total_qa:
                            next_q = get_question_text(st.session_state.qa_pool[st.session_state.qa_idx])
                            next_msg = f"🎯 **Next Question:** {next_q} <audio>{next_q}</audio>"
                            ntxt, naud = asyncio.run(handle_audio_logic(next_msg))
                            st.session_state.messages.append({"role": "assistant", "content": ntxt, "audio": naud})
                        else:
                            end_msg = "🎉 **恭喜完成所有难关，非常棒！**\n\n顺利完成了翻译和情景问答！这次课程到此结束，下课啦！希望能继续保持对中文的热情，下次再见！💪 <audio>恭喜攻克所有难关，下课啦！</audio>" if lang_key == "es" else "🎉 **Congratulations on overcoming all challenges, excellent work!**\n\nYou successfully finished the translation and Q&A! This class is now over. Hope you keep up your passion for Chinese, see you next time! 💪 <audio>恭喜攻克所有难关，下课啦！</audio>"
                            etxt, eaud = asyncio.run(handle_audio_logic(end_msg))
                            st.session_state.messages.append({"role": "assistant", "content": etxt, "audio": eaud})
                        st.session_state.qa_start_idx = len(st.session_state.messages)
                    else:
                        st.session_state.qa_retry_count += 1
                        txt, aud = asyncio.run(handle_audio_logic(raw_ai_reply))
                        
                        if st.session_state.qa_retry_count >= 3:
                            st.session_state.qa_retry_count = 0
                            st.session_state.qa_idx += 1
                            
                            skip_hint = "\n\n💡 **DA LONGREN:** Parece que estás atascado aquí. ¡No te preocupes, pasemos a la siguiente!" if lang_key == "es" else "\n\n💡 **DA LONGREN:** It seems you are stuck here. Don't worry, let's move on to the next one! 🌟"
                            txt += skip_hint
                            st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
                            
                            if st.session_state.qa_idx < total_qa:
                                next_q = get_question_text(st.session_state.qa_pool[st.session_state.qa_idx])
                                next_msg = f"🎯 **Next Question:** {next_q} <audio>{next_q}</audio>"
                                ntxt, naud = asyncio.run(handle_audio_logic(next_msg))
                                st.session_state.messages.append({"role": "assistant", "content": ntxt, "audio": naud})
                            else:
                                end_msg = "🎉 **恭喜完成所有难关，非常棒！**\n\n顺利完成了翻译和情景问答！这次课程到此结束，下课啦！希望能继续保持对中文的热情，下次再见！💪 <audio>恭喜攻克所有难关，下课啦！</audio>" if lang_key == "es" else "🎉 **Congratulations on overcoming all challenges, excellent work!**\n\nYou successfully finished the translation and Q&A! This class is now over. Hope you keep up your passion for Chinese, see you next time! 💪 <audio>恭喜攻克所有难关，下课啦！</audio>"
                                etxt, eaud = asyncio.run(handle_audio_logic(end_msg))
                                st.session_state.messages.append({"role": "assistant", "content": etxt, "audio": eaud})
                            
                            st.session_state.qa_start_idx = len(st.session_state.messages)
                        else:
                            st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
                        
                st.rerun()

    elif st.session_state.current_view in ["pal", "quest"]:
        st.sidebar.button("⬅️ Back", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.selectbox("HSK Level", ["HSK 1", "HSK 2", "HSK 3"])
        
        is_quest = (st.session_state.current_view == "quest")
        st.header(T.get('m3_title', 'Quest Mode') if is_quest else f"{DRAGON_PAL} - Friend Chat")
        
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
            user_input = st.chat_input(T.get('input_placeholder', 'Type...'))
        with col_mic:
            audio_input = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_pal")
            
        audio_hash = hash(audio_input['bytes']) if audio_input else None
        is_new_audio = audio_input and (audio_hash != st.session_state.last_audio_hash)

        if user_input or is_new_audio:
            if is_new_audio:
                st.session_state.last_audio_hash = audio_hash
                st.session_state.messages.append({"role": "user", "content": "🎤 [Voice Message]"})
            else:
                st.session_state.messages.append({"role": "user", "content": user_input})
            
            if is_quest:
                system_prompt = SCENARIO_DB[st.session_state.active_quest]["prompt"] + " 每次回复都要在最后加上 <audio>发音的中文句子</audio> 标签。"
            else:
                system_prompt = f"当前身份是'{DRAGON_PAL}'，一个热情、幽默的中文语伴。请务必使用简单的 HSK 1 词汇。每次回复都要在最后加上 <audio>发音的中文句子</audio> 标签。"
            
            with st.spinner(T.get('analyzing', 'Analyzing...')):
                audio_bytes = audio_input['bytes'] if is_new_audio else None
                raw_ai_reply = get_ai_response(st.session_state.messages, system_prompt, audio_bytes=audio_bytes)
                txt, audio = asyncio.run(handle_audio_logic(raw_ai_reply))
                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": audio})
            st.rerun()

if __name__ == "__main__":
    main()
