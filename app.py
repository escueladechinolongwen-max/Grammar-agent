import streamlit as st
import re
import random
import asyncio
import time

# ==========================================
# 1. 全量知识库与场景库 (KNOWLEDGE_BASE)
# ==========================================
KNOWLEDGE_BASE = {
    "u1": {"title": "Unit 1", "sentences": ["你好！", "您好！", "你们好！", "再见！"]},
    "u2": {"title": "Unit 2", "sentences": ["谢谢！", "不客气。", "不谢。", "对不起！", "没关系。"]},
    "u3": {"title": "Unit 3", "sentences": ["我是老师。", "你们是学生。", "他们是西班牙人。", "我叫 Lucia。", "我不是老师。", "你是中国人吗？", "你叫什么名字？"]},
    "u4": {"title": "Unit 4", "sentences": ["我的老师。", "你的同学。", "她的朋友。", "谁是你的汉语老师？", "你是哪国人？", "我是美国人，你呢？", "我的老师叫李月，你的老师呢？"]},
    "u5": {"title": "Unit 5", "sentences": ["一只狗。", "三只猫。", "四口人。", "两只狗。", "两个老师。", "你有几只狗？", "我有四只狗。", "你家有几口人？", "我家有五口人。", "你女儿几岁了？", "我女儿四岁了。", "你今年多大了？", "我三十岁了。"]},
    "u6": {"title": "Unit 6", "sentences": ["我妈妈会说汉语。", "我不会写汉字。", "你会做中国菜吗？", "中国很大。", "中国菜很好吃。", "汉字怎么写？", "中国菜怎么做？", "你妈妈怎么会说汉语？", "这个汉字怎么读？"]},
    "u7": {"title": "Unit 7", "sentences": ["今天是三月二号。", "明天星期几？", "昨天几号？", "谁去学校？", "我们去学校看书。", "请问。", "我们明天去你家。", "你几月去中国？", "我九月去中国。"]},
    "u8": {"title": "Unit 8", "sentences": ["你想喝什么？", "我想喝茶。", "你想吃什么？", "我想吃米饭。", "下午我想去商店。", "你想买什么？", "我想买一个杯子。", "这个杯子多少钱？", "那个杯子十八块。", "你们学校有多少个学生？"]},
    "u9": {"title": "Unit 9", "sentences": ["我在吃饭。", "你儿子在哪儿工作？", "我儿子在医院工作。", "你爸爸在这家医院工作吗？", "你的小猫在哪儿？", "我的小猫在那儿。", "小猫在椅子下面。", "这儿有大医院吗？"]},
    "u10": {"title": "Unit 10", "sentences": ["桌子上有一个电脑和两本汉语书。", "我能坐在这儿吗？", "请你坐在她后面。", "这个学校后面没有大商店。", "椅子下面的书是谁的？", "在买书的那个（人）是我女儿。", "她是你说的那个人吗？"]},
    "u11": {"title": "Unit 11", "sentences": ["现在几点？", "现在十点十分。", "今天下午三点。", "女儿今天几点回家？", "妈妈，我们什么时候去看电影？", "你这个星期一前能回家吗？", "我想去北京住三年。", "我女儿吃饭前想读三十分钟书。"]},
    "u12": {"title": "Unit 12", "sentences": ["北京的天气怎么样？", "你妈妈做的饭太好吃了。", "这本书不太好看。", "这些水果太好吃了。", "我想喝一些中国茶。", "明天会下雨吗？", "明天李小姐会来吗？", "多喝热水，多吃米饭。"]},
    "u13": {"title": "Unit 13", "sentences": ["他在打电话呢。", "我也喜欢看电视。", "你在做什么呢？", "我们在和朋友们喝茶。", "我们下午去商店买些水果吧！", "你明天来我家吧！", "我想给你这本书。", "你在给谁打电话？"]},
    "u14": {"title": "Unit 14", "sentences": ["她买了不少东西。", "我昨天看见李老师了。", "我今天买了不少水果。", "我学了十五分钟汉语。", "我给她买了一件漂亮的衣服。", "我昨天没去学校学汉语。", "我去商店了，但是没买水果。"]},
    "u15": {"title": "Unit 15", "sentences": ["听说你认识王先生。", "我坐出租车去他家。", "我们是两年前认识的。", "我们是在大学认识的。", "我在火车上看见他的。", "我是和朋友们一起坐飞机回来的。", "这本书不是在这家书店买的。"]}
}

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
# 2. TTS 音频引擎与正则解析
# ==========================================
def generate_tts_audio(text, voice_code="zh-CN-XiaoxiaoNeural", rate="+0%"):
    # 此处对接您的真实 TTS API
    return "temp_audio.mp3"

async def handle_audio_logic(full_response, ui_lang):
    display_text = re.sub(r'</?p>', '', full_response)
    display_text = re.sub(r'<audio[^>]*>.*?</audio>', '', display_text)
    display_text = display_text.replace('</audio>', '')
    
    audio_texts = re.findall(r'<audio[^>]*>(.*?)</audio>', full_response, flags=re.DOTALL)
    
    audio_file_path = None
    if audio_texts:
        spinner_msg = "Generating voice..." if ui_lang == "English" else "Generando voz..." if ui_lang == "Español" else "生成语音中..."
        with st.spinner(f"🎵 {spinner_msg}"):
            text_to_speak = " ".join(audio_texts)
            audio_file_path = generate_tts_audio(text_to_speak)
    return display_text, audio_file_path

# ==========================================
# 3. 鹰架教学拦截器
# ==========================================
def apply_scaffolding(student_input, target_sentence):
    # 针对“几”的量词检查
    if "几" in student_input:
        mws = ["个", "口", "只", "本", "岁", "块", "件"]
        if not any(mw in student_input.split("几")[1][:2] for mw in mws if len(student_input.split("几")) > 1):
            return False, "⚠️ 语法提醒：使用'几'时，请务必在后面加上量词（如：个、只、口、本等）。"
            
    # 针对“的”的位置检查
    if "的" in target_sentence and any(p in target_sentence for p in ["上", "下", "前", "后", "里"]):
        if "的" in student_input:
            key_nouns = ["书", "水果", "电脑", "猫", "狗", "衣服"]
            for noun in key_nouns:
                if noun in student_input and student_input.find(noun) < student_input.find("的"):
                    return False, "⚠️ 语法提醒：中文的描述语（位置/所属）必须放在名词前面。公式：[位置] + 的 + [名词]。"
    return True, ""

# ==========================================
# 4. 主程序与多页面路由
# ==========================================
def main():
    st.set_page_config(page_title="AI Chinese Speaking", layout="wide")
    
    # 全局 CSS
    st.markdown("""
        <style>
        .block-container { padding-top: 2rem; }
        .module-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; text-align: center; border: 1px solid #e9ecef; }
        </style>
    """, unsafe_allow_html=True)

    # --- 语言选择 (右上角) ---
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

    # ------------------------------------------
    # Landing 页面
    # ------------------------------------------
    if st.session_state.current_view == "landing":
        st.markdown("<h1 style='text-align: center;'>AI Chinese Speaking</h1>", unsafe_allow_html=True)
        st.markdown("<h4 style='text-align: center; color: gray; margin-bottom: 40px;'>Elige tu modo de aprendizaje</h4>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"<div class='module-card'><h2>👨‍🏫</h2><h3>{UI['m1']}</h3><p>Práctica estructurada y corrección estricta (HSK 1-6).</p></div>", unsafe_allow_html=True)
            if st.button("Entrar", key="btn_m1", use_container_width=True):
                st.session_state.current_view = "master"
                st.session_state.messages = []
                st.rerun()
        with c2:
            st.markdown(f"<div class='module-card'><h2>🤝</h2><h3>{UI['m2']}</h3><p>Práctica de conversación sin presión. IA adaptativa.</p></div>", unsafe_allow_html=True)
            if st.button("Entrar", key="btn_m2", use_container_width=True):
                st.session_state.current_view = "pal"
                st.session_state.messages = [{"role": "assistant", "content": "你好！今天过得怎么样？"}]
                st.rerun()
        with c3:
            st.markdown(f"<div class='module-card'><h2>🗺️</h2><h3>{UI['m3']}</h3><p>10 escenarios de la vida real para aplicación práctica.</p></div>", unsafe_allow_html=True)
            if st.button("Entrar", key="btn_m3", use_container_width=True):
                st.session_state.current_view = "quest"
                st.session_state.messages = []
                st.rerun()

    # ------------------------------------------
    # 模式 1: Academic Master (金牌导师)
    # ------------------------------------------
    elif st.session_state.current_view == "master":
        st.sidebar.button(f"⬅️ {UI['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.title(UI['m1'])
        
        hsk_level = st.sidebar.selectbox("Nivel HSK", ["HSK 1", "HSK 2", "HSK 3", "HSK 4", "HSK 5", "HSK 6"])
        if hsk_level == "HSK 1":
            unit = st.sidebar.selectbox("Unidad", list(KNOWLEDGE_BASE.keys()), format_func=lambda x: KNOWLEDGE_BASE[x]["title"])
            
            st.header(f"Traducción - {KNOWLEDGE_BASE[unit]['title']}")
            
            if 'master_idx' not in st.session_state: st.session_state.master_idx = 0
            sentences = KNOWLEDGE_BASE[unit]["sentences"]
            target = sentences[st.session_state.master_idx % len(sentences)]
            
            st.info(f"**Target Sentence:** {target}")
            
            # 聊天流 UI
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            user_input = st.chat_input("Escribe tu traducción aquí...")
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # 执行无情扫描与鹰架拦截
                passed, scaffold_msg = apply_scaffolding(user_input, target)
                if not passed:
                    st.session_state.messages.append({"role": "assistant", "content": scaffold_msg})
                else:
                    if user_input.strip() == target:
                        raw_response = f"Correcto. <audio>{target}</audio>"
                        display_text, audio_path = asyncio.run(handle_audio_logic(raw_response, ui_lang))
                        st.session_state.messages.append({"role": "assistant", "content": display_text})
                        if audio_path: st.audio(audio_path)
                        st.session_state.master_idx += 1
                    else:
                        st.session_state.messages.append({"role": "assistant", "content": f"Incorrecto. La respuesta estándar es: {target}"})
                st.rerun()

    # ------------------------------------------
    # 模式 2: Fluent Pal (流利拍档)
    # ------------------------------------------
    elif st.session_state.current_view == "pal":
        st.sidebar.button(f"⬅️ {UI['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.title(UI['m2'])
        st.sidebar.selectbox("Nivel HSK", ["HSK 1", "HSK 2", "HSK 3", "HSK 4", "HSK 5", "HSK 6"])
        
        st.header("Conversación Libre")
        
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
        user_input = st.chat_input("Habla con tu amigo AI...")
        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # 自适应难度逻辑判定
            if len(user_input) > 10 or "因为" in user_input or "所以" in user_input:
                ai_reply = f"你说得对！<audio>你的中文越来越好了，接下来你打算做什么？</audio>"
            else:
                ai_reply = f"很好！<audio>我们继续聊天吧，你喜欢吃什么？</audio>"
                
            display_text, audio_path = asyncio.run(handle_audio_logic(ai_reply, ui_lang))
            st.session_state.messages.append({"role": "assistant", "content": display_text})
            if audio_path: st.audio(audio_path)
            st.rerun()

    # ------------------------------------------
    # 模式 3: Immersive Quests (沉浸式实战)
    # ------------------------------------------
    elif st.session_state.current_view == "quest":
        st.sidebar.button(f"⬅️ {UI['back']}", on_click=lambda: st.session_state.update({"current_view": "landing"}))
        st.sidebar.title(UI['m3'])
        st.sidebar.selectbox("Nivel HSK", ["HSK 1", "HSK 2", "HSK 3", "HSK 4", "HSK 5", "HSK 6"])
        
        if 'active_quest' not in st.session_state: st.session_state.active_quest = None

        if not st.session_state.active_quest:
            st.header("Selecciona un escenario")
            cols = st.columns(2)
            for idx, (title, desc) in enumerate(SCENARIO_DB.items()):
                with cols[idx % 2]:
                    with st.container(border=True):
                        st.subheader(title)
                        st.write(desc)
                        if st.button("Iniciar Misión", key=f"start_{title}"):
                            st.session_state.active_quest = title
                            st.session_state.messages = [{"role": "assistant", "content": f"【Escenario: {title}】 开始了。你好！"}]
                            st.rerun()
        else:
            st.header(st.session_state.active_quest)
            if st.button("Terminar Misión"):
                st.session_state.active_quest = None
                st.rerun()
                
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
                
            user_input = st.chat_input("Completa tu misión...")
            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})
                ai_reply = f"收到。<audio>好的，请继续。</audio>"
                display_text, audio_path = asyncio.run(handle_audio_logic(ai_reply, ui_lang))
                st.session_state.messages.append({"role": "assistant", "content": display_text})
                if audio_path: st.audio(audio_path)
                st.rerun()

if __name__ == "__main__":
    main()
