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
        "progress": "Progreso"
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
        "progress": "Progress"
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
    
    # 安全合并连续的 user/model 消息，防止 400 错误
    gemini_history = []
    for msg in messages_history[:-1]:
        role = "user" if msg["role"] == "user" else "model"
        content = msg["content"]
        # 清除音频标签，防止大模型误读干扰
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
    """安全提取问题文本，防 KeyError"""
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
    """安全提取外语翻译文本"""
    if isinstance(q_item, dict):
        return q_item.get(lang_key, q_item.get("en", "Translate this"))
    return "Translate this"

def is_translation_match(user_input, target):
    """高级语感判分引擎：根据 HSK1 规则进行智能放行"""
    def clean(t):
        return re.sub(r'[^\w\u4e00-\u9fff]', '', t).strip()

    u_clean = clean(user_input)
    t_clean = clean(target)

    # 1. 绝对一致直接放行
    if u_clean == t_clean:
        return True

    # 2. 单复数/敬语等价 (你/你们/您/您们)
    u_temp = u_clean.replace("你们", "你").replace("您们", "你").replace("您", "你")
    t_temp = t_clean.replace("你们", "你").replace("您们", "你").replace("您", "你")
    if u_temp == t_temp:
        return True

    # 3. 亲属/场所“的”字精确豁免
    close_nouns = ["妈妈", "爸爸", "哥哥", "姐姐", "弟弟", "妹妹", "朋友", "家", "学校", "老师", "名字"]
    u_de = u_temp
    t_de = t_temp
    for noun in close_nouns:
        u_de = u_de.replace(f"的{noun}", noun)
        t_de = t_de.replace(f"的{noun}", noun)
    if u_de == t_de:
        return True

    # 4. 日期/时间语境下的“哪天/几号”等价与“是”字豁免
    u_time = u_de.replace("哪天", "几号")
    t_time = t_de.replace("哪天", "几号")
    date_keywords = ["月", "号", "日", "星期", "今天", "明天", "昨天", "今年", "明年", "去年", "几"]
    
    if any(k in t_time for k in date_keywords):
        u_shi = u_time.replace("是", "")
        t_shi = t_time.replace("是", "")
        if u_shi == t_shi:
            return True

    return False

def apply_scaffolding(student_input, target_sentence, lang_dict):
    # 特定题型不触发量词鹰架
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
    # 增加随机数防止缓存冲突
    output_file = f"temp_audio_{int(time.time())}_{random.randint(100,999)}.mp3"
    communicate = edge_tts.Communicate(text, voice_code)
    await communicate.save(output_file)
    return output_file

async def handle_audio_logic(full_response):
    # 精准剥离 <audio> 标签用于渲染组件
    clean_text = re.sub(r'<audio[^>]*>.*?</audio>', '', full_response, flags=re.DOTALL).strip()
    audio_match = re.search(r'<audio[^>]*>(.*?)</audio>', full_response, flags=re.DOTALL)
    
    if audio_match:
        audio_path = await generate_tts_audio(audio_match.group(1))
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

    # 全局状态初始化
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
    # 全局音频哈希锁，用于防止语音组件引起死循环
    if 'last_audio_hash' not in st.session_state:
        st.session_state.last_audio_hash = None

    # ------------------------------------------
    # 首页视图
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

    # ------------------------------------------
    # Master 主线模式
    # ------------------------------------------
    elif st.session_state.current_view == "master":
        st.sidebar.button("⬅️ Back", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        unit = st.sidebar.selectbox("Unit", list(KNOWLEDGE_BASE.keys()), format_func=lambda x: KNOWLEDGE_BASE[x]["title"])
        st.header(f"{DRAGON_MASTER} - {KNOWLEDGE_BASE[unit]['title']}")
        
        # 单元重置与抽题初始化
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
            
            # 1. 抽取翻译题 (分桶随机抽样算法)
            all_sentences = KNOWLEDGE_BASE[unit].get("sentences", [])
            target_count = 10
            sampled_questions = []
            
            if len(all_sentences) <= target_count:
                sampled_questions = list(all_sentences)
            else:
                bucket_size = len(all_sentences) / target_count
                for i in range(target_count):
                    start_idx = int(i * bucket_size)
                    end_idx = int((i + 1) * bucket_size) if i < target_count - 1 else len(all_sentences)
                    bucket = all_sentences[start_idx:end_idx]
                    if bucket:
                        sampled_questions.append(random.choice(bucket))
                
            st.session_state.active_questions = sampled_questions
            
            # 2. 组装终极防撞车问答池
            all_dialogues = KNOWLEDGE_BASE[unit].get("dialogues", [])
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
        
        questions = st.session_state.active_questions
        total_q = len(questions)
        
        # ------------------------------------------
        # 阶段 1：翻译特训
        # ------------------------------------------
        if st.session_state.master_mode == "training":
            current_q = st.session_state.master_idx
            
            st.progress(current_q / total_q if total_q > 0 else 0)
            st.caption(f"{T['progress']}: {current_q}/{total_q}")
            
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
                user_input_text = st.chat_input(T['input_placeholder'])
            with col_mic: 
                audio_input = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_master")
            
            # 音频死循环锁
            audio_hash = hash(audio_input['bytes']) if audio_input else None
            is_new_audio = audio_input and (audio_hash != st.session_state.last_audio_hash)

            if user_input_text or is_new_audio:
                user_text_clean = ""
                if is_new_audio:
                    st.session_state.last_audio_hash = audio_hash
                    with st.spinner(T['transcribing']):
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
                        correct_response = f"{T['correct']} <audio>{target_zh}</audio>"
                        txt, aud = asyncio.run(handle_audio_logic(correct_response))
                        st.session_state.messages.append({"role": "assistant", "content": txt, "audio": aud})
                        
                        if getattr(st.session_state, 'failed_current', False) and st.session_state.consolidation_count < 2:
                            all_unit_sentences = KNOWLEDGE_BASE[unit].get("sentences", [])
                            active_zhs = [get_question_text(q) for q in st.session_state.active_questions]
                            remaining_pool = [q for q in all_unit_sentences if get_question_text(q) not in active_zhs]
                            
                            if remaining_pool:
                                st.session_state.consolidation_count += 1
                                consolidation_q = random.choice(remaining_pool)
                                st.session_state.active_questions.insert(st.session_state.master_idx + 1, consolidation_q)
                                consol_msg = "💡 **DA LONGREN:** Let's consolidate! (See the new challenge below)"
                                st.session_state.messages.append({"role": "assistant", "content": consol_msg, "audio": None})
                        
                        st.session_state.master_idx += 1 
                        st.session_state.failed_current = False
                    else:
                        st.session_state.failed_current = True
                        with st.spinner(T['analyzing']):
                            da_longren_translation_prompt = f"""
                            You are {DRAGON_MASTER}, an enthusiastic, patient, and deeply encouraging HSK 1 grammar tutor.
                            The student is translating: "{display_foreign}". 
                            Target answer: "{target_zh}".
                            Student's actual input: "{user_text_clean}".
                            
                            LANGUAGE & TONE RULE:
                            1. Speak to the student entirely in {ui_lang}. ONLY the target Chinese words/sentences should be in Simplified Chinese.
                            2. TONE: Be warm and supportive! Use encouraging phrases like "Don't worry!", "You are so close!", or "Great try!" and add friendly emojis.
                            
                            CRITICAL ALGORITHM (Analyze the student's actual input against the target):
                            1. DID THEY JUST USE THE WRONG CHARACTER/PRONOUN? (e.g., student inputted '他' instead of '她', or vice versa):
                               - Gently point out the specific character mistake (e.g., "You got the structure and pronunciation perfectly right, but check the Chinese character for 'he/she/it'!" or similar).
                               - Stop generating immediately.
                               
                            2. IS THE TARGET SENTENCE A QUESTION? (Check if "{target_zh}" contains a question mark or question words like 什么, 几, 哪).
                               IF YES, AND you detect direct translation in their input (e.g. "什么是你的名字", "什么星期"):
                               - Say warmly in {ui_lang}: "This is typical foreign language thinking. Let's switch to Chinese thinking. Let's think about the declarative answer to this question first."
                               - Ask them to provide the declarative answer (e.g., "My name is Lucia" or "Tomorrow is Tuesday"). Wait for their reply.
                               - Once they provide the declarative answer, explicitly guide them: "Excellent! Now, to form the question, replace the specific word (like the name or number) with the correct question word." 
                               - Stop generating immediately.
                               
                            3. IS THE TARGET SENTENCE A STATEMENT? (e.g. Target is "我叫Lucia", but student says "我名字是Lucia").
                               IF YES, AND you detect direct translation:
                               - Say warmly in {ui_lang}: "Good try! However, this is typical foreign language thinking. Let's look at the correct Chinese structure."
                               - Provide the basic grammar structure scaffold (e.g., "In Chinese, to say 'My name is', we use Subject + 叫 + Name").
                               - Gently ask them to try again.
                               - Stop generating immediately.
                               
                            4. NORMAL MISTAKES: Point out specifically what is missing or wrong based on their actual input (e.g., "You forgot the word for 'teacher'") OR give the basic grammar scaffold.
                            
                            5. STRICTEST RULE: NEVER give the full correct target sentence ("{target_zh}") directly in your response! NEVER! You must guide the student to correct their own input.
                            6. DO NOT EXPLAIN OMISSIONS. DO NOT say "you can omit 是 or 的".
                            7. DO NOT output internal commands like "SHUT UP AND WAIT".
                            8. DO NOT say goodbye or wrap up.
                            """
                            ai_feedback = get_ai_response(st.session_state.messages, da_longren_translation_prompt)
                            st.session_state.messages.append({"role": "assistant", "content": ai_feedback, "audio": None})
                st.rerun()

        # ------------------------------------------
        # 阶段 2：智能实战问答池
        # ------------------------------------------
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
                user_input = st.chat_input(T['input_placeholder'], disabled=is_class_dismissed)
            with col_mic:
                if not is_class_dismissed:
                    audio_input = mic_recorder(start_prompt="🎤", stop_prompt="⏹️", key="mic_pool")
                else:
                    audio_input = None
            
            # 音频死循环锁
            audio_hash = hash(audio_input['bytes']) if audio_input else None
            is_new_audio = audio_input and (audio_hash != st.session_state.last_audio_hash)

            if user_input or is_new_audio:
                if is_new_audio:
                    st.session_state.last_audio_hash = audio_hash
                    with st.spinner(T['transcribing']):
                        transcribed_text = transcribe_audio_to_text(audio_input['bytes'])
                        st.session_state.messages.append({"role": "user", "content": f"🎤 {transcribed_text}"})
                else:
                    st.session_state.messages.append({"role": "user", "content": user_input})
                    
                with st.spinner(T['analyzing']):
                    current_q_zh = get_question_text(st.session_state.qa_pool[st.session_state.qa_idx])
                    
                    da_longren_qa_prompt = f"""
                    You are {DRAGON_MASTER}, a warm, encouraging, and highly supportive HSK 1 grammar tutor conducting a Q&A test. 
                    You just asked the student: "{current_q_zh}"
                    The student replied with the latest message.
                    
                    LANGUAGE & TONE RULE:
                    1. You MUST speak to the student entirely in {ui_lang} for all instructions, praises, and feedback. ONLY output Chinese for the student's correct sentence in the <audio> tag. Do NOT explain grammar in Chinese.
                    2. TONE: Be extremely positive and friendly! Use emojis (🎉, 👏, ✨, 💡) to celebrate their success and offer gentle encouragement if they make a mistake.
                    
                    YOUR TASK:
                    1. Check if they are merely TRANSLATING. If they translated the question instead of answering it, tell them gently in {ui_lang}: "Oops! This is not a translation exercise. Please answer the question based on a real situation! 💡"
                    2. Check their ANSWER. If it makes logical sense as a response to "{current_q_zh}" and uses acceptable HSK1 grammar, you MUST include the exact secret flag "[PASS]" anywhere in the response. Praise them enthusiastically in {ui_lang} and output their correct sentence in <audio>.
                    3. If their answer is wrong or unnatural, comfort them, gently correct the grammar in {ui_lang} and ask them to try answering again. 
                    4. DO NOT ASK THE NEXT QUESTION. The system handles the next question automatically.
                    """
                    
                    raw_ai_reply = get_ai_response(st.session_state.messages, da_longren_qa_prompt)
                    
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
                    else:
                        st.session_state.qa_retry_count += 1
                        txt, aud = asyncio.run(handle_audio_logic(raw_ai_reply))
                        
                        # 熔断机制：答错达到 3 次强制跳过
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
                        else:
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
            
        # 【核心修复】：切断旧语音伴随文字发送的幽灵 Bug
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
            
            with st.spinner("Analyzing..."):
                # 【关键修复】：仅当 is_new_audio 为真时，才向大模型传输语音字节码
                audio_bytes = audio_input['bytes'] if is_new_audio else None
                raw_ai_reply = get_ai_response(st.session_state.messages, system_prompt, audio_bytes=audio_bytes)
                txt, audio = asyncio.run(handle_audio_logic(raw_ai_reply))
                st.session_state.messages.append({"role": "assistant", "content": txt, "audio": audio})
            st.rerun()

if __name__ == "__main__":
    main()
