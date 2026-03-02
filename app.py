import streamlit as st
import re
import random
import time

# ==========================================
# 1. 核心语料库 (1-15 单元全量例句)
# ==========================================
KNOWLEDGE_BASE = {
    "u1": {"title": "U1: Hello", "sentences": ["你好！", "您好！", "你们好！", "再见！"], "dialogues": [{"p": "你好！", "r": "你好！"}]},
    "u2": {"title": "U2: Thanks", "sentences": ["谢谢！", "不客气。", "对不起！", "没关系。"], "dialogues": [{"p": "谢谢！", "r": "不客气。"}]},
    "u3": {"title": "U3: Name", "sentences": ["我叫 Lucia。", "你叫什么名字？", "我是老师。", "你是中国人吗？"], "dialogues": [{"p": "你叫什么名字？", "r": "我叫[Nombre]."}]},
    "u4": {"title": "U4: Nationality", "sentences": ["你是哪国人？", "我是美国人，你呢？", "谁是你的汉语老师？"], "dialogues": [{"p": "你是哪国人？", "r": "我是西班牙人。"}]},
    "u5": {"title": "U5: Age/Family", "sentences": ["你家有几口人？", "我有四只狗。", "你女儿几岁了？", "我女儿四岁了。", "你今年多大了？", "我三十岁了。"], "dialogues": [{"p": "你家有几口人？", "r": "我家有四口人。"}]},
    "u6": {"title": "U6: Ability/How", "sentences": ["我妈妈会说汉语。", "你会做中国菜吗？", "汉字怎么写？", "中国菜很好吃。", "你会写几个汉字？"], "dialogues": [{"p": "你会说汉语吗？", "r": "我会说一点儿。"}]},
    "u7": {"title": "U7: Date/Week", "sentences": ["今天是三月二号。", "明天星期几？", "我们去学校看书。", "你几月去中国？"], "dialogues": [{"p": "今天几号？", "r": "今天2号。"}]},
    "u8": {"title": "U8: Shopping", "sentences": ["你想喝什么？", "我想喝茶。", "这个杯子多少钱？", "那个杯子十八块。"], "dialogues": [{"p": "你想吃什么？", "r": "我想吃米饭。"}]},
    "u9": {"title": "U9: Work/Location", "sentences": ["我在吃饭。", "你儿子在哪儿工作？", "小猫在椅子下面。", "这儿有大医院吗？"], "dialogues": [{"p": "你在做什么？", "r": "我在看书。"}]},
    "u10": {"title": "U10: Existence", "sentences": ["桌子上有一个电脑和两本汉语书。", "我能坐在这儿吗？", "椅子下面的书是谁的？", "在买书的那个（人）是我女儿。"], "dialogues": [{"p": "椅子下面的书是谁的？", "r": "是我的。"}]},
    "u11": {"title": "U11: Time", "sentences": ["现在十点十分。", "妈妈，我们什么时候去看电影？", "我想去北京住三天。"], "dialogues": [{"p": "现在几点？", "r": "现在三点。"}]},
    "u12": {"title": "U12: Weather", "sentences": ["明天会下雨吗？", "今天天气太热了。", "多喝热水，多吃水果。"], "dialogues": [{"p": "今天天气怎么样？", "r": "太冷了。"}]},
    "u13": {"title": "U13: Calling", "sentences": ["他在打电话呢。", "我也喜欢看电视。", "我们下午去买些水果吧。"], "dialogues": [{"p": "你在做什么呢？", "r": "我在学习。"}]},
    "u14": {"title": "U14: Things (了)", "sentences": ["她买了不少东西。", "我看见李先生了。", "这件衣服很漂亮。"], "dialogues": [{"p": "你买什么了？", "r": "我买了点儿水果。"}]},
    "u15": {"title": "U15: Emphasis (是...的)", "sentences": ["我们是两年前认识的。", "我是坐飞机回来的。", "听说你认识王先生。"], "dialogues": [{"p": "你们是怎么认识的？", "r": "我们是大学同学。"}]}
}

SCENARIO_DB = {
    "Coffee Shop": {"goal": "Order a tea and pay.", "intro": "You are at a cafe. Ask for tea and price.", "unit": "u8"},
    "Hospital": {"goal": "Find Dr. Zhang's son.", "intro": "Ask if Dr. Zhang's son works here.", "unit": "u9"},
    "University": {"goal": "Talk about where you met.", "intro": "Tell a friend you met at university.", "unit": "u15"},
    "Phone Call": {"goal": "Tell a friend what you are doing.", "intro": "Friend calls you. Answer them.", "unit": "u13"},
    "Weather Call": {"goal": "Check on parents' health.", "intro": "Ask how the weather is and their health.", "unit": "u12"}
}

# ==========================================
# 2. 界面增强与工具函数
# ==========================================
def inject_custom_css():
    st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; font-weight: bold; }
    .landing-card { padding: 20px; border-radius: 15px; background-color: #f0f2f6; text-align: center; height: 250px; }
    </style>
    """, unsafe_allow_html=True)

def clean_audio_tags(text):
    return re.sub(r'<audio[^>]*>.*?</audio>', '', text)

# ==========================================
# 3. 核心功能逻辑
# ==========================================
def main():
    inject_custom_css()
    try:
        # --- 顶部：语言选择 (右上角) ---
        col_title, col_lang = st.columns([8, 2])
        with col_lang:
            ui_lang = st.selectbox("🌐 Language", ["English", "Español", "中文"], label_visibility="collapsed")
        
        # UI 文字映射
        ui_text = {
            "English": {"home": "Home", "tutor": "Academic Master", "pal": "Fluent Pal", "quest": "Immersive Quests"},
            "Español": {"home": "Inicio", "tutor": "Maestro Académico", "pal": "Compañero Fluido", "quest": "Misiones Inmersivas"}
        }.get(ui_lang, {"home": "Home", "tutor": "Academic Master", "pal": "Fluent Pal", "quest": "Immersive Quests"})

        # 初始化状态
        if 'page' not in st.session_state: st.session_state.page = "Landing"
        if 'messages' not in st.session_state: st.session_state.messages = []
        if 'hsk_level' not in st.session_state: st.session_state.hsk_level = "HSK 1"

        # --- LANDING 页面 ---
        if st.session_state.page == "Landing":
            st.title("🎓 AI Chinese Speaking")
            st.write("### Welcome, select your learning path:")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"<div class='landing-card'><h3>👨‍🏫 {ui_text['tutor']}</h3><p>Systematic learning & strict corrections.</p></div>", unsafe_allow_html=True)
                if st.button("Enter Tutor Mode"): 
                    st.session_state.page = "Master"
                    st.rerun()
            with c2:
                st.markdown(f"<div class='landing-card'><h3>🤝 {ui_text['pal']}</h3><p>Zero-pressure chat with AI partner.</p></div>", unsafe_allow_html=True)
                if st.button("Enter Pal Mode"): 
                    st.session_state.page = "Pal"
                    st.rerun()
            with c3:
                st.markdown(f"<div class='landing-card'><h3>🗺️ {ui_text['quest']}</h3><p>Real-life missions and scenarios.</p></div>", unsafe_allow_html=True)
                if st.button("Enter Quest Mode"): 
                    st.session_state.page = "Quest"
                    st.rerun()

        # --- A. MASTER 模式 (Academic Master) ---
        elif st.session_state.page == "Master":
            st.sidebar.button("⬅️ " + ui_text["home"], on_click=lambda: st.session_state.update({"page": "Landing"}))
            st.sidebar.title(ui_text["tutor"])
            
            level = st.sidebar.radio("Level", ["HSK 1", "HSK 2-6 (Soon)"])
            unit_key = st.sidebar.selectbox("Unit", list(KNOWLEDGE_BASE.keys()), format_func=lambda x: KNOWLEDGE_BASE[x]['title'])
            
            st.title(f"Mastering {KNOWLEDGE_BASE[unit_key]['title']}")
            
            # 翻译逻辑
            target = KNOWLEDGE_BASE[unit_key]['sentences'][0] # 示例取第一句
            st.write(f"**Translate to Chinese:** {target}")
            ans = st.text_input("Input:", key="master_in")
            
            if st.button("Check"):
                # 鹰架拦截：几 + 量词
                if "几" in ans and not any(mw in ans for mw in ["个", "口", "只", "本", "岁", "块"]):
                    st.warning("⚠️ Teacher: Don't forget the Measure Word after '几'!")
                    return
                # 鹰架拦截：的 位置
                if "的" in target and ans.find("的") > ans.find("书") if "书" in ans else False:
                    st.warning("⚠️ Teacher: The description goes BEFORE '的'.")
                    return
                
                if ans == target: st.success("Perfect! Correct.")
                else: st.error(f"Try again. Standard: {target}")

        # --- B. PAL 模式 (Fluent Pal) ---
        elif st.session_state.page == "Pal":
            st.sidebar.button("⬅️ " + ui_text["home"], on_click=lambda: st.session_state.update({"page": "Landing"}))
            st.sidebar.title(ui_text["pal"])
            st.sidebar.info("Difficulty: Adaptive 🧠")
            
            st.title("Zero-Pressure Chat")
            st.write("*Your AI friend is waiting for you to start talking!*")
            
            # 模拟对话历史展示
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.write(msg["content"])
            
            chat_in = st.chat_input("Say something to your friend...")
            if chat_in:
                st.session_state.messages.append({"role": "user", "content": chat_in})
                # AI 回复逻辑：包含主动引导
                ai_res = "你今天怎么样？想去学校还是去商店？" if "你好" in chat_in else "太棒了！我也很喜欢。"
                st.session_state.messages.append({"role": "assistant", "content": ai_res})
                st.rerun()

        # --- C. QUEST 模式 (Immersive Quests) ---
        elif st.session_state.page == "Quest":
            st.sidebar.button("⬅️ " + ui_text["home"], on_click=lambda: st.session_state.update({"page": "Landing"}))
            st.sidebar.title(ui_text["quest"])
            
            st.title("Immersive Scenario Quests")
            st.write("Pick a mission and use what you've learned!")
            
            # 平铺展示卡片
            cols = st.columns(2)
            for i, (name, data) in enumerate(SCENARIO_DB.items()):
                with cols[i % 2]:
                    with st.expander(f"📍 {name}"):
                        st.write(f"**Goal:** {data['goal']}")
                        st.write(f"_{data['intro']}_")
                        if st.button(f"Start Mission: {name}", key=f"btn_{name}"):
                            st.info(f"AI (Waiter/Doctor): 您好！你想做些什么？")

    except Exception as e:
        st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
