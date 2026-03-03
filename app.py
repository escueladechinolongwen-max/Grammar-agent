import streamlit as st
import json
import os
import re
import random
import asyncio

# ==========================================
# 1. 数据加载与容错模块
# ==========================================
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

# 完整的场景库
SCENARIO_DB = {
    "☕ Cafe Order": {"goal_en": "Order a drink and pay.", "goal_es": "Pide una bebida y paga.", "ai_start_zh": "你好，想喝点什么？"},
    "🏥 At Hospital": {"goal_en": "Find Dr. Zhang.", "goal_es": "Encuentra al Dr. Zhang.", "ai_start_zh": "你好，请问你找谁？"},
    "🎓 University": {"goal_en": "Talk about university.", "goal_es": "Habla de la universidad.", "ai_start_zh": "我们是在哪里认识的？"},
    "📞 Phone Call": {"goal_en": "Answer a call.", "goal_es": "Contesta una llamada.", "ai_start_zh": "喂？你在做什么呢？"},
    "🛒 Shopping": {"goal_en": "Buy clothes.", "goal_es": "Compra ropa.", "ai_start_zh": "欢迎光临，你想买什么？"}
}

# ==========================================
# 2. 严格的 UI 语言字典 (解决语言混杂问题)
# ==========================================
UI_TEXT = {
    "Español": {
        "title": "Aprendizaje de Chino AI",
        "subtitle": "Elige tu modo de aprendizaje",
        "back": "Volver al Inicio",
        "m1_title": "👨‍🏫 Maestro Académico",
        "m1_desc": "Práctica estructurada y corrección estricta.",
        "m2_title": "🤝 Compañero Fluido",
        "m2_desc": "Práctica de conversación sin presión.",
        "m3_title": "🗺️ Misiones Inmersivas",
        "m3_desc": "Escenarios reales para aplicación práctica.",
        "enter": "Entrar",
        "translate_prompt": "Traduce al chino:",
        "input_placeholder": "Escribe tu traducción aquí...",
        "btn_check": "Comprobar",
        "correct": "¡Correcto!",
        "incorrect": "Incorrecto. La respuesta estándar es:",
        "pal_header": "Conversación Libre",
        "pal_input": "Habla con tu amigo AI...",
        "quest_header": "Selecciona un escenario",
        "quest_btn": "Iniciar Misión",
        "quest_end": "Terminar Misión",
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
        "m1_desc": "Systematic correction and translation training.",
        "m2_title": "🤝 Fluent Pal",
        "m2_desc": "Zero-pressure chat with an AI friend.",
        "m3_title": "🗺️ Immersive Quests",
        "m3_desc": "Real-life scenarios for practical application.",
        "enter": "Enter",
        "translate_prompt": "Translate to Chinese:",
        "input_placeholder": "Type your translation here...",
        "btn_check": "Check Answer",
        "correct": "Correct!",
        "incorrect": "Incorrect. The standard answer is:",
        "pal_header": "Free Conversation",
        "pal_input": "Talk to your AI friend...",
        "quest_header": "Select a Scenario",
        "quest_btn": "Start Mission",
        "quest_end": "End Mission",
        "unit": "Unit",
        "level": "HSK Level",
        "scaffold_mw": "⚠️ Reminder: Don't forget the measure word after '几' (e.g., 个, 只, 本)!",
        "scaffold_de": "⚠️ Reminder: The description goes BEFORE '的'. [Location] + 的 + [Noun]."
    }
}

# ==========================================
# 3. 鹰架逻辑与 TTS
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
    return "temp.mp3" # 替换为真实 TTS 逻辑

async def handle_audio_logic(full_response):
    display_text = re.sub(r'</?p>', '', full_response)
    display_text = re.sub(r'<audio[^>]*>.*?</audio>', '', display_text).replace('</audio>', '')
    audio_texts = re.findall(r'<audio[^>]*>(.*?)</audio>', full_response, flags=re.DOTALL)
    if audio_texts:
        return display_text, generate_tts_audio(" ".join(audio_texts))
    return display_text, None

# ==========================================
# 4. 主程序架构
# ==========================================
def main():
    if not KNOWLEDGE_BASE:
        st.stop()

    st.set_page_config(page_title="AI Chinese Speaking", layout="wide")
    
    # --- 语言控制台 ---
    col_empty, col_lang = st.columns([8, 2])
    with col_lang:
        ui_lang = st.selectbox("Language / Idioma", ["English", "Español"], label_visibility="collapsed")
    
    # 加载对应语言包
    T = UI_TEXT[ui_lang]
    # 用于从 JSON 中提取对应语言的缩写
    lang_key = "es" if ui_lang == "Español" else "en"

    # --- 状态初始化 ---
    if 'current_view' not in st.session_state: st.session_state.current_view = "landing"
    if 'messages' not in st.session_state: st.session_state.messages = []

    # ------------------------------------------
    # Landing 页面
    # ------------------------------------------
    if st.session_state.current_view == "landing":
        st.markdown(f"<h1 style='text-align: center;'>{T['title']}</h1>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align: center; color: gray; margin-bottom: 40px;'>{T['subtitle']}</h4>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info(f"### {T['m1_title']}\n{T['m1_desc']}")
            if st.button(T['enter'], key="b1", use_container_width=True):
                st.session_state.current_view = "master"
                st.session_state.messages = []
                st.rerun()
        with c2:
            st.success(f"### {T['m2_title']}\n{T['m2_desc']}")
            if st.button(T['enter'], key="b2", use_container_width=True):
                st.session_state.current_view = "pal"
                st.session_state.messages = [{"role": "assistant", "content": "你好！今天过得怎么样？"}]
                st.rerun()
        with c3:
            st.warning(f"### {T['m3_title']}\n{T['m3_desc']}")
            if st.button(T['enter'], key="b3", use_container_width=True):
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
        
        if 'master_idx' not in st.session_state: st.session_state.master_idx = 0
        sentences = KNOWLEDGE_BASE[unit]["sentences"]
        current_data = sentences[st.session_state.master_idx % len(sentences)]
        
        # 核心修复 1：显示外语，要求输入中文！
        target_zh = current_data if isinstance(current_data, str) else current_data.get("zh", "")
        display_foreign = current_data.get(lang_key, target_zh) if isinstance(current_data, dict) else target_zh
        
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
                    st.session_state.messages.append({"role": "assistant", "content": f"{T['incorrect']} {target_zh}"})
            st.rerun()

    # ------------------------------------------
    # 模式 2: 🤝 Compañero Fluido (完全修复空白问题)
    # ------------------------------------------
    elif st.session_state.current_view == "pal":
        st.sidebar.button(f"⬅️ {T['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.selectbox(T['level'], ["HSK 1", "HSK 2", "HSK 3"])
        
        st.header(T['pal_header'])
        
        # 渲染聊天记录
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        user_input = st.chat_input(T['pal_input'])
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # 简单的陪聊逻辑
            ai_reply = f"很有意思！<audio>你还会说别的吗？</audio>"
            txt, audio = asyncio.run(handle_audio_logic(ai_reply))
            st.session_state.messages.append({"role": "assistant", "content": txt})
            st.rerun()

    # ------------------------------------------
    # 模式 3: 🗺️ Misiones Inmersivas (完全修复空白问题)
    # ------------------------------------------
    elif st.session_state.current_view == "quest":
        st.sidebar.button(f"⬅️ {T['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.selectbox(T['level'], ["HSK 1", "HSK 2", "HSK 3"])
        
        if not st.session_state.get('active_quest'):
            st.header(T['quest_header'])
            cols = st.columns(2)
            for idx, (title, data) in enumerate(SCENARIO_DB.items()):
                with cols[idx % 2]:
                    with st.container(border=True):
                        st.subheader(title)
                        st.write(f"**Goal:** {data[f'goal_{lang_key}']}")
                        if st.button(T['quest_btn'], key=f"btn_{title}"):
                            st.session_state.active_quest = title
                            st.session_state.messages = [{"role": "assistant", "content": data['ai_start_zh']}]
                            st.rerun()
        else:
            st.header(st.session_state.active_quest)
            if st.button(T['quest_end']):
                st.session_state.active_quest = None
                st.rerun()
                
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
                
            user_input = st.chat_input(T['input_placeholder'])
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                txt, audio = asyncio.run(handle_audio_logic(f"收到。<audio>好的，请继续。</audio>"))
                st.session_state.messages.append({"role": "assistant", "content": txt})
                st.rerun()

if __name__ == "__main__":
    main()
