import streamlit as st
import os
import google.generativeai as genai

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="Long Wen - HSK1 Smart Tutor",
    page_icon="🐲",
    layout="wide"
)

# --- 2. API Key ---
api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    st.error("⚠️ Error: API Key not found.")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 📚 核心知识库 (HSK1 Unit 1-15)
# ==========================================
# 这里融合了 PDF 的生词表和 DOCX 的纠错规则
KNOWLEDGE_BASE = {
    "Unit 1: Hello (你好)": {
        "grammar": """
        1. **Pinyin & Tones**: Focus on distinguishing tones (mā, má, mǎ, mà).
        2. **Basic Greetings**: 
           - 你好 (Nǐ hǎo) - Hello.
           - 您好 (Nín hǎo) - Respectful form.
        3. **Iron Law (Unit 1)**: Do not teach complex sentences. Stick to "Nǐ hǎo", "Nǐ hǎo ma", "Hěn hǎo".
        """,
        "vocab": "你(nǐ), 好(hǎo), 您(nín), 你们(nǐmen), 对不起(duìbuqǐ), 没关系(méiguānxi)"
    },
    
    "Unit 2: What is your name? (你叫什么名字)": {
        "grammar": """
        1. **Question Word '什么' (What)**: 
           - Structure: Subj + Verb + 什么 (+ Noun)? 
           - (你叫什么名字?)
        2. **Verb '是' (To be)**: 
           - I am teacher = 我是老师. (No 'am/is/are' variations).
        3. **Particle '吗' (Yes/No)**: 
           - Added at the end of a statement. (你是中国人吗?)
        4. **Iron Law (Unit 2)**: 
           - NEVER use '吗' with '什么'. (Wrong: 你叫什么名字吗?)
           - '是' connects Nouns, NOT Adjectives. (Wrong: 我是高兴).
        """,
        "vocab": "叫(jiào), 什么(shénme), 名字(míngzi), 我(wǒ), 是(shì), 老师(lǎoshī), 吗(ma), 学生(xuésheng), 人(rén)"
    },

    "Unit 3: I have 3 books (我有三本书)": {
        "grammar": """
        1. **Numbers 0-10**: yī, èr, sān...
        2. **'有' (To have)**: 
           - Negation is '没有' (méiyǒu), NOT '不有'.
        3. **Measure Word '个' & '口'**: 
           - Number + Measure Word + Noun. (三个人, 五口人).
        4. **Iron Law (Unit 3)**: 
           - Distinction between '二' (èr - counting) and '两' (liǎng - quantity before measure words). 
           - Use '两' for '2' when counting people/things (两个人).
        """,
        "vocab": "有(yǒu), 个(gè), 爸爸(bàba), 妈妈(māma), 哥哥(gēge), 弟弟(dìdi), 妹妹(mèimei), 和(hé), 没(méi)"
    },

    "Unit 4: She is my teacher (她是我的老师)": {
        "grammar": """
        1. **Pronouns**: 他 (He), 她 (She), 它 (It).
        2. **Particle '的' (Possession)**: 
           - My book = 我的书. 
           - *Note*: For close family/relationships, '的' can be omitted (我妈妈).
        3. **Questions '谁' (Who)**: 
           - 他是谁? (Who is he?).
           - 谁是李月? (Who is Li Yue?).
        """,
        "vocab": "他(tā), 她(tā), 谁(shéi), 的(de), 汉语(Hànyǔ), 哪(nǎ), 国(guó), 呢(ne), 同学(tóngxué), 朋友(péngyou)"
    },

    "Unit 5: Her daughter is 20 (她女儿今年二十岁)": {
        "grammar": """
        1. **Numbers 11-99**: 十一 (11), 二十 (20), 九十九 (99).
        2. **Question '几' vs '多少'**:
           - 几 (jǐ): For small numbers (<10). Structure: 几 + Measure Word? (几个人?)
           - 多少 (duōshao): For any number. No Measure Word needed usually. (多少人?)
        3. **Iron Law (Unit 5)**: 
           - '几' MUST be followed by a Measure Word (口/个/岁). 
           - '多大' is for age (你多大?).
        """,
        "vocab": "几(jǐ), 岁(suì), 了(le), 今年(jīnnián), 多(duō), 大(dà)"
    },

    "Unit 6: Can speak Chinese (我会说汉语)": {
        "grammar": """
        1. **Modal Verb '会' (Can/Skill)**: 
           - Learned skill. (我会写汉字).
        2. **Sentences with Verb+Object**: 
           - 妈妈做菜 (Mom cooks food).
        3. **Question '怎么' (How to do)**: 
           - 怎么 + Verb? (怎么读? How to read?).
        4. **Iron Law (Unit 6)**: 
           - '怎么' asks about process/method.
        """,
        "vocab": "会(huì), 说(shuō), 菜(cài), 很(hěn), 好吃(hǎochī), 做(zuò), 写(xiě), 汉字(Hànzì), 字(zì), 怎么(zěnme), 读(dú)"
    },

    "Unit 7: What is the date? (今天几号)": {
        "grammar": """
        1. **Dates**: Month + Date + Day of week. 
           - (九月一号星期三).
        2. **Sentence with Nominal Predicate**: 
           - 明天星期六 (Tomorrow is Saturday) - No '是' needed.
        3. **Question '去' (Go)**:
           - 去 + Place + (to do sth).
           - (我去学校看书).
        """,
        "vocab": "请(qǐng), 问(wèn), 今天(jīntiān), 号(hào), 月(yuè), 星期(xīngqī), 昨天(zuótiān), 明天(míngtiān), 去(qù), 学校(xuéxiào), 看(kàn), 书(shū)"
    },

    "Unit 8: I want to drink tea (我想喝茶)": {
        "grammar": """
        1. **Modal Verb '想' (Want/Would like)**: 
           - Subject + 想 + Verb. (我想买东西).
        2. **Question '多少钱' (How much money)**: 
           - 这个杯子多少钱?
        3. **Measure Words**: 个(general), 口(family), 本(book).
        """,
        "vocab": "想(xiǎng), 喝(hē), 茶(chá), 吃(chī), 米饭(mǐfàn), 下午(xiàwǔ), 商店(shāngdiàn), 买(mǎi), 个(gè), 杯子(bēizi), 这(zhè), 多少(duōshao), 钱(qián), 块(kuài), 那(nà)"
    },

    "Unit 9: Where is the cat? (小猫在哪儿)": {
        "grammar": """
        1. **Verb '在' (To be at/in/on)**: 
           - Subject + 在 + Place/Location. (猫在椅子下面).
        2. **Location Words**: 上(up), 下(down), 里(inside). 
           - Use AFTER the noun (桌子里 inside table).
        3. **Iron Law (Unit 9)**: 
           - Word Order: Place word comes BEFORE the action if used as a modifier.
           - "在" indicates location existence.
        """,
        "vocab": "小(xiǎo), 猫(māo), 在(zài), 那儿(nàr), 狗(gǒu), 椅子(yǐzi), 下面(xiàmian), 在(zài-preposition), 哪儿(nǎr), 工作(gōngzuò), 儿子(érzi), 医院(yīyuàn), 医生(yīshēng), 爸爸(bàba)"
    },
    
    "Unit 10: Can I sit here? (我能坐这儿吗)": {
        "grammar": """
        1. **'有' (Existential - There be)**: 
           - Place + 有 + Object. (桌子上有一个杯子).
        2. **Modal Verb '能' (Can/Permission)**: 
           - 我能坐这儿吗? (Can/May I sit here?).
        3. **Imperative '请' (Please)**: 请坐 (Please sit).
        """,
        "vocab": "桌子(zhuōzi), 上(shang), 电脑(diànnǎo), 和(hé), 本(běn), 里(li), 前面(qiánmiàn), 后面(hòumiàn), 这儿(zhèr), 没有(méiyǒu), 能(néng), 坐(zuò)"
    },
    
    "Unit 11: Time & Duration (现在几点)": {
        "grammar": """
        1. **Time Expression**: ...前 (Before...). (三天前).
        2. **Time Telling**: 点 (o'clock), 分 (minute). 
           - 10:10 = 十点十分.
        3. **Iron Law (Unit 11)**: 
           - '分' (minute) is for clock time.
           - For duration, use '分钟' (minutes).
        """,
        "vocab": "现在(xiànzài), 点(diǎn), 分(fēn), 中午(zhōngwǔ), 吃饭(chīfàn), 时候(shíhou), 回(huí), 我们(wǒmen), 电影(diànyǐng), 住(zhù), 前(qián)"
    },
    
    "Unit 12: Weather (明天天气怎么样)": {
        "grammar": """
        1. **Subject-Predicate Predicate**: 
           - 明天天气很好 (Tomorrow weather is good).
        2. **'怎么' vs '怎么样'**: 
           - 怎么样 asks about condition/quality (How is it?).
        3. **'太...了' (Too...)**: 
           - 太热了 (Too hot).
        4. **Modal Verb '会' (Future Possibility)**: 
           - 明天会下雨吗? (Will it rain tomorrow?).
        """,
        "vocab": "天气(tiānqì), 怎么样(zěnmeyàng), 太(tài), 太...了(tài...le), 热(rè), 冷(lěng), 下雨(xià yǔ), 下(xià), 雨(yǔ), 小姐(xiǎojiě), 来(lái), 身体(shēntǐ), 爱(ài), 些(xiē), 水果(shuǐguǒ), 水(shuǐ)"
    },
    
    "Unit 13: Learning to Cook (他在学做中国菜呢)": {
        "grammar": """
        1. **Interjection '喂'**: Hello (on phone).
        2. **Particle '呢' (Ongoing Action)**: 
           - 他睡觉呢 (He is sleeping).
           - 在...呢 (Subject + 在 + Verb + 呢).
        3. **Phone Numbers**: Read digit by digit. '1' is often read as 'yāo'.
        """,
        "vocab": "喂(wèi), 也(yě), 学习(xuéxí), 上午(shàngwǔ), 睡觉(shuìjiào), 电视(diànshì), 喜欢(xǐhuan), 给(gěi), 打电话(dǎ diànhuà), 吧(ba)"
    },
    
    "Unit 14: She bought clothes (她买了不少衣服)": {
        "grammar": """
        1. **'了' (Completion)**: 
           - Only for COMPLETED actions, not just 'past time'.
           - 我买了一个苹果 (I bought an apple).
        2. **'后' (After)**: 
           - Time/Event + 后. (五点后, 吃饭后).
        3. **'都是' (All are)**: 
           - 我们都是学生.
        """,
        "vocab": "东西(dōngxi), 一点儿(yīdiǎnr), 苹果(píngguǒ), 看见(kànjiàn), 先生(xiānsheng), 开(kāi), 车(chē), 回来(huílái), 分钟(fēnzhōng), 后(hòu), 张(zhāng), 衣服(yīfu), 漂亮(piàoliang), 啊(a), 少(shǎo), 不少(bùshǎo), 这些(zhèxiē), 都(dōu)"
    },
    
    "Unit 15: I came by plane (我是坐飞机来的)": {
        "grammar": """
        1. **'是...的' Construction**: 
           - Used to emphasize distinct details (time, place, manner) of a PAST event.
           - 我是昨天来的 (It was yesterday that I came).
           - 我是坐飞机来的 (It was by plane that I came).
        2. **Iron Law (Unit 15)**: 
           - Do not use '了' inside '是...的' sentences usually.
        """,
        "vocab": "认识(rènshi), 年(nián), 大学(dàxué), 饭店(fàndiàn), 出租车(chūzūchē), 一起(yīqǐ), 高兴(gāoxìng), 听(tīng), 飞机(fēijī)"
    }
}

# --- 3. 侧边栏 (Sidebar) ---
with st.sidebar:
    st.image("https://img.icons8.com/color/96/dragon.png", width=60)
    st.title("🐲 龙文 HSK1")
    st.markdown("---")
    
    # 模式选择 (Role Selection)
    role_mode = st.radio(
        "🎭 选择模式 / Select Mode:",
        ["🧑‍🏫 严厉老师 (Teacher)", "🧑‍🤝‍🧑 中国朋友 (Friend)"]
    )

    st.markdown("---")

    # 单元选择器
    selected_unit_name = st.selectbox(
        "📖 选择单元 / Select Unit:",
        options=list(KNOWLEDGE_BASE.keys()), 
        index=0
    )
    
    # 动态显示当前规则
    st.caption(f"当前焦点: {selected_unit_name}")
    with st.expander("查看当前语法规则 / View Rules"):
        st.markdown(KNOWLEDGE_BASE[selected_unit_name]['grammar'])

    # 切换清理逻辑
    if "last_config" not in st.session_state:
        st.session_state.last_config = f"{selected_unit_name}_{role_mode}"
    
    if st.session_state.last_config != f"{selected_unit_name}_{role_mode}":
        st.session_state.messages = []
        st.session_state.last_config = f"{selected_unit_name}_{role_mode}"
        st.rerun()

# --- 4. 动态构建 AI 大脑 (System Prompt) ---
current_unit_data = KNOWLEDGE_BASE[selected_unit_name]

# 基础人设
if "Teacher" in role_mode:
    ROLE_PROMPT = """
    **ROLE**: You are a STRICT Grammar Teacher. 
    **GOAL**: Correct every mistake. Explain grammar rules clearly. 
    **TONE**: Professional, educational, encouraging but precise.
    **ACTION**: After explaining, ALWAYS set a translation challenge.
    """
else:
    ROLE_PROMPT = """
    **ROLE**: You are a SUPPORTIVE Chinese Friend (HSK1-2 Level).
    **GOAL**: Chat naturally. Do NOT correct minor mistakes unless communication fails. Build confidence.
    **TONE**: Friendly, casual, uses Emojis (😊, 👍). 
    **ACTION**: Ask follow-up questions to keep the chat going. Keep sentences SIMPLE.
    """

SYSTEM_PROMPT = f"""
{ROLE_PROMPT}

### 🌍 LANGUAGE PROTOCOL
- User English -> Reply English.
- User Spanish -> Reply Spanish.
- User Chinese -> Reply Chinese (with Pinyin if in Friend mode).

### 📚 KNOWLEDGE BASE FOR {selected_unit_name}
{current_unit_data['grammar']}

### 📝 VOCABULARY RESTRICTION
- STRICTLY use words from HSK1 Units 1-{selected_unit_name.split(':')[0].replace('Unit ', '')}.
- Target Vocab: {current_unit_data['vocab']}
- **NO PAST TENSE MARKERS (了/过)** unless explicitly allowed in Unit 14/15.

### 🛑 CRITICAL IRON LAWS (DO NOT BREAK)
1. **Unit 1-9 Constraints**:
   - Don't use 'ma' with Question Words (Shenme, Nar).
   - 'Zai' + Place goes BEFORE the verb (Zai xuexiao kanshu).
   - Use 'Liang' for '2' when counting.
2. **Separable Verbs (Unit 11)**: Time goes in middle (Shui jiao).
"""

# --- 5. 模型初始化 ---
try:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash", 
        system_instruction=SYSTEM_PROMPT
    )
except Exception as e:
    st.error(f"Model config error: {e}")
    st.stop()

# --- 6. 聊天主界面 ---
st.header(f"🐲 {selected_unit_name}")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if not st.session_state.messages:
    welcome_msg = "同学们好！我们开始上课吧。" if "Teacher" in role_mode else "你好！很高兴见到你！👋"
    st.info(welcome_msg)

if prompt := st.chat_input("Type your answer here..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            chat = model.start_chat(history=[
                {"role": m["role"], "parts": [m["content"]]} 
                for m in st.session_state.messages[:-1]
            ])
            
            response = chat.send_message(prompt)
            message_placeholder.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
            
        except Exception as e:
            st.error(f"Connection Error: {e}")
