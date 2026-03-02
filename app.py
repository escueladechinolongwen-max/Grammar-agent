import streamlit as st
import json
import os
import re
import random
import asyncio
import time

# ==========================================
# 1. 独立数据加载模块
# ==========================================
def load_knowledge_base():
    file_path = "hsk1_corpus.json"
    if not os.path.exists(file_path):
        st.error(f"Error: 找不到数据文件 {file_path}。请确保它与 app.py 在同一文件夹。")
        return {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error: 解析 JSON 失败: {e}")
        return {}

KNOWLEDGE_BASE = load_knowledge_base()

SCENARIO_DB = {
    "☕ Cafe Order": "You are at a cafe in Beijing. Order something to drink and ask for the price.",
    "🏥 At Hospital": "You are looking for Dr. Zhang's son at the hospital.",
    "🎓 University": "Talk about how you met your friend at the university.",
    "📞 Phone Call": "A friend calls to ask what you are doing right now.",
    "🌦️ Weather Talk": "Call your parents to ask about the weather and their health.",
    "🛒 Shopping": "You are at a store. Try to buy some apples or clothes.",
    "🏠 Home Visit": "You are going to your teacher's house. Discuss the time.",
    "💼 Job Interview": "Introduce your job and your family members.",
    "🎬 Cinema": "Discuss with a friend when to go to the cinema.",
    "🏮 New Friend": "Introduce yourself to a new friend."
}

# ==========================================
# 2. TTS 音频与鹰架拦截逻辑
# ==========================================
def generate_tts_audio(text, voice_code="zh-CN-XiaoxiaoNeural"):
    return "temp_audio.mp3" # 对接真实 TTS API

async def handle_audio_logic(full_response, ui_lang):
    display_text = re.sub(r'</?p>', '', full_response)
    display_text = re.sub(r'<audio[^>]*>.*?</audio>', '', display_text).replace('</audio>', '')
    audio_texts = re.findall(r'<audio[^>]*>(.*?)</audio>', full_response, flags=re.DOTALL)
    
    audio_file_path = None
    if audio_texts:
        with st.spinner("🎵 Generating voice..."):
            audio_file_path = generate_tts_audio(" ".join(audio_texts))
    return display_text, audio_file_path

def apply_scaffolding(student_input, target_sentence):
    if "几" in student_input:
        mws = ["个", "口", "只", "本", "岁", "块", "件"]
        if not any(mw in student_input.split("几")[1][:2] for mw in mws if len(student_input.split("几")) > 1):
            return False, "⚠️ 提醒：使用'几'时，请务必在后面加上量词（如：个、只、口、本等）。"
    if "的" in target_sentence and any(p in target_sentence for p in ["上", "下", "前", "后", "里"]):
        if "的" in student_input:
            for noun in ["书", "水果", "电脑", "猫", "狗", "衣服"]:
                if noun in student_input and student_input.find(noun) < student_input.find("的"):
                    return False, "⚠️ 注意句序：中文的描述语（位置/所属）必须放在名词前面。公式：[位置] + 的 + [名词]。"
    return True, ""

# ==========================================
# 3. 核心路由与 UI
# ==========================================
def main():
    if not KNOWLEDGE_BASE:
        st.stop() # 如果数据没加载成功，直接拦截，防止崩溃

    st.set_page_config(page_title="AI Chinese Speaking", layout="wide")
    
    col_empty, col_lang = st.columns([8, 2])
    with col_lang:
        ui_lang = st.selectbox("Language", ["Español", "English", "中文"], label_visibility="collapsed")
    
    UI = {
        "Español": {"back": "Volver", "m1": "Maestro Académico", "m2": "Compañero Fluido", "m3": "Misiones Inmersivas"},
        "English": {"back": "Back", "m1": "Academic Master", "m2": "Fluent Pal", "m3": "Immersive Quests"},
        "中文": {"back": "返回主页", "m1": "金牌导师", "m2": "流利拍档", "m3": "沉浸式实战"}
    }[ui_lang]

    if 'current_view' not in st.session_state: st.session_state.current_view = "landing"
    if 'messages' not in st.session_state: st.session_state.messages = []
    if 'master_mode' not in st.session_state: st.session_state.master_mode = "translation" # 翻译或对话状态

    # --- Landing 页面 ---
    if st.session_state.current_view == "landing":
        st.markdown("<h1 style='text-align: center;'>AI Chinese Speaking</h1>", unsafe_allow_html=True)
        st.divider()
        c1, c2, c3 = st.columns(3)
        with c1:
            st.info(f"### 👨‍🏫 {UI['m1']}\n系统纠错与翻译训练。")
            if st.button("Entrar", key="b1", use_container_width=True):
                st.session_state.current_view = "master"
                st.session_state.messages = []
                st.session_state.master_mode = "translation"
                st.rerun()
        with c2:
            st.success(f"### 🤝 {UI['m2']}\n自适应难度陪练。")
            if st.button("Entrar", key="b2", use_container_width=True):
                st.session_state.current_view = "pal"
                st.session_state.messages = [{"role": "assistant", "content": "你好！今天过得怎么样？"}]
                st.rerun()
        with c3:
            st.warning(f"### 🗺️ {UI['m3']}\n真实场景实战。")
            if st.button("Entrar", key="b3", use_container_width=True):
                st.session_state.current_view = "quest"
                st.session_state.messages = []
                st.rerun()

    # --- 模式 1: Academic Master ---
    elif st.session_state.current_view == "master":
        st.sidebar.button(f"⬅️ {UI['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        unit = st.sidebar.selectbox("Unit", list(KNOWLEDGE_BASE.keys()), format_func=lambda x: KNOWLEDGE_BASE[x]["title"])
        
        st.header(f"Academic Master - {KNOWLEDGE_BASE[unit]['title']}")
        
        # 判断是处于 10 题翻译阶段，还是触发了情景对话奖励
        if st.session_state.master_mode == "translation":
            if 'master_idx' not in st.session_state: st.session_state.master_idx = 0
            sentences = KNOWLEDGE_BASE[unit]["sentences"]
            target = sentences[st.session_state.master_idx % len(sentences)]
            
            st.info(f"**Translate:** {target}")
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            user_input = st.chat_input("Escribe tu traducción...")
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                passed, scaffold_msg = apply_scaffolding(user_input, target)
                if not passed:
                    st.session_state.messages.append({"role": "assistant", "content": scaffold_msg})
                else:
                    if user_input.strip() == target:
                        raw = f"Correcto. <audio>{target}</audio>"
                        txt, audio = asyncio.run(handle_audio_logic(raw, ui_lang))
                        st.session_state.messages.append({"role": "assistant", "content": txt})
                        st.session_state.master_idx += 1
                        
                        # 模拟达到 10 题，进入对话模式
                        if st.session_state.master_idx > 0 and st.session_state.master_idx % 10 == 0:
                            st.session_state.master_mode = "dialogue"
                            st.session_state.messages.append({"role": "assistant", "content": "🎉 翻译全部正确！现在进入实战对话。"})
                    else:
                        st.session_state.messages.append({"role": "assistant", "content": f"Incorrecto. Respuesta: {target}"})
                st.rerun()
                
        elif st.session_state.master_mode == "dialogue":
            # 提取 JSON 中的 dialogues 数组
            dialogue_pair = random.choice(KNOWLEDGE_BASE[unit]["dialogues"])
            
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
                
            st.info(f"**AI:** {dialogue_pair['p']}")
            ans = st.chat_input("Responde a la IA...")
            if ans:
                st.session_state.messages.append({"role": "user", "content": ans})
                st.session_state.messages.append({"role": "assistant", "content": f"非常好！标准回答参考：{dialogue_pair['r']}"})
                st.rerun()
            if st.button("Terminar Unidad"):
                st.session_state.master_mode = "translation"
                st.session_state.messages = []
                st.rerun()

    # --- 模式 2 & 3: Pal 和 Quest 逻辑保持不变 (省略部分重复 UI 代码) ---
    elif st.session_state.current_view in ["pal", "quest"]:
        st.sidebar.button(f"⬅️ {UI['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.header(UI['m2'] if st.session_state.current_view == "pal" else UI['m3'])
        st.write("UI para conversación libre / escenarios...")

if __name__ == "__main__":
    main()
