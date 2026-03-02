import streamlit as st
import random

# ==========================================
# 1. 完整语料库 (KNOWLEDGE_BASE) - 严禁自我发挥
# 这里的每一句都直接提取自你的 PDF 课件
# ==========================================
KNOWLEDGE_BASE = {
    "u1": {"title": "Unit 1: 你好", "sentences": ["你好！", "您好！", "你们好！", "再见！"], "dialogues": [{"p": "你好！", "r": "你好！"}]},
    "u2": {"title": "Unit 2: 谢谢你", "sentences": ["谢谢！", "不客气。", "不谢。", "对不起！", "没关系。"], "dialogues": [{"p": "谢谢！", "r": "不客气。"}]},
    "u3": {"title": "Unit 3: 你叫什么名字", "sentences": ["我是老师。", "你们是学生。", "他们是西班牙人。", "我叫 Lucia。", "我不是老师。", "你是中国人吗？", "你叫什么名字？"], "dialogues": [{"p": "你叫什么名字？", "r": "我叫[学生名]。"}]},
    "u4": {"title": "Unit 4: 你是哪国人", "sentences": ["我的老师。", "你的同学。", "中国老师。", "汉语老师。", "西班牙语学生。", "他们是谁？", "你是哪国人？", "我是美国人，你呢？"], "dialogues": [{"p": "你是哪国人？", "r": "我是西班牙人。"}]},
    "u5": {"title": "Unit 5: 你今年几岁了", "sentences": ["一只狗。", "三只猫。", "四口人。", "两只狗。", "两个老师。", "你有几只狗？", "我有四只狗。", "你家有几口人？", "我家有五口人。", "你女儿几岁了？", "我女儿四岁了。", "你今年多大了？", "我三十岁了。"], "dialogues": [{"p": "你家有几口人？", "r": "我家有[数字]口人。"}]},
    "u6": {"title": "Unit 6: 我会说汉语", "sentences": ["我妈妈会说汉语。", "我不会写汉字。", "你会做中国菜吗？", "谁会说西班牙语？", "中国菜很好吃。", "汉字怎么写？", "中国菜怎么做？", "你妈妈怎么会说汉语？", "这个汉字怎么读？"], "dialogues": [{"p": "你会说汉语吗？", "r": "我会说一点儿。"}]},
    "u7": {"title": "Unit 7: 今天几月几号", "sentences": ["今天是三月二号。", "明天星期几？", "昨天几号？", "我朋友去学校。", "我们去学校看书。", "请说汉语。", "请问。", "我们明天去你家。", "你几月去中国？", "我九月去中国。"], "dialogues": [{"p": "今天几号？", "r": "今天2号。"}]},
    "u8": {"title": "Unit 8: 你想吃什么", "sentences": ["你想喝什么？", "我想喝茶。", "你想吃什么？", "我想吃米饭。", "下午我想去商店。", "你想买什么？", "我想买一个杯子。", "这个杯子多少钱？", "那个杯子十八块。", "你们学校有多少个学生？"], "dialogues": [{"p": "你想吃什么？", "r": "我想吃米饭。"}]},
    "u9": {"title": "Unit 9: 你在哪儿工作", "sentences": ["我在吃饭。", "你在做什么？", "你儿子在哪儿工作？", "我儿子在医院工作。", "你爸爸在这家医院工作？", "你的小猫在哪儿？", "我的小猫在那儿。", "小猫在椅子下面。", "这儿有大医院吗？"], "dialogues": [{"p": "他在做什么？", "r": "他在学习。"}]},
    "u10": {"title": "Unit 10: 桌子上有什么", "sentences": ["桌子上有一个电脑和两本汉语书。", "我能坐在这儿吗？", "请你坐在她后面。", "这个学校后面没有大商店。", "椅子下面的书是谁的？", "在买书的那个（人）是我女儿。", "她是你说的那个人吗？"], "dialogues": [{"p": "椅子下面的书是谁的？", "r": "是我的。"}]},
    "u11": {"title": "Unit 11: 现在几点", "sentences": ["现在十点十分。", "女儿今天几点回家？", "妈妈，我们什么时候去看电影？", "你这个星期一前能回家吗？", "回家前，我想去看一个电影。", "我想去北京住三天。", "我女儿吃饭前想读三十分钟书。"], "dialogues": [{"p": "现在几点？", "r": "现在三点。"}]},
    "u12": {"title": "Unit 12: 明天天气怎么样", "sentences": ["北京的天气怎么样？", "你妈妈做的饭太好吃了。", "这本书不太好看。", "这些水果太好吃了。", "我想喝一些中国茶。", "明天会下雨吗？", "明天李小姐会来吗？", "多喝热水，多吃米饭。"], "dialogues": [{"p": "今天天气怎么样？", "r": "太冷了。"}]},
    "u13": {"title": "Unit 13: 她在打电话呢", "sentences": ["我喜欢在家看电视。", "你在做什么呢？", "她在和朋友们喝茶。", "我们下午去商店买些水果吧！", "你明天来我家吧！", "我想给你这本书。", "你在给谁打电话？"], "dialogues": [{"p": "你在做什么呢？", "r": "我在学习。"}]},
    "u14": {"title": "Unit 14: 她买了不少东西", "sentences": ["她买了不少东西。", "我昨天看见李老师了。", "我今天买了不少水果。", "我给她买了一件漂亮的衣服。", "我去商店了，但是没买水果。", "我今天想学二十分钟汉语。"], "dialogues": [{"p": "你买什么了？", "r": "我买了点儿水果。"}]},
    "u15": {"title": "Unit 15: 我是坐飞机来的", "sentences": ["听说你认识王先生。", "我坐出租车去他家。", "我们是两年前认识的。", "我们是在大学认识的。", "我在火车上看见他的。", "我是和朋友们一起坐飞机回来的。", "这本书不是在这家书店买的。"], "dialogues": [{"p": "你们怎么认识的？", "r": "我们是大学同学。"}]}
}

# ==========================================
# 2. 核心教学逻辑引擎
# ==========================================
def main():
    try:
        st.set_page_config(page_title="PREDC1 HSK Tutor", layout="centered")
        st.title("HSK 1 Web Version - Original Reproduction")

        if 'unit' not in st.session_state: st.session_state.unit = "u1"
        if 'count' not in st.session_state: st.session_state.count = 0
        if 'mode' not in st.session_state: st.session_state.mode = "translation"

        # 单元选择
        st.session_state.unit = st.sidebar.selectbox("选择单元", list(KNOWLEDGE_BASE.keys()), 
                                                     format_func=lambda x: KNOWLEDGE_BASE[x]['title'])
        
        unit_data = KNOWLEDGE_BASE[st.session_state.unit]

        # 1. 翻译挑战环节 (必须完成10句或该单元全部句子)
        if st.session_state.mode == "translation":
            target_list = unit_data['sentences']
            idx = st.session_state.count % len(target_list)
            target = target_list[idx]

            st.info(f"进度: {st.session_state.count + 1} / 10")
            st.subheader(f"请翻译: {target}")
            
            user_input = st.text_input("请输入中文:", key=f"input_{st.session_state.count}")

            if st.button("提交答案"):
                # --- 鹰架拦截逻辑 1: 几 + 量词 ---
                if "几" in user_input:
                    mws = ["个", "口", "只", "本", "岁", "块"]
                    if not any(mw in user_input.split("几")[1][:2] for mw in mws if "几" in user_input):
                        st.warning("⚠️ 提醒：使用'几'询问数量时，不要忘记使用量词（如：个、只、口等）！")
                        return

                # --- 鹰架拦截逻辑 2: 的 的位置 (定语位置纠偏) ---
                # 针对 U9/U10 位置描述逻辑：[地点] + 的 + [名词]
                if any(pos in target for pos in ["上", "下", "前", "后", "里"]) and "的" in target:
                    # 检查名词是否错位（例如学生写：书在桌子上）
                    key_nouns = ["书", "水果", "电脑", "猫", "狗"]
                    for noun in key_nouns:
                        if noun in user_input and "的" in user_input:
                            if user_input.find(noun) < user_input.find("的"):
                                st.warning("⚠️ 注意：中文的描述语（位置/所属）要放在名词前面。公式：[描述语] + 的 + [名词]。")
                                return

                # 精准匹配校验
                if user_input.strip() == target:
                    st.success("正确！")
                    st.session_state.count += 1
                    if st.session_state.count >= 10:
                        st.session_state.mode = "dialogue"
                    st.rerun()
                else:
                    st.error(f"课件标准答案是: {target}")

        # 2. 情景对话环节 (翻译达标后触发)
        else:
            st.balloons()
            st.success("翻译环节完成！现在进行随机情景对话测试。")
            pair = random.choice(unit_data['dialogues'])
            st.subheader(f"AI 问: {pair['p']}")
            st.text_input("你如何回答？", key="dialogue_ans")
            
            if st.button("完成单元"):
                st.session_state.count = 0
                st.session_state.mode = "translation"
                st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")

if __name__ == "__main__":
    main()
